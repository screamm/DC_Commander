"""
Tests for async file operations integration with UI.

Verifies that async operations work correctly with progress reporting
and cancellation support.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import shutil

from services.file_service_async import AsyncFileService, AsyncOperationProgress
from src.utils.async_file_ops import AsyncFileOperations


class TestAsyncFileService:
    """Test async file service operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)

    @pytest.fixture
    def async_service(self):
        """Create async file service instance."""
        return AsyncFileService(chunk_size=1024)

    @pytest.fixture
    def sample_files(self, temp_dir):
        """Create sample files for testing."""
        files = []
        for i in range(3):
            file_path = temp_dir / f"test_file_{i}.txt"
            file_path.write_text(f"Test content {i}" * 100)
            files.append(file_path)
        return files

    def test_should_use_async_small_files(self, async_service, temp_dir):
        """Small files should use sync operations."""
        small_file = temp_dir / "small.txt"
        small_file.write_text("small")

        assert not async_service.should_use_async([small_file])

    def test_should_use_async_large_files(self, async_service, temp_dir):
        """Large files should use async operations."""
        large_file = temp_dir / "large.txt"
        # Create file larger than 1MB threshold
        large_file.write_bytes(b"x" * (1024 * 1024 + 1))

        assert async_service.should_use_async([large_file])

    def test_should_use_async_large_directory(self, async_service, temp_dir):
        """Large directories should use async operations."""
        large_dir = temp_dir / "large_dir"
        large_dir.mkdir()

        # Create multiple files totaling > 1MB
        for i in range(5):
            file_path = large_dir / f"file_{i}.txt"
            file_path.write_bytes(b"x" * (300 * 1024))

        assert async_service.should_use_async([large_dir])

    @pytest.mark.asyncio
    async def test_copy_files_async_success(self, async_service, temp_dir, sample_files):
        """Test successful async copy operation."""
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        progress_updates = []

        def progress_callback(progress: AsyncOperationProgress):
            progress_updates.append(progress)

        result = await async_service.copy_files_async(
            sample_files,
            dest_dir,
            overwrite=False,
            progress_callback=progress_callback
        )

        # Verify success
        assert result.success_count == len(sample_files)
        assert result.error_count == 0
        assert len(result.errors) == 0

        # Verify files copied
        for file in sample_files:
            dest_file = dest_dir / file.name
            assert dest_file.exists()
            assert dest_file.read_text() == file.read_text()

        # Verify progress updates received
        assert len(progress_updates) > 0
        final_progress = progress_updates[-1]
        assert final_progress.files_completed == len(sample_files)

    @pytest.mark.asyncio
    async def test_copy_files_async_overwrite_protection(self, async_service, temp_dir, sample_files):
        """Test that existing files are not overwritten without flag."""
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        # Create existing file
        existing_file = dest_dir / sample_files[0].name
        existing_file.write_text("existing content")

        result = await async_service.copy_files_async(
            sample_files[:1],
            dest_dir,
            overwrite=False
        )

        # Verify error
        assert result.success_count == 0
        assert result.error_count == 1
        assert "already exists" in result.errors[0][1]

        # Verify original content unchanged
        assert existing_file.read_text() == "existing content"

    @pytest.mark.asyncio
    async def test_copy_files_async_cancellation(self, async_service, temp_dir):
        """Test cancellation of async copy operation."""
        # Create large file to ensure operation takes time
        large_file = temp_dir / "large.txt"
        large_file.write_bytes(b"x" * (5 * 1024 * 1024))  # 5MB

        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        # Start copy and cancel immediately
        async def cancel_after_start():
            await asyncio.sleep(0.01)
            async_service.cancel()

        cancel_task = asyncio.create_task(cancel_after_start())

        result = await async_service.copy_files_async([large_file], dest_dir)
        await cancel_task

        # Verify partial result
        assert result.success_count == 0 or result.error_count > 0

    @pytest.mark.asyncio
    async def test_move_files_async_success(self, async_service, temp_dir, sample_files):
        """Test successful async move operation."""
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        progress_updates = []

        def progress_callback(progress: AsyncOperationProgress):
            progress_updates.append(progress)

        # Store original paths and content
        original_data = {f: f.read_text() for f in sample_files}

        result = await async_service.move_files_async(
            sample_files,
            dest_dir,
            overwrite=False,
            progress_callback=progress_callback
        )

        # Verify success
        assert result.success_count == len(sample_files)
        assert result.error_count == 0

        # Verify files moved (originals gone, destinations exist)
        for orig_file in original_data.keys():
            assert not orig_file.exists()

            dest_file = dest_dir / orig_file.name
            assert dest_file.exists()
            assert dest_file.read_text() == original_data[orig_file]

        # Verify progress updates
        assert len(progress_updates) > 0
        assert progress_updates[-1].operation_type == "move"

    @pytest.mark.asyncio
    async def test_delete_files_async_success(self, async_service, temp_dir, sample_files):
        """Test successful async delete operation."""
        progress_updates = []

        def progress_callback(progress: AsyncOperationProgress):
            progress_updates.append(progress)

        result = await async_service.delete_files_async(
            sample_files,
            progress_callback=progress_callback
        )

        # Verify success
        assert result.success_count == len(sample_files)
        assert result.error_count == 0

        # Verify files deleted
        for file in sample_files:
            assert not file.exists()

        # Verify progress updates
        assert len(progress_updates) > 0
        assert progress_updates[-1].operation_type == "delete"

    @pytest.mark.asyncio
    async def test_delete_directory_async_success(self, async_service, temp_dir):
        """Test successful async directory deletion."""
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()

        # Create files in directory
        for i in range(5):
            (test_dir / f"file_{i}.txt").write_text(f"content {i}")

        result = await async_service.delete_files_async([test_dir])

        # Verify success
        assert result.success_count == 1
        assert result.error_count == 0
        assert not test_dir.exists()


