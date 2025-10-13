"""
Performance benchmarks for search functionality

Benchmarks:
- Index build performance (10K, 100K files)
- Search query performance (indexed vs non-indexed)
- Fuzzy matching performance
- Cache hit/miss performance
- Memory usage analysis
"""

import unittest
import tempfile
import shutil
import time
import sys
from pathlib import Path
from typing import List, Tuple

from features.advanced_search import AdvancedFileSearch, AdvancedSearchOptions
from features.search_indexer import FileIndexer
from features.search_cache import SearchResultCache


class PerformanceBenchmark:
    """Performance benchmark helper"""

    @staticmethod
    def measure_time(func, *args, **kwargs) -> Tuple[float, any]:
        """Measure execution time of function"""
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        return elapsed, result

    @staticmethod
    def measure_memory(obj) -> float:
        """Estimate memory usage in MB (rough approximation)"""
        return sys.getsizeof(obj) / (1024 * 1024)

    @staticmethod
    def create_test_files(root: Path, count: int) -> List[Path]:
        """Create test file structure"""
        files = []

        # Create diverse file structure
        extensions = ['.txt', '.py', '.md', '.json', '.csv']
        prefixes = ['test', 'file', 'data', 'doc', 'report']

        for i in range(count):
            ext = extensions[i % len(extensions)]
            prefix = prefixes[i % len(prefixes)]

            # Create some subdirectories
            if i % 100 == 0:
                subdir = root / f'dir{i // 100}'
                subdir.mkdir(exist_ok=True)
                filepath = subdir / f'{prefix}{i}{ext}'
            else:
                filepath = root / f'{prefix}{i}{ext}'

            filepath.write_text(f'content {i}')
            files.append(filepath)

        return files


class TestIndexBuildPerformance(unittest.TestCase):
    """Benchmark index building performance"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.benchmark = PerformanceBenchmark()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_index_build_1k_files(self):
        """Benchmark: Index 1,000 files"""
        files = self.benchmark.create_test_files(self.root, 1000)

        indexer = FileIndexer(cache_dir=Path(self.temp_dir) / 'cache')

        elapsed, index = self.benchmark.measure_time(
            indexer.build_index, self.root
        )

        self.assertEqual(index.file_count, 1000)

        # Performance target: <100ms for 1K files
        self.assertLess(elapsed, 0.1)

        files_per_sec = index.file_count / elapsed

        print(f"\n📊 Index Build (1K files):")
        print(f"   Time: {elapsed*1000:.2f}ms")
        print(f"   Speed: {files_per_sec:.0f} files/s")
        print(f"   ✅ Target: <100ms - {'PASS' if elapsed < 0.1 else 'FAIL'}")

    def test_index_build_10k_files(self):
        """Benchmark: Index 10,000 files"""
        files = self.benchmark.create_test_files(self.root, 10000)

        indexer = FileIndexer(cache_dir=Path(self.temp_dir) / 'cache')

        elapsed, index = self.benchmark.measure_time(
            indexer.build_index, self.root
        )

        self.assertEqual(index.file_count, 10000)

        # Performance target: <1s for 10K files
        self.assertLess(elapsed, 1.0)

        files_per_sec = index.file_count / elapsed

        print(f"\n📊 Index Build (10K files):")
        print(f"   Time: {elapsed*1000:.2f}ms ({elapsed:.2f}s)")
        print(f"   Speed: {files_per_sec:.0f} files/s")
        print(f"   ✅ Target: <1s - {'PASS' if elapsed < 1.0 else 'FAIL'}")

    def test_incremental_update_performance(self):
        """Benchmark: Incremental file updates"""
        files = self.benchmark.create_test_files(self.root, 1000)

        indexer = FileIndexer(cache_dir=Path(self.temp_dir) / 'cache')
        index = indexer.build_index(self.root)

        # Add new file
        new_file = self.root / 'new_file.txt'
        new_file.write_text('new content')

        elapsed, success = self.benchmark.measure_time(
            indexer.update_file, self.root, new_file
        )

        self.assertTrue(success)

        # Performance target: <10ms for single file update
        self.assertLess(elapsed, 0.01)

        print(f"\n📊 Incremental Update:")
        print(f"   Time: {elapsed*1000:.2f}ms")
        print(f"   ✅ Target: <10ms - {'PASS' if elapsed < 0.01 else 'FAIL'}")


class TestSearchQueryPerformance(unittest.TestCase):
    """Benchmark search query performance"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.benchmark = PerformanceBenchmark()

        # Create test files
        self.benchmark.create_test_files(self.root, 10000)

        self.searcher = AdvancedFileSearch()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_exact_search_performance(self):
        """Benchmark: Exact filename search"""
        options = AdvancedSearchOptions(use_index=True)

        # Build index first
        self.searcher.indexer.build_index(self.root)

        elapsed, results = self.benchmark.measure_time(
            self.searcher.search_files,
            self.root, 'file5000.txt', options
        )

        self.assertEqual(len(results), 1)

        # Performance target: <10ms for exact search
        self.assertLess(elapsed, 0.01)

        print(f"\n📊 Exact Search (10K files):")
        print(f"   Time: {elapsed*1000:.2f}ms")
        print(f"   ✅ Target: <10ms - {'PASS' if elapsed < 0.01 else 'FAIL'}")

    def test_wildcard_search_performance(self):
        """Benchmark: Wildcard search"""
        options = AdvancedSearchOptions(use_index=True)

        # Build index
        self.searcher.indexer.build_index(self.root)

        elapsed, results = self.benchmark.measure_time(
            self.searcher.search_files,
            self.root, 'file5*.txt', options
        )

        self.assertGreater(len(results), 0)

        # Performance target: <50ms for wildcard search
        self.assertLess(elapsed, 0.05)

        print(f"\n📊 Wildcard Search (10K files):")
        print(f"   Time: {elapsed*1000:.2f}ms")
        print(f"   Results: {len(results)}")
        print(f"   ✅ Target: <50ms - {'PASS' if elapsed < 0.05 else 'FAIL'}")

    def test_fuzzy_search_performance(self):
        """Benchmark: Fuzzy search"""
        options = AdvancedSearchOptions(fuzzy_threshold=0.5)

        elapsed, results = self.benchmark.measure_time(
            self.searcher.search_fuzzy,
            self.root, 'file5000', options
        )

        self.assertGreater(len(results), 0)

        # Performance target: <200ms for fuzzy search
        self.assertLess(elapsed, 0.2)

        print(f"\n📊 Fuzzy Search (10K files):")
        print(f"   Time: {elapsed*1000:.2f}ms")
        print(f"   Results: {len(results)}")
        print(f"   ✅ Target: <200ms - {'PASS' if elapsed < 0.2 else 'FAIL'}")

    def test_regex_search_performance(self):
        """Benchmark: Regex search"""
        options = AdvancedSearchOptions(use_index=True)

        # Build index
        self.searcher.indexer.build_index(self.root)

        elapsed, results = self.benchmark.measure_time(
            self.searcher.search_regex,
            self.root, r'file\d{4}\.txt', options
        )

        self.assertGreater(len(results), 0)

        # Performance target: <100ms for regex search
        self.assertLess(elapsed, 0.1)

        print(f"\n📊 Regex Search (10K files):")
        print(f"   Time: {elapsed*1000:.2f}ms")
        print(f"   Results: {len(results)}")
        print(f"   ✅ Target: <100ms - {'PASS' if elapsed < 0.1 else 'FAIL'}")


