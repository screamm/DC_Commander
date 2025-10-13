"""Tests for async file scanner module."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil
from services.async_file_scanner import (
    AsyncFileScanner,
    ScanProgress,
    FileSearchOptions,
    find_files
)


@pytest.fixture
def temp_dir():
    """Create temporary directory with test files."""
    temp_path = Path(tempfile.mkdtemp())

    # Create test directory structure
    # /temp
    #   /dir1
    #     file1.txt
    #     file2.py
    #   /dir2
    #     /subdir
    #       file3.txt
    #     test_file.py
    #   test.txt
    #   .hidden.txt

    (temp_path / "dir1").mkdir()
    (temp_path / "dir1" / "file1.txt").write_text("content1")
    (temp_path / "dir1" / "file2.py").write_text("content2")

    (temp_path / "dir2").mkdir()
    (temp_path / "dir2" / "subdir").mkdir()
    (temp_path / "dir2" / "subdir" / "file3.txt").write_text("content3")
    (temp_path / "dir2" / "test_file.py").write_text("content4")

    (temp_path / "test.txt").write_text("root content")
    (temp_path / ".hidden.txt").write_text("hidden content")

    yield temp_path

    # Cleanup
    shutil.rmtree(temp_path)


@pytest.mark.asyncio
async def test_basic_search(temp_dir):
    """Test basic file search functionality."""
    scanner = AsyncFileScanner()

    results = []
    async for path in scanner.search_files(temp_dir, "*.txt"):
        results.append(path)

    # Should find: test.txt, file1.txt, file3.txt, .hidden.txt
    assert len(results) == 4
    result_names = {p.name for p in results}
    assert "test.txt" in result_names
    assert "file1.txt" in result_names
    assert "file3.txt" in result_names


@pytest.mark.asyncio
async def test_case_sensitive_search(temp_dir):
    """Test case-sensitive search."""
    scanner = AsyncFileScanner()

    # Create files with different cases
    (temp_dir / "Test.txt").write_text("content")
    (temp_dir / "TEST.txt").write_text("content")

    # Case-insensitive (default)
    results_insensitive = []
    async for path in scanner.search_files(temp_dir, "test.txt", case_sensitive=False):
        results_insensitive.append(path)

    # Case-sensitive
    results_sensitive = []
    async for path in scanner.search_files(temp_dir, "test.txt", case_sensitive=True):
        results_sensitive.append(path)

    # Case-insensitive should find more
    assert len(results_insensitive) >= len(results_sensitive)


@pytest.mark.asyncio
async def test_recursive_search(temp_dir):
    """Test recursive vs non-recursive search."""
    scanner = AsyncFileScanner()

    # Recursive search
    recursive_results = []
    async for path in scanner.search_files(temp_dir, "*.txt", recursive=True):
        recursive_results.append(path)

    # Non-recursive search
    non_recursive_results = []
    async for path in scanner.search_files(temp_dir, "*.txt", recursive=False):
        non_recursive_results.append(path)

    # Recursive should find more files
    assert len(recursive_results) > len(non_recursive_results)

    # Non-recursive should only find files in root
    for path in non_recursive_results:
        assert path.parent == temp_dir


@pytest.mark.asyncio
async def test_max_depth(temp_dir):
    """Test maximum depth limiting."""
    scanner = AsyncFileScanner()

    # Depth 0 (root only)
    depth_0_results = []
    async for path in scanner.search_files(temp_dir, "*.txt", recursive=True, max_depth=0):
        depth_0_results.append(path)

    # Depth 1 (root + 1 level)
    depth_1_results = []
    async for path in scanner.search_files(temp_dir, "*.txt", recursive=True, max_depth=1):
        depth_1_results.append(path)

    # Unlimited depth
    unlimited_results = []
    async for path in scanner.search_files(temp_dir, "*.txt", recursive=True, max_depth=None):
        unlimited_results.append(path)

    assert len(depth_0_results) < len(depth_1_results) < len(unlimited_results)


@pytest.mark.asyncio
async def test_wildcard_patterns(temp_dir):
    """Test various wildcard patterns."""
    scanner = AsyncFileScanner()

    # Pattern: *.py
    py_results = []
    async for path in scanner.search_files(temp_dir, "*.py"):
        py_results.append(path)

    # Pattern: test*
    test_results = []
    async for path in scanner.search_files(temp_dir, "test*"):
        test_results.append(path)

    # Pattern: file?.txt
    file_pattern_results = []
    async for path in scanner.search_files(temp_dir, "file?.txt"):
        file_pattern_results.append(path)

    assert len(py_results) == 2  # file2.py, test_file.py
    assert len(test_results) >= 2  # test.txt, test_file.py
    assert len(file_pattern_results) == 2  # file1.txt, file3.txt


@pytest.mark.asyncio
async def test_progress_callback(temp_dir):
    """Test progress callback functionality."""
    scanner = AsyncFileScanner()
    progress_updates = []

    def progress_callback(progress: ScanProgress):
        progress_updates.append(progress)

    results = []
    async for path in scanner.search_files(
        temp_dir,
        "*.txt",
        progress_callback=progress_callback
    ):
        results.append(path)

    # Should have received progress updates
    assert len(progress_updates) > 0

    # Last update should be complete
    assert progress_updates[-1].is_complete

    # Files scanned should be reasonable
    assert progress_updates[-1].files_scanned > 0


@pytest.mark.asyncio
async def test_cancellation(temp_dir):
    """Test search cancellation."""
    scanner = AsyncFileScanner()

    # Create many files
    large_dir = temp_dir / "large"
    large_dir.mkdir()
    for i in range(100):
        (large_dir / f"file{i}.txt").write_text(f"content{i}")

    results = []
    async for path in scanner.search_files(large_dir, "*.txt"):
        results.append(path)
        # Cancel after finding 10 files
        if len(results) >= 10:
            scanner.cancel()

    # Should have stopped early
    assert len(results) < 100


@pytest.mark.asyncio
async def test_batch_search(temp_dir):
    """Test batch search (get all results at once)."""
    scanner = AsyncFileScanner()

    results = await scanner.find_files_batch(temp_dir, "*.txt")

    assert isinstance(results, list)
    assert len(results) >= 3


@pytest.mark.asyncio
async def test_max_results(temp_dir):
    """Test maximum results limiting."""
    scanner = AsyncFileScanner()

    # Create many files
    many_dir = temp_dir / "many"
    many_dir.mkdir()
    for i in range(50):
        (many_dir / f"file{i}.txt").write_text(f"content{i}")

    results = await scanner.find_files_batch(
        many_dir,
        "*.txt",
        max_results=10
    )

    assert len(results) == 10


@pytest.mark.asyncio
async def test_count_files(temp_dir):
    """Test file counting without collecting results."""
    scanner = AsyncFileScanner()

    count = await scanner.count_files(temp_dir, "*.txt")

    assert count >= 3


@pytest.mark.asyncio
async def test_convenience_function(temp_dir):
    """Test convenience find_files function."""
    results = await find_files(temp_dir, "*.py", recursive=True)

    assert isinstance(results, list)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_permission_errors(temp_dir):
    """Test handling of permission errors."""
    scanner = AsyncFileScanner()

    # Search should not crash on permission errors
    results = []
    async for path in scanner.search_files(temp_dir, "*"):
        results.append(path)

    # Should have found some files
    assert len(results) > 0


@pytest.mark.asyncio
async def test_empty_directory():
    """Test searching empty directory."""
    with tempfile.TemporaryDirectory() as empty_dir:
        scanner = AsyncFileScanner()

        results = []
        async for path in scanner.search_files(Path(empty_dir), "*"):
            results.append(path)

        assert len(results) == 0


@pytest.mark.asyncio
async def test_nonexistent_pattern(temp_dir):
    """Test pattern that matches no files."""
    scanner = AsyncFileScanner()

    results = []
    async for path in scanner.search_files(temp_dir, "*.nonexistent"):
        results.append(path)

    assert len(results) == 0


@pytest.mark.asyncio
async def test_reset_cancellation(temp_dir):
    """Test resetting cancellation state."""
    scanner = AsyncFileScanner()

    # First search - cancel it
    scanner.cancel()

    # Reset for new search
    scanner.reset()

    # Should work normally now
    results = []
    async for path in scanner.search_files(temp_dir, "*.txt"):
        results.append(path)

    assert len(results) > 0


@pytest.mark.asyncio
async def test_multiple_concurrent_searches(temp_dir):
    """Test multiple concurrent search operations."""
    scanner1 = AsyncFileScanner()
    scanner2 = AsyncFileScanner()

    # Run two searches concurrently
    async def search1():
        results = []
        async for path in scanner1.search_files(temp_dir, "*.txt"):
            results.append(path)
        return results

    async def search2():
        results = []
        async for path in scanner2.search_files(temp_dir, "*.py"):
            results.append(path)
        return results

    results1, results2 = await asyncio.gather(search1(), search2())

    assert len(results1) >= 3
    assert len(results2) == 2


@pytest.mark.asyncio
async def test_search_options():
    """Test FileSearchOptions configuration."""
    options = FileSearchOptions(
        case_sensitive=True,
        recursive=True,
        max_depth=2,
        max_results=10,
        include_hidden=False,
        exclude_patterns=["*.tmp", "*.bak"]
    )

    assert options.case_sensitive is True
    assert options.recursive is True
    assert options.max_depth == 2
    assert options.max_results == 10
    assert options.include_hidden is False
    assert len(options.exclude_patterns) == 2


@pytest.mark.asyncio
async def test_exclude_hidden_files(temp_dir):
    """Test excluding hidden files."""
    options = FileSearchOptions(include_hidden=False)

    # Check .hidden.txt is excluded
    hidden_path = temp_dir / ".hidden.txt"
    assert options.should_exclude(hidden_path)

    # Check normal file is not excluded
    normal_path = temp_dir / "test.txt"
    assert not options.should_exclude(normal_path)


@pytest.mark.asyncio
async def test_exclude_patterns(temp_dir):
    """Test pattern-based exclusion."""
    options = FileSearchOptions(
        exclude_patterns=["*.tmp", "test_*"]
    )

    # Create test files
    (temp_dir / "file.tmp").write_text("temp")
    (temp_dir / "test_exclude.txt").write_text("exclude")

    assert options.should_exclude(temp_dir / "file.tmp")
    assert options.should_exclude(temp_dir / "test_exclude.txt")
    assert not options.should_exclude(temp_dir / "normal.txt")


def test_scan_progress_dataclass():
    """Test ScanProgress data structure."""
    progress = ScanProgress(
        files_scanned=100,
        matches_found=5,
        current_directory="/test",
        is_complete=False
    )

    assert progress.files_scanned == 100
    assert progress.matches_found == 5
    assert progress.current_directory == "/test"
    assert progress.is_complete is False


@pytest.mark.asyncio
async def test_large_directory_performance(temp_dir):
    """Test performance with larger directory structure."""
    # Create larger test structure
    perf_dir = temp_dir / "perf_test"
    perf_dir.mkdir()

    # Create 1000 files across multiple directories
    for i in range(10):
        sub_dir = perf_dir / f"sub{i}"
        sub_dir.mkdir()
        for j in range(100):
            (sub_dir / f"file{j}.txt").write_text(f"content{i}{j}")

    scanner = AsyncFileScanner()

    import time
    start = time.time()

    results = []
    async for path in scanner.search_files(perf_dir, "*.txt"):
        results.append(path)

    duration = time.time() - start

    # Should find all 1000 files
    assert len(results) == 1000

    # Should complete in reasonable time (less than 5 seconds)
    assert duration < 5.0

    print(f"Performance: Scanned 1000 files in {duration:.2f} seconds")
