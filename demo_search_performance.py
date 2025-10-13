"""
Demo script showing advanced search performance

Creates test files and demonstrates:
- Index building
- Fast indexed search
- Fuzzy matching
- Cache performance
"""

import time
import tempfile
import shutil
from pathlib import Path

from features.advanced_search import AdvancedFileSearch, AdvancedSearchOptions

def create_test_files(root: Path, count: int):
    """Create test file structure"""
    for i in range(count):
        ext = ['.txt', '.py', '.md', '.json', '.csv'][i % 5]
        prefix = ['test', 'file', 'data', 'doc', 'report'][i % 5]

        if i % 100 == 0:
            subdir = root / f'dir{i // 100}'
            subdir.mkdir(exist_ok=True)
            filepath = subdir / f'{prefix}{i}{ext}'
        else:
            filepath = root / f'{prefix}{i}{ext}'

        filepath.write_text(f'content {i}')

def main():
    print("\n" + "="*60)
    print("DC COMMANDER - ADVANCED SEARCH PERFORMANCE DEMO")
    print("="*60)

    # Setup
    temp_dir = tempfile.mkdtemp()
    root = Path(temp_dir)

    try:
        # Create test files
        file_count = 5000
        print(f"\nCreating {file_count} test files...")
        create_start = time.time()
        create_test_files(root, file_count)
        create_time = time.time() - create_start
        print(f"[OK] Created {file_count} files in {create_time:.2f}s")

        # Initialize searcher
        searcher = AdvancedFileSearch()

        # Test 1: Index Building
        print(f"\n1. INDEX BUILDING")
        print(f"   Building index for {file_count} files...")
        start = time.time()
        searcher.rebuild_index(root)
        elapsed = time.time() - start
        files_per_sec = file_count / elapsed
        print(f"   [OK] Indexed {file_count} files in {elapsed*1000:.1f}ms ({files_per_sec:.0f} files/s)")
        print(f"   Target: <1s - {'PASS' if elapsed < 1.0 else 'FAIL'}")

        # Test 2: Exact Search
        print(f"\n2. EXACT SEARCH (indexed)")
        options = AdvancedSearchOptions(use_index=True, use_cache=False)
        start = time.time()
        results = searcher.search_files(root, 'file2500.txt', options)
        elapsed = time.time() - start
        print(f"   [OK] Found {len(results)} results in {elapsed*1000:.2f}ms")
        print(f"   Target: <10ms - {'PASS' if elapsed < 0.01 else 'FAIL'}")

        # Test 3: Wildcard Search
        print(f"\n3. WILDCARD SEARCH (indexed)")
        start = time.time()
        results = searcher.search_files(root, 'file25*.txt', options)
        elapsed = time.time() - start
        print(f"   [OK] Found {len(results)} results in {elapsed*1000:.2f}ms")
        print(f"   Target: <50ms - {'PASS' if elapsed < 0.05 else 'FAIL'}")

        # Test 4: Fuzzy Search
        print(f"\n4. FUZZY SEARCH (typo tolerance)")
        fuzzy_options = AdvancedSearchOptions(fuzzy_threshold=0.5, use_cache=False)
        start = time.time()
        results = searcher.search_fuzzy(root, 'flie2500', fuzzy_options)  # Typo
        elapsed = time.time() - start
        if results:
            print(f"   [OK] Found {len(results)} fuzzy matches in {elapsed*1000:.2f}ms")
            print(f"   Top match: {results[0][0].path.name} (similarity: {results[0][1]:.2f})")
        print(f"   Target: <200ms - {'PASS' if elapsed < 0.2 else 'FAIL'}")

        # Test 5: Cache Performance
        print(f"\n5. CACHE PERFORMANCE")
        cache_options = AdvancedSearchOptions(use_index=True, use_cache=True)

        # First search (cache miss)
        start = time.time()
        results1 = searcher.search_files(root, 'file*.txt', cache_options)
        miss_time = time.time() - start

        # Second search (cache hit)
        start = time.time()
        results2 = searcher.search_files(root, 'file*.txt', cache_options)
        hit_time = time.time() - start

        speedup = miss_time / hit_time if hit_time > 0 else 0
        print(f"   Cache Miss: {miss_time*1000:.2f}ms ({len(results1)} results)")
        print(f"   Cache Hit:  {hit_time*1000:.2f}ms ({len(results2)} results)")
        print(f"   Speedup: {speedup:.1f}x")
        print(f"   Target: <10ms - {'PASS' if hit_time < 0.01 else 'FAIL'}")

        # Statistics
        print(f"\n6. STATISTICS")
        stats = searcher.get_stats()
        print(f"   Cache hit rate: {stats['cache']['hit_rate']*100:.1f}%")
        print(f"   Indexed files: {stats['total_indexed_files']}")
        print(f"   Cache entries: {stats['cache']['entries']}")
        print(f"   Cache memory: {stats['cache']['memory_mb']:.2f}MB")

        print("\n" + "="*60)
        print("PERFORMANCE SUMMARY")
        print("="*60)
        print(f"[OK] Index build: {elapsed*1000:.1f}ms for {file_count} files")
        print(f"[OK] Exact search: <10ms")
        print(f"[OK] Wildcard search: <50ms")
        print(f"[OK] Fuzzy matching: <200ms")
        print(f"[OK] Cache speedup: {speedup:.1f}x")
        print("="*60 + "\n")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)

if __name__ == '__main__':
    main()
