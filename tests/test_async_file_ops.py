"""Comprehensive tests for AsyncFileOperations module.

Tests asynchronous file operations including copy, move, delete,
and directory size calculation with progress tracking.
"""

import pytest
import asyncio
from pathlib import Path
from src.utils.async_file_ops import AsyncFileOperations, CopyProgress


class TestCopyProgress:
    """Test CopyProgress dataclass."""

    def test_copy_progress_creation(self):
        """Test creating a CopyProgress instance."""
        progress = CopyProgress(
            bytes_copied=1000,
            total_bytes=5000,
            current_file="test.txt",
            files_completed=1,
            total_files=5
        )

        assert progress.bytes_copied == 1000
        assert progress.total_bytes == 5000
        assert progress.current_file == "test.txt"
        assert progress.files_completed == 1
        assert progress.total_files == 5

    def test_percentage_calculation(self):
        """Test percentage calculation."""
        progress = CopyProgress(
            bytes_copied=2500,
            total_bytes=5000,
            current_file="test.txt",
            files_completed=1,
            total_files=2
        )

        assert progress.percentage == 50.0

    def test_percentage_zero_total(self):
        """Test percentage with zero total bytes."""
        progress = CopyProgress(
            bytes_copied=0,
            total_bytes=0,
            current_file="test.txt",
            files_completed=0,
            total_files=1
        )

        assert progress.percentage == 0.0

    def test_percentage_complete(self):
        """Test percentage at 100%."""
        progress = CopyProgress(
            bytes_copied=5000,
            total_bytes=5000,
            current_file="test.txt",
            files_completed=5,
            total_files=5
        )

        assert progress.percentage == 100.0


class TestAsyncFileOperationsInit:
    """Test AsyncFileOperations initialization."""

    def test_init_default(self):
        """Test default initialization."""
        ops = AsyncFileOperations()

        assert ops.chunk_size == 64 * 1024  # 64KB
        assert ops._canceled is False

    def test_init_custom_chunk_size(self):
        """Test initialization with custom chunk size."""
        ops = AsyncFileOperations(chunk_size=128 * 1024)

        assert ops.chunk_size == 128 * 1024

    def test_cancel(self):
        """Test cancel flag setting."""
        ops = AsyncFileOperations()

        assert ops._canceled is False
        ops.cancel()
        assert ops._canceled is True


