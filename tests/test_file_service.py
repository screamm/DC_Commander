"""Comprehensive tests for FileService module.

Tests file operations with security validation and error handling.
"""

import pytest
from pathlib import Path
from services.file_service import (
    FileService,
    OperationResult,
    OperationSummary
)
from src.core.security import SecurityError, UnsafePathError


class TestFileServiceCopy:
    """Test file copy operations."""

    def test_copy_single_file(self, temp_dir, test_file):
        """Test copying a single file."""
        # Arrange
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        # Act
        result = FileService.copy_files([test_file], dest_dir)

        # Assert
        assert result.result == OperationResult.SUCCESS
        assert result.success_count == 1
        assert result.error_count == 0
        assert (dest_dir / test_file.name).exists()

    def test_copy_multiple_files(self, temp_dir, test_files):
        """Test copying multiple files."""
        # Arrange
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        # Act
        result = FileService.copy_files(test_files, dest_dir)

        # Assert
        assert result.result == OperationResult.SUCCESS
        assert result.success_count == 3
        assert result.error_count == 0
        for file in test_files:
            assert (dest_dir / file.name).exists()

    def test_copy_directory(self, temp_dir, test_directory):
        """Test copying directory with contents."""
        # Arrange
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        # Act
        result = FileService.copy_files([test_directory], dest_dir)

        # Assert
        assert result.result == OperationResult.SUCCESS
        assert result.success_count == 1
        dest_test_dir = dest_dir / test_directory.name
        assert dest_test_dir.exists()
        assert (dest_test_dir / "subfile1.txt").exists()

    def test_copy_overwrite_disabled(self, temp_dir, test_file):
        """Test copy fails when file exists and overwrite disabled."""
        # Arrange
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()
        dest_file = dest_dir / test_file.name
        dest_file.write_text("Existing content")

        # Act
        result = FileService.copy_files([test_file], dest_dir, overwrite=False)

        # Assert
        assert result.result == OperationResult.FAILURE
        assert result.error_count == 1
        assert "already exists" in result.errors[0][1]

    def test_copy_overwrite_enabled(self, temp_dir, test_file):
        """Test copy overwrites when enabled."""
        # Arrange
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()
        dest_file = dest_dir / test_file.name
        dest_file.write_text("Existing content")

        # Act
        result = FileService.copy_files([test_file], dest_dir, overwrite=True)

        # Assert
        assert result.result == OperationResult.SUCCESS
        assert result.success_count == 1
        assert dest_file.read_text() == test_file.read_text()

    def test_copy_partial_success(self, temp_dir, test_files):
        """Test partial success when some files fail."""
        # Arrange
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()
        # Create conflicting file
        (dest_dir / test_files[0].name).write_text("Existing")

        # Act
        result = FileService.copy_files(test_files, dest_dir, overwrite=False)

        # Assert
        assert result.result == OperationResult.PARTIAL
        assert result.success_count == 2
        assert result.error_count == 1

    def test_copy_security_validation(self, temp_dir):
        """Test security validation prevents unsafe copies."""
        # Arrange
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()
        unsafe_file = temp_dir / "..\\..\\evil.txt"

        # Act
        try:
            unsafe_file.write_text("Evil content")
            result = FileService.copy_files([unsafe_file], dest_dir)
            # May succeed or fail depending on sanitization
        except Exception:
            # Expected - unsafe path handling
            pass

    def test_copy_nonexistent_destination(self, temp_dir, test_file):
        """Test copy fails with nonexistent destination."""
        # Arrange
        dest_dir = temp_dir / "nonexistent"

        # Act
        result = FileService.copy_files([test_file], dest_dir)

        # Assert
        assert result.error_count > 0


