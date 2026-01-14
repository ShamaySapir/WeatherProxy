"""Open-Meteo weather API client with retry and circuit breaker."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

import httpx
from tenacity import RetryError, retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.errors import (
    CircuitBreakerOpenError,
    NotFoundError,
    UpstreamError,
    UpstreamTimeoutError,
)

logger = logging.getLogger(__name__)

OPEN_METEO_FORECAST_BASE_URL = "https://api.open-meteo.com/v1"
OPEN_METEO_GEOCODING_BASE_URL = "https://geocoding-api.open-meteo.com/v1/search"

T = TypeVar("T")


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, UpstreamError):
        return exc.retryable
    return isinstance(exc, (UpstreamTimeoutError, httpx.RequestError))


def _unwrap_retry_error(exc: BaseException) -> BaseException:
    if isinstance(exc, RetryError):
        inner = exc.last_attempt.exception()
        return inner if inner is not None else exc
    return exc

@dataclass
class AsyncCircuitBreaker:
    """
    Minimal async-safe circuit breaker.

    - Opens after `fail_max` consecutive failures.
    - While open, rejects calls for `reset_timeout` seconds.
    - After timeout, allows calls again; a success closes it, a failure opens it.
    """
    fail_max: int
    reset_timeout: float  # seconds

    failure_count: int = 0
    opened_at: float | None = None

    def _is_open(self) -> bool:
        if self.opened_at is None:
            return False
        return (time.monotonic() - self.opened_at) < self.reset_timeout

    def _record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None

    def _record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.fail_max:
            self.opened_at = time.monotonic()

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        if self._is_open():
            raise CircuitBreakerOpenError("Upstream service unavailable (circuit open)")

        try:
            result = await func(*args, **kwargs)
        except Exception:
            self._record_failure()
            raise
        else:
            self._record_success()
            return result


class OpenMeteoClient:
    """Async client for Open-Meteo weather API with retry + circuit breaker."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.timeout = httpx.Timeout(self.settings.upstream_timeout_seconds)
        self.circuit_breaker = AsyncCircuitBreaker(
            fail_max=5,
            reset_timeout=10,
        )

    async def fetch_weather(self, city: str) -> dict[str, Any]:
        try:
            lat, lon = await self._fetch_geocoding(city)
        except RetryError as e:
            raise _unwrap_retry_error(e) from e

        try:
            return await self._fetch_forecast(lat, lon)
        except RetryError as e:
            raise _unwrap_retry_error(e) from e

    @retry(
        retry=retry_if_exception(_should_retry),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _fetch_geocoding(self, city: str) -> tuple[float, float]:
        url = f"{OPEN_METEO_GEOCODING_BASE_URL}"
        params = {"name": city, "count": 1, "language": "en", "format": "json"}

        try:
            start_time = time.perf_counter()
            async with httpx.AsyncClient() as client:
                response = await self.circuit_breaker.call(
                    self._call_with_timeout, client, "GET", url, params
                )
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "geocoding_request_completed",
                extra={
                    "request_id": "-",
                    "city": city,
                    "upstream_status_code": response.status_code,
                    "upstream_duration_ms": duration_ms,
                },
            )

            if response.status_code == 200:
                data = response.json()
                if not data.get("results"):
                    raise NotFoundError(f"City '{city}' not found")
                result = data["results"][0]
                return float(result["latitude"]), float(result["longitude"])

            if 400 <= response.status_code < 500:
                raise NotFoundError(f"City '{city}' not found")

            if response.status_code >= 500:
                raise UpstreamError(
                    f"Upstream geocoding error (status {response.status_code})",
                    status_code=response.status_code,
                )

            raise UpstreamError(
                "Upstream error during geocoding",
                status_code=502,
                details={"upstream_status_code": response.status_code},
            )

        except httpx.TimeoutException as e:
            logger.error("geocoding_timeout", extra={"request_id": "-", "city": city})
            raise UpstreamTimeoutError("Upstream geocoding service timeout") from e

        except (NotFoundError, UpstreamTimeoutError, CircuitBreakerOpenError):
            raise

        except httpx.RequestError as e:
            logger.error("geocoding_request_error", extra={"request_id": "-", "city": city})
            raise UpstreamError("Upstream geocoding service error") from e

    @retry(
        retry=retry_if_exception(_should_retry),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _fetch_forecast(self, lat: float, lon: float) -> dict[str, Any]:
        url = f"{OPEN_METEO_FORECAST_BASE_URL}/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code",
            "timezone": "auto",
        }

        try:
            start_time = time.perf_counter()
            async with httpx.AsyncClient() as client:
                response = await self.circuit_breaker.call(
                    self._call_with_timeout, client, "GET", url, params
                )
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "forecast_request_completed",
                extra={
                    "request_id": "-",
                    "latitude": lat,
                    "longitude": lon,
                    "upstream_status_code": response.status_code,
                    "upstream_duration_ms": duration_ms,
                },
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code >= 500:
                raise UpstreamError(
                    f"Upstream forecast error (status {response.status_code})",
                    status_code=response.status_code,
                )

            if 400 <= response.status_code < 500:
                raise UpstreamError(
                    "Upstream forecast service returned client error",
                    status_code=502,
                    details={"upstream_status_code": response.status_code},
                    retryable=False,
                )

            raise UpstreamError(
                "Upstream error during forecast fetch",
                status_code=502,
                details={"upstream_status_code": response.status_code},
            )

        except httpx.TimeoutException as e:
            logger.error(
                "forecast_timeout",
                extra={"request_id": "-", "latitude": lat, "longitude": lon},
            )
            raise UpstreamTimeoutError("Upstream forecast service timeout") from e

        except (UpstreamTimeoutError, CircuitBreakerOpenError):
            raise

        except httpx.RequestError as e:
            logger.error(
                "forecast_request_error",
                extra={"request_id": "-", "latitude": lat, "longitude": lon},
            )
            raise UpstreamError("Upstream forecast service error") from e

    async def _call_with_timeout(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        params: dict[str, Any],
    ) -> httpx.Response:
        return await client.request(method, url, params=params, timeout=self.timeout)
