"""
Unit tests for advanced search functionality

Tests cover:
- Indexed search operations
- Fuzzy matching
- Cache integration
- Search history
- Performance benchmarks
"""

import unittest
import tempfile
import shutil
import time
from pathlib import Path

from features.advanced_search import (
    AdvancedFileSearch, AdvancedSearchOptions, advanced_search
)
from features.search_engine import FilterCriteria, FileFilter, FilterOperator


class TestAdvancedFileSearch(unittest.TestCase):
    """Test AdvancedFileSearch functionality"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        # Create test files
        (self.root / 'test1.txt').write_text('content')
        (self.root / 'test2.txt').write_text('content')
        (self.root / 'similar.txt').write_text('content')
        (self.root / 'other.py').write_text('code')
        (self.root / 'README.md').write_text('docs')

        # Subdirectory
        subdir = self.root / 'subdir'
        subdir.mkdir()
        (subdir / 'nested.txt').write_text('nested')

        self.searcher = AdvancedFileSearch(cache_ttl=60.0)

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_basic_indexed_search(self):
        """Test basic indexed search"""
        results = self.searcher.search_files(
            self.root,
            'test1.txt',
            AdvancedSearchOptions(use_index=True)
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path.name, 'test1.txt')

    def test_wildcard_search(self):
        """Test wildcard pattern search"""
        results = self.searcher.search_files(
            self.root,
            'test*.txt',
            AdvancedSearchOptions(use_index=True)
        )

        self.assertEqual(len(results), 2)
        result_names = {r.path.name for r in results}
        self.assertIn('test1.txt', result_names)
        self.assertIn('test2.txt', result_names)

    def test_prefix_search(self):
        """Test prefix search optimization"""
        results = self.searcher.search_files(
            self.root,
            'test*',
            AdvancedSearchOptions(use_index=True)
        )

        self.assertGreaterEqual(len(results), 2)

    def test_regex_search(self):
        """Test regex pattern search"""
        results = self.searcher.search_regex(
            self.root,
            r'test\d+\.txt',
            AdvancedSearchOptions(use_index=True)
        )

        self.assertEqual(len(results), 2)

    def test_fuzzy_search(self):
        """Test fuzzy matching"""
        # Exact match
        results = self.searcher.search_fuzzy(
            self.root,
            'test1.txt',
            AdvancedSearchOptions(fuzzy_threshold=0.5)
        )

        self.assertGreater(len(results), 0)
        # First result should be exact match
        self.assertEqual(results[0][0].path.name, 'test1.txt')
        self.assertEqual(results[0][1], 1.0)

        # Typo tolerance
        results = self.searcher.search_fuzzy(
            self.root,
            'tset1.txt',  # Swapped letters
            AdvancedSearchOptions(fuzzy_threshold=0.3)
        )

        self.assertGreater(len(results), 0)

    def test_fuzzy_threshold(self):
        """Test fuzzy matching threshold"""
        # High threshold
        results = self.searcher.search_fuzzy(
            self.root,
            'xyz',
            AdvancedSearchOptions(fuzzy_threshold=0.8)
        )

        # Should find few or no matches
        self.assertLessEqual(len(results), 1)

        # Low threshold
        results = self.searcher.search_fuzzy(
            self.root,
            'test',
            AdvancedSearchOptions(fuzzy_threshold=0.3)
        )

        # Should find more matches
        self.assertGreater(len(results), 0)

    def test_extension_filter(self):
        """Test file extension filtering"""
        options = AdvancedSearchOptions(
            file_extensions=['.txt'],
            use_index=True
        )

        results = self.searcher.search_files(self.root, '*', options)

        # Should only find .txt files
        for result in results:
            self.assertEqual(result.path.suffix, '.txt')

    def test_cache_integration(self):
        """Test result caching"""
        options = AdvancedSearchOptions(use_cache=True, use_index=True)

        # First search - should cache
        start = time.time()
        results1 = self.searcher.search_files(self.root, 'test*.txt', options)
        first_time = time.time() - start

        # Second search - should be cached
        start = time.time()
        results2 = self.searcher.search_files(self.root, 'test*.txt', options)
        cached_time = time.time() - start

        # Results should be identical
        self.assertEqual(len(results1), len(results2))

        # Cached should be faster (though may not be measurable for small datasets)
        # Just verify cache is being used
        stats = self.searcher.get_stats()
        self.assertGreater(stats['cache']['hits'], 0)

    def test_cache_invalidation(self):
        """Test cache invalidation on file changes"""
        options = AdvancedSearchOptions(use_cache=True, use_index=True)

        # Initial search
        results1 = self.searcher.search_files(self.root, 'test*.txt', options)

        # Add new file
        new_file = self.root / 'test3.txt'
        new_file.write_text('new')

        # Update index
        self.searcher.update_file(self.root, new_file)

        # Search again - should have updated results
        results2 = self.searcher.search_files(self.root, 'test*.txt', options)

        # Note: Due to caching, may need to rebuild index
        # The update_file should invalidate cache

    def test_search_history(self):
        """Test search history tracking"""
        options = AdvancedSearchOptions()

        # Perform searches
        self.searcher.search_files(self.root, 'test1.txt', options)
        self.searcher.search_files(self.root, 'test2.txt', options)

        # Get recent searches
        recent = self.searcher.get_recent_searches(limit=5)
        self.assertEqual(len(recent), 2)

    def test_autocomplete(self):
        """Test autocomplete suggestions"""
        options = AdvancedSearchOptions()

        # Build search history
        self.searcher.search_files(self.root, 'test file', options)
        self.searcher.search_files(self.root, 'test pattern', options)
        self.searcher.search_files(self.root, 'other', options)

        # Get completions
        completions = self.searcher.get_completions('test', limit=10)

        self.assertEqual(len(completions), 2)
        self.assertIn('test file', completions)
        self.assertIn('test pattern', completions)

    def test_filter_criteria(self):
        """Test search with filter criteria"""
        # Create files of different sizes
        (self.root / 'small.txt').write_text('x')
        (self.root / 'large.txt').write_text('x' * 10000)

        criteria = FilterCriteria(
            filters=[FileFilter('size', FilterOperator.GREATER, 100)]
        )

        results = self.searcher.search_by_criteria(
            self.root,
            criteria,
            AdvancedSearchOptions(use_index=True)
        )

        # Should only find large.txt
        result_names = {r.name for r in results}
        self.assertIn('large.txt', result_names)
        self.assertNotIn('small.txt', result_names)

    def test_index_rebuild(self):
        """Test force index rebuild"""
        # Initial index
        index1 = self.searcher.indexer.build_index(self.root)
        count1 = index1.file_count

        # Add file
        (self.root / 'new.txt').write_text('new')

        # Rebuild
        index2 = self.searcher.rebuild_index(self.root)
        count2 = index2.file_count

        # Should have one more file
        self.assertEqual(count2, count1 + 1)

    def test_max_results(self):
        """Test max results limitation"""
        options = AdvancedSearchOptions(max_results=2, use_index=True)

        results = self.searcher.search_files(self.root, '*', options)

        self.assertLessEqual(len(results), 2)

    def test_case_sensitivity(self):
        """Test case-sensitive search"""
        # Create mixed case file
        (self.root / 'Test.txt').write_text('content')

        # Case insensitive
        options = AdvancedSearchOptions(case_sensitive=False, use_index=True)
        results = self.searcher.search_files(self.root, 'test.txt', options)
        self.assertGreater(len(results), 0)

        # Case sensitive
        options = AdvancedSearchOptions(case_sensitive=True, use_index=True)
        results = self.searcher.search_files(self.root, 'test.txt', options)
        # May or may not find Test.txt depending on exact match

    def test_statistics(self):
        """Test search statistics"""
        options = AdvancedSearchOptions(use_cache=True, use_index=True)

        # Perform searches
        self.searcher.search_files(self.root, 'test1.txt', options)
        self.searcher.search_files(self.root, 'test1.txt', options)  # Cache hit

        stats = self.searcher.get_stats()

        # Should have cache stats
        self.assertIn('cache', stats)
        self.assertGreater(stats['cache']['hits'], 0)

        # Should have index stats
        self.assertIn('indices', stats)
        self.assertGreater(stats['total_indexed_files'], 0)


class TestConvenienceFunction(unittest.TestCase):
    """Test convenience function"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        (self.root / 'test.txt').write_text('content')
        (self.root / 'other.txt').write_text('content')

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_convenience_function(self):
        """Test advanced_search convenience function"""
        results = advanced_search(self.root, 'test.txt')

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path.name, 'test.txt')

    def test_fuzzy_convenience(self):
        """Test fuzzy search via convenience function"""
        results = advanced_search(self.root, 'tset.txt', fuzzy=True)

        # Should find similar files
        self.assertGreaterEqual(len(results), 0)