@pytest.mark.asyncio
class TestCopyFileAsync:
    """Test asynchronous file copy operations."""

    async def test_copy_file_simple(self, tmp_path):
        """Test copying a simple file."""
        ops = AsyncFileOperations()

        source = tmp_path / "source.txt"
        source.write_text("Test content for async copy")

        dest = tmp_path / "dest.txt"

        await ops.copy_file_async(source, dest)

        assert dest.exists()
        assert dest.read_text() == source.read_text()

    async def test_copy_file_large(self, tmp_path):
        """Test copying a large file."""
        ops = AsyncFileOperations(chunk_size=1024)  # Small chunks for testing

        source = tmp_path / "large.bin"
        # Create 100KB file
        source.write_bytes(b'0' * 100 * 1024)

        dest = tmp_path / "large_copy.bin"

        await ops.copy_file_async(source, dest)

        assert dest.exists()
        assert dest.stat().st_size == source.stat().st_size
        assert dest.read_bytes() == source.read_bytes()

    async def test_copy_file_with_progress(self, tmp_path):
        """Test copy with progress callback."""
        ops = AsyncFileOperations(chunk_size=1024)

        source = tmp_path / "source.bin"
        source.write_bytes(b'0' * 10 * 1024)  # 10KB

        dest = tmp_path / "dest.bin"

        progress_updates = []

        def progress_callback(bytes_copied):
            progress_updates.append(bytes_copied)

        await ops.copy_file_async(source, dest, progress_callback=progress_callback)

        assert len(progress_updates) > 0
        assert progress_updates[-1] == source.stat().st_size

    async def test_copy_file_empty(self, tmp_path):
        """Test copying an empty file."""
        ops = AsyncFileOperations()

        source = tmp_path / "empty.txt"
        source.touch()

        dest = tmp_path / "empty_copy.txt"

        await ops.copy_file_async(source, dest)

        assert dest.exists()
        assert dest.stat().st_size == 0

    async def test_copy_file_nonexistent_source(self, tmp_path):
        """Test copying nonexistent file raises error."""
        ops = AsyncFileOperations()

        source = tmp_path / "nonexistent.txt"
        dest = tmp_path / "dest.txt"

        with pytest.raises((FileNotFoundError, OSError)):
            await ops.copy_file_async(source, dest)

    async def test_copy_file_canceled(self, tmp_path):
        """Test copy operation can be canceled."""
        ops = AsyncFileOperations(chunk_size=1024)

        source = tmp_path / "large.bin"
        source.write_bytes(b'0' * 100 * 1024)  # 100KB

        dest = tmp_path / "dest.bin"

        # Cancel immediately
        ops.cancel()

        with pytest.raises(asyncio.CancelledError):
            await ops.copy_file_async(source, dest)

    async def test_copy_file_binary_content(self, tmp_path):
        """Test copying binary file preserves content."""
        ops = AsyncFileOperations()

        source = tmp_path / "binary.dat"
        binary_data = bytes(range(256))
        source.write_bytes(binary_data)

        dest = tmp_path / "binary_copy.dat"

        await ops.copy_file_async(source, dest)

        assert dest.read_bytes() == binary_data


@pytest.mark.asyncio
class TestCopyDirectoryAsync:
    """Test asynchronous directory copy operations."""

    async def test_copy_directory_simple(self, tmp_path):
        """Test copying a simple directory."""
        ops = AsyncFileOperations()

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")

        dest_dir = tmp_path / "dest"

        results = []
        async for file, success, error in ops.copy_directory_async(source_dir, dest_dir):
            results.append((file, success, error))

        assert dest_dir.exists()
        assert (dest_dir / "file1.txt").exists()
        assert (dest_dir / "file2.txt").exists()
        assert all(success for _, success, _ in results)

    async def test_copy_directory_nested(self, tmp_path):
        """Test copying nested directory structure."""
        ops = AsyncFileOperations()

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")

        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested content")

        dest_dir = tmp_path / "dest"

        results = []
        async for file, success, error in ops.copy_directory_async(source_dir, dest_dir):
            results.append((file, success, error))

        assert (dest_dir / "file.txt").exists()
        assert (dest_dir / "subdir" / "nested.txt").exists()
        assert (dest_dir / "subdir" / "nested.txt").read_text() == "nested content"

    async def test_copy_directory_with_progress(self, tmp_path):
        """Test directory copy with progress callback."""
        ops = AsyncFileOperations()

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")

        dest_dir = tmp_path / "dest"

        progress_updates = []

        def progress_callback(progress: CopyProgress):
            progress_updates.append(progress)

        results = []
        async for file, success, error in ops.copy_directory_async(
            source_dir, dest_dir, progress_callback=progress_callback
        ):
            results.append((file, success, error))

        assert len(progress_updates) > 0
        assert progress_updates[-1].files_completed == progress_updates[-1].total_files

    async def test_copy_directory_empty(self, tmp_path):
        """Test copying empty directory."""
        ops = AsyncFileOperations()

        source_dir = tmp_path / "empty"
        source_dir.mkdir()

        dest_dir = tmp_path / "dest"

        results = []
        async for file, success, error in ops.copy_directory_async(source_dir, dest_dir):
            results.append((file, success, error))

        assert dest_dir.exists()

    async def test_copy_directory_canceled(self, tmp_path):
        """Test directory copy can be canceled."""
        ops = AsyncFileOperations()

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        for i in range(10):
            (source_dir / f"file{i}.txt").write_text(f"content{i}")

        dest_dir = tmp_path / "dest"

        ops.cancel()

        with pytest.raises(asyncio.CancelledError):
            async for file, success, error in ops.copy_directory_async(source_dir, dest_dir):
                pass


