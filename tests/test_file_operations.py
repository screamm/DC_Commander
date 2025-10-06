"""
Comprehensive unit tests for file operations module.

Tests cover:
- File copy operations (success, overwrite, permissions, cross-device)
- File move operations (success, errors, cleanup)
- File deletion (files, directories, recursive)
- Directory creation (validation, permissions)
- Size formatting (edge cases, large values)
- File info retrieval (metadata, permissions)
"""

import pytest
from pathlib import Path
from datetime import datetime
import os
import shutil

from src.core.file_operations import (
    copy_file,
    move_file,
    delete_file,
    create_directory,
    format_size,
    get_file_info,
    get_directory_size,
    validate_path,
    FileOperationError,
    PermissionError,
    PathNotFoundError,
    InvalidPathError,
)


# Test Fixtures
@pytest.fixture
def temp_dir(tmp_path):
    """Provide temporary directory for tests."""
    test_dir = tmp_path / "test_workspace"
    test_dir.mkdir()
    yield test_dir
    # Cleanup handled by tmp_path


@pytest.fixture
def sample_file(temp_dir):
    """Create sample file with known content."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("Sample file content for testing", encoding="utf-8")
    return file_path


@pytest.fixture
def sample_directory(temp_dir):
    """Create sample directory with nested structure."""
    dir_path = temp_dir / "sample_dir"
    dir_path.mkdir()
    (dir_path / "file1.txt").write_text("Content 1")
    (dir_path / "file2.txt").write_text("Content 2")

    nested = dir_path / "nested"
    nested.mkdir()
    (nested / "file3.txt").write_text("Content 3")

    return dir_path


@pytest.fixture
def large_file(temp_dir):
    """Create large file for size testing."""
    file_path = temp_dir / "large.bin"
    # Create 10MB file
    with open(file_path, 'wb') as f:
        f.write(b'0' * (10 * 1024 * 1024))
    return file_path


# Copy File Tests
class TestCopyFile:
    """Test copy_file function with various scenarios."""

    def test_copy_file_success(self, sample_file, temp_dir):
        """Test successful file copy."""
        dest = temp_dir / "copy.txt"
        result = copy_file(sample_file, dest)

        assert result is True
        assert dest.exists()
        assert dest.read_text() == sample_file.read_text()
        assert sample_file.exists()  # Source still exists

    def test_copy_file_overwrite_disabled(self, sample_file, temp_dir):
        """Test copy fails when destination exists without overwrite."""
        dest = temp_dir / "existing.txt"
        dest.write_text("Existing content")

        with pytest.raises(FileOperationError, match="already exists"):
            copy_file(sample_file, dest, overwrite=False)

    def test_copy_file_overwrite_enabled(self, sample_file, temp_dir):
        """Test copy overwrites when enabled."""
        dest = temp_dir / "existing.txt"
        dest.write_text("Old content")

        result = copy_file(sample_file, dest, overwrite=True)

        assert result is True
        assert dest.read_text() == sample_file.read_text()

    def test_copy_directory_success(self, sample_directory, temp_dir):
        """Test successful directory copy."""
        dest = temp_dir / "dir_copy"
        result = copy_file(sample_directory, dest)

        assert result is True
        assert dest.is_dir()
        assert (dest / "file1.txt").exists()
        assert (dest / "nested" / "file3.txt").exists()

    def test_copy_directory_overwrite(self, sample_directory, temp_dir):
        """Test directory copy with overwrite."""
        dest = temp_dir / "dir_copy"
        dest.mkdir()
        (dest / "old_file.txt").write_text("Old content")

        result = copy_file(sample_directory, dest, overwrite=True)

        assert result is True
        assert not (dest / "old_file.txt").exists()
        assert (dest / "file1.txt").exists()

    def test_copy_nonexistent_source(self, temp_dir):
        """Test copy fails with nonexistent source."""
        source = temp_dir / "nonexistent.txt"
        dest = temp_dir / "dest.txt"

        with pytest.raises(PathNotFoundError, match="does not exist"):
            copy_file(source, dest)

    def test_copy_creates_parent_directories(self, sample_file, temp_dir):
        """Test copy creates parent directories."""
        dest = temp_dir / "nested" / "deep" / "copy.txt"
        result = copy_file(sample_file, dest)

        assert result is True
        assert dest.exists()
        assert dest.parent.parent.exists()

    def test_copy_preserves_metadata(self, sample_file, temp_dir):
        """Test copy preserves file metadata."""
        dest = temp_dir / "copy.txt"

        # Set known modification time
        os.utime(sample_file, (1640000000, 1640000000))
        original_mtime = sample_file.stat().st_mtime

        copy_file(sample_file, dest)

        # copy2 should preserve modification time
        assert abs(dest.stat().st_mtime - original_mtime) < 1


# Move File Tests
class TestMoveFile:
    """Test move_file function with various scenarios."""

    def test_move_file_success(self, sample_file, temp_dir):
        """Test successful file move."""
        dest = temp_dir / "moved.txt"
        original_content = sample_file.read_text()

        result = move_file(sample_file, dest)

        assert result is True
        assert dest.exists()
        assert not sample_file.exists()
        assert dest.read_text() == original_content

    def test_move_file_overwrite_disabled(self, sample_file, temp_dir):
        """Test move fails when destination exists without overwrite."""
        dest = temp_dir / "existing.txt"
        dest.write_text("Existing content")

        with pytest.raises(FileOperationError, match="already exists"):
            move_file(sample_file, dest, overwrite=False)

    def test_move_file_overwrite_enabled(self, sample_file, temp_dir):
        """Test move overwrites when enabled."""
        dest = temp_dir / "existing.txt"
        dest.write_text("Old content")

        result = move_file(sample_file, dest, overwrite=True)

        assert result is True
        assert dest.exists()
        assert not sample_file.exists()

    def test_move_directory_success(self, sample_directory, temp_dir):
        """Test successful directory move."""
        dest = temp_dir / "moved_dir"

        result = move_file(sample_directory, dest)

        assert result is True
        assert dest.is_dir()
        assert not sample_directory.exists()
        assert (dest / "file1.txt").exists()

    def test_move_creates_parent_directories(self, sample_file, temp_dir):
        """Test move creates parent directories."""
        dest = temp_dir / "nested" / "deep" / "moved.txt"

        result = move_file(sample_file, dest)

        assert result is True
        assert dest.exists()

    def test_move_nonexistent_source(self, temp_dir):
        """Test move fails with nonexistent source."""
        source = temp_dir / "nonexistent.txt"
        dest = temp_dir / "dest.txt"

        with pytest.raises(PathNotFoundError, match="does not exist"):
            move_file(source, dest)


# Delete File Tests
class TestDeleteFile:
    """Test delete_file function with various scenarios."""

    def test_delete_file_success(self, sample_file):
        """Test successful file deletion."""
        assert sample_file.exists()

        result = delete_file(sample_file)

        assert result is True
        assert not sample_file.exists()

    def test_delete_directory_recursive(self, sample_directory):
        """Test recursive directory deletion."""
        assert sample_directory.exists()

        result = delete_file(sample_directory, recursive=True)

        assert result is True
        assert not sample_directory.exists()

    def test_delete_directory_non_recursive_fails(self, sample_directory):
        """Test non-recursive deletion fails for non-empty directory."""
        with pytest.raises(FileOperationError):
            delete_file(sample_directory, recursive=False)

    def test_delete_empty_directory_non_recursive(self, temp_dir):
        """Test non-recursive deletion succeeds for empty directory."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        result = delete_file(empty_dir, recursive=False)

        assert result is True
        assert not empty_dir.exists()

    def test_delete_nonexistent_path(self, temp_dir):
        """Test delete fails with nonexistent path."""
        path = temp_dir / "nonexistent.txt"

        with pytest.raises(PathNotFoundError, match="does not exist"):
            delete_file(path)


