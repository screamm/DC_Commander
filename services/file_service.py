"""File service layer for Modern Commander.

Provides high-level file operations with error handling and validation.
Integrated with security module for path validation and filename sanitization.
"""

from pathlib import Path
from typing import List, Optional, Tuple
import shutil
from dataclasses import dataclass
from enum import Enum

# Import security validation
from src.core.security import (
    validate_path,
    sanitize_filename,
    is_safe_filename,
    SecurityError,
    UnsafePathError
)

# Import atomic file operations
from src.core.file_operations import (
    copy_file,
    move_file,
    delete_file,
    FileOperationError
)


class OperationResult(Enum):
    """Result status for file operations."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


@dataclass
class OperationSummary:
    """Summary of a file operation."""
    result: OperationResult
    success_count: int
    error_count: int
    errors: List[Tuple[str, str]]  # (filename, error_message)


class FileService:
    """Service layer for file operations."""

    @staticmethod
    def copy_files(
        items: List[Path],
        dest_path: Path,
        overwrite: bool = False
    ) -> OperationSummary:
        """Copy files to destination.

        Args:
            items: List of file/directory paths to copy
            dest_path: Destination directory
            overwrite: Whether to overwrite existing files

        Returns:
            Operation summary
        """
        success_count = 0
        error_count = 0
        errors = []

        for item in items:
            try:
                # SECURITY: Validate source path
                is_valid, error_msg = validate_path(item, item.parent)
                if not is_valid:
                    errors.append((item.name, f"Security: {error_msg}"))
                    error_count += 1
                    continue

                # SECURITY: Sanitize destination filename
                safe_name = sanitize_filename(item.name)
                dest_file = dest_path / safe_name

                # SECURITY: Validate destination path
                is_valid, error_msg = validate_path(dest_file, dest_path)
                if not is_valid:
                    errors.append((item.name, f"Security: {error_msg}"))
                    error_count += 1
                    continue

                # Use atomic copy operation to prevent data loss
                copy_file(item, dest_file, overwrite=overwrite)
                success_count += 1

            except FileOperationError as e:
                errors.append((item.name, str(e)))
                error_count += 1
            except PermissionError as e:
                errors.append((item.name, f"Permission denied: {e}"))
                error_count += 1
            except Exception as e:
                errors.append((item.name, str(e)))
                error_count += 1

        # Determine result status
        if error_count == 0:
            result = OperationResult.SUCCESS
        elif success_count == 0:
            result = OperationResult.FAILURE
        else:
            result = OperationResult.PARTIAL

        return OperationSummary(result, success_count, error_count, errors)

    @staticmethod
    def move_files(
        items: List[Path],
        dest_path: Path,
        overwrite: bool = False
    ) -> OperationSummary:
        """Move files to destination.

        Args:
            items: List of file/directory paths to move
            dest_path: Destination directory
            overwrite: Whether to overwrite existing files

        Returns:
            Operation summary
        """
        success_count = 0
        error_count = 0
        errors = []

        for item in items:
            try:
                # SECURITY: Validate source path
                is_valid, error_msg = validate_path(item, item.parent)
                if not is_valid:
                    errors.append((item.name, f"Security: {error_msg}"))
                    error_count += 1
                    continue

                # SECURITY: Sanitize destination filename
                safe_name = sanitize_filename(item.name)
                dest_file = dest_path / safe_name

                # SECURITY: Validate destination path
                is_valid, error_msg = validate_path(dest_file, dest_path)
                if not is_valid:
                    errors.append((item.name, f"Security: {error_msg}"))
                    error_count += 1
                    continue

                # Use atomic move operation to prevent data loss
                move_file(item, dest_file, overwrite=overwrite)
                success_count += 1

            except FileOperationError as e:
                errors.append((item.name, str(e)))
                error_count += 1
            except PermissionError as e:
                errors.append((item.name, f"Permission denied: {e}"))
                error_count += 1
            except Exception as e:
                errors.append((item.name, str(e)))
                error_count += 1

        # Determine result status
        if error_count == 0:
            result = OperationResult.SUCCESS
        elif success_count == 0:
            result = OperationResult.FAILURE
        else:
            result = OperationResult.PARTIAL

        return OperationSummary(result, success_count, error_count, errors)

    @staticmethod
    def delete_files(items: List[Path]) -> OperationSummary:
        """Delete files and directories.

        Args:
            items: List of file/directory paths to delete

        Returns:
            Operation summary
        """
        success_count = 0
        error_count = 0
        errors = []

        for item in items:
            try:
                # Use atomic delete operation
                delete_file(item, recursive=True)
                success_count += 1

            except FileOperationError as e:
                errors.append((item.name, str(e)))
                error_count += 1
            except PermissionError as e:
                errors.append((item.name, f"Permission denied: {e}"))
                error_count += 1
            except Exception as e:
                errors.append((item.name, str(e)))
                error_count += 1

        # Determine result status
        if error_count == 0:
            result = OperationResult.SUCCESS
        elif success_count == 0:
            result = OperationResult.FAILURE
        else:
            result = OperationResult.PARTIAL

        return OperationSummary(result, success_count, error_count, errors)

    @staticmethod
    def create_directory(parent_path: Path, dir_name: str) -> Tuple[bool, Optional[str]]:
        """Create a new directory.

        Args:
            parent_path: Parent directory
            dir_name: Name of new directory

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # SECURITY: Validate and sanitize directory name
            if not is_safe_filename(dir_name):
                return (False, "Invalid directory name")

            safe_name = sanitize_filename(dir_name)
            new_dir = parent_path / safe_name

            # SECURITY: Validate path
            is_valid, error_msg = validate_path(new_dir, parent_path)
            if not is_valid:
                return (False, f"Security: {error_msg}")

            new_dir.mkdir(parents=False, exist_ok=False)
            return (True, None)

        except FileExistsError:
            return (False, "Directory already exists")
        except PermissionError:
            return (False, "Permission denied")
        except Exception as e:
            return (False, str(e))

    @staticmethod
    def rename_file(old_path: Path, new_name: str) -> Tuple[bool, Optional[str]]:
        """Rename a file or directory.

        Args:
            old_path: Current file path
            new_name: New name

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # SECURITY: Validate and sanitize new name
            if not is_safe_filename(new_name):
                return (False, "Invalid filename")

            safe_name = sanitize_filename(new_name)
            new_path = old_path.parent / safe_name

            # SECURITY: Validate new path
            is_valid, error_msg = validate_path(new_path, old_path.parent)
            if not is_valid:
                return (False, f"Security: {error_msg}")

            old_path.rename(new_path)
            return (True, None)

        except FileExistsError:
            return (False, "File already exists")
        except PermissionError:
            return (False, "Permission denied")
        except Exception as e:
            return (False, str(e))

    @staticmethod
    def get_file_info(path: Path) -> Optional[dict]:
        """Get detailed file information.

        Args:
            path: File path

        Returns:
            Dictionary with file information or None on error
        """
        try:
            stat = path.stat()

            return {
                "name": path.name,
                "path": str(path),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "is_dir": path.is_dir(),
                "is_file": path.is_file(),
                "is_symlink": path.is_symlink(),
                "mode": stat.st_mode,
            }

        except Exception:
            return None

    @staticmethod
    def calculate_directory_size(path: Path) -> int:
        """Calculate total size of a directory.

        Args:
            path: Directory path

        Returns:
            Total size in bytes
        """
        total_size = 0

        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total_size += entry.stat().st_size
        except Exception:
            pass

        return total_size
