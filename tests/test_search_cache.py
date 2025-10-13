"""
Unit tests for search caching functionality

Tests cover:
- Cache storage and retrieval
- TTL expiration
- LRU eviction
- Memory limits
- Query key generation
- Search history
"""

import unittest
import time
from pathlib import Path

from features.search_cache import (
    SearchResultCache, CacheEntry, QueryCache, SearchHistoryCache
)


class TestCacheEntry(unittest.TestCase):
    """Test CacheEntry functionality"""

    def test_entry_creation(self):
        """Test creating cache entry"""
        entry = CacheEntry(
            key='test',
            value=[1, 2, 3],
            created_at=time.time(),
            ttl=60.0
        )

        self.assertEqual(entry.key, 'test')
        self.assertEqual(entry.value, [1, 2, 3])
        self.assertEqual(entry.access_count, 0)

    def test_expiration_check(self):
        """Test TTL expiration"""
        # Create entry with 0.1s TTL
        entry = CacheEntry(
            key='test',
            value='data',
            created_at=time.time(),
            ttl=0.1
        )

        # Should not be expired immediately
        self.assertFalse(entry.is_expired())

        # Wait for expiration
        time.sleep(0.15)
        self.assertTrue(entry.is_expired())

    def test_access_tracking(self):
        """Test access count tracking"""
        entry = CacheEntry(
            key='test',
            value='data',
            created_at=time.time(),
            ttl=60.0
        )

        initial_access = entry.last_access

        entry.touch()
        self.assertEqual(entry.access_count, 1)
        self.assertGreaterEqual(entry.last_access, initial_access)

        entry.touch()
        self.assertEqual(entry.access_count, 2)


class TestSearchResultCache(unittest.TestCase):
    """Test SearchResultCache functionality"""

    def test_basic_set_get(self):
        """Test basic cache set/get"""
        cache = SearchResultCache(max_entries=10)

        cache.set('key1', 'value1')
        result = cache.get('key1')

        self.assertEqual(result, 'value1')

    def test_cache_miss(self):
        """Test cache miss"""
        cache = SearchResultCache(max_entries=10)

        result = cache.get('nonexistent')
        self.assertIsNone(result)

    def test_ttl_expiration(self):
        """Test TTL-based expiration"""
        cache = SearchResultCache(default_ttl=0.1)

        cache.set('key1', 'value1')

        # Should exist immediately
        self.assertIsNotNone(cache.get('key1'))

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired
        self.assertIsNone(cache.get('key1'))

    def test_custom_ttl(self):
        """Test custom TTL per entry"""
        cache = SearchResultCache(default_ttl=60.0)

        # Set with short TTL
        cache.set('key1', 'value1', ttl=0.1)

        time.sleep(0.15)
        self.assertIsNone(cache.get('key1'))

    def test_lru_eviction(self):
        """Test LRU eviction policy"""
        cache = SearchResultCache(max_entries=3)

        # Fill cache
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.set('key3', 'value3')

        # Access key1 to make it recently used
        cache.get('key1')

        # Add new entry - should evict key2 (least recently used)
        cache.set('key4', 'value4')

        self.assertIsNotNone(cache.get('key1'))
        self.assertIsNone(cache.get('key2'))  # Evicted
        self.assertIsNotNone(cache.get('key3'))
        self.assertIsNotNone(cache.get('key4'))

    def test_memory_limit_eviction(self):
        """Test eviction based on memory limit"""
        # Small memory limit
        cache = SearchResultCache(max_entries=100, max_memory_mb=0.001)  # 1KB

        # Add entries until memory limit
        for i in range(20):
            cache.set(f'key{i}', 'x' * 100)  # 100 bytes each

        # Should have evicted some entries
        self.assertLess(len(cache._cache), 20)

    def test_invalidation(self):
        """Test cache invalidation"""
        cache = SearchResultCache()

        cache.set('key1', 'value1')
        self.assertIsNotNone(cache.get('key1'))

        # Invalidate
        removed = cache.invalidate('key1')
        self.assertTrue(removed)
        self.assertIsNone(cache.get('key1'))

        # Invalidate non-existent
        removed = cache.invalidate('nonexistent')
        self.assertFalse(removed)

    def test_pattern_invalidation(self):
        """Test pattern-based invalidation"""
        cache = SearchResultCache()

        cache.set('file:test1', 'value1')
        cache.set('file:test2', 'value2')
        cache.set('content:test1', 'value3')

        # Invalidate all 'file:' entries
        count = cache.invalidate_pattern('file:')
        self.assertEqual(count, 2)

        # file: entries should be gone
        self.assertIsNone(cache.get('file:test1'))
        self.assertIsNone(cache.get('file:test2'))

        # content: entry should remain
        self.assertIsNotNone(cache.get('content:test1'))

    def test_cleanup_expired(self):
        """Test expired entry cleanup"""
        cache = SearchResultCache(default_ttl=0.1)

        cache.set('key1', 'value1')
        cache.set('key2', 'value2', ttl=60.0)  # Long TTL

        time.sleep(0.15)

        # Cleanup expired
        count = cache.cleanup_expired()

        self.assertEqual(count, 1)
        self.assertIsNone(cache.get('key1'))
        self.assertIsNotNone(cache.get('key2'))

    def test_clear(self):
        """Test cache clearing"""
        cache = SearchResultCache()

        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        cache.clear()

        self.assertIsNone(cache.get('key1'))
        self.assertIsNone(cache.get('key2'))
        self.assertEqual(len(cache._cache), 0)

    def test_statistics(self):
        """Test cache statistics"""
        cache = SearchResultCache(max_entries=10)

        # Add entries
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        # Some hits
        cache.get('key1')
        cache.get('key1')

        # Some misses
        cache.get('nonexistent')

        stats = cache.get_stats()

        self.assertEqual(stats['entries'], 2)
        self.assertEqual(stats['hits'], 2)
        self.assertEqual(stats['misses'], 1)
        self.assertGreater(stats['hit_rate'], 0)


