"""Tests for AsyncCacheRepository."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.repositories import AsyncCacheRepository


@pytest.fixture
def cache() -> AsyncCacheRepository:
    """Provide a fresh cache instance for each test."""
    return AsyncCacheRepository()


@pytest.mark.asyncio
async def test_cache_set_and_get(cache: AsyncCacheRepository) -> None:
    """Test basic set and get operations."""
    await cache.set("key1", "value1", ttl=3600)
    result = await cache.get("key1")
    assert result == "value1"


@pytest.mark.asyncio
async def test_cache_get_nonexistent_key(
    cache: AsyncCacheRepository,
) -> None:
    """Test getting a key that does not exist."""
    result = await cache.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_with_zero_ttl(cache: AsyncCacheRepository) -> None:
    """Test set with zero TTL (should store indefinitely)."""
    await cache.set("persist", "forever", ttl=0)
    result = await cache.get("persist")
    assert result == "forever"


@pytest.mark.asyncio
async def test_cache_expiration(cache: AsyncCacheRepository) -> None:
    """Test that cached values expire after TTL (using mocked time)."""
    current_time = 1000.0
    time_values = [current_time, current_time, current_time + 2.0]
    with patch.object(cache, "_get_current_time", side_effect=time_values):
        await cache.set("temp", "data", ttl=1)
        # Immediately after set, should exist
        assert await cache.get("temp") == "data"
        # After 2 seconds (past expiry), should be expired
        assert await cache.get("temp") is None


@pytest.mark.asyncio
async def test_cache_overwrite(cache: AsyncCacheRepository) -> None:
    """Test overwriting an existing cache entry."""
    await cache.set("key", "value1", ttl=3600)
    await cache.set("key", "value2", ttl=3600)
    result = await cache.get("key")
    assert result == "value2"
