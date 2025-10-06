"""
File operations module for Modern Commander.

Provides safe, reliable file and directory operations with comprehensive error handling
and security validation.
"""

import shutil
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from .security import (
    sanitize_filename,
    is_safe_filename,
    validate_path as security_validate_path,
    check_permissions
)


class FileOperationError(Exception):
    """Base exception for file operation errors."""
    pass


class PermissionError(FileOperationError):
    """Raised when operation fails due to permission issues."""
    pass


class PathNotFoundError(FileOperationError):
    """Raised when specified path does not exist."""
    pass


class InvalidPathError(FileOperationError):
    """Raised when path is invalid or malformed."""
    pass


def copy_file(source: Path, dest: Path, overwrite: bool = False) -> bool:
    """
    Copy file or directory to destination.

    Args:
        source: Source path to copy from
        dest: Destination path to copy to
        overwrite: If True, overwrite existing destination

    Returns:
        True if copy succeeded

    Raises:
        PathNotFoundError: Source path does not exist
        PermissionError: Insufficient permissions for operation
        FileOperationError: Copy operation failed
    """
    try:
        if not source.exists():
            raise PathNotFoundError(f"Source path does not exist: {source}")

        if dest.exists() and not overwrite:
            raise FileOperationError(f"Destination already exists: {dest}")

        if source.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(source, dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)

        return True

    except OSError as e:
        if e.errno == 13:
            raise PermissionError(f"Permission denied: {e}")
        raise FileOperationError(f"Copy failed: {e}")


def move_file(source: Path, dest: Path, overwrite: bool = False) -> bool:
    """
    Move file or directory to destination.

    Args:
        source: Source path to move from
        dest: Destination path to move to
        overwrite: If True, overwrite existing destination

    Returns:
        True if move succeeded

    Raises:
        PathNotFoundError: Source path does not exist
        PermissionError: Insufficient permissions for operation
        FileOperationError: Move operation failed
    """
    try:
        if not source.exists():
            raise PathNotFoundError(f"Source path does not exist: {source}")

        if dest.exists():
            if not overwrite:
                raise FileOperationError(f"Destination already exists: {dest}")
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(dest))

        return True

    except OSError as e:
        if e.errno == 13:
            raise PermissionError(f"Permission denied: {e}")
        raise FileOperationError(f"Move failed: {e}")


def delete_file(path: Path, recursive: bool = True) -> bool:
    """
    Delete file or directory.

    Args:
        path: Path to delete
        recursive: If True, delete directories recursively

    Returns:
        True if deletion succeeded

    Raises:
        PathNotFoundError: Path does not exist
        PermissionError: Insufficient permissions for operation
        FileOperationError: Delete operation failed
    """
    try:
        if not path.exists():
            raise PathNotFoundError(f"Path does not exist: {path}")

        if path.is_dir():
            if recursive:
                shutil.rmtree(path)
            else:
                path.rmdir()
        else:
            path.unlink()

        return True

    except OSError as e:
        if e.errno == 13:
            raise PermissionError(f"Permission denied: {e}")
        raise FileOperationError(f"Delete failed: {e}")


def create_directory(
    path: Path,
    name: str,
    exist_ok: bool = False,
    validate_name: bool = True
) -> Path:
    """
    Create new directory with optional name validation.

    Args:
        path: Parent directory path
        name: Name of new directory
        exist_ok: If True, don't raise error if directory exists
        validate_name: If True, validate directory name for safety

    Returns:
        Path to created directory

    Raises:
        InvalidPathError: Invalid directory name
        PermissionError: Insufficient permissions for operation
        FileOperationError: Directory creation failed
    """
    try:
        # Validate name if requested
        if validate_name:
            if not name or '/' in name or '\\' in name:
                raise InvalidPathError(f"Invalid directory name: {name}")

            # Use security validation
            if not is_safe_filename(name):
                raise InvalidPathError(
                    f"Directory name contains unsafe characters: {name}"
                )

        new_dir = path / name
        new_dir.mkdir(parents=True, exist_ok=exist_ok)

        return new_dir

    except OSError as e:
        if e.errno == 13:
            raise PermissionError(f"Permission denied: {e}")
        raise FileOperationError(f"Directory creation failed: {e}")


def get_file_info(path: Path) -> dict:
    """
    Get comprehensive file information.

    Args:
        path: Path to file or directory

    Returns:
        Dictionary with file information

    Raises:
        PathNotFoundError: Path does not exist
        PermissionError: Insufficient permissions to access file
    """
    try:
        if not path.exists():
            raise PathNotFoundError(f"Path does not exist: {path}")

        stat = path.stat()

        info = {
            'name': path.name,
            'path': str(path.absolute()),
            'size': stat.st_size,
            'size_formatted': format_size(stat.st_size),
            'is_directory': path.is_dir(),
            'is_file': path.is_file(),
            'is_symlink': path.is_symlink(),
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'accessed': datetime.fromtimestamp(stat.st_atime),
            'permissions': oct(stat.st_mode)[-3:],
            'extension': path.suffix if path.is_file() else None
        }

        if path.is_dir():
            try:
                items = list(path.iterdir())
                info['item_count'] = len(items)
            except PermissionError:
                info['item_count'] = None

        return info

    except OSError as e:
        if e.errno == 13:
            raise PermissionError(f"Permission denied: {e}")
        raise FileOperationError(f"Failed to get file info: {e}")


def format_size(bytes: int) -> str:
    """
    Format byte size to human-readable string.

    Args:
        bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB", "3.2 GB")
    """
    if bytes < 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    size = float(bytes)

    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def get_directory_size(path: Path) -> int:
    """
    Calculate total size of directory and all its contents.

    Args:
        path: Directory path

    Returns:
        Total size in bytes

    Raises:
        PathNotFoundError: Path does not exist
        InvalidPathError: Path is not a directory
    """
    try:
        if not path.exists():
            raise PathNotFoundError(f"Path does not exist: {path}")

        if not path.is_dir():
            raise InvalidPathError(f"Path is not a directory: {path}")

        total_size = 0
        for item in path.rglob('*'):
            if item.is_file():
                try:
                    total_size += item.stat().st_size
                except (OSError, PermissionError):
                    continue

        return total_size

    except OSError as e:
        raise FileOperationError(f"Failed to calculate directory size: {e}")


def validate_path(
    path: Path,
    allowed_base: Optional[Path] = None,
    check_permissions_mode: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate path accessibility, permissions, and security.

    This function provides backward compatibility while adding security validation.

    Args:
        path: Path to validate
        allowed_base: Optional base directory for security validation
        check_permissions_mode: Optional permission mode to check ('r', 'w', 'x')

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Basic existence check
        if not path.exists():
            return False, "Path does not exist"

        if not path.is_dir() and not path.is_file():
            return False, "Path is neither file nor directory"

        # Security validation if base directory provided
        if allowed_base is not None:
            is_safe, error = security_validate_path(path, allowed_base)
            if not is_safe:
                return False, f"Security validation failed: {error}"

        # Permission check if requested
        if check_permissions_mode:
            is_allowed, error = check_permissions(path, check_permissions_mode)
            if not is_allowed:
                return False, f"Permission check failed: {error}"

        # Basic accessibility check
        path.stat()

        if path.is_dir():
            list(path.iterdir())
        else:
            # Just check if readable, don't actually read large files
            with open(path, 'rb') as f:
                f.read(1)

        return True, None

    except PermissionError:
        return False, "Permission denied"
    except OSError as e:
        return False, f"Path access error: {e}"