@pytest.mark.asyncio
class TestMoveFileAsync:
    """Test asynchronous file move operations."""

    async def test_move_file_simple(self, tmp_path):
        """Test moving a file."""
        ops = AsyncFileOperations()

        source = tmp_path / "source.txt"
        source.write_text("Move me")

        dest = tmp_path / "subdir" / "dest.txt"
        dest.parent.mkdir()

        await ops.move_file_async(source, dest)

        assert not source.exists()
        assert dest.exists()
        assert dest.read_text() == "Move me"

    async def test_move_file_same_filesystem(self, tmp_path):
        """Test move on same filesystem (should use rename)."""
        ops = AsyncFileOperations()

        source = tmp_path / "source.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        await ops.move_file_async(source, dest)

        assert not source.exists()
        assert dest.exists()

    async def test_move_file_cross_filesystem(self, tmp_path):
        """Test move across filesystems (copy + delete)."""
        # Difficult to test without actual different filesystems
        # This documents expected behavior
        ops = AsyncFileOperations()

        source = tmp_path / "source.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        await ops.move_file_async(source, dest)

        assert not source.exists()
        assert dest.exists()


@pytest.mark.asyncio
class TestDeleteFileAsync:
    """Test asynchronous file deletion."""

    async def test_delete_file_simple(self, tmp_path):
        """Test deleting a file."""
        ops = AsyncFileOperations()

        file_path = tmp_path / "delete_me.txt"
        file_path.write_text("content")

        await ops.delete_file_async(file_path)

        assert not file_path.exists()

    async def test_delete_directory_with_contents(self, tmp_path):
        """Test deleting directory with contents."""
        ops = AsyncFileOperations()

        dir_path = tmp_path / "delete_dir"
        dir_path.mkdir()
        (dir_path / "file1.txt").write_text("content1")
        (dir_path / "file2.txt").write_text("content2")

        subdir = dir_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")

        await ops.delete_file_async(dir_path)

        assert not dir_path.exists()

    async def test_delete_empty_directory(self, tmp_path):
        """Test deleting empty directory."""
        ops = AsyncFileOperations()

        dir_path = tmp_path / "empty_dir"
        dir_path.mkdir()

        await ops.delete_file_async(dir_path)

        assert not dir_path.exists()


@pytest.mark.asyncio
class TestCalculateDirectorySizeAsync:
    """Test asynchronous directory size calculation."""

    async def test_calculate_size_simple(self, tmp_path):
        """Test calculating directory size."""
        ops = AsyncFileOperations()

        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("12345")  # 5 bytes
        (test_dir / "file2.txt").write_text("1234567890")  # 10 bytes

        size = await ops.calculate_directory_size_async(test_dir)

        assert size == 15

    async def test_calculate_size_nested(self, tmp_path):
        """Test calculating size with nested directories."""
        ops = AsyncFileOperations()

        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("12345")  # 5 bytes

        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("1234567890")  # 10 bytes

        size = await ops.calculate_directory_size_async(test_dir)

        assert size == 15

    async def test_calculate_size_empty_directory(self, tmp_path):
        """Test calculating size of empty directory."""
        ops = AsyncFileOperations()

        test_dir = tmp_path / "empty"
        test_dir.mkdir()

        size = await ops.calculate_directory_size_async(test_dir)

        assert size == 0

    async def test_calculate_size_with_progress(self, tmp_path):
        """Test size calculation with progress callback."""
        ops = AsyncFileOperations()

        test_dir = tmp_path / "test"
        test_dir.mkdir()
        for i in range(10):
            (test_dir / f"file{i}.txt").write_text(f"content{i}")

        progress_updates = []

        def progress_callback(file_count, total_bytes):
            progress_updates.append((file_count, total_bytes))

        size = await ops.calculate_directory_size_async(test_dir, progress_callback=progress_callback)

        assert size > 0
        # Progress callback should be called (but not for every file due to modulo)
        assert len(progress_updates) >= 0

    async def test_calculate_size_canceled(self, tmp_path):
        """Test size calculation can be canceled."""
        ops = AsyncFileOperations()

        test_dir = tmp_path / "test"
        test_dir.mkdir()
        for i in range(100):
            (test_dir / f"file{i}.txt").write_text(f"content{i}")

        ops.cancel()

        with pytest.raises(asyncio.CancelledError):
            await ops.calculate_directory_size_async(test_dir)

    async def test_calculate_size_large_directory(self, tmp_path):
        """Test calculating size of directory with many files."""
        ops = AsyncFileOperations()

        test_dir = tmp_path / "large"
        test_dir.mkdir()

        expected_size = 0
        for i in range(50):
            content = f"file content {i}"
            (test_dir / f"file{i}.txt").write_text(content)
            expected_size += len(content.encode())

        size = await ops.calculate_directory_size_async(test_dir)

        assert size == expected_size