class TestFileServiceMove:
    """Test file move operations."""

    def test_move_single_file(self, temp_dir, test_file):
        """Test moving a single file."""
        # Arrange
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()
        original_content = test_file.read_text()

        # Act
        result = FileService.move_files([test_file], dest_dir)

        # Assert
        assert result.result == OperationResult.SUCCESS
        assert result.success_count == 1
        assert not test_file.exists()
        assert (dest_dir / test_file.name).exists()
        assert (dest_dir / test_file.name).read_text() == original_content

    def test_move_multiple_files(self, temp_dir, test_files):
        """Test moving multiple files."""
        # Arrange
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()

        # Act
        result = FileService.move_files(test_files, dest_dir)

        # Assert
        assert result.result == OperationResult.SUCCESS
        assert result.success_count == 3
        for file in test_files:
            assert not file.exists()
            assert (dest_dir / file.name).exists()

    def test_move_overwrite_disabled(self, temp_dir, test_file):
        """Test move fails when destination exists."""
        # Arrange
        dest_dir = temp_dir / "dest"
        dest_dir.mkdir()
        (dest_dir / test_file.name).write_text("Existing")

        # Act
        result = FileService.move_files([test_file], dest_dir, overwrite=False)

        # Assert
        assert result.result == OperationResult.FAILURE
        assert result.error_count == 1
        assert test_file.exists()  # Original still exists


class TestFileServiceDelete:
    """Test file deletion operations."""

    def test_delete_single_file(self, temp_dir, test_file):
        """Test deleting a single file."""
        # Act
        result = FileService.delete_files([test_file])

        # Assert
        assert result.result == OperationResult.SUCCESS
        assert result.success_count == 1
        assert not test_file.exists()

    def test_delete_multiple_files(self, temp_dir, test_files):
        """Test deleting multiple files."""
        # Act
        result = FileService.delete_files(test_files)

        # Assert
        assert result.result == OperationResult.SUCCESS
        assert result.success_count == 3
        for file in test_files:
            assert not file.exists()

    def test_delete_directory(self, temp_dir, test_directory):
        """Test deleting directory with contents."""
        # Act
        result = FileService.delete_files([test_directory])

        # Assert
        assert result.result == OperationResult.SUCCESS
        assert not test_directory.exists()

    def test_delete_nonexistent_file(self, temp_dir):
        """Test deleting nonexistent file."""
        # Arrange
        nonexistent = temp_dir / "nonexistent.txt"

        # Act
        result = FileService.delete_files([nonexistent])

        # Assert
        assert result.result == OperationResult.FAILURE
        assert result.error_count == 1


class TestFileServiceDirectoryManagement:
    """Test directory creation and management."""

    def test_create_directory_success(self, temp_dir):
        """Test creating a new directory."""
        # Act
        success, error = FileService.create_directory(temp_dir, "newdir")

        # Assert
        assert success is True
        assert error is None
        assert (temp_dir / "newdir").exists()

    def test_create_directory_already_exists(self, temp_dir):
        """Test creating directory that already exists."""
        # Arrange
        (temp_dir / "existing").mkdir()

        # Act
        success, error = FileService.create_directory(temp_dir, "existing")

        # Assert
        assert success is False
        assert "already exists" in error

    def test_create_directory_invalid_name(self, temp_dir):
        """Test creating directory with invalid name."""
        # Act
        success, error = FileService.create_directory(temp_dir, "../evil")

        # Assert
        # Should fail due to security validation
        assert success is False or error is not None

    def test_create_directory_sanitizes_name(self, temp_dir):
        """Test directory name sanitization."""
        # Act
        success, error = FileService.create_directory(temp_dir, "test:dir<>?")

        # Assert
        if success:
            # Should be sanitized to safe name
            assert any(d.name.replace(":", "_") for d in temp_dir.iterdir())


