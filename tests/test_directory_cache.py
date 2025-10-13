"""Comprehensive tests for DirectoryCache module.

Tests LRU caching with TTL for directory listings including
cache operations, expiration, threading, and statistics.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from time import sleep
from threading import Thread
from src.utils.directory_cache import DirectoryCache, CacheEntry


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_cache_entry_creation(self, tmp_path):
        """Test creating a cache entry."""
        data = ["file1.txt", "file2.txt"]
        timestamp = datetime.now()

        entry = CacheEntry(data=data, timestamp=timestamp, path=tmp_path)

        assert entry.data == data
        assert entry.timestamp == timestamp
        assert entry.path == tmp_path

    def test_is_expired_not_expired(self, tmp_path):
        """Test entry is not expired within TTL."""
        entry = CacheEntry(
            data=["test"],
            timestamp=datetime.now(),
            path=tmp_path
        )

        ttl = timedelta(seconds=60)
        assert entry.is_expired(ttl) is False

    def test_is_expired_expired(self, tmp_path):
        """Test entry is expired after TTL."""
        old_timestamp = datetime.now() - timedelta(seconds=120)
        entry = CacheEntry(
            data=["test"],
            timestamp=old_timestamp,
            path=tmp_path
        )

        ttl = timedelta(seconds=60)
        assert entry.is_expired(ttl) is True

    def test_is_expired_exact_ttl(self, tmp_path):
        """Test entry expiration at exact TTL boundary."""
        old_timestamp = datetime.now() - timedelta(seconds=60)
        entry = CacheEntry(
            data=["test"],
            timestamp=old_timestamp,
            path=tmp_path
        )

        ttl = timedelta(seconds=60)
        # Should be expired (>= TTL)
        assert entry.is_expired(ttl) is True


class TestDirectoryCacheInit:
    """Test DirectoryCache initialization."""

    def test_init_default(self):
        """Test default initialization."""
        cache = DirectoryCache()

        assert cache.maxsize == 100
        assert cache.ttl == timedelta(seconds=60)
        assert cache.size == 0
        assert cache._hits == 0
        assert cache._misses == 0

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        cache = DirectoryCache(maxsize=50, ttl_seconds=30)

        assert cache.maxsize == 50
        assert cache.ttl == timedelta(seconds=30)

    def test_init_large_maxsize(self):
        """Test initialization with large maxsize."""
        cache = DirectoryCache(maxsize=10000)

        assert cache.maxsize == 10000

    def test_init_small_ttl(self):
        """Test initialization with small TTL."""
        cache = DirectoryCache(ttl_seconds=1)

        assert cache.ttl == timedelta(seconds=1)


class TestCacheGetPut:
    """Test basic cache get/put operations."""

    def test_put_and_get(self, tmp_path):
        """Test putting and getting cache entry."""
        cache = DirectoryCache()
        data = ["file1.txt", "file2.txt"]

        cache.put(tmp_path, data)
        result = cache.get(tmp_path)

        assert result == data
        assert cache._hits == 1
        assert cache._misses == 0

    def test_get_nonexistent(self, tmp_path):
        """Test getting nonexistent entry returns None."""
        cache = DirectoryCache()

        result = cache.get(tmp_path)

        assert result is None
        assert cache._hits == 0
        assert cache._misses == 1

    def test_put_overwrites_existing(self, tmp_path):
        """Test putting to existing key overwrites data."""
        cache = DirectoryCache()

        cache.put(tmp_path, ["old_data"])
        cache.put(tmp_path, ["new_data"])

        result = cache.get(tmp_path)
        assert result == ["new_data"]

    def test_put_multiple_paths(self, tmp_path):
        """Test putting multiple different paths."""
        cache = DirectoryCache()

        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir2"
        path3 = tmp_path / "dir3"

        cache.put(path1, ["data1"])
        cache.put(path2, ["data2"])
        cache.put(path3, ["data3"])

        assert cache.get(path1) == ["data1"]
        assert cache.get(path2) == ["data2"]
        assert cache.get(path3) == ["data3"]
        assert cache.size == 3

    def test_get_updates_access_order(self, tmp_path):
        """Test get updates LRU access order."""
        cache = DirectoryCache(maxsize=2)

        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir2"

        cache.put(path1, ["data1"])
        cache.put(path2, ["data2"])

        # Access path1 to make it recently used
        cache.get(path1)

        # Add path3, should evict path2 (least recently used)
        path3 = tmp_path / "dir3"
        cache.put(path3, ["data3"])

        assert cache.get(path1) is not None  # Still in cache
        assert cache.get(path2) is None  # Evicted
        assert cache.get(path3) is not None  # In cache


class TestCacheExpiration:
    """Test cache entry expiration."""

    def test_expired_entry_returns_none(self, tmp_path):
        """Test getting expired entry returns None."""
        cache = DirectoryCache(ttl_seconds=1)

        cache.put(tmp_path, ["data"])

        # Wait for expiration
        sleep(1.1)

        result = cache.get(tmp_path)
        assert result is None
        assert cache._misses > 0

    def test_expired_entry_removed_from_cache(self, tmp_path):
        """Test expired entry is removed from cache."""
        cache = DirectoryCache(ttl_seconds=1)

        cache.put(tmp_path, ["data"])
        initial_size = cache.size

        # Wait for expiration
        sleep(1.1)

        cache.get(tmp_path)

        # Size should decrease after accessing expired entry
        assert cache.size < initial_size

    def test_not_expired_entry_accessible(self, tmp_path):
        """Test non-expired entry remains accessible."""
        cache = DirectoryCache(ttl_seconds=10)

        cache.put(tmp_path, ["data"])

        # Access immediately
        result = cache.get(tmp_path)

        assert result == ["data"]
        assert cache._hits == 1


class TestCacheLRU:
    """Test LRU eviction policy."""

    def test_lru_eviction_basic(self, tmp_path):
        """Test LRU eviction when cache is full."""
        cache = DirectoryCache(maxsize=3)

        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir2"
        path3 = tmp_path / "dir3"
        path4 = tmp_path / "dir4"

        # Fill cache to capacity
        cache.put(path1, ["data1"])
        cache.put(path2, ["data2"])
        cache.put(path3, ["data3"])

        # Add one more, should evict path1 (oldest)
        cache.put(path4, ["data4"])

        assert cache.get(path1) is None  # Evicted
        assert cache.get(path2) is not None
        assert cache.get(path3) is not None
        assert cache.get(path4) is not None

    def test_lru_access_updates_order(self, tmp_path):
        """Test accessing entry updates its position in LRU."""
        cache = DirectoryCache(maxsize=3)

        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir2"
        path3 = tmp_path / "dir3"
        path4 = tmp_path / "dir4"

        cache.put(path1, ["data1"])
        cache.put(path2, ["data2"])
        cache.put(path3, ["data3"])

        # Access path1 to make it recently used
        cache.get(path1)

        # Add path4, should evict path2 (least recently used)
        cache.put(path4, ["data4"])

        assert cache.get(path1) is not None  # Still in cache
        assert cache.get(path2) is None  # Evicted
        assert cache.get(path3) is not None
        assert cache.get(path4) is not None

    def test_lru_put_updates_order(self, tmp_path):
        """Test putting existing entry updates its position."""
        cache = DirectoryCache(maxsize=3)

        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir2"
        path3 = tmp_path / "dir3"
        path4 = tmp_path / "dir4"

        cache.put(path1, ["data1"])
        cache.put(path2, ["data2"])
        cache.put(path3, ["data3"])

        # Update path1 to make it recently used
        cache.put(path1, ["updated1"])

        # Add path4, should evict path2
        cache.put(path4, ["data4"])

        assert cache.get(path1) is not None  # Still in cache (updated)
        assert cache.get(path2) is None  # Evicted
        assert cache.get(path3) is not None
        assert cache.get(path4) is not None


class TestGetOrLoad:
    """Test get_or_load convenience method."""

    def test_get_or_load_cache_hit(self, tmp_path):
        """Test get_or_load returns cached data."""
        cache = DirectoryCache()
        data = ["cached_data"]

        cache.put(tmp_path, data)

        def loader(path):
            return ["loaded_data"]

        result = cache.get_or_load(tmp_path, loader)

        assert result == data  # Should return cached data
        assert cache._hits == 1

    def test_get_or_load_cache_miss(self, tmp_path):
        """Test get_or_load loads and caches on miss."""
        cache = DirectoryCache()

        def loader(path):
            return ["loaded_data"]

        result = cache.get_or_load(tmp_path, loader)

        assert result == ["loaded_data"]
        assert cache._misses == 1

        # Should now be cached
        result2 = cache.get(tmp_path)
        assert result2 == ["loaded_data"]

    def test_get_or_load_calls_loader(self, tmp_path):
        """Test get_or_load calls loader function."""
        cache = DirectoryCache()
        loader_called = False

        def loader(path):
            nonlocal loader_called
            loader_called = True
            return ["data"]

        result = cache.get_or_load(tmp_path, loader)

        assert loader_called is True
        assert result == ["data"]

    def test_get_or_load_loader_receives_path(self, tmp_path):
        """Test loader receives correct path."""
        cache = DirectoryCache()

        def loader(path):
            assert path == tmp_path
            return ["data"]

        cache.get_or_load(tmp_path, loader)


class TestCacheInvalidation:
    """Test cache invalidation operations."""

    def test_invalidate_existing_entry(self, tmp_path):
        """Test invalidating existing entry."""
        cache = DirectoryCache()

        cache.put(tmp_path, ["data"])
        result = cache.invalidate(tmp_path)

        assert result is True
        assert cache.get(tmp_path) is None

    def test_invalidate_nonexistent_entry(self, tmp_path):
        """Test invalidating nonexistent entry returns False."""
        cache = DirectoryCache()

        result = cache.invalidate(tmp_path)

        assert result is False

    def test_invalidate_tree_single_path(self, tmp_path):
        """Test invalidating single path in tree."""
        cache = DirectoryCache()

        cache.put(tmp_path, ["data"])
        count = cache.invalidate_tree(tmp_path)

        assert count == 1
        assert cache.get(tmp_path) is None

    def test_invalidate_tree_nested_paths(self, tmp_path):
        """Test invalidating nested path tree."""
        cache = DirectoryCache()

        path1 = tmp_path
        path2 = tmp_path / "subdir"
        path3 = tmp_path / "subdir" / "nested"

        cache.put(path1, ["data1"])
        cache.put(path2, ["data2"])
        cache.put(path3, ["data3"])

        count = cache.invalidate_tree(tmp_path)

        assert count == 3
        assert cache.get(path1) is None
        assert cache.get(path2) is None
        assert cache.get(path3) is None

    def test_invalidate_tree_partial_match(self, tmp_path):
        """Test invalidate_tree only affects matching paths."""
        cache = DirectoryCache()

        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir1" / "subdir"
        path3 = tmp_path / "dir2"

        cache.put(path1, ["data1"])
        cache.put(path2, ["data2"])
        cache.put(path3, ["data3"])

        count = cache.invalidate_tree(path1)

        assert count == 2  # path1 and path2
        assert cache.get(path1) is None
        assert cache.get(path2) is None
        assert cache.get(path3) is not None  # Not affected

    def test_clear(self, tmp_path):
        """Test clearing entire cache."""
        cache = DirectoryCache()

        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir2"

        cache.put(path1, ["data1"])
        cache.put(path2, ["data2"])

        # Access to generate stats
        cache.get(path1)

        cache.clear()

        assert cache.size == 0
        assert cache._hits == 0
        assert cache._misses == 0
        assert cache.get(path1) is None
        assert cache.get(path2) is None


class TestCacheStatistics:
    """Test cache statistics and metrics."""

    def test_size_property(self, tmp_path):
        """Test size property returns correct count."""
        cache = DirectoryCache()

        assert cache.size == 0

        cache.put(tmp_path / "dir1", ["data1"])
        assert cache.size == 1

        cache.put(tmp_path / "dir2", ["data2"])
        assert cache.size == 2

    def test_hit_rate_no_access(self):
        """Test hit rate with no access."""
        cache = DirectoryCache()

        assert cache.hit_rate == 0.0

    def test_hit_rate_all_hits(self, tmp_path):
        """Test hit rate with all hits."""
        cache = DirectoryCache()

        cache.put(tmp_path, ["data"])
        cache.get(tmp_path)  # Hit
        cache.get(tmp_path)  # Hit

        assert cache.hit_rate == 100.0

    def test_hit_rate_all_misses(self, tmp_path):
        """Test hit rate with all misses."""
        cache = DirectoryCache()

        cache.get(tmp_path / "dir1")  # Miss
        cache.get(tmp_path / "dir2")  # Miss

        assert cache.hit_rate == 0.0

    def test_hit_rate_mixed(self, tmp_path):
        """Test hit rate with mixed hits and misses."""
        cache = DirectoryCache()

        cache.put(tmp_path, ["data"])

        cache.get(tmp_path)  # Hit
        cache.get(tmp_path / "other")  # Miss

        assert cache.hit_rate == 50.0

    def test_get_stats(self, tmp_path):
        """Test get_stats returns complete statistics."""
        cache = DirectoryCache(maxsize=100, ttl_seconds=60)

        cache.put(tmp_path, ["data"])
        cache.get(tmp_path)  # Hit
        cache.get(tmp_path / "other")  # Miss

        stats = cache.get_stats()

        assert stats["size"] == 1
        assert stats["maxsize"] == 100
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0
        assert stats["ttl_seconds"] == 60


class TestThreadSafety:
    """Test thread-safe cache operations."""

    def test_concurrent_put(self, tmp_path):
        """Test concurrent put operations."""
        cache = DirectoryCache(maxsize=1000)

        def put_data(i):
            path = tmp_path / f"dir{i}"
            cache.put(path, [f"data{i}"])

        threads = [Thread(target=put_data, args=(i,)) for i in range(100)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All entries should be added
        assert cache.size == 100

    def test_concurrent_get(self, tmp_path):
        """Test concurrent get operations."""
        cache = DirectoryCache()
        cache.put(tmp_path, ["data"])

        results = []

        def get_data():
            result = cache.get(tmp_path)
            results.append(result)

        threads = [Thread(target=get_data) for _ in range(50)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All gets should succeed
        assert len(results) == 50
        assert all(r == ["data"] for r in results)

    def test_concurrent_invalidate(self, tmp_path):
        """Test concurrent invalidation."""
        cache = DirectoryCache()

        # Pre-populate cache
        for i in range(10):
            path = tmp_path / f"dir{i}"
            cache.put(path, [f"data{i}"])

        def invalidate_data(i):
            path = tmp_path / f"dir{i}"
            cache.invalidate(path)

        threads = [Thread(target=invalidate_data, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Cache should be empty
        assert cache.size == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_cache_size_one(self, tmp_path):
        """Test cache with maxsize of 1."""
        cache = DirectoryCache(maxsize=1)

        path1 = tmp_path / "dir1"
        path2 = tmp_path / "dir2"

        cache.put(path1, ["data1"])
        cache.put(path2, ["data2"])

        # Only most recent should remain
        assert cache.size == 1
        assert cache.get(path1) is None
        assert cache.get(path2) is not None

    def test_cache_ttl_zero(self, tmp_path):
        """Test cache with zero TTL."""
        cache = DirectoryCache(ttl_seconds=0)

        cache.put(tmp_path, ["data"])

        # Should expire immediately
        result = cache.get(tmp_path)
        assert result is None

    def test_empty_data(self, tmp_path):
        """Test caching empty data."""
        cache = DirectoryCache()

        cache.put(tmp_path, [])

        result = cache.get(tmp_path)
        assert result == []

    def test_none_data(self, tmp_path):
        """Test caching None as data."""
        cache = DirectoryCache()

        cache.put(tmp_path, None)

        result = cache.get(tmp_path)
        assert result is None  # Ambiguous with cache miss

    def test_large_data(self, tmp_path):
        """Test caching large data structures."""
        cache = DirectoryCache()

        large_data = [f"file{i}.txt" for i in range(10000)]
        cache.put(tmp_path, large_data)

        result = cache.get(tmp_path)
        assert result == large_data

    def test_very_long_path(self, tmp_path):
        """Test caching with very long path."""
        cache = DirectoryCache()

        long_path = tmp_path
        for i in range(50):
            long_path = long_path / f"level{i}"

        cache.put(long_path, ["data"])

        result = cache.get(long_path)
        assert result == ["data"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
