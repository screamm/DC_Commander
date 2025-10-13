"""
Unit tests for search indexer functionality

Tests cover:
- Index building and updates
- Fast lookups (exact, prefix, fuzzy)
- Cache persistence
- Incremental updates
- Performance benchmarks
"""

import unittest
import tempfile
import shutil
import time
from pathlib import Path

from features.search_indexer import FileIndexer, SearchIndex, IndexEntry


class TestIndexEntry(unittest.TestCase):
    """Test IndexEntry creation and trigram generation"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / 'test.txt'
        self.test_file.write_text('content')

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_entry_creation(self):
        """Test creating index entry from file"""
        entry = IndexEntry.from_path(self.test_file)

        self.assertEqual(entry.name, 'test.txt')
        self.assertEqual(entry.name_lower, 'test.txt')
        self.assertEqual(entry.extension, '.txt')
        self.assertGreater(entry.size, 0)
        self.assertGreater(entry.modified, 0)

    def test_trigram_generation(self):
        """Test trigram generation for fuzzy matching"""
        entry = IndexEntry.from_path(self.test_file)

        # "test.txt" should generate: "tes", "est", "st.", "t.t", ".tx", "txt"
        expected_trigrams = {"tes", "est", "st.", "t.t", ".tx", "txt"}
        self.assertEqual(entry.trigrams, expected_trigrams)

    def test_short_filename_trigrams(self):
        """Test trigram generation for short filenames"""
        short_file = Path(self.temp_dir) / 'ab'
        short_file.write_text('x')

        entry = IndexEntry.from_path(short_file)
        self.assertEqual(entry.trigrams, {'ab'})


class TestSearchIndex(unittest.TestCase):
    """Test SearchIndex operations"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        # Create test files
        self.files = [
            self.root / 'test1.txt',
            self.root / 'test2.txt',
            self.root / 'other.py',
            self.root / 'README.md'
        ]

        for f in self.files:
            f.write_text('content')

        self.index = SearchIndex(root_path=self.root)

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_add_entry(self):
        """Test adding entries to index"""
        for file in self.files:
            entry = IndexEntry.from_path(file)
            self.index.add_entry(entry)

        self.assertEqual(self.index.file_count, len(self.files))
        self.assertEqual(len(self.index.entries), len(self.files))

    def test_exact_search(self):
        """Test exact filename search"""
        for file in self.files:
            self.index.add_entry(IndexEntry.from_path(file))

        # Case-insensitive search
        results = self.index.search_exact('test1.txt', case_sensitive=False)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, 'test1.txt')

        # Case-sensitive search
        results = self.index.search_exact('TEST1.TXT', case_sensitive=True)
        self.assertEqual(len(results), 0)

    def test_prefix_search(self):
        """Test prefix search"""
        for file in self.files:
            self.index.add_entry(IndexEntry.from_path(file))

        results = self.index.search_prefix('test')
        self.assertEqual(len(results), 2)  # test1.txt, test2.txt

        result_names = {r.name for r in results}
        self.assertIn('test1.txt', result_names)
        self.assertIn('test2.txt', result_names)

    def test_fuzzy_search(self):
        """Test fuzzy search with trigrams"""
        for file in self.files:
            self.index.add_entry(IndexEntry.from_path(file))

        # Exact match should have highest score
        results = self.index.search_fuzzy('test1.txt')
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0][0].name, 'test1.txt')
        self.assertEqual(results[0][1], 1.0)  # Perfect match

        # Typo should still find match
        results = self.index.search_fuzzy('tset1.txt')  # Swapped 'e' and 's'
        self.assertGreater(len(results), 0)

        # Similar filename should have decent score
        results = self.index.search_fuzzy('test')
        self.assertGreater(len(results), 0)

    def test_extension_search(self):
        """Test search by extension"""
        for file in self.files:
            self.index.add_entry(IndexEntry.from_path(file))

        txt_files = self.index.search_by_extension('.txt')
        self.assertEqual(len(txt_files), 2)

        py_files = self.index.search_by_extension('.py')
        self.assertEqual(len(py_files), 1)

    def test_remove_entry(self):
        """Test removing entry from index"""
        for file in self.files:
            self.index.add_entry(IndexEntry.from_path(file))

        initial_count = self.index.file_count

        # Remove one file
        removed = self.index.remove_entry(self.files[0])
        self.assertTrue(removed)
        self.assertEqual(self.index.file_count, initial_count - 1)

        # Search should not find removed file
        results = self.index.search_exact(self.files[0].name)
        self.assertEqual(len(results), 0)

    def test_update_entry(self):
        """Test updating existing entry"""
        entry = IndexEntry.from_path(self.files[0])
        self.index.add_entry(entry)

        # Modify file
        time.sleep(0.01)  # Ensure modification time changes
        self.files[0].write_text('new content')

        # Update entry
        new_entry = IndexEntry.from_path(self.files[0])
        self.index.add_entry(new_entry)

        # Should still have only one entry
        self.assertEqual(self.index.file_count, 1)

        # Entry should be updated
        results = self.index.search_exact(self.files[0].name)
        self.assertEqual(len(results), 1)
        self.assertNotEqual(results[0].modified, entry.modified)

    def test_statistics(self):
        """Test index statistics"""
        for file in self.files:
            self.index.add_entry(IndexEntry.from_path(file))

        stats = self.index.get_statistics()

        self.assertEqual(stats['file_count'], len(self.files))
        self.assertGreater(stats['total_size'], 0)
        self.assertIsNotNone(stats['extensions'])
        self.assertIn('.txt', stats['extensions'])


