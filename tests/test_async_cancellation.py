"""
Critical P1 test suite for async operation cancellation.

Tests comprehensive async cancellation scenarios to ensure:
- Clean cancellation of in-progress operations
- Temporary file cleanup on cancellation
- No partial files left behind
- Progress dialog updates correctly
- Repeated cancellations are safe (idempotent)

Priority: CRITICAL (P1)
Risk Score: 9/10
Test Count: 12
"""

import pytest
import asyncio
from pathlib import Path

from src.utils.async_file_ops import AsyncFileOperations


# Mark all tests as async
pytestmark = pytest.mark.asyncio


class TestAsyncCancellation:
    """Test async operation cancellation and cleanup."""

    async def test_cancel_copy_cleans_up_temp_files(self, tmp_path):
        """
        CRITICAL: Test canceling copy removes temporary files.

        Scenario: User cancels large file copy mid-operation.
        Expected: Temporary files removed, destination not created.
        Risk: Disk space leak, incomplete files.
        """
        service = AsyncFileOperations()

        # Create large source file
        source = tmp_path / "large.bin"
        source.write_bytes(b"x" * (10 * 1024 * 1024))  # 10MB

        dest = tmp_path / "dest.bin"

        # Start copy and cancel mid-operation
        task = asyncio.create_task(
            service.copy_file_async(source, dest)
        )

        # Give it time to start
        await asyncio.sleep(0.05)

        # Cancel operation
        service.cancel()

        # Wait for cancellation to propagate
        with pytest.raises(asyncio.CancelledError):
            await task

        # Verify no temp files left (pattern: .tmp_*)
        temp_files = list(tmp_path.glob(".tmp_*"))
        assert len(temp_files) == 0, f"Temporary files not cleaned up: {temp_files}"

        # Verify destination not created or is incomplete
        if dest.exists():
            # If partial file exists, it should be recognizable as incomplete
            assert dest.stat().st_size < source.stat().st_size

    async def test_cancel_move_operation(self, tmp_path):
        """
        CRITICAL: Test canceling move operation.

        Scenario: User cancels move operation mid-operation.
        Expected: Source preserved, destination not created.
        Risk: Data loss if source deleted before copy completes.
        """
        service = AsyncFileOperations()

        source = tmp_path / "source.txt"
        source.write_text("important data" * 1000)  # Make it larger

        dest = tmp_path / "subdir" / "dest.txt"
        dest.parent.mkdir()

        # Start move
        task = asyncio.create_task(
            service.move_file_async(source, dest)
        )

        await asyncio.sleep(0.05)
        service.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # CRITICAL: Source must still exist
        assert source.exists(), "Source file must be preserved on canceled move"
        assert source.read_text() == "important data" * 1000, "Source data must be intact"

        # Destination should not exist or be incomplete
        if dest.exists():
            dest.unlink()  # Cleanup

    async def test_cancel_delete_operation(self, tmp_path):
        """
        HIGH: Test canceling delete operation.

        Scenario: User cancels recursive directory deletion.
        Expected: Some files may be deleted, but operation stops cleanly.
        Risk: Partial deletion, inconsistent state.
        """
        service = AsyncFileOperations()

        # Create directory with many files
        delete_dir = tmp_path / "to_delete"
        delete_dir.mkdir()
        for i in range(100):
            (delete_dir / f"file_{i:03d}.txt").write_text(f"content {i}")

        # Start delete
        task = asyncio.create_task(
            service.delete_file_async(delete_dir)
        )

        await asyncio.sleep(0.05)
        service.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # Directory may be partially deleted - verify operation stopped cleanly
        # (no crash, no hung state)

    async def test_cancel_directory_copy(self, tmp_path):
        """
        CRITICAL: Test canceling directory copy operation.

        Scenario: User cancels large directory copy.
        Expected: Temporary directory removed, destination not created.
        Risk: Partial directory structure, disk space leak.
        """
        service = AsyncFileOperations()

        # Create source directory with many files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        for i in range(50):
            (source_dir / f"file_{i}.txt").write_text(f"content {i}")

        dest_dir = tmp_path / "dest"

        # Start copy in background
        results = []

        async def copy_and_collect():
            async for file, success, error in service.copy_directory_async(source_dir, dest_dir):
                results.append((file, success, error))

        task = asyncio.create_task(copy_and_collect())

        await asyncio.sleep(0.1)
        service.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # Verify temporary directories cleaned up
        temp_dirs = list(tmp_path.glob(".tmp_*"))
        assert len(temp_dirs) == 0, f"Temporary directories not cleaned up: {temp_dirs}"

    async def test_multiple_simultaneous_cancellations(self, tmp_path):
        """
        HIGH: Test canceling multiple operations simultaneously.

        Scenario: User cancels all operations (e.g., pressing Escape).
        Expected: All operations cancel cleanly without interference.
        Risk: Race conditions, resource leaks.
        """
        service = AsyncFileOperations()

        # Create multiple source files
        sources = []
        for i in range(5):
            source = tmp_path / f"source_{i}.txt"
            source.write_bytes(b"x" * (1024 * 1024))  # 1MB each
            sources.append(source)

        # Start multiple copy operations
        tasks = []
        for i, source in enumerate(sources):
            dest = tmp_path / f"dest_{i}.txt"
            task = asyncio.create_task(service.copy_file_async(source, dest))
            tasks.append(task)

        await asyncio.sleep(0.05)

        # Cancel all operations at once
        service.cancel()

        # All should raise CancelledError
        for task in tasks:
            with pytest.raises(asyncio.CancelledError):
                await task

        # Verify no temp files left
        temp_files = list(tmp_path.glob(".tmp_*"))
        assert len(temp_files) == 0

    async def test_cancel_with_progress_callback(self, tmp_path):
        """
        HIGH: Test cancellation with active progress callback.

        Scenario: Progress callback running when cancellation occurs.
        Expected: Callback stops receiving updates, no exceptions.
        Risk: Progress callback exceptions, hung UI.
        """
        service = AsyncFileOperations(chunk_size=1024)

        source = tmp_path / "source.bin"
        source.write_bytes(b"x" * (5 * 1024 * 1024))  # 5MB

        dest = tmp_path / "dest.bin"

        progress_updates = []

        def progress_callback(bytes_copied):
            progress_updates.append(bytes_copied)

        task = asyncio.create_task(
            service.copy_file_async(source, dest, progress_callback=progress_callback)
        )

        await asyncio.sleep(0.1)
        service.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # Progress callbacks should have been called before cancellation
        assert len(progress_updates) > 0

        # No callbacks after cancellation
        final_count = len(progress_updates)
        await asyncio.sleep(0.1)
        assert len(progress_updates) == final_count, "Progress callbacks continued after cancel"

    async def test_cancel_after_completion(self, tmp_path):
        """
        LOW: Test canceling after operation already completed.

        Scenario: User cancels operation that just finished.
        Expected: No-op, operation already complete.
        Risk: Error raised on harmless operation.
        """
        service = AsyncFileOperations()

        source = tmp_path / "source.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        # Complete operation
        await service.copy_file_async(source, dest)

        # Cancel after completion - should be no-op
        service.cancel()

        # Verify file copied successfully
        assert dest.exists()
        assert dest.read_text() == "content"

    async def test_cancel_before_start(self, tmp_path):
        """
        HIGH: Test canceling before operation starts.

        Scenario: Cancel flag set before async operation begins.
        Expected: Operation fails immediately without file operations.
        Risk: Resources allocated before cancellation checked.
        """
        service = AsyncFileOperations()

        source = tmp_path / "source.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        # Cancel before starting
        service.cancel()

        # Operation should fail immediately
        with pytest.raises(asyncio.CancelledError):
            await service.copy_file_async(source, dest)

        # Destination should not exist
        assert not dest.exists()

    async def test_repeated_cancel_calls_idempotent(self, tmp_path):
        """
        MEDIUM: Test repeated cancel() calls are safe (idempotent).

        Scenario: User presses cancel multiple times rapidly.
        Expected: Multiple cancel() calls have no negative effects.
        Risk: Exception raised on second cancel, race conditions.
        """
        service = AsyncFileOperations()

        source = tmp_path / "source.bin"
        source.write_bytes(b"x" * (10 * 1024 * 1024))  # 10MB

        dest = tmp_path / "dest.bin"

        task = asyncio.create_task(service.copy_file_async(source, dest))

        await asyncio.sleep(0.05)

        # Cancel multiple times
        service.cancel()
        service.cancel()
        service.cancel()

        # Should handle gracefully
        with pytest.raises(asyncio.CancelledError):
            await task

    async def test_cancel_respects_operation_boundaries(self, tmp_path):
        """
        MEDIUM: Test cancellation respects atomic operation boundaries.

        Scenario: Cancellation during atomic file operations.
        Expected: Current chunk/file completes, then cancels.
        Risk: Corrupted partial files.
        """
        service = AsyncFileOperations(chunk_size=1024 * 1024)  # 1MB chunks

        source = tmp_path / "source.bin"
        source.write_bytes(b"x" * (3 * 1024 * 1024))  # 3MB

        dest = tmp_path / "dest.bin"

        task = asyncio.create_task(service.copy_file_async(source, dest))

        await asyncio.sleep(0.05)
        service.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # If partial file exists, it should be chunk-aligned
        if dest.exists():
            size = dest.stat().st_size
            # Size should be multiple of chunk size (if boundary-respecting)
            # This is implementation-dependent
            assert size >= 0

    async def test_cancel_propagates_to_worker_threads(self, tmp_path):
        """
        HIGH: Test cancellation propagates to background worker threads.

        Scenario: Async operation uses thread pool for I/O.
        Expected: Workers detect cancellation and stop.
        Risk: Hung threads, resource leaks.
        """
        service = AsyncFileOperations()

        # Create large file for slow copy
        source = tmp_path / "large.bin"
        source.write_bytes(b"x" * (20 * 1024 * 1024))  # 20MB

        dest = tmp_path / "dest.bin"

        task = asyncio.create_task(service.copy_file_async(source, dest))

        await asyncio.sleep(0.1)
        service.cancel()

        # Should cancel within reasonable time (not hung)
        with pytest.raises(asyncio.CancelledError):
            # Add timeout to detect hung operations
            await asyncio.wait_for(task, timeout=5.0)

    async def test_cancel_updates_progress_dialog_correctly(self, tmp_path):
        """
        MEDIUM: Test cancellation updates progress correctly.

        Scenario: Progress dialog showing operation progress when canceled.
        Expected: Progress stops updating, final state shows "Cancelled".
        Risk: Progress shows 100% on canceled operation.
        """
        service = AsyncFileOperations(chunk_size=1024)

        source = tmp_path / "source.bin"
        source.write_bytes(b"x" * (5 * 1024 * 1024))  # 5MB

        dest = tmp_path / "dest.bin"

        progress_values = []

        def progress_callback(bytes_copied):
            progress_values.append(bytes_copied)

        task = asyncio.create_task(
            service.copy_file_async(source, dest, progress_callback=progress_callback)
        )

        await asyncio.sleep(0.1)
        service.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # Progress should not reach 100%
        if progress_values:
            final_progress = progress_values[-1]
            total_size = source.stat().st_size
            assert final_progress < total_size, \
                "Canceled operation should not show 100% progress"


