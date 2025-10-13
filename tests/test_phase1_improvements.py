"""
Integration tests for Phase 1 improvements:
- Error boundary and recovery
- Atomic file operations with rollback
- Async cancellation with cleanup
- Input validation
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil


# Test Error Boundary
def test_error_boundary_creation():
    """Test error boundary can be created."""
    from src.core.error_boundary import ErrorBoundary

    boundary = ErrorBoundary()
    assert boundary is not None
    assert boundary.history is not None


def test_error_context_tracking():
    """Test error context is tracked properly."""
    from src.core.error_boundary import ErrorBoundary, ErrorSeverity

    boundary = ErrorBoundary()

    # Create test error
    test_error = ValueError("Test error")

    # Handle error synchronously
    import asyncio
    result = asyncio.run(boundary.handle_error(
        test_error,
        "test_operation",
        context="Unit test",
        severity=ErrorSeverity.ERROR
    ))

    # Verify error was recorded
    assert len(boundary.history.errors) == 1
    recorded = boundary.history.errors[0]
    assert recorded.error == test_error
    assert recorded.operation == "test_operation"


# Test Atomic Operations
def test_atomic_copy_operation():
    """Test atomic copy with rollback capability."""
    from src.core.atomic_operations import AtomicFileOperation

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create source file
        source = tmppath / "source.txt"
        source.write_text("Test content")

        # Create destination
        dest = tmppath / "dest.txt"

        # Perform atomic copy
        handler = AtomicFileOperation(temp_dir=tmppath / "temp")
        success, error = handler.copy_file_atomic(source, dest)

        assert success is True
        assert error is None
        assert dest.exists()
        assert dest.read_text() == "Test content"


def test_atomic_copy_rollback():
    """Test atomic copy rollback on failure."""
    from src.core.atomic_operations import AtomicFileOperation

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create source file
        source = tmppath / "source.txt"
        source.write_text("Original")

        # Create existing destination
        dest = tmppath / "dest.txt"
        dest.write_text("Existing")

        # Try to copy without overwrite
        handler = AtomicFileOperation(temp_dir=tmppath / "temp")
        success, error = handler.copy_file_atomic(source, dest, overwrite=False)

        # Should fail
        assert success is False
        assert "exists" in error.lower()

        # Destination should be unchanged
        assert dest.read_text() == "Existing"


# Test Input Validation
def test_filename_validation():
    """Test filename validation."""
    from src.core.input_validation import validate_filename

    # Valid filename
    valid, error = validate_filename("test.txt")
    assert valid is True
    assert error is None

    # Invalid filename (null byte)
    valid, error = validate_filename("test\x00.txt")
    assert valid is False
    assert "null" in error.lower()

    # Invalid filename (path separator)
    valid, error = validate_filename("../test.txt")
    assert valid is False


def test_filename_sanitization():
    """Test filename sanitization."""
    from src.core.input_validation import sanitize_filename

    # Remove path separators
    result = sanitize_filename("../test.txt")
    assert "/" not in result
    assert "\\" not in result

    # Remove null bytes
    result = sanitize_filename("test\x00file.txt")
    assert "\x00" not in result

    # Preserve extension
    result = sanitize_filename("test<file>.txt")
    assert result.endswith(".txt")


def test_wildcard_pattern_validation():
    """Test wildcard pattern validation."""
    from src.core.input_validation import validate_wildcard_pattern

    # Valid pattern
    valid, error = validate_wildcard_pattern("*.py")
    assert valid is True

    # Too many wildcards (ReDoS prevention)
    valid, error = validate_wildcard_pattern("*" * 20)
    assert valid is False
    assert "complex" in error.lower() or "many" in error.lower()


# Test Async Cancellation
@pytest.mark.asyncio
async def test_async_service_cancellation():
    """Test async service cancellation with cleanup."""
    from services.file_service_async import AsyncFileService
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create test files
        files = []
        for i in range(5):
            f = tmppath / f"file{i}.txt"
            f.write_text("x" * 1000)
            files.append(f)

        dest = tmppath / "dest"
        dest.mkdir()

        # Start copy operation
        service = AsyncFileService()
        task = asyncio.create_task(
            service.copy_files_async(files, dest)
        )

        # Let it start
        await asyncio.sleep(0.1)

        # Cancel with cleanup
        cleaned = await service.cancel_with_cleanup()

        # Wait for task to complete
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify cleanup happened
        assert cleaned >= 0
        assert len(service._partial_files) == 0


# Test Path Validation
def test_path_validation_comprehensive():
    """Test comprehensive path validation."""
    from src.core.input_validation import validate_path_comprehensive
    from pathlib import Path

    # Valid path
    valid_path = Path.cwd()
    is_valid, error = validate_path_comprehensive(valid_path)
    assert is_valid is True

    # Path with null byte
    is_valid, error = validate_path_comprehensive(Path("test\x00path"))
    assert is_valid is False


# Test Progress Tracking
def test_progress_tracker():
    """Test progress tracking with ETA."""
    from src.utils.progress_tracker import ProgressTracker
    import time

    tracker = ProgressTracker(
        total_bytes=10000,
        total_files=10,
        operation_type="copy"
    )

    # Update progress
    info = tracker.update(bytes_completed=5000, files_completed=5)

    assert info.percentage == 50.0
    assert info.files_completed == 5
    assert info.total_files == 10


# Test Performance Metrics
def test_performance_monitoring():
    """Test performance metric tracking."""
    from src.utils.performance_metrics import PerformanceMonitor

    monitor = PerformanceMonitor(slow_threshold=0.1)

    @monitor.track_operation("test_operation", "test")
    def slow_function():
        import time
        time.sleep(0.15)
        return "result"

    # Execute function
    result = slow_function()

    # Check metrics were recorded
    stats = monitor.get_statistics("test_operation")
    assert stats['calls'] == 1
    assert stats['avg_duration'] > 0.1
    assert stats['slow_operations'] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