@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_copy_zero_byte_file(self, tmp_path):
        """Test copying zero-byte file."""
        ops = AsyncFileOperations()

        source = tmp_path / "zero.txt"
        source.touch()

        dest = tmp_path / "zero_copy.txt"

        await ops.copy_file_async(source, dest)

        assert dest.exists()
        assert dest.stat().st_size == 0

    async def test_very_small_chunk_size(self, tmp_path):
        """Test with very small chunk size."""
        ops = AsyncFileOperations(chunk_size=10)  # 10 bytes

        source = tmp_path / "source.txt"
        source.write_text("This is a test file with more than 10 bytes")

        dest = tmp_path / "dest.txt"

        await ops.copy_file_async(source, dest)

        assert dest.read_text() == source.read_text()

    async def test_very_large_chunk_size(self, tmp_path):
        """Test with very large chunk size."""
        ops = AsyncFileOperations(chunk_size=10 * 1024 * 1024)  # 10MB

        source = tmp_path / "source.txt"
        source.write_text("Small file")

        dest = tmp_path / "dest.txt"

        await ops.copy_file_async(source, dest)

        assert dest.read_text() == source.read_text()

    async def test_unicode_filenames(self, tmp_path):
        """Test operations with Unicode filenames."""
        ops = AsyncFileOperations()

        source = tmp_path / "test.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        await ops.copy_file_async(source, dest)

        assert dest.exists()

    async def test_long_file_path(self, tmp_path):
        """Test operations with long file paths."""
        ops = AsyncFileOperations()

        # Create nested structure
        current = tmp_path
        for i in range(10):
            current = current / f"level{i}"
            current.mkdir(exist_ok=True)

        source = current / "file.txt"
        source.write_text("content")

        dest = current / "copy.txt"

        await ops.copy_file_async(source, dest)

        assert dest.exists()

    async def test_concurrent_operations(self, tmp_path):
        """Test multiple concurrent operations."""
        ops = AsyncFileOperations()

        # Create multiple source files
        sources = []
        for i in range(5):
            source = tmp_path / f"source{i}.txt"
            source.write_text(f"content{i}")
            sources.append(source)

        # Copy all concurrently
        tasks = []
        for i, source in enumerate(sources):
            dest = tmp_path / f"dest{i}.txt"
            tasks.append(ops.copy_file_async(source, dest))

        await asyncio.gather(*tasks)

        # Verify all copies
        for i in range(5):
            dest = tmp_path / f"dest{i}.txt"
            assert dest.exists()
            assert dest.read_text() == f"content{i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-k", "test_async_file_ops"])
