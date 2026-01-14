from __future__ import annotations

from collections.abc import AsyncIterator, Generator

import httpx
import pytest
import respx

from app.dependencies import get_weather_service
from app.integrations.open_meteo import OpenMeteoClient
from app.integrations.open_meteo_provider import OpenMeteoProvider
from app.main import app
from app.repositories.cache import AsyncCacheRepository
from app.services.weather_service import WeatherService


@pytest.fixture(autouse=True)
def _clear_dependency_overrides() -> Generator[None, None, None]:
    """
    Ensure dependency overrides are cleared even if a test fails.
    Prevents cascading failures across the test suite.
    """
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def asgi_client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _override_weather_service() -> None:
    cache = AsyncCacheRepository()
    provider = OpenMeteoProvider(OpenMeteoClient())
    service = WeatherService(cache=cache, provider=provider, ttl_seconds=300.0)
    app.dependency_overrides[get_weather_service] = lambda: service


@pytest.mark.asyncio
async def test_weather_cache_behavior_respx_mocks_open_meteo_calls(
    asgi_client: httpx.AsyncClient,
) -> None:
    _override_weather_service()

    with respx.mock(assert_all_called=True) as rsps:
        geocoding_route = rsps.get(
            "https://geocoding-api.open-meteo.com/v1/search"
        ).respond(
            200,
            json={"results": [{"latitude": 32.0625, "longitude": 34.8125}]},
        )
        forecast_route = rsps.get("https://api.open-meteo.com/v1/forecast").respond(
            200,
            json={
                "latitude": 32.0625,
                "longitude": 34.8125,
                "timezone": "Asia/Jerusalem",
                "current": {
                    "time": "2026-01-14T14:00",
                    "interval": 900,
                    "temperature_2m": 16.8,
                    "relative_humidity_2m": 48,
                    "weather_code": 2,
                },
            },
        )

        r1 = await asgi_client.get("/weather", params={"city": "  Tel Aviv  "})
        assert r1.status_code == 200
        body1 = r1.json()
        assert body1["cache_hit"] is False
        assert body1["city"] == "tel aviv"
        assert body1["data"]["current"]["temperature_2m"] == 16.8
        assert geocoding_route.call_count == 1
        assert forecast_route.call_count == 1

        r2 = await asgi_client.get("/weather", params={"city": "Tel Aviv"})
        assert r2.status_code == 200
        body2 = r2.json()
        assert body2["cache_hit"] is True
        assert body2["data"]["current"]["temperature_2m"] == 16.8

        # Ensure no additional upstream calls on cache hit.
        assert geocoding_route.call_count == 1
        assert forecast_route.call_count == 1


@pytest.mark.asyncio
async def test_weather_missing_city_param_returns_validation_error(
    asgi_client: httpx.AsyncClient,
) -> None:
    r = await asgi_client.get("/weather")

    # Depending on your RequestValidationError handler, this can be 400 (custom)
    # or 422 (FastAPI default). The important part is consistency.
    assert r.status_code in (400, 422)

    if r.status_code == 400:
        body = r.json()
        assert "error" in body
        assert body["error"]["code"] == "validation_error"
        assert isinstance(body["error"]["message"], str)
        assert body["error"]["status_code"] == 400


@pytest.mark.asyncio
async def test_weather_city_not_found_returns_error_envelope(
    asgi_client: httpx.AsyncClient,
) -> None:
    _override_weather_service()

    with respx.mock(assert_all_called=True) as rsps:
        rsps.get("https://geocoding-api.open-meteo.com/v1/search").respond(
            200, json={"results": []}
        )

        r = await asgi_client.get("/weather", params={"city": "NoSuchCity"})
        assert r.status_code == 404

        body = r.json()
        assert "error" in body
        assert body["error"]["code"] == "not_found"
        assert isinstance(body["error"]["message"], str)
        assert body["error"]["status_code"] == 404


@pytest.mark.asyncio
async def test_weather_upstream_error_returns_error_envelope(
    asgi_client: httpx.AsyncClient,
) -> None:
    """
    Use a forecast 4xx scenario to avoid retries/backoff sleeps.
    In OpenMeteoClient._fetch_forecast, 4xx raises UpstreamError(retryable=False,
    status_code=502).
    """
    _override_weather_service()

    with respx.mock(assert_all_called=True) as rsps:
        rsps.get("https://geocoding-api.open-meteo.com/v1/search").respond(
            200,
            json={"results": [{"latitude": 32.0625, "longitude": 34.8125}]},
        )
        rsps.get("https://api.open-meteo.com/v1/forecast").respond(
            400,
            json={"error": "bad request"},
        )

        r = await asgi_client.get("/weather", params={"city": "London"})
        assert r.status_code == 502

        body = r.json()
        assert "error" in body
        assert body["error"]["code"] == "upstream_error"
        assert isinstance(body["error"]["message"], str)
        assert body["error"]["status_code"] == 502