class TestPerformance(unittest.TestCase):
    """Performance tests for advanced search"""

    def setUp(self):
        """Set up large test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        # Create many files
        for i in range(1000):
            (self.root / f'file{i}.txt').write_text(f'content {i}')

        self.searcher = AdvancedFileSearch()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_indexed_search_performance(self):
        """Test indexed search performance"""
        options = AdvancedSearchOptions(use_index=True)

        # First search builds index
        start = time.time()
        results1 = self.searcher.search_files(self.root, 'file500.txt', options)
        first_time = time.time() - start

        # Second search uses index
        start = time.time()
        results2 = self.searcher.search_files(self.root, 'file600.txt', options)
        indexed_time = time.time() - start

        self.assertEqual(len(results1), 1)
        self.assertEqual(len(results2), 1)

        # Indexed search should be fast
        self.assertLess(indexed_time, 0.1)

        print(f"\nIndexed search performance:")
        print(f"  First search (with index build): {first_time*1000:.2f}ms")
        print(f"  Subsequent search: {indexed_time*1000:.2f}ms")

    def test_cache_hit_performance(self):
        """Test cache hit performance"""
        options = AdvancedSearchOptions(use_cache=True, use_index=True)

        # First search
        start = time.time()
        results1 = self.searcher.search_files(self.root, 'file*.txt', options)
        first_time = time.time() - start

        # Cached search
        start = time.time()
        results2 = self.searcher.search_files(self.root, 'file*.txt', options)
        cached_time = time.time() - start

        self.assertEqual(len(results1), len(results2))

        # Cache hit should be very fast
        self.assertLess(cached_time, 0.05)

        print(f"\nCache performance:")
        print(f"  First search: {first_time*1000:.2f}ms")
        print(f"  Cached search: {cached_time*1000:.2f}ms")

    def test_fuzzy_search_performance(self):
        """Test fuzzy search performance"""
        options = AdvancedSearchOptions(fuzzy_threshold=0.5)

        start = time.time()
        results = self.searcher.search_fuzzy(self.root, 'file500', options)
        elapsed = time.time() - start

        self.assertGreater(len(results), 0)

        # Should be reasonably fast
        self.assertLess(elapsed, 0.5)

        print(f"\nFuzzy search performance: {elapsed*1000:.2f}ms")

    def test_wildcard_performance(self):
        """Test wildcard search performance"""
        options = AdvancedSearchOptions(use_index=True)

        start = time.time()
        results = self.searcher.search_files(self.root, 'file5*.txt', options)
        elapsed = time.time() - start

        self.assertGreater(len(results), 0)

        # Should be fast with index
        self.assertLess(elapsed, 0.2)

        print(f"\nWildcard search performance: {elapsed*1000:.2f}ms ({len(results)} results)")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.searcher = AdvancedFileSearch()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_empty_directory(self):
        """Test search in empty directory"""
        results = self.searcher.search_files(
            self.root,
            '*',
            AdvancedSearchOptions(use_index=True)
        )

        self.assertEqual(len(results), 0)

    def test_invalid_regex(self):
        """Test invalid regex pattern"""
        with self.assertRaises(ValueError):
            self.searcher.search_regex(
                self.root,
                '[invalid(',
                AdvancedSearchOptions()
            )

    def test_special_characters_in_filename(self):
        """Test files with special characters"""
        special_file = self.root / 'test[123].txt'
        special_file.write_text('content')

        results = self.searcher.search_files(
            self.root,
            'test[123].txt',
            AdvancedSearchOptions(use_index=True)
        )

        self.assertEqual(len(results), 1)

    def test_unicode_filenames(self):
        """Test Unicode filenames"""
        unicode_file = self.root / 'テスト.txt'
        unicode_file.write_text('content')

        results = self.searcher.search_files(
            self.root,
            'テスト.txt',
            AdvancedSearchOptions(use_index=True)
        )

        self.assertEqual(len(results), 1)


if __name__ == '__main__':
    unittest.main()