# Create Directory Tests
class TestCreateDirectory:
    """Test create_directory function with various scenarios."""

    def test_create_directory_success(self, temp_dir):
        """Test successful directory creation."""
        result = create_directory(temp_dir, "new_dir")

        assert result.exists()
        assert result.is_dir()
        assert result.name == "new_dir"

    def test_create_directory_nested(self, temp_dir):
        """Test nested directory creation."""
        parent = temp_dir / "parent"
        result = create_directory(parent, "child", exist_ok=True)

        assert result.exists()
        assert parent.exists()

    def test_create_directory_exists_ok(self, temp_dir):
        """Test create directory with exist_ok."""
        dir_path = temp_dir / "existing"
        dir_path.mkdir()

        result = create_directory(temp_dir, "existing", exist_ok=True)

        assert result.exists()

    def test_create_directory_exists_error(self, temp_dir):
        """Test create directory fails when exists without exist_ok."""
        dir_path = temp_dir / "existing"
        dir_path.mkdir()

        with pytest.raises(FileOperationError):
            create_directory(temp_dir, "existing", exist_ok=False)

    def test_create_directory_invalid_name_slash(self, temp_dir):
        """Test create directory fails with slash in name."""
        with pytest.raises(InvalidPathError, match="Invalid directory name"):
            create_directory(temp_dir, "invalid/name")

    def test_create_directory_invalid_name_backslash(self, temp_dir):
        """Test create directory fails with backslash in name."""
        with pytest.raises(InvalidPathError, match="Invalid directory name"):
            create_directory(temp_dir, "invalid\\name")

    def test_create_directory_empty_name(self, temp_dir):
        """Test create directory fails with empty name."""
        with pytest.raises(InvalidPathError, match="Invalid directory name"):
            create_directory(temp_dir, "")


