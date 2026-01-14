"""Tests for OpenMeteoClient."""

from __future__ import annotations

import pytest
import respx
from httpx import ConnectError, Response, TimeoutException

from app.core.errors import (
    NotFoundError,
    UpstreamError,
    UpstreamTimeoutError,
)
from app.integrations import OpenMeteoClient


@pytest.fixture
def client() -> OpenMeteoClient:
    """Provide a fresh OpenMeteoClient instance for each test."""
    return OpenMeteoClient()


@pytest.mark.asyncio
async def test_fetch_weather_successful(client: OpenMeteoClient) -> None:
    """Test successful weather fetch with geocoding + forecast."""
    with respx.mock:
        # Mock geocoding endpoint
        respx.get("https://api.open-meteo.com/v1/geocoding").mock(
            return_value=Response(
                200,
                json={
                    "results": [
                        {
                            "latitude": 40.7128,
                            "longitude": -74.0060,
                            "name": "New York",
                        }
                    ]
                },
            )
        )

        # Mock forecast endpoint
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(
                200,
                json={
                    "current": {
                        "temperature_2m": 15.0,
                        "relative_humidity_2m": 65,
                        "weather_code": 0,
                    }
                },
            )
        )

        result = await client.fetch_weather("New York")

        assert result["current"]["temperature_2m"] == 15.0
        assert result["current"]["relative_humidity_2m"] == 65


@pytest.mark.asyncio
async def test_fetch_weather_invalid_city(client: OpenMeteoClient) -> None:
    """Test that invalid city raises NotFoundError."""
    with respx.mock:
        # Mock geocoding endpoint with empty results
        respx.get("https://api.open-meteo.com/v1/geocoding").mock(
            return_value=Response(200, json={"results": []})
        )

        with pytest.raises(NotFoundError):
            await client.fetch_weather("InvalidCityXYZ")


@pytest.mark.asyncio
async def test_fetch_weather_timeout(client: OpenMeteoClient) -> None:
    """Test that timeout raises UpstreamTimeoutError."""
    with respx.mock:
        # Mock geocoding endpoint to timeout
        respx.get("https://api.open-meteo.com/v1/geocoding").mock(
            side_effect=TimeoutException("Request timed out")
        )

        with pytest.raises(UpstreamTimeoutError):
            await client.fetch_weather("New York")


@pytest.mark.asyncio
async def test_fetch_weather_connection_error(client: OpenMeteoClient) -> None:
    """Test that connection error raises UpstreamError."""
    with respx.mock:
        # Mock geocoding endpoint with connection error
        respx.get("https://api.open-meteo.com/v1/geocoding").mock(
            side_effect=ConnectError("Connection refused")
        )

        with pytest.raises(UpstreamError):
            await client.fetch_weather("New York")


@pytest.mark.asyncio
async def test_fetch_weather_5xx_eventual_success(
    client: OpenMeteoClient,
) -> None:
    """Test retry on 5xx: eventually succeeds after retries."""
    with respx.mock:
        # First call: 502, second call: 502, third call: success
        geocoding_mock = respx.get("https://api.open-meteo.com/v1/geocoding")
        geocoding_mock.side_effect = [
            Response(502),
            Response(502),
            Response(
                200,
                json={
                    "results": [
                        {
                            "latitude": 40.7128,
                            "longitude": -74.0060,
                            "name": "New York",
                        }
                    ]
                },
            ),
        ]

        forecast_mock = respx.get("https://api.open-meteo.com/v1/forecast")
        forecast_mock.mock(
            return_value=Response(
                200,
                json={
                    "current": {
                        "temperature_2m": 15.0,
                        "relative_humidity_2m": 65,
                        "weather_code": 0,
                    }
                },
            )
        )

        result = await client.fetch_weather("New York")

        assert result["current"]["temperature_2m"] == 15.0
        # Verify we made 3 geocoding calls
        assert geocoding_mock.calls.call_count == 3


@pytest.mark.asyncio
async def test_fetch_weather_5xx_eventual_failure(
    client: OpenMeteoClient,
) -> None:
    """Test retry on 5xx: fails after max retries exhausted."""
    with respx.mock:
        # All calls return 502
        geocoding_mock = respx.get("https://api.open-meteo.com/v1/geocoding")
        geocoding_mock.mock(return_value=Response(502))

        with pytest.raises(UpstreamError):
            await client.fetch_weather("New York")

        # Verify we made 3 geocoding calls (max retries)
        assert geocoding_mock.calls.call_count == 3


@pytest.mark.asyncio
async def test_fetch_weather_4xx_no_retry(client: OpenMeteoClient) -> None:
    """Test that 4xx errors are not retried."""
    with respx.mock:
        # Geocoding returns 404
        geocoding_mock = respx.get("https://api.open-meteo.com/v1/geocoding")
        geocoding_mock.mock(return_value=Response(404))

        with pytest.raises(NotFoundError):
            await client.fetch_weather("InvalidCity")

        # Verify we made only 1 call (no retries for 4xx)
        assert geocoding_mock.calls.call_count == 1


@pytest.mark.asyncio
async def test_fetch_weather_forecast_4xx_no_retry(
    client: OpenMeteoClient,
) -> None:
    """Test that 4xx errors in forecast are not retried and
    502 is returned to client."""
    with respx.mock:
        # Mock successful geocoding
        respx.get("https://api.open-meteo.com/v1/geocoding").mock(
            return_value=Response(
                200,
                json={
                    "results": [
                        {
                            "latitude": 40.7128,
                            "longitude": -74.0060,
                            "name": "New York",
                        }
                    ]
                },
            )
        )

        # Forecast returns 403 (client error)
        forecast_mock = respx.get("https://api.open-meteo.com/v1/forecast")
        forecast_mock.mock(return_value=Response(403))

        with pytest.raises(UpstreamError) as exc_info:
            await client.fetch_weather("New York")

        # Verify that UpstreamError has 502 status (not leaked 403)
        assert exc_info.value.status_code == 502

        # Verify upstream status is stored in details for debugging
        assert exc_info.value.details is not None
        assert exc_info.value.details["upstream_status_code"] == 403

        # Verify we made only 1 call (no retries for 4xx)
        assert forecast_mock.calls.call_count == 1
