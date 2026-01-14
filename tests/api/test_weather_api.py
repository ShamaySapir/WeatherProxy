from __future__ import annotations

import httpx
import pytest
import respx

from app.dependencies import get_weather_service
from app.integrations.open_meteo import OpenMeteoClient
from app.integrations.open_meteo_provider import OpenMeteoProvider
from app.main import app
from app.repositories.cache import AsyncCacheRepository
from app.services.weather_service import WeatherService


@pytest.mark.asyncio
async def test_weather_cache_behavior_respx_mocks_open_meteo_calls() -> None:
    # Fresh cache per test.
    cache = AsyncCacheRepository()
    provider = OpenMeteoProvider(OpenMeteoClient())
    service = WeatherService(cache=cache, provider=provider, ttl_seconds=300.0)

    app.dependency_overrides[get_weather_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with respx.mock(assert_all_called=True) as rsps:
            geocoding_route = rsps.get("https://api.open-meteo.com/v1/geocoding").respond(
                200,
                json={"results": [{"latitude": 32.0853, "longitude": 34.7818}]},
            )
            forecast_route = rsps.get("https://api.open-meteo.com/v1/forecast").respond(
                200,
                json={
                    "latitude": 32.0853,
                    "longitude": 34.7818,
                    "current": {
                        "temperature_2m": 25.0,
                        "relative_humidity_2m": 60,
                        "weather_code": 3,
                    },
                },
            )

            # First call => cache miss => hits upstream (geocoding + forecast).
            r1 = await client.get("/weather", params={"city": "  Tel Aviv  "})
            assert r1.status_code == 200
            body1 = r1.json()
            assert body1["cache_hit"] is False
            assert body1["city"] == "tel aviv"
            assert body1["data"]["current"]["temperature_2m"] == 25.0
            assert geocoding_route.call_count == 1
            assert forecast_route.call_count == 1

            # Second call => cache hit => no more upstream calls.
            r2 = await client.get("/weather", params={"city": "Tel Aviv"})
            assert r2.status_code == 200
            body2 = r2.json()
            assert body2["cache_hit"] is True
            assert body2["data"]["current"]["temperature_2m"] == 25.0
            assert geocoding_route.call_count == 1
            assert forecast_route.call_count == 1

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_weather_missing_city_param_returns_validation_error() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/weather")

        # Your app uses a custom RequestValidationError handler.
        # In this codebase validation errors are mapped to a stable AppError envelope.
        assert r.status_code == 400

        body = r.json()
        assert "error" in body
        assert body["error"]["code"] == "validation_error"
        assert isinstance(body["error"]["message"], str)
        assert body["error"]["status_code"] == 400


@pytest.mark.asyncio
async def test_weather_city_not_found_returns_error_envelope() -> None:
    cache = AsyncCacheRepository()
    provider = OpenMeteoProvider(OpenMeteoClient())
    service = WeatherService(cache=cache, provider=provider, ttl_seconds=300.0)
    app.dependency_overrides[get_weather_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with respx.mock(assert_all_called=True) as rsps:
            rsps.get("https://api.open-meteo.com/v1/geocoding").respond(200, json={"results": []})

            r = await client.get("/weather", params={"city": "NoSuchCity"})
            assert r.status_code == 404
            body = r.json()

            assert "error" in body
            assert isinstance(body["error"]["code"], str)
            assert isinstance(body["error"]["message"], str)
            assert body["error"]["status_code"] == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_weather_upstream_500_returns_error_envelope() -> None:
    cache = AsyncCacheRepository()
    provider = OpenMeteoProvider(OpenMeteoClient())
    service = WeatherService(cache=cache, provider=provider, ttl_seconds=300.0)
    app.dependency_overrides[get_weather_service] = lambda: service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with respx.mock(assert_all_called=True) as rsps:
            rsps.get("https://api.open-meteo.com/v1/geocoding").respond(500, json={"error": "upstream failed"})

            r = await client.get("/weather", params={"city": "London"})
            assert r.status_code == 500
            body = r.json()

            assert "error" in body
            assert body["error"]["code"] == "upstream_error"
            assert isinstance(body["error"]["message"], str)
            assert body["error"]["status_code"] == 500

    app.dependency_overrides.clear()
