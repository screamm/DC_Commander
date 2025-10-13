"""
File operations module for Modern Commander.

Provides safe, reliable file and directory operations with comprehensive error handling
and security validation with TOCTOU protection.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from .security import (
    sanitize_filename,
    is_safe_filename,
    validate_path as security_validate_path,
    check_permissions,
    secure_open,
    secure_stat,
    secure_copy_data,
    TOCTOUError,
    SecurityError
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


def copy_file_secure(source: Path, dest: Path, overwrite: bool = False) -> bool:
    """
    Copy file with TOCTOU protection using O_NOFOLLOW.

    Prevents Time-of-Check-Time-of-Use race conditions by using atomic
    operations with O_NOFOLLOW flag to detect symlink substitution attacks.

    Args:
        source: Source path to copy from
        dest: Destination path to copy to
        overwrite: If True, overwrite existing destination

    Returns:
        True if copy succeeded

    Raises:
        PathNotFoundError: Source path does not exist
        TOCTOUError: Symlink detected during operation (TOCTOU protection)
        SecurityError: Security validation failed
        FileOperationError: Copy operation failed

    Security:
        Uses secure_open() with O_NOFOLLOW to atomically verify paths
        are not symlinks, preventing TOCTOU race conditions.
    """
    try:
        # Validate source exists using secure stat (TOCTOU protected)
        try:
            source_stat = secure_stat(source, follow_symlinks=False)
        except FileNotFoundError:
            raise PathNotFoundError(f"Source path does not exist: {source}")
        except TOCTOUError as e:
            raise SecurityError(f"Source is symlink (TOCTOU protection): {source}")

        # Security validation for source path
        is_valid, error = security_validate_path(source, source.parent, allow_symlinks=False)
        if not is_valid:
            raise InvalidPathError(f"Security validation failed for source: {error}")

        # Security validation for destination path
        is_valid, error = security_validate_path(dest, dest.parent, allow_symlinks=False)
        if not is_valid:
            raise InvalidPathError(f"Security validation failed for destination: {error}")

        # Check if destination exists when overwrite is False
        if dest.exists() and not overwrite:
            raise FileOperationError(f"Destination already exists: {dest}")

        # Ensure destination parent directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Use atomic secure operations with O_NOFOLLOW (critical for TOCTOU prevention)
        try:
            # Open source with O_NOFOLLOW - atomic check
            with secure_open(source, 'rb', follow_symlinks=False) as src_f:
                # If we get here, source is safe (not a symlink replaced during check)

                # Determine destination open flags
                if overwrite:
                    # Truncate existing file
                    with secure_open(dest, 'wb', follow_symlinks=False) as dst_f:
                        # Copy using file descriptors (atomic operations)
                        bytes_copied = secure_copy_data(src_f.fileno(), dst_f.fileno())
                else:
                    # Create new file, fail if exists
                    dest_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL

                    # Add O_NOFOLLOW on Unix (not available on Windows)
                    if hasattr(os, 'O_NOFOLLOW'):
                        dest_flags |= os.O_NOFOLLOW

                    if os.name == 'nt':
                        dest_flags |= os.O_BINARY
                        # On Windows, check for symlink before opening
                        if dest.exists() and dest.is_symlink():
                            raise TOCTOUError(f"Symlink detected (TOCTOU protection): {dest}")

                    try:
                        dest_fd = os.open(dest, dest_flags, 0o644)
                        try:
                            # Copy using file descriptors
                            bytes_copied = secure_copy_data(src_f.fileno(), dest_fd)
                        finally:
                            os.close(dest_fd)
                    except FileExistsError:
                        raise FileOperationError(f"Destination already exists: {dest}")

            # Preserve metadata (permissions, timestamps)
            try:
                shutil.copystat(source, dest)
            except OSError:
                pass  # Best effort metadata preservation

            return True

        except TOCTOUError as e:
            raise SecurityError(f"TOCTOU attack detected during copy: {e}")

    except OSError as e:
        if e.errno == 13:
            raise PermissionError(f"Permission denied: {e}")
        raise FileOperationError(f"Secure copy failed: {e}")


def copy_file(source: Path, dest: Path, overwrite: bool = False) -> bool:
    """
    Atomically copy file or directory to destination with rollback on failure.

    For files, uses TOCTOU-protected secure copy. For directories, uses
    two-stage copy process with atomic replacement.

    Args:
        source: Source path to copy from
        dest: Destination path to copy to
        overwrite: If True, overwrite existing destination

    Returns:
        True if copy succeeded

    Raises:
        PathNotFoundError: Source path does not exist
        PermissionError: Insufficient permissions for operation
        TOCTOUError: Symlink detected during operation
        FileOperationError: Copy operation failed
    """
    try:
        # Validate source exists
        if not source.exists():
            raise PathNotFoundError(f"Source path does not exist: {source}")

        # For single files, use secure TOCTOU-protected copy
        if source.is_file():
            return copy_file_secure(source, dest, overwrite=overwrite)

        # For directories, use atomic two-stage copy
        if not source.is_dir():
            raise InvalidPathError(f"Source is neither file nor directory: {source}")

        # Check if destination exists when overwrite is False
        if dest.exists() and not overwrite:
            raise FileOperationError(f"Destination already exists: {dest}")

        # Ensure destination parent directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Stage 1: Copy to temporary location (safe)
        temp_dest = dest.parent / f".tmp_{dest.name}_{uuid.uuid4().hex[:8]}"

        try:
            shutil.copytree(source, temp_dest, symlinks=False)  # Don't follow symlinks

            # Stage 2: Atomic replacement
            if dest.exists():
                # Backup old version during replacement
                backup = dest.parent / f".backup_{dest.name}_{uuid.uuid4().hex[:8]}"
                try:
                    # Atomic rename operations
                    dest.rename(backup)  # Move old file to backup
                    temp_dest.rename(dest)  # Move new file to destination

                    # Cleanup old version on success
                    shutil.rmtree(backup)

                except Exception as e:
                    # Rollback: restore from backup if rename failed
                    if backup.exists() and not dest.exists():
                        try:
                            backup.rename(dest)
                        except:
                            pass  # Best effort rollback
                    raise FileOperationError(f"Atomic replacement failed: {e}")
            else:
                # Simple case: just rename temp to dest (atomic)
                temp_dest.rename(dest)

            return True

        except Exception as e:
            # Cleanup temporary file on any failure
            if temp_dest.exists():
                try:
                    shutil.rmtree(temp_dest)
                except:
                    pass  # Best effort cleanup
            raise

    except TOCTOUError as e:
        raise SecurityError(f"TOCTOU attack detected: {e}")
    except OSError as e:
        if e.errno == 13:
            raise PermissionError(f"Permission denied: {e}")
        raise FileOperationError(f"Copy failed: {e}")


def move_file(source: Path, dest: Path, overwrite: bool = False) -> bool:
    """
    Atomically move file or directory to destination with rollback on failure.

    Uses atomic rename when possible (same filesystem), otherwise falls back to
    TOCTOU-protected copy-then-delete with proper error handling.

    Args:
        source: Source path to move from
        dest: Destination path to move to
        overwrite: If True, overwrite existing destination

    Returns:
        True if move succeeded

    Raises:
        PathNotFoundError: Source path does not exist
        PermissionError: Insufficient permissions for operation
        TOCTOUError: Symlink detected during operation
        FileOperationError: Move operation failed
        InvalidPathError: Security validation failed
    """
    try:
        # Validate source exists
        if not source.exists():
            raise PathNotFoundError(f"Source path does not exist: {source}")

        # Security validation for source path
        is_valid, error = security_validate_path(source, source.parent, allow_symlinks=False)
        if not is_valid:
            raise InvalidPathError(f"Security validation failed for source: {error}")

        # Security validation for destination path
        is_valid, error = security_validate_path(dest, dest.parent, allow_symlinks=False)
        if not is_valid:
            raise InvalidPathError(f"Security validation failed for destination: {error}")

        # Validate source filename is safe
        if not is_safe_filename(source.name):
            raise InvalidPathError(f"Unsafe source filename: {source.name}")

        # Validate destination filename is safe
        if not is_safe_filename(dest.name):
            raise InvalidPathError(f"Unsafe destination filename: {dest.name}")

        # Check if destination exists when overwrite is False
        if dest.exists() and not overwrite:
            raise FileOperationError(f"Destination already exists: {dest}")

        # Ensure destination parent directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Try atomic rename first (only works on same filesystem)
        try:
            if dest.exists():
                # Backup and replace atomically
                backup = dest.parent / f".backup_{dest.name}_{uuid.uuid4().hex[:8]}"
                try:
                    dest.rename(backup)  # Atomic backup
                    source.rename(dest)  # Atomic move

                    # Cleanup old version on success
                    if backup.is_dir():
                        shutil.rmtree(backup)
                    else:
                        backup.unlink()

                except Exception as e:
                    # Rollback: restore backup if rename failed
                    if backup.exists() and not dest.exists():
                        try:
                            backup.rename(dest)
                        except:
                            pass  # Best effort rollback
                    raise
            else:
                # Simple atomic rename
                source.rename(dest)

            return True

        except OSError as e:
            # Rename failed (likely cross-filesystem), fall back to copy-then-delete
            if e.errno in (18, 17):  # EXDEV (cross-device link) or EEXIST
                # Use TOCTOU-protected copy then delete source
                success = copy_file(source, dest, overwrite=overwrite)
                if success:
                    # Only delete source after successful copy
                    try:
                        if source.is_dir():
                            shutil.rmtree(source)
                        else:
                            source.unlink()
                        return True
                    except Exception as delete_error:
                        # Copy succeeded but delete failed - log warning but don't fail
                        raise FileOperationError(
                            f"Move succeeded but failed to delete source: {delete_error}"
                        )
                else:
                    raise FileOperationError("Copy operation failed during cross-filesystem move")
            else:
                raise

    except TOCTOUError as e:
        raise SecurityError(f"TOCTOU attack detected: {e}")
    except OSError as e:
        if e.errno == 13:
            raise PermissionError(f"Permission denied: {e}")
        raise FileOperationError(f"Move failed: {e}")


def delete_file(path: Path, recursive: bool = True) -> bool:
    """
    Delete file or directory with TOCTOU protection.

    Args:
        path: Path to delete
        recursive: If True, delete directories recursively

    Returns:
        True if deletion succeeded

    Raises:
        PathNotFoundError: Path does not exist
        PermissionError: Insufficient permissions for operation
        TOCTOUError: Symlink detected during operation
        FileOperationError: Delete operation failed
    """
    try:
        # Use secure stat to detect symlinks (TOCTOU protection)
        try:
            file_stat = secure_stat(path, follow_symlinks=False)
        except FileNotFoundError:
            raise PathNotFoundError(f"Path does not exist: {path}")
        except TOCTOUError as e:
            raise SecurityError(f"Symlink detected (TOCTOU protection): {path}")

        # Check if it's a directory
        import stat as stat_module
        is_dir = stat_module.S_ISDIR(file_stat.st_mode)

        if is_dir:
            if recursive:
                shutil.rmtree(path)
            else:
                path.rmdir()
        else:
            path.unlink()

        return True

    except TOCTOUError as e:
        raise SecurityError(f"TOCTOU attack detected: {e}")
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


def get_file_info(path: Path, follow_symlinks: bool = False) -> dict:
    """
    Get comprehensive file information with TOCTOU protection.

    Args:
        path: Path to file or directory
        follow_symlinks: Follow symlinks (default: False for security)

    Returns:
        Dictionary with file information

    Raises:
        PathNotFoundError: Path does not exist
        TOCTOUError: Symlink detected when follow_symlinks=False
        PermissionError: Insufficient permissions to access file
    """
    try:
        # Use secure stat for TOCTOU protection
        try:
            stat = secure_stat(path, follow_symlinks=follow_symlinks)
        except FileNotFoundError:
            raise PathNotFoundError(f"Path does not exist: {path}")
        except TOCTOUError as e:
            raise SecurityError(f"Symlink detected (TOCTOU protection): {path}")

        import stat as stat_module

        info = {
            'name': path.name,
            'path': str(path.absolute()),
            'size': stat.st_size,
            'size_formatted': format_size(stat.st_size),
            'is_directory': stat_module.S_ISDIR(stat.st_mode),
            'is_file': stat_module.S_ISREG(stat.st_mode),
            'is_symlink': stat_module.S_ISLNK(stat.st_mode),
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'accessed': datetime.fromtimestamp(stat.st_atime),
            'permissions': oct(stat.st_mode)[-3:],
            'extension': path.suffix if stat_module.S_ISREG(stat.st_mode) else None
        }

        if stat_module.S_ISDIR(stat.st_mode):
            try:
                items = list(path.iterdir())
                info['item_count'] = len(items)
            except PermissionError:
                info['item_count'] = None

        return info

    except TOCTOUError as e:
        raise SecurityError(f"TOCTOU attack detected: {e}")
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
            is_safe, error = security_validate_path(path, allowed_base, allow_symlinks=False)
            if not is_safe:
                return False, f"Security validation failed: {error}"

        # Permission check if requested
        if check_permissions_mode:
            is_allowed, error = check_permissions(path, check_permissions_mode)
            if not is_allowed:
                return False, f"Permission check failed: {error}"

        # Basic accessibility check using secure operations
        try:
            secure_stat(path, follow_symlinks=False)
        except TOCTOUError:
            return False, "Symlink detected (security policy violation)"

        if path.is_dir():
            list(path.iterdir())
        else:
            # Just check if readable, don't actually read large files
            with secure_open(path, 'rb', follow_symlinks=False) as f:
                f.read(1)

        return True, None

    except TOCTOUError:
        return False, "Symlink detected during validation (TOCTOU protection)"
    except PermissionError:
        return False, "Permission denied"
    except OSError as e:
        return False, f"Path access error: {e}"