class TestCachePerformance(unittest.TestCase):
    """Benchmark cache performance"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.benchmark = PerformanceBenchmark()

        self.benchmark.create_test_files(self.root, 1000)
        self.searcher = AdvancedFileSearch()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_cache_hit_performance(self):
        """Benchmark: Cache hit performance"""
        options = AdvancedSearchOptions(use_cache=True, use_index=True)

        # First search (cache miss)
        elapsed_miss, results1 = self.benchmark.measure_time(
            self.searcher.search_files,
            self.root, 'file*.txt', options
        )

        # Second search (cache hit)
        elapsed_hit, results2 = self.benchmark.measure_time(
            self.searcher.search_files,
            self.root, 'file*.txt', options
        )

        self.assertEqual(len(results1), len(results2))

        # Cache hit should be faster
        speedup = elapsed_miss / elapsed_hit if elapsed_hit > 0 else 0

        # Performance target: <10ms for cache hit
        self.assertLess(elapsed_hit, 0.01)

        print(f"\n📊 Cache Performance:")
        print(f"   Cache Miss: {elapsed_miss*1000:.2f}ms")
        print(f"   Cache Hit: {elapsed_hit*1000:.2f}ms")
        print(f"   Speedup: {speedup:.1f}x")
        print(f"   ✅ Target: <10ms - {'PASS' if elapsed_hit < 0.01 else 'FAIL'}")

    def test_cache_storage_performance(self):
        """Benchmark: Cache storage operations"""
        cache = SearchResultCache(max_entries=10000)

        # Store performance
        elapsed_store, _ = self.benchmark.measure_time(
            lambda: [cache.set(f'key{i}', f'value{i}') for i in range(1000)]
        )

        # Retrieve performance
        elapsed_get, _ = self.benchmark.measure_time(
            lambda: [cache.get(f'key{i}') for i in range(1000)]
        )

        print(f"\n📊 Cache Operations (1K entries):")
        print(f"   Store: {elapsed_store*1000:.2f}ms ({1000/elapsed_store:.0f} ops/s)")
        print(f"   Retrieve: {elapsed_get*1000:.2f}ms ({1000/elapsed_get:.0f} ops/s)")


class TestMemoryUsage(unittest.TestCase):
    """Benchmark memory usage"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.benchmark = PerformanceBenchmark()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_index_memory_usage(self):
        """Benchmark: Index memory usage"""
        # Create test files
        self.benchmark.create_test_files(self.root, 10000)

        indexer = FileIndexer(cache_dir=Path(self.temp_dir) / 'cache')
        index = indexer.build_index(self.root)

        # Estimate memory usage
        entry_size = sys.getsizeof(index.entries[0]) if index.entries else 0
        entries_mb = (len(index.entries) * entry_size) / (1024 * 1024)

        indices_mb = (
            sys.getsizeof(index.name_index) +
            sys.getsizeof(index.extension_index) +
            sys.getsizeof(index.trigram_index)
        ) / (1024 * 1024)

        total_mb = entries_mb + indices_mb

        # Performance target: <10MB for 10K files
        self.assertLess(total_mb, 10)

        print(f"\n📊 Memory Usage (10K files):")
        print(f"   Entries: {entries_mb:.2f}MB")
        print(f"   Indices: {indices_mb:.2f}MB")
        print(f"   Total: {total_mb:.2f}MB")
        print(f"   ✅ Target: <10MB - {'PASS' if total_mb < 10 else 'FAIL'}")

    def test_cache_memory_usage(self):
        """Benchmark: Cache memory usage"""
        cache = SearchResultCache(max_entries=1000, max_memory_mb=50)

        # Fill cache
        for i in range(1000):
            cache.set(f'key{i}', ['result'] * 10)

        stats = cache.get_stats()
        memory_mb = stats['memory_mb']

        # Should stay within limit
        self.assertLess(memory_mb, 50)

        print(f"\n📊 Cache Memory (1K entries):")
        print(f"   Used: {memory_mb:.2f}MB")
        print(f"   Limit: {stats['max_memory_mb']:.2f}MB")
        print(f"   Utilization: {(memory_mb/stats['max_memory_mb']*100):.1f}%")


