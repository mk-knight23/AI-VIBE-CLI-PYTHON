"""Simple caching layer for Friday AI.

Provides in-memory and persistent caching with TTL support.
"""

import hashlib
import json
import logging
import pickle
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)


_T = TypeVar("_T")


class CacheEntry:
    """Cache entry with value and metadata."""

    def __init__(self, key: str, value: Any, ttl: int = 300):
        """Initialize cache entry.

        Args:
            key: Cache key
            value: Cached value
            ttl: Time to live (seconds)
        """
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl)
        self.hits = 0
        self.misses = 0

    def is_expired(self) -> bool:
        """Check if cache entry is expired.

        Returns:
            True if expired, False otherwise
        """
        return datetime.now() > self.expires_at

    def touch(self):
        """Update access time and increment hits."""
        self.hits += 1
        if self.created_at < self.expires_at:
            # Refresh expiration if accessed while expired
            self.created_at = datetime.now()
            self.expires_at = self.created_at + timedelta(seconds=300)


class Cache:
    """Simple thread-safe cache with LRU eviction policy."""

    def __init__(self, max_size: int = 128):
        """Initialize cache.

        Args:
            max_size: Maximum number of entries
        """
        self.max_size = max_size
        self._cache: dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    def get(self, key: str, default_value: Any = None, ttl: int = 300) -> Any:
        """Get value from cache.

        Args:
            key: Cache key
            default_value: Default value if cache miss
            ttl: Time to live in seconds (default 300)
        """
        # Check cache
        entry = self._cache.get(key)

        if entry and not entry.is_expired():
            entry.touch()
            return entry.value
        if default_value is not None:
            entry = CacheEntry(key, default_value, ttl)
            self._add_entry(entry)
        else:
            self._stats["misses"] += 1
            self._stats["misses"] += 1
            return default_value

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live (default 300)
        """
        entry = CacheEntry(key, value, ttl)
        self._add_entry(entry)

    def _add_entry(self, entry: CacheEntry) -> None:
        """Add entry to cache, evicting if necessary.

        Args:
            entry: Cache entry to add
        """
        # Evict oldest if cache is full
        while len(self._cache) >= self.max_size:
            oldest_key = min(self._cache, key=lambda e: e.created_at)
            del self._cache[oldest_key]
            self._stats["evictions"] += 1

        # Add new entry
        self._cache[entry.key] = entry

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Cache statistics dictionary
        """
        return self._stats.copy()

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
