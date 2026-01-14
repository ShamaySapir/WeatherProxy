# app/services/weather_service.py
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from app.repositories.cache import AsyncCache

logger = logging.getLogger(__name__)


class WeatherProvider(Protocol):
    async def get_weather(self, city: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class WeatherResult:
    city: str
    data: dict[str, Any]
    cache_hit: bool


class WeatherService:
    def __init__(self, *, cache: AsyncCache, provider: WeatherProvider, ttl_seconds: float = 300.0) -> None:
        self._cache = cache
        self._provider = provider
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def normalize_city(city: str) -> str:
        return city.strip().lower()

    @staticmethod
    def _cache_key(city_normalized: str) -> str:
        return f"weather:{city_normalized}"

    async def get_weather(self, city: str) -> WeatherResult:
        city_norm = self.normalize_city(city)
        key = self._cache_key(city_norm)

        # 1) Cache GET (best effort)
        cached_raw: str | None
        try:
            cached_raw = await self._cache.get(key)
        except Exception:
            logger.exception("cache_get_failed key=%s", key)
            cached_raw = None

        if cached_raw is not None:
            try:
                cached_data = json.loads(cached_raw)
                if isinstance(cached_data, dict):
                    return WeatherResult(city=city_norm, data=cached_data, cache_hit=True)
            except Exception:
                # Cache contains invalid JSON → treat as miss
                logger.exception("cache_decode_failed key=%s", key)

        # 2) Cache miss (or cache failed) -> provider
        data = await self._provider.get_weather(city_norm)  # provider errors propagate

        # 3) Cache SET (best effort)
        try:
            await self._cache.set(key, json.dumps(data), ttl=self._ttl_seconds)
        except Exception:
            logger.exception("cache_set_failed key=%s", key)

        return WeatherResult(city=city_norm, data=data, cache_hit=False)
