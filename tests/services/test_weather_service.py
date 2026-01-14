import json
import pytest
from typing import Any

from app.services import WeatherService


class FakeAsyncCache:
    def __init__(
        self,
        initial: dict[str, str] | None = None,
        fail_get: bool = False,
        fail_set: bool = False,
    ):
        self.store = dict(initial or {})
        self.fail_get = fail_get
        self.fail_set = fail_set

    async def get(self, key: str) -> str | None:
        if self.fail_get:
            raise RuntimeError("cache get boom")
        return self.store.get(key)

    async def set(self, key: str, value: str, ttl: float) -> None:
        if self.fail_set:
            raise RuntimeError("cache set boom")
        self.store[key] = value


class CountingProvider:
    def __init__(self, data: dict[str, Any], exc: Exception | None = None):
        self.data = data
        self.exc = exc
        self.calls: list[str] = []

    async def get_weather(self, city: str) -> dict[str, Any]:
        self.calls.append(city)
        if self.exc:
            raise self.exc
        return self.data


@pytest.mark.asyncio
async def test_cache_hit_does_not_call_provider():
    cache = FakeAsyncCache(initial={"weather:tel aviv": json.dumps({"temp": 20})})
    provider = CountingProvider(data={"temp": 999})
    service = WeatherService(cache=cache, provider=provider)

    result = await service.get_weather("  Tel Aviv  ")
    assert result.cache_hit is True
    assert result.data == {"temp": 20}
    assert provider.calls == []


@pytest.mark.asyncio
async def test_cache_miss_calls_provider_exactly_once_and_stores():
    cache = FakeAsyncCache()
    provider = CountingProvider(data={"temp": 21})
    service = WeatherService(cache=cache, provider=provider)

    result = await service.get_weather("Berlin")
    assert result.cache_hit is False
    assert provider.calls == ["berlin"]
    assert json.loads(cache.store["weather:berlin"]) == {"temp": 21}


@pytest.mark.asyncio
async def test_cache_failures_fall_back_to_fresh_provider_fetch():
    cache = FakeAsyncCache(fail_get=True, fail_set=True)
    provider = CountingProvider(data={"temp": 22})
    service = WeatherService(cache=cache, provider=provider)

    result = await service.get_weather("Rome")
    assert result.cache_hit is False
    assert result.data == {"temp": 22}
    assert provider.calls == ["rome"]


@pytest.mark.asyncio
async def test_provider_errors_propagate_correctly():
    cache = FakeAsyncCache()
    provider = CountingProvider(data={"temp": 0}, exc=ValueError("provider down"))
    service = WeatherService(cache=cache, provider=provider)

    with pytest.raises(ValueError, match="provider down"):
        await service.get_weather("Paris")
