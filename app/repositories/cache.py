"""Cache repository for caching data with TTL support."""

from __future__ import annotations

import time


class AsyncCacheRepository:
    """In-memory cache with TTL support.

    Stores key-value pairs with optional time-to-live (TTL) expiration.
    TTL is measured in seconds from the time of storage.
    """

    def __init__(self) -> None:
        """Initialize the cache store."""
        self._store: dict[str, tuple[str, float]] = {}

    def _get_current_time(self) -> float:
        """Get the current time in seconds (allows mocking in tests)."""
        return time.time()

    async def get(self, key: str) -> str | None:
        """Retrieve a cached value by key.

        Args:
            key: The cache key to retrieve.

        Returns:
            The cached value if it exists and has not expired, None otherwise.
        """
        if key not in self._store:
            return None

        value, expiry_time = self._store[key]
        if self._get_current_time() >= expiry_time:
            del self._store[key]
            return None

        return value

    async def set(
        self,
        key: str,
        value: str,
        ttl: float,
    ) -> None:
        """Store a value in the cache with TTL.

        Args:
            key: The cache key.
            value: The value to store.
            ttl: Time to live in seconds. If 0 or negative, store indefinitely.
        """
        if ttl <= 0:
            expiry_time = float("inf")
        else:
            expiry_time = self._get_current_time() + ttl

        self._store[key] = (value, expiry_time)