class TestQueryCache(unittest.TestCase):
    """Test QueryCache functionality"""

    def test_key_generation(self):
        """Test cache key generation"""
        cache = QueryCache()

        key1 = cache.make_key(Path('/path'), 'pattern', 'filename', opt1='val1')
        key2 = cache.make_key(Path('/path'), 'pattern', 'filename', opt1='val1')
        key3 = cache.make_key(Path('/path'), 'different', 'filename', opt1='val1')

        # Same parameters should generate same key
        self.assertEqual(key1, key2)

        # Different parameters should generate different key
        self.assertNotEqual(key1, key3)

    def test_cache_results(self):
        """Test caching search results"""
        cache = QueryCache()

        results = ['file1.txt', 'file2.txt']
        cache.cache_results(Path('/path'), 'test', 'filename', results)

        # Retrieve cached results
        cached = cache.get_results(Path('/path'), 'test', 'filename')
        self.assertEqual(cached, results)

    def test_options_affect_key(self):
        """Test that options affect cache key"""
        cache = QueryCache()

        results1 = ['result1']
        results2 = ['result2']

        # Cache with different options
        cache.cache_results(Path('/path'), 'test', 'filename', results1, case_sensitive=True)
        cache.cache_results(Path('/path'), 'test', 'filename', results2, case_sensitive=False)

        # Should retrieve correct results based on options
        cached1 = cache.get_results(Path('/path'), 'test', 'filename', case_sensitive=True)
        cached2 = cache.get_results(Path('/path'), 'test', 'filename', case_sensitive=False)

        self.assertEqual(cached1, results1)
        self.assertEqual(cached2, results2)

    def test_path_invalidation(self):
        """Test invalidation by path"""
        cache = QueryCache()

        cache.cache_results(Path('/path1'), 'test', 'filename', ['result1'])
        cache.cache_results(Path('/path2'), 'test', 'filename', ['result2'])

        # Invalidate path1
        count = cache.invalidate_path(Path('/path1'))
        self.assertGreater(count, 0)

        # path1 should be invalidated
        self.assertIsNone(cache.get_results(Path('/path1'), 'test', 'filename'))

        # path2 should remain
        self.assertIsNotNone(cache.get_results(Path('/path2'), 'test', 'filename'))


