"""Comprehensive tests for the cache module."""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from friday_ai.cache.cache import Cache, CacheEntry, cached, ttl_cache


class TestCacheEntry:
    """Test CacheEntry class."""

    def test_cache_entry_initialization(self):
        """Test CacheEntry initialization."""
        entry = CacheEntry(key="test_key", value="test_value", ttl=300)
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.hits == 0
        assert entry.misses == 0
        assert entry.expires_at > entry.created_at

    def test_cache_entry_is_expired_false(self):
        """Test is_expired returns False for fresh entry."""
        entry = CacheEntry(key="test", value="value", ttl=300)
        assert not entry.is_expired()

    def test_cache_entry_is_expired_true(self):
        """Test is_expired returns True for expired entry."""
        entry = CacheEntry(key="test", value="value", ttl=-1)
        assert entry.is_expired()

    def test_cache_entry_touch(self):
        """Cache entry touch increments hits and refreshes expiration."""
        entry = CacheEntry(key="test", value="value", ttl=300)
        old_hits = entry.hits
        old_created = entry.created_at
        old_expires = entry.expires_at

        # Wait a tiny bit to ensure timestamp difference
        time.sleep(0.01)
        entry.touch()

        assert entry.hits == old_hits + 1
        assert entry.created_at > old_created
        assert entry.expires_at > old_expires


class TestCache:
    """Test Cache class."""

    def test_cache_initialization(self):
        """Test Cache initialization with default values."""
        cache = Cache()
        assert cache.max_size == 128
        assert len(cache._cache) == 0
        assert cache.get_stats() == {"hits": 0, "misses": 0, "evictions": 0}

    def test_cache_initialization_custom_size(self):
        """Test Cache initialization with custom size."""
        cache = Cache(max_size=10)
        assert cache.max_size == 10

    def test_cache_set_and_get(self):
        """Test setting and getting values from cache."""
        cache = Cache()
        cache.set("key1", "value1", ttl=300)
        assert cache.get("key1") == "value1"

    def test_cache_get_with_default(self):
        """Test getting non-existent key returns default."""
        cache = Cache()
        assert cache.get("nonexistent", default_value="default") == "default"

    def test_cache_get_expired_entry(self):
        """Test getting expired entry returns default."""
        cache = Cache()
        cache.set("key", "value", ttl=-1)  # Immediately expired
        assert cache.get("key", default_value="default") == "default"

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = Cache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
        assert cache.get_stats()["evictions"] == 1

    def test_cache_lru_moves_to_end(self):
        """Test accessing entry moves it to end (most recent)."""
        cache = Cache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.get("key1")  # Access key1, should move to end
        cache.set("key4", "value4")  # Should evict key2 (oldest)

        assert cache.get("key1") == "value1"  # Still present
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_cache_stats_hits(self):
        """Test cache statistics track hits."""
        cache = Cache()
        cache.set("key", "value")
        cache.get("key")
        assert cache.get_stats()["hits"] == 1

    def test_cache_stats_misses(self):
        """Test cache statistics track misses."""
        cache = Cache()
        cache.get("nonexistent")
        assert cache.get_stats()["misses"] == 1

    def test_cache_clear(self):
        """Test clearing the cache."""
        cache = Cache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert len(cache._cache) == 0
        assert cache.get_stats() == {"hits": 0, "misses": 0, "evictions": 0}

    def test_cache_update_existing_key(self):
        """Test updating an existing cache key."""
        cache = Cache()
        cache.set("key", "value1")
        cache.set("key", "value2")
        assert cache.get("key") == "value2"

    def test_cache_with_different_value_types(self):
        """Test cache with various value types."""
        cache = Cache()
        cache.set("string", "value")
        cache.set("int", 123)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"key": "value"})
        cache.set("none", None)

        assert cache.get("string") == "value"
        assert cache.get("int") == 123
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"key": "value"}
        assert cache.get("none") is None