class TestComparisons(unittest.TestCase):
    """Compare indexed vs non-indexed performance"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.benchmark = PerformanceBenchmark()

        self.benchmark.create_test_files(self.root, 5000)
        self.searcher = AdvancedFileSearch()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_indexed_vs_traditional(self):
        """Compare indexed vs traditional search"""

        # Traditional search
        options_trad = AdvancedSearchOptions(use_index=False, use_cache=False)
        elapsed_trad, results_trad = self.benchmark.measure_time(
            self.searcher.search_files,
            self.root, 'file5*.txt', options_trad
        )

        # Indexed search
        options_idx = AdvancedSearchOptions(use_index=True, use_cache=False)
        elapsed_idx, results_idx = self.benchmark.measure_time(
            self.searcher.search_files,
            self.root, 'file5*.txt', options_idx
        )

        speedup = elapsed_trad / elapsed_idx if elapsed_idx > 0 else 0

        print(f"\n📊 Indexed vs Traditional (5K files):")
        print(f"   Traditional: {elapsed_trad*1000:.2f}ms")
        print(f"   Indexed: {elapsed_idx*1000:.2f}ms")
        print(f"   Speedup: {speedup:.1f}x")
        print(f"   ✅ Target: >5x speedup - {'PASS' if speedup > 5 else 'FAIL'}")


class TestScalability(unittest.TestCase):
    """Test scalability with large datasets"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.benchmark = PerformanceBenchmark()

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    @unittest.skipUnless(
        '--stress' in sys.argv,
        "Skipping stress test (use --stress to run)"
    )
    def test_stress_100k_files(self):
        """Stress test: 100K files"""
        print(f"\n⚠️  Creating 100K test files (this may take a while)...")

        files = self.benchmark.create_test_files(self.root, 100000)

        indexer = FileIndexer(cache_dir=Path(self.temp_dir) / 'cache')

        elapsed, index = self.benchmark.measure_time(
            indexer.build_index, self.root
        )

        # Performance target: <10s for 100K files
        self.assertLess(elapsed, 10.0)

        files_per_sec = index.file_count / elapsed

        print(f"\n📊 Stress Test (100K files):")
        print(f"   Index Build: {elapsed:.2f}s")
        print(f"   Speed: {files_per_sec:.0f} files/s")
        print(f"   ✅ Target: <10s - {'PASS' if elapsed < 10.0 else 'FAIL'}")


def print_summary():
    """Print performance benchmark summary"""
    print("\n" + "="*60)
    print("🎯 PERFORMANCE TARGETS SUMMARY")
    print("="*60)
    print("\nIndex Build:")
    print("  ✓ 1K files:    <100ms")
    print("  ✓ 10K files:   <1s")
    print("  ✓ 100K files:  <10s (stress test)")
    print("\nSearch Performance:")
    print("  ✓ Exact:       <10ms")
    print("  ✓ Wildcard:    <50ms")
    print("  ✓ Fuzzy:       <200ms")
    print("  ✓ Regex:       <100ms")
    print("  ✓ Cache Hit:   <10ms")
    print("\nMemory Usage:")
    print("  ✓ 10K files:   <10MB")
    print("  ✓ 100K files:  <100MB")
    print("\nIncremental Updates:")
    print("  ✓ Single file: <10ms")
    print("="*60)


if __name__ == '__main__':
    print_summary()
    unittest.main()