class TestSearchHistoryCache(unittest.TestCase):
    """Test SearchHistoryCache functionality"""

    def test_add_search(self):
        """Test adding search to history"""
        history = SearchHistoryCache(max_history=10)

        history.add_search('test query')
        recent = history.get_recent(limit=5)

        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0][0], 'test query')

    def test_frequency_tracking(self):
        """Test search frequency tracking"""
        history = SearchHistoryCache()

        # Add same query multiple times
        for _ in range(3):
            history.add_search('common query')

        history.add_search('rare query')

        # Get completions
        completions = history.get_completions('', max_results=10)

        # Common query should appear first
        self.assertEqual(completions[0], 'common query')

    def test_autocomplete(self):
        """Test autocomplete suggestions"""
        history = SearchHistoryCache()

        history.add_search('test file')
        history.add_search('test pattern')
        history.add_search('other query')

        # Get completions for 'test'
        completions = history.get_completions('test', max_results=10)

        self.assertEqual(len(completions), 2)
        self.assertIn('test file', completions)
        self.assertIn('test pattern', completions)

    def test_case_insensitive_completion(self):
        """Test case-insensitive autocomplete"""
        history = SearchHistoryCache()

        history.add_search('Test File')

        # Should match regardless of case
        completions = history.get_completions('test', max_results=10)
        self.assertEqual(len(completions), 1)

        completions = history.get_completions('TEST', max_results=10)
        self.assertEqual(len(completions), 1)

    def test_max_history_limit(self):
        """Test history size limit"""
        history = SearchHistoryCache(max_history=5)

        # Add more than max
        for i in range(10):
            history.add_search(f'query {i}')

        recent = history.get_recent(limit=100)

        # Should only keep max_history entries
        self.assertLessEqual(len(recent), 5)

    def test_recent_searches(self):
        """Test getting recent searches"""
        history = SearchHistoryCache()

        queries = ['query1', 'query2', 'query3']
        for q in queries:
            history.add_search(q)
            time.sleep(0.01)  # Ensure different timestamps

        recent = history.get_recent(limit=2)

        # Should return most recent first
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0][0], 'query3')
        self.assertEqual(recent[1][0], 'query2')

    def test_clear_history(self):
        """Test clearing history"""
        history = SearchHistoryCache()

        history.add_search('query1')
        history.add_search('query2')

        history.clear()

        recent = history.get_recent()
        self.assertEqual(len(recent), 0)

        completions = history.get_completions('')
        self.assertEqual(len(completions), 0)


class TestPerformance(unittest.TestCase):
    """Performance tests for caching"""

    def test_cache_performance(self):
        """Test cache operation performance"""
        cache = SearchResultCache(max_entries=10000)

        # Set performance
        start = time.time()
        for i in range(1000):
            cache.set(f'key{i}', f'value{i}')
        set_time = time.time() - start

        # Should be fast
        self.assertLess(set_time, 0.1)

        # Get performance
        start = time.time()
        for i in range(1000):
            cache.get(f'key{i}')
        get_time = time.time() - start

        # Should be very fast
        self.assertLess(get_time, 0.05)

        print(f"\nCache performance:")
        print(f"  Set 1000 entries: {set_time*1000:.2f}ms")
        print(f"  Get 1000 entries: {get_time*1000:.2f}ms")

    def test_eviction_performance(self):
        """Test LRU eviction performance"""
        cache = SearchResultCache(max_entries=100)

        # Fill beyond capacity
        start = time.time()
        for i in range(500):
            cache.set(f'key{i}', f'value{i}')
        elapsed = time.time() - start

        # Should handle eviction efficiently
        self.assertLess(elapsed, 0.5)
        self.assertEqual(len(cache._cache), 100)

        print(f"\nEviction performance: {elapsed*1000:.2f}ms for 500 insertions with 100 limit")


if __name__ == '__main__':
    unittest.main()