class TestCachedDecorator:
    """Test cached decorator."""

    def test_cached_decorator_basic(self):
        """Test basic cached decorator functionality."""
        call_count = 0

        @cached(ttl=60)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        # First call
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1

        # Second call should use cache
        result2 = expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Not incremented

    def test_cached_decorator_different_args(self):
        """Test cached decorator with different arguments."""
        call_count = 0

        @cached(ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(10)
        result3 = expensive_function(5)  # Should use cache

        assert call_count == 2
        assert result1 == 10
        assert result2 == 20
        assert result3 == 10

    def test_cached_decorator_with_custom_key_func(self):
        """Test cached decorator with custom key function."""
        call_count = 0

        def custom_key(self, path):
            return f"list_dir:{path}"

        @cached(ttl=60, key_func=custom_key)
        def list_directory(self, path):
            nonlocal call_count
            call_count += 1
            return [f"{path}/file1", f"{path}/file2"]

        class MockClass:
            pass

        obj = MockClass()
        result1 = list_directory(obj, "/tmp")
        result2 = list_directory(obj, "/tmp")  # Should use cache

        assert call_count == 1
        assert result1 == ["/tmp/file1", "/tmp/file2"]

    def test_cached_decorator_with_kwargs(self):
        """Test cached decorator with keyword arguments."""
        call_count = 0

        @cached(ttl=60)
        def func(a, b, c=None):
            nonlocal call_count
            call_count += 1
            return a + b + (c or 0)

        result1 = func(1, 2, c=3)
        result2 = func(1, 2, c=3)  # Should use cache
        result3 = func(1, 2)  # Different args

        assert call_count == 2
        assert result1 == 6
        assert result3 == 3

    def test_cached_decorator_cache_clear(self):
        """Test cache_clear method added by decorator."""
        @cached(ttl=60)
        def func(x):
            return x * 2

        func(5)
        func.cache_clear()
        # After clearing, next call should execute function

    def test_cached_decorator_cache_stats(self):
        """Test cache_stats method added by decorator."""
        @cached(ttl=60)
        def func(x):
            return x * 2

        func(5)
        func(5)  # Cache hit
        stats = func.cache_stats()

        assert stats["hits"] >= 1
        assert "misses" in stats


class TestTTLCacheDecorator:
    """Test ttl_cache decorator."""

    def test_ttl_cache_basic(self):
        """Test basic ttl_cache functionality."""
        call_count = 0

        @ttl_cache(maxsize=10, ttl=60)
        def func(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        result1 = func(1, 2)
        result2 = func(1, 2)  # Should use cache

        assert call_count == 1
        assert result1 == 3

    def test_ttl_cache_expiration(self):
        """Test ttl_cache respects TTL."""
        call_count = 0

        @ttl_cache(maxsize=10, ttl=0)  # Immediate expiration
        def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        func(5)
        func(5)  # Cache expired, should call again

        assert call_count == 2

    def test_ttl_cache_maxsize(self):
        """Test ttl_cache respects maxsize."""
        call_count = 0

        @ttl_cache(maxsize=2, ttl=60)
        def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        func(1)
        func(2)
        func(3)  # Should evict oldest
        func(1)  # Should call again (evicted)

        assert call_count == 4

    def test_ttl_cache_with_different_args(self):
        """Test ttl_cache with different argument combinations."""
        call_count = 0

        @ttl_cache(maxsize=10, ttl=60)
        def func(a, b, c=None):
            nonlocal call_count
            call_count += 1
            return a + b + (c or 0)

        func(1, 2)
        func(1, 2, c=3)
        func(1, 2, c=3)  # Should hit cache

        assert call_count == 2

    def test_ttl_cache_clear(self):
        """Test cache_clear on ttl_cache."""
        @ttl_cache(maxsize=10, ttl=60)
        def func(x):
            return x * 2

        func(5)
        func.cache_clear()

    def test_ttl_cache_stats(self):
        """Test cache stats methods on ttl_cache."""
        @ttl_cache(maxsize=10, ttl=60)
        def func(x):
            return x * 2

        func(5)
        func(5)

        stats = func.cache_stats()
        assert "hits" in stats
        assert "misses" in stats

        info = func.cache_info()
        assert info is not None


class TestCacheEdgeCases:
    """Test edge cases and error conditions."""

    def test_cache_with_none_value(self):
        """Test caching None value."""
        cache = Cache()
        cache.set("key", None)
        # None is a valid cached value, not a miss
        result = cache.get("key", default_value="default")
        assert result is None

    def test_cache_with_zero_ttl(self):
        """Test cache entry with zero TTL expires immediately."""
        cache = Cache()
        cache.set("key", "value", ttl=0)
        # Small delay to ensure expiration check
        time.sleep(0.01)
        result = cache.get("key", default_value="default")
        assert result == "default"

    def test_cache_with_large_ttl(self):
        """Test cache entry with very large TTL."""
        cache = Cache()
        cache.set("key", "value", ttl=86400)  # 1 day
        assert cache.get("key") == "value"

    def test_cache_empty_key(self):
        """Test cache with empty string key."""
        cache = Cache()
        cache.set("", "value")
        assert cache.get("") == "value"

    def test_cache_unicode_values(self):
        """Test cache with Unicode strings."""
        cache = Cache()
        cache.set("emoji", "Hello 🌍")
        cache.set("chinese", "你好")
        cache.set("arabic", "مرحبا")

        assert cache.get("emoji") == "Hello 🌍"
        assert cache.get("chinese") == "你好"
        assert cache.get("arabic") == "مرحبا"

    def test_cache_stats_immutability(self):
        """Test that get_stats returns a copy, not reference."""
        cache = Cache()
        stats1 = cache.get_stats()
        stats1["hits"] = 999  # Try to modify

        stats2 = cache.get_stats()
        assert stats2["hits"] == 0  # Original unchanged

    def test_cached_decorator_preserves_docstring(self):
        """Test that cached decorator preserves function docstring."""
        @cached(ttl=60)
        def documented_function():
            """This is a documented function."""
            return 42

        assert documented_function.__doc__ == "This is a documented function."

    def test_ttl_cache_preserves_function_name(self):
        """Test that ttl_cache preserves function name."""
        @ttl_cache(maxsize=10, ttl=60)
        def my_function():
            return 42

        assert my_function.__name__ == "my_function"