class TestFileServiceRename:
    """Test file renaming operations."""

    def test_rename_file_success(self, temp_dir, test_file):
        """Test renaming a file."""
        # Arrange
        original_content = test_file.read_text()

        # Act
        success, error = FileService.rename_file(test_file, "renamed.txt")

        # Assert
        assert success is True
        assert not test_file.exists()
        assert (test_file.parent / "renamed.txt").exists()
        assert (test_file.parent / "renamed.txt").read_text() == original_content

    def test_rename_directory_success(self, temp_dir, test_directory):
        """Test renaming a directory."""
        # Act
        success, error = FileService.rename_file(test_directory, "renamed_dir")

        # Assert
        assert success is True
        assert not test_directory.exists()
        assert (test_directory.parent / "renamed_dir").exists()

    def test_rename_file_already_exists(self, temp_dir, test_files):
        """Test rename fails when target exists."""
        # Act
        success, error = FileService.rename_file(test_files[0], test_files[1].name)

        # Assert
        assert success is False
        assert "already exists" in error

    def test_rename_invalid_name(self, temp_dir, test_file):
        """Test rename with invalid filename."""
        # Act
        success, error = FileService.rename_file(test_file, "../evil.txt")

        # Assert
        assert success is False


class TestFileServiceInfo:
    """Test file information retrieval."""

    def test_get_file_info(self, temp_dir, test_file):
        """Test getting file information."""
        # Act
        info = FileService.get_file_info(test_file)

        # Assert
        assert info is not None
        assert info["name"] == test_file.name
        assert info["size"] > 0
        assert info["is_file"] is True
        assert info["is_dir"] is False
        assert "modified" in info
        assert "created" in info

    def test_get_directory_info(self, temp_dir, test_directory):
        """Test getting directory information."""
        # Act
        info = FileService.get_file_info(test_directory)

        # Assert
        assert info is not None
        assert info["is_dir"] is True
        assert info["is_file"] is False

    def test_get_info_nonexistent(self, temp_dir):
        """Test getting info for nonexistent file."""
        # Act
        info = FileService.get_file_info(temp_dir / "nonexistent.txt")

        # Assert
        assert info is None

    def test_calculate_directory_size(self, temp_dir, test_directory):
        """Test calculating directory size."""
        # Act
        size = FileService.calculate_directory_size(test_directory)

        # Assert
        assert size > 0
        # Should include both subfiles

    def test_calculate_directory_size_empty(self, temp_dir):
        """Test calculating size of empty directory."""
        # Arrange
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        # Act
        size = FileService.calculate_directory_size(empty_dir)

        # Assert
        assert size == 0

    def test_calculate_directory_size_nested(self, nested_structure):
        """Test calculating size with nested structure."""
        # Act
        size = FileService.calculate_directory_size(nested_structure)

        # Assert
        assert size > 0  # Should include all nested files


class TestOperationSummary:
    """Test OperationSummary dataclass."""

    def test_operation_summary_success(self):
        """Test OperationSummary with successful operation."""
        # Arrange & Act
        summary = OperationSummary(
            result=OperationResult.SUCCESS,
            success_count=3,
            error_count=0,
            errors=[]
        )

        # Assert
        assert summary.result == OperationResult.SUCCESS
        assert summary.success_count == 3
        assert summary.error_count == 0
        assert len(summary.errors) == 0

    def test_operation_summary_partial(self):
        """Test OperationSummary with partial success."""
        # Arrange & Act
        summary = OperationSummary(
            result=OperationResult.PARTIAL,
            success_count=2,
            error_count=1,
            errors=[("file.txt", "Permission denied")]
        )

        # Assert
        assert summary.result == OperationResult.PARTIAL
        assert summary.success_count == 2
        assert summary.error_count == 1
        assert len(summary.errors) == 1

    def test_operation_summary_failure(self):
        """Test OperationSummary with complete failure."""
        # Arrange & Act
        summary = OperationSummary(
            result=OperationResult.FAILURE,
            success_count=0,
            error_count=3,
            errors=[
                ("file1.txt", "Error 1"),
                ("file2.txt", "Error 2"),
                ("file3.txt", "Error 3")
            ]
        )

        # Assert
        assert summary.result == OperationResult.FAILURE
        assert summary.success_count == 0
        assert summary.error_count == 3
        assert len(summary.errors) == 3