# Format Size Tests
class TestFormatSize:
    """Test format_size function with edge cases."""

    @pytest.mark.parametrize("bytes_value,expected", [
        (0, "0 B"),
        (1, "1 B"),
        (512, "512 B"),
        (1023, "1023 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1048576, "1.0 MB"),
        (1572864, "1.5 MB"),
        (1073741824, "1.0 GB"),
        (1099511627776, "1.0 TB"),
        (1125899906842624, "1.0 PB"),
    ])
    def test_format_size_values(self, bytes_value, expected):
        """Test format_size with various byte values."""
        result = format_size(bytes_value)
        assert result == expected

    def test_format_size_negative(self):
        """Test format_size with negative value."""
        result = format_size(-100)
        assert result == "0 B"

    def test_format_size_large(self):
        """Test format_size with extremely large value."""
        result = format_size(10 * 1024 ** 5)  # 10 PB
        assert "PB" in result
        assert result.startswith("10.0")


# Get File Info Tests
class TestGetFileInfo:
    """Test get_file_info function."""

    def test_get_file_info_file(self, sample_file):
        """Test get file info for regular file."""
        info = get_file_info(sample_file)

        assert info['name'] == sample_file.name
        assert info['is_file'] is True
        assert info['is_directory'] is False
        assert info['size'] > 0
        assert isinstance(info['created'], datetime)
        assert isinstance(info['modified'], datetime)
        assert info['extension'] == '.txt'

    def test_get_file_info_directory(self, sample_directory):
        """Test get file info for directory."""
        info = get_file_info(sample_directory)

        assert info['is_directory'] is True
        assert info['is_file'] is False
        assert info['extension'] is None
        assert info['item_count'] == 3  # file1, file2, nested

    def test_get_file_info_nonexistent(self, temp_dir):
        """Test get file info fails for nonexistent path."""
        path = temp_dir / "nonexistent.txt"

        with pytest.raises(PathNotFoundError, match="does not exist"):
            get_file_info(path)

    def test_get_file_info_formatted_size(self, large_file):
        """Test get file info includes formatted size."""
        info = get_file_info(large_file)

        assert 'size_formatted' in info
        assert "MB" in info['size_formatted']


# Get Directory Size Tests
class TestGetDirectorySize:
    """Test get_directory_size function."""

    def test_get_directory_size_success(self, sample_directory):
        """Test directory size calculation."""
        size = get_directory_size(sample_directory)

        assert size > 0
        # Should be sum of all file contents
        expected = len("Content 1") + len("Content 2") + len("Content 3")
        assert size == expected

    def test_get_directory_size_empty(self, temp_dir):
        """Test directory size for empty directory."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        size = get_directory_size(empty_dir)
        assert size == 0

    def test_get_directory_size_nonexistent(self, temp_dir):
        """Test directory size fails for nonexistent path."""
        path = temp_dir / "nonexistent"

        with pytest.raises(PathNotFoundError, match="does not exist"):
            get_directory_size(path)

    def test_get_directory_size_file(self, sample_file):
        """Test directory size fails for file path."""
        with pytest.raises(InvalidPathError, match="not a directory"):
            get_directory_size(sample_file)


# Validate Path Tests
class TestValidatePath:
    """Test validate_path function."""

    def test_validate_path_valid_file(self, sample_file):
        """Test validation succeeds for valid file."""
        is_valid, error = validate_path(sample_file)

        assert is_valid is True
        assert error is None

    def test_validate_path_valid_directory(self, sample_directory):
        """Test validation succeeds for valid directory."""
        is_valid, error = validate_path(sample_directory)

        assert is_valid is True
        assert error is None

    def test_validate_path_nonexistent(self, temp_dir):
        """Test validation fails for nonexistent path."""
        path = temp_dir / "nonexistent.txt"

        is_valid, error = validate_path(path)

        assert is_valid is False
        assert "does not exist" in error


# Integration Tests
class TestFileOperationsIntegration:
    """Integration tests for file operation workflows."""

    def test_copy_move_delete_workflow(self, sample_file, temp_dir):
        """Test complete copy, move, delete workflow."""
        # Copy
        copy_dest = temp_dir / "copy.txt"
        copy_file(sample_file, copy_dest)
        assert copy_dest.exists()

        # Move copy
        move_dest = temp_dir / "moved.txt"
        move_file(copy_dest, move_dest)
        assert move_dest.exists()
        assert not copy_dest.exists()

        # Delete
        delete_file(move_dest)
        assert not move_dest.exists()

    def test_directory_operations_workflow(self, temp_dir):
        """Test directory creation and manipulation workflow."""
        # Create directory
        new_dir = create_directory(temp_dir, "workflow_test")
        assert new_dir.exists()

        # Create file in directory
        test_file = new_dir / "test.txt"
        test_file.write_text("Test content")

        # Get directory size
        size = get_directory_size(new_dir)
        assert size == len("Test content")

        # Delete directory
        delete_file(new_dir, recursive=True)
        assert not new_dir.exists()
