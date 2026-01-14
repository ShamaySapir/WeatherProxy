from __future__ import annotations

from functools import lru_cache

from app.integrations import OpenMeteoClient, OpenMeteoProvider
from app.repositories.cache import AsyncCacheRepository
from app.services.weather_service import WeatherService


@lru_cache
def get_cache() -> AsyncCacheRepository:
    return AsyncCacheRepository()


@lru_cache
def get_open_meteo_client() -> OpenMeteoClient:
    return OpenMeteoClient()


@lru_cache
def get_open_meteo_provider() -> OpenMeteoProvider:
    return OpenMeteoProvider(get_open_meteo_client())


def get_weather_service() -> WeatherService:
    return WeatherService(
        cache=get_cache(),
        provider=get_open_meteo_provider(),
        ttl_seconds=300.0,
    )