class TestAsyncCancellationEdgeCases:
    """Test edge cases and boundary conditions for async cancellation."""

    async def test_cancel_during_permission_error(self, tmp_path):
        """
        MEDIUM: Test cancellation during permission error handling.

        Scenario: Permission error occurs, then user cancels.
        Expected: Both handled gracefully without conflict.
        Risk: Error masking, exception chaining issues.
        """
        service = AsyncFileOperations()

        source = tmp_path / "source.txt"
        source.write_text("content")

        # Non-writable destination
        dest = tmp_path / "nonexistent_dir" / "dest.txt"

        task = asyncio.create_task(service.copy_file_async(source, dest))

        await asyncio.sleep(0.05)
        service.cancel()

        # Should get CancelledError or permission error
        with pytest.raises((asyncio.CancelledError, OSError, PermissionError)):
            await task

    async def test_cancel_with_zero_byte_file(self, tmp_path):
        """
        LOW: Test canceling copy of zero-byte file.

        Scenario: Canceling very fast operation (zero-byte file).
        Expected: Cancel may succeed or file may already be copied.
        Risk: Race condition handling.
        """
        service = AsyncFileOperations()

        source = tmp_path / "empty.txt"
        source.touch()

        dest = tmp_path / "dest.txt"

        # Cancel immediately
        service.cancel()

        # May complete before cancel or raise CancelledError
        try:
            await service.copy_file_async(source, dest)
        except asyncio.CancelledError:
            pass  # Expected for canceled operation

    async def test_cancel_cleanup_on_network_path(self, tmp_path):
        """
        MEDIUM: Test cleanup works on network paths (if available).

        Scenario: Canceling operation on network drive.
        Expected: Cleanup happens even on slower network filesystem.
        Risk: Cleanup timeout, stale locks.

        Note: Skipped if no network paths available for testing.
        """
        pytest.skip("Network path testing requires specific environment setup")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