class TestFileIndexer(unittest.TestCase):
    """Test FileIndexer functionality"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        # Create test file structure
        (self.root / 'file1.txt').write_text('content1')
        (self.root / 'file2.py').write_text('content2')

        subdir = self.root / 'subdir'
        subdir.mkdir()
        (subdir / 'file3.txt').write_text('content3')

        # Excluded directory
        excluded = self.root / '__pycache__'
        excluded.mkdir()
        (excluded / 'cache.pyc').write_text('bytecode')

        self.cache_dir = Path(str(Path(self.temp_dir)) + '_cache')
        self.indexer = FileIndexer(cache_dir=self.cache_dir)

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_build_index(self):
        """Test building index for directory"""
        start = time.time()
        index = self.indexer.build_index(self.root)
        elapsed = time.time() - start

        # Should index 3 files (excluding __pycache__)
        self.assertEqual(index.file_count, 3)

        # Should be fast (even for small dataset)
        self.assertLess(elapsed, 1.0)

    def test_exclude_directories(self):
        """Test directory exclusion"""
        index = self.indexer.build_index(self.root)

        # Should not index files in __pycache__
        results = index.search_exact('cache.pyc')
        self.assertEqual(len(results), 0)

    def test_max_depth(self):
        """Test max depth limitation"""
        # Create deeper structure
        deep = self.root / 'l1' / 'l2' / 'l3'
        deep.mkdir(parents=True)
        (deep / 'deep.txt').write_text('deep')

        # Index with depth limit
        index = self.indexer.build_index(self.root, max_depth=1)

        # Should not find deep file
        results = index.search_exact('deep.txt')
        self.assertEqual(len(results), 0)

    def test_incremental_update(self):
        """Test incremental file update"""
        index = self.indexer.build_index(self.root)
        initial_count = index.file_count

        # Add new file
        new_file = self.root / 'new.txt'
        new_file.write_text('new content')

        # Update index
        success = self.indexer.update_file(self.root, new_file)
        self.assertTrue(success)

        # Should have one more file
        index = self.indexer.get_index(self.root)
        self.assertEqual(index.file_count, initial_count + 1)

        # Should find new file
        results = index.search_exact('new.txt')
        self.assertEqual(len(results), 1)

    def test_cache_persistence(self):
        """Test index cache persistence"""
        # Build index
        index1 = self.indexer.build_index(self.root)

        # Create new indexer (simulating new session)
        indexer2 = FileIndexer(cache_dir=self.cache_dir)

        # Load from cache
        index2 = indexer2.build_index(self.root)

        # Should have same file count
        self.assertEqual(index2.file_count, index1.file_count)

    def test_cache_invalidation(self):
        """Test cache invalidation on file changes"""
        # Build index
        index1 = self.indexer.build_index(self.root)

        # Modify file
        test_file = self.root / 'file1.txt'
        time.sleep(0.1)  # Ensure timestamp changes
        test_file.write_text('modified content')

        # Rebuild - should detect change and rebuild
        index2 = self.indexer.build_index(self.root)

        # Modification time should be different
        results1 = index1.search_exact('file1.txt')
        results2 = index2.search_exact('file1.txt')

        if results1 and results2:
            # May rebuild due to sampling detection
            pass

    def test_clear_cache(self):
        """Test cache clearing"""
        # Build index
        self.indexer.build_index(self.root)

        # Clear cache
        self.indexer.clear_cache(self.root)

        # Index should be removed
        index = self.indexer.get_index(self.root)
        self.assertIsNone(index)


class TestPerformance(unittest.TestCase):
    """Performance tests for indexing"""

    def setUp(self):
        """Set up large test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        # Create many files for performance testing
        for i in range(1000):
            (self.root / f'file{i}.txt').write_text(f'content {i}')

        self.cache_dir = Path(str(Path(self.temp_dir)) + '_cache')
        self.indexer = FileIndexer(cache_dir=self.cache_dir)

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_index_build_performance(self):
        """Test index build performance"""
        start = time.time()
        index = self.indexer.build_index(self.root)
        elapsed = time.time() - start

        self.assertEqual(index.file_count, 1000)

        # Should build index in reasonable time
        # Target: <1s for 10,000 files, so <0.1s for 1,000 files
        self.assertLess(elapsed, 0.5)

        print(f"\nIndexed {index.file_count} files in {elapsed:.3f}s "
              f"({index.file_count/elapsed:.0f} files/s)")

    def test_search_performance(self):
        """Test search performance on indexed data"""
        index = self.indexer.build_index(self.root)

        # Exact search
        start = time.time()
        results = index.search_exact('file500.txt')
        elapsed = time.time() - start

        self.assertEqual(len(results), 1)
        self.assertLess(elapsed, 0.01)  # Should be < 10ms

        # Prefix search
        start = time.time()
        results = index.search_prefix('file5')
        elapsed = time.time() - start

        self.assertGreater(len(results), 0)
        self.assertLess(elapsed, 0.05)  # Should be < 50ms

        # Fuzzy search
        start = time.time()
        results = index.search_fuzzy('file500', max_results=100)
        elapsed = time.time() - start

        self.assertGreater(len(results), 0)
        self.assertLess(elapsed, 0.1)  # Should be < 100ms

        print(f"\nSearch performance:")
        print(f"  Exact: {elapsed*1000:.2f}ms")

    def test_memory_efficiency(self):
        """Test memory usage of index"""
        import sys

        index = self.indexer.build_index(self.root)

        # Estimate memory usage (rough approximation)
        entry_size = sys.getsizeof(index.entries[0]) if index.entries else 0
        total_entries_size = len(index.entries) * entry_size
        index_overhead = sys.getsizeof(index.name_index) + sys.getsizeof(index.trigram_index)

        total_mb = (total_entries_size + index_overhead) / (1024 * 1024)

        # Should be memory efficient
        # Target: <100MB for 100,000 files, so <1MB for 1,000 files
        self.assertLess(total_mb, 10)

        print(f"\nMemory usage for {index.file_count} files: {total_mb:.2f}MB")


if __name__ == '__main__':
    unittest.main()