class TestAsyncOperationProgress:
    """Test async operation progress dataclass."""

    def test_progress_creation(self):
        """Test progress object creation."""
        progress = AsyncOperationProgress(
            current_file="test.txt",
            current_bytes=500,
            total_bytes=1000,
            files_completed=1,
            total_files=2,
            percentage=50.0,
            operation_type="copy"
        )

        assert progress.current_file == "test.txt"
        assert progress.percentage == 50.0
        assert progress.operation_type == "copy"

    def test_progress_percentage_calculation(self):
        """Test percentage is correctly stored."""
        progress = AsyncOperationProgress(
            current_file="test.txt",
            current_bytes=250,
            total_bytes=1000,
            files_completed=0,
            total_files=1,
            percentage=25.0,
            operation_type="copy"
        )

        assert progress.percentage == 25.0


class TestAsyncFileOperations:
    """Test low-level async file operations."""

    @pytest.fixture
    def async_ops(self):
        """Create async operations instance."""
        return AsyncFileOperations(chunk_size=1024)

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        if temp_path.exists():
            shutil.rmtree(temp_path)

    @pytest.mark.asyncio
    async def test_copy_file_async_with_progress(self, async_ops, temp_dir):
        """Test file copy with progress reporting."""
        source = temp_dir / "source.txt"
        source.write_text("test content" * 100)

        dest = temp_dir / "dest.txt"

        progress_updates = []

        def progress_callback(bytes_copied: int):
            progress_updates.append(bytes_copied)

        await async_ops.copy_file_async(
            source,
            dest,
            progress_callback=progress_callback
        )

        # Verify file copied
        assert dest.exists()
        assert dest.read_text() == source.read_text()

        # Verify progress updates received
        assert len(progress_updates) > 0
        assert progress_updates[-1] == source.stat().st_size

    @pytest.mark.asyncio
    async def test_copy_file_async_cancellation(self, async_ops, temp_dir):
        """Test file copy cancellation."""
        source = temp_dir / "source.txt"
        source.write_bytes(b"x" * (1024 * 1024))  # 1MB

        dest = temp_dir / "dest.txt"

        # Cancel immediately
        async_ops.cancel()

        with pytest.raises(asyncio.CancelledError):
            await async_ops.copy_file_async(source, dest)

    @pytest.mark.asyncio
    async def test_move_file_async_same_filesystem(self, async_ops, temp_dir):
        """Test file move on same filesystem (should use rename)."""
        source = temp_dir / "source.txt"
        source.write_text("test content")

        dest = temp_dir / "dest.txt"

        await async_ops.move_file_async(source, dest)

        # Verify moved
        assert not source.exists()
        assert dest.exists()
        assert dest.read_text() == "test content"

    @pytest.mark.asyncio
    async def test_calculate_directory_size_async(self, async_ops, temp_dir):
        """Test async directory size calculation."""
        # Create test files
        for i in range(5):
            file_path = temp_dir / f"file_{i}.txt"
            file_path.write_bytes(b"x" * 1024)  # 1KB each

        total_size = await async_ops.calculate_directory_size_async(temp_dir)

        # Verify size (should be approximately 5KB)
        assert total_size == 5 * 1024


class TestProgressDialogIntegration:
    """Test progress dialog integration with async operations."""

    def test_progress_dialog_creation(self):
        """Test progress dialog can be created."""
        from components.dialogs import ProgressDialog

        dialog = ProgressDialog(
            title="Test Operation",
            total=100,
            show_cancel=True
        )

        assert dialog.dialog_title == "Test Operation"
        assert dialog.total == 100
        assert dialog.show_cancel is True

    def test_progress_dialog_update(self):
        """Test progress dialog update method."""
        from components.dialogs import ProgressDialog

        dialog = ProgressDialog(title="Test", total=100)

        # Update progress (only check attributes, not widgets)
        dialog.update_progress(50.0, "Processing...")

        # Verify attributes are set (widgets are only accessible after mounting)
        assert dialog.progress == 50.0
        assert dialog.status_text == "Processing..."

    def test_progress_dialog_cancellation(self):
        """Test progress dialog cancellation flag."""
        from components.dialogs import ProgressDialog

        cancel_called = False

        def on_cancel():
            nonlocal cancel_called
            cancel_called = True

        dialog = ProgressDialog(
            title="Test",
            total=100,
            show_cancel=True,
            on_cancel=on_cancel
        )

        assert not dialog.is_cancelled
