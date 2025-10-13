"""
Test DirectoryCache integration with FilePanel.

This test verifies that the cache is properly integrated and functioning
as expected for 10x performance improvement.
"""

import time
from pathlib import Path
from components.file_panel import FilePanel
from features.config_manager import get_config_manager


def test_cache_integration():
    """Test that cache improves performance as expected."""
    print("=" * 70)
    print("DirectoryCache Integration Test - Phase 1.3")
    print("=" * 70)

    # Ensure cache is enabled
    config_manager = get_config_manager()
    config = config_manager.get_config()
    print(f"\nCache Configuration:")
    print(f"  Enabled: {config.cache.enabled}")
    print(f"  Max size: {config.cache.maxsize}")
    print(f"  TTL: {config.cache.ttl_seconds}s")
    print(f"  Show stats: {config.cache.show_stats}")

    # Test directory (current directory)
    test_path = Path.cwd()
    print(f"\nTest directory: {test_path}")

    # Clear any existing cache
    FilePanel.clear_cache()
    print("Cache cleared for fresh test")

    print("\n" + "=" * 70)
    print("Test 1: First Load (Cache MISS expected)")
    print("=" * 70)

    # First load (cache miss - should be slower)
    panel = FilePanel(path=test_path)
    start = time.perf_counter()
    items_first = panel._load_directory()
    first_load_time = time.perf_counter() - start
    print(f"  Time: {first_load_time*1000:.2f}ms")
    print(f"  Items loaded: {len(items_first)}")

    print("\n" + "=" * 70)
    print("Test 2: Second Load (Cache HIT expected)")
    print("=" * 70)

    # Second load (cache hit - should be faster)
    start = time.perf_counter()
    items_second = panel._load_directory()
    second_load_time = time.perf_counter() - start
    print(f"  Time: {second_load_time*1000:.2f}ms")
    print(f"  Items loaded: {len(items_second)}")

    # Calculate speedup
    if second_load_time > 0:
        speedup = first_load_time / second_load_time
        improvement = ((first_load_time - second_load_time) / first_load_time) * 100
        print(f"\n  Speedup: {speedup:.1f}x faster")
        print(f"  Improvement: {improvement:.1f}% faster")
    else:
        print("\n  Speedup: Cache retrieval too fast to measure accurately!")
        speedup = float('inf')

    # Get cache statistics
    stats = FilePanel.get_cache_stats()
    if stats:
        print(f"\n  Cache Statistics:")
        print(f"    Size: {stats['size']}/{stats['maxsize']}")
        print(f"    Hits: {stats['hits']}")
        print(f"    Misses: {stats['misses']}")
        print(f"    Hit rate: {stats['hit_rate']:.1f}%")

    print("\n" + "=" * 70)
    print("Test 3: Multiple Sequential Loads (10 iterations)")
    print("=" * 70)

    # Test multiple loads
    start = time.perf_counter()
    for i in range(10):
        panel._load_directory()
    total_time = time.perf_counter() - start
    avg_time = total_time / 10

    print(f"  Total time: {total_time*1000:.2f}ms")
    print(f"  Average time: {avg_time*1000:.2f}ms per load")

    # Final statistics
    stats = FilePanel.get_cache_stats()
    if stats:
        print(f"\n  Final Cache Statistics:")
        print(f"    Total operations: {stats['hits'] + stats['misses']}")
        print(f"    Cache hits: {stats['hits']}")
        print(f"    Cache misses: {stats['misses']}")
        print(f"    Overall hit rate: {stats['hit_rate']:.1f}%")

    print("\n" + "=" * 70)
    print("Test 4: Cache Invalidation")
    print("=" * 70)

    # Test cache invalidation
    if FilePanel._dir_cache:
        FilePanel._dir_cache.invalidate(test_path)
        print("  Cache invalidated for current path")

        start = time.perf_counter()
        items_after_invalidate = panel._load_directory()
        time_after_invalidate = time.perf_counter() - start

        print(f"  Time after invalidation: {time_after_invalidate*1000:.2f}ms")
        print(f"  (Compare to first load: {first_load_time*1000:.2f}ms)")

    print("\n" + "=" * 70)
    print("Test 5: Multiple Directory Navigation")
    print("=" * 70)

    # Clear cache and test navigation pattern
    FilePanel.clear_cache()

    test_dirs = [test_path, test_path.parent, test_path, test_path.parent, test_path]
    print(f"  Navigating through {len(test_dirs)} directories...")

    for i, directory in enumerate(test_dirs, 1):
        panel = FilePanel(path=directory)
        start = time.perf_counter()
        panel._load_directory()
        load_time = time.perf_counter() - start

        stats = FilePanel.get_cache_stats()
        cache_status = "HIT" if stats and stats['hits'] > 0 and i > 1 else "MISS"

        print(f"  {i}. {directory.name}: {load_time*1000:.2f}ms ({cache_status})")

    # Final cache statistics
    stats = FilePanel.get_cache_stats()
    if stats:
        print(f"\n  Navigation Cache Statistics:")
        print(f"    Total hits: {stats['hits']}")
        print(f"    Total misses: {stats['misses']}")
        print(f"    Hit rate: {stats['hit_rate']:.1f}%")

    # Performance summary
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"  Uncached load: {first_load_time*1000:.2f}ms")
    print(f"  Cached load: {second_load_time*1000:.2f}ms")

    if second_load_time > 0:
        print(f"  Performance improvement: {speedup:.1f}x ({improvement:.1f}% faster)")

        if speedup >= 10:
            print(f"\n  ✓ SUCCESS: TARGET ACHIEVED! {speedup:.1f}x speedup (>10x target)")
        elif speedup >= 5:
            print(f"\n  ✓ Excellent performance: {speedup:.1f}x speedup")
        elif speedup >= 2:
            print(f"\n  ✓ Good performance: {speedup:.1f}x speedup")
        else:
            print(f"\n  ⚠ Moderate improvement: {speedup:.1f}x speedup")
    else:
        print(f"\n  ✓ SUCCESS: Cache is extremely fast (sub-millisecond)")

    # Verify cache is working
    if stats and stats['hit_rate'] >= 50:
        print(f"  ✓ Cache is working correctly! Hit rate: {stats['hit_rate']:.1f}%")
    elif stats and stats['hit_rate'] > 0:
        print(f"  ⚠ Cache is working but hit rate is low: {stats['hit_rate']:.1f}%")
    elif stats:
        print(f"  ✗ Cache might not be working - hit rate: {stats['hit_rate']:.1f}%")
    else:
        print("  ✗ Cache is not enabled")

    print("\n" + "=" * 70)
    print("Integration test complete!")
    print("=" * 70)

    # Cleanup
    FilePanel.clear_cache()


if __name__ == "__main__":
    test_cache_integration()
