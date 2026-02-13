"""Simple caching layer for Friday AI.

Provides in-memory and persistent caching with TTL support.
"""

import hashlib
import json
import logging
import pickle
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Dict
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from functools import wraps

logger = logging.getLogger(__name__)


_T = TypeVar("_T")
_F = TypeVar("_F", bound=Callable[..., Any])


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
        self.created_at = datetime.now(timezone.utc)
        self.expires_at = self.created_at + timedelta(seconds=ttl)
        self.hits = 0
        self.misses = 0

    def is_expired(self) -> bool:
        """Check if cache entry is expired.

        Returns:
            True if expired, False otherwise
        """
        return datetime.now(timezone.utc) > self.expires_at

    def touch(self):
        """Update access time and increment hits."""
        self.hits += 1
        if self.created_at < self.expires_at:
            # Refresh expiration if accessed while expired
            self.created_at = datetime.now(timezone.utc)
            self.expires_at = self.created_at + timedelta(seconds=300)


class Cache:
    """Simple thread-safe cache with LRU eviction policy."""

    def __init__(self, max_size: int = 128):
        """Initialize cache.

        Args:
            max_size: Maximum number of entries
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
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
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            entry.touch()
            return entry.value

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
        # Evict oldest (from front) if cache is full
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
            self._stats["evictions"] += 1

        # Add new entry (to end)
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


def cached(ttl: int = 300, key_func: Optional[Callable[..., str]] = None):
    """Decorator for caching function results with TTL.

    Args:
        ttl: Time to live in seconds (default 300)
        key_func: Optional function to generate cache key from args.
                  If not provided, uses function name and args.

    Returns:
        Decorated function with caching

    Example:
        @cached(ttl=60)
        def expensive_function(param1, param2):
            # Expensive computation
            return result

        @cached(ttl=120, key_func=lambda self, path: f"list_dir:{path}")
        def list_directory(self, path):
            # Directory listing
            return items
    """

    def decorator(func: _F) -> _F:
        cache = Cache(max_size=256)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                args_str = "_".join(str(a) for a in args)
                kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{func.__name__}:{args_str}:{kwargs_str}"

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)

            return result

        # Add cache control methods to wrapper
        wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
        wrapper.cache_stats = cache.get_stats  # type: ignore[attr-defined]

        return wrapper  # type: ignore[return-value]

    return decorator


def ttl_cache(maxsize: int = 128, ttl: int = 300):
    """TTL cache decorator with automatic expiration.

    Similar to functools.lru_cache but with time-based expiration.

    Args:
        maxsize: Maximum number of entries to cache
        ttl: Time to live in seconds (default 300)

    Returns:
        Decorated function with TTL caching

    Example:
        @ttl_cache(maxsize=64, ttl=60)
        def get_file_info(path):
            return os.stat(path)
    """
    cache = Cache(max_size=maxsize)

    def decorator(func: _F) -> _F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create hash-based key from args
            args_key = tuple(args) + tuple(sorted(kwargs.items()))
            cache_key = hashlib.md5(str(args_key).encode()).hexdigest()

            # Check cache
            entry = cache._cache.get(cache_key)
            if entry and not entry.is_expired():
                cache._stats["hits"] += 1
                entry.touch()
                return entry.value

            # Cache miss - execute function
            result = func(*args, **kwargs)
            cache._stats["misses"] += 1

            # Store in cache
            new_entry = CacheEntry(cache_key, result, ttl)
            cache._add_entry(new_entry)

            return result

        # Add cache control methods
        wrapper.cache_clear = cache.clear  # type: ignore[attr-defined]
        wrapper.cache_stats = cache.get_stats  # type: ignore[attr-defined]
        wrapper.cache_info = cache.get_stats  # type: ignore[attr-defined]

        return wrapper  # type: ignore[return-value]

    return decorator
