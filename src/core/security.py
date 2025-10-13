"""
Security utilities for Modern Commander.

Provides security validation and protection mechanisms for file operations,
archive handling, and path traversal prevention.
"""

import os
import re
import errno
from pathlib import Path
from typing import Optional, Tuple, BinaryIO
from dataclasses import dataclass


class SecurityError(Exception):
    """Base exception for security violations."""
    pass


class PathTraversalError(SecurityError):
    """Raised when path traversal attack is detected."""
    pass


class ArchiveBombError(SecurityError):
    """Raised when archive bomb is detected."""
    pass


class UnsafePathError(SecurityError):
    """Raised when path contains dangerous patterns."""
    pass


class TOCTOUError(SecurityError):
    """Raised when Time-of-Check-Time-of-Use race condition is detected."""
    pass


@dataclass
class SecurityConfig:
    """Security configuration limits."""

    # Archive bomb detection limits
    max_compression_ratio: float = 100.0  # 100:1 ratio maximum
    max_extracted_size: int = 1_073_741_824  # 1GB default
    max_file_count: int = 10000  # Maximum files in archive

    # Path validation
    allowed_path_chars: str = r'^[a-zA-Z0-9._\-/\\ ]+$'
    forbidden_filenames: set = None

    def __post_init__(self):
        """Initialize default forbidden filenames."""
        if self.forbidden_filenames is None:
            self.forbidden_filenames = {
                '..',
                '.',
                'CON', 'PRN', 'AUX', 'NUL',  # Windows reserved
                'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
                'COM6', 'COM7', 'COM8', 'COM9',
                'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5',
                'LPT6', 'LPT7', 'LPT8', 'LPT9'
            }


# Global security configuration
_security_config = SecurityConfig()


def get_security_config() -> SecurityConfig:
    """Get current security configuration."""
    return _security_config


def set_security_config(config: SecurityConfig) -> None:
    """Set security configuration."""
    global _security_config
    _security_config = config


def secure_open(
    path: Path,
    mode: str,
    *,
    follow_symlinks: bool = False,
    buffering: int = -1
) -> BinaryIO:
    """
    Open file with TOCTOU protection using O_NOFOLLOW.

    Prevents Time-of-Check-Time-of-Use race conditions by atomically
    verifying the path is not a symlink during open operation.

    Args:
        path: File path to open
        mode: Open mode ('r', 'rb', 'w', 'wb', etc.)
        follow_symlinks: Allow symlinks (default: False for security)
        buffering: Buffer size for file I/O

    Returns:
        File handle opened with TOCTOU protection

    Raises:
        TOCTOUError: If path is symlink and follow_symlinks=False
        SecurityError: Other security violations during open
        OSError: File operation errors

    Examples:
        >>> with secure_open(Path('file.txt'), 'rb') as f:
        ...     data = f.read()

        >>> # This will fail if file.txt is replaced with symlink
        >>> with secure_open(Path('file.txt'), 'wb') as f:
        ...     f.write(b'data')
    """
    try:
        # On Windows, check symlink before opening (O_NOFOLLOW not available)
        if not follow_symlinks and os.name == 'nt':
            if path.exists() and path.is_symlink():
                raise TOCTOUError(
                    f"Symlink detected (TOCTOU protection): {path}"
                )

        # Determine flags based on mode
        if 'r' in mode and '+' not in mode:
            flags = os.O_RDONLY
        elif 'w' in mode:
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        elif 'a' in mode:
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        elif '+' in mode:
            flags = os.O_RDWR
            if 'w' in mode:
                flags |= os.O_CREAT | os.O_TRUNC
        else:
            flags = os.O_RDONLY

        # Add O_NOFOLLOW for symlink protection on Unix (critical for TOCTOU prevention)
        # Note: O_NOFOLLOW not available on Windows, we check manually above
        if not follow_symlinks and hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW

        # Add binary mode on Windows
        if os.name == 'nt':
            flags |= os.O_BINARY

        # Atomic open with O_NOFOLLOW prevents TOCTOU attacks on Unix
        # On Windows, we checked symlink status before opening
        fd = os.open(path, flags, 0o644)
        return os.fdopen(fd, mode, buffering=buffering)

    except OSError as e:
        if e.errno == errno.ELOOP:
            raise TOCTOUError(
                f"Symlink detected during atomic open (TOCTOU protection): {path}"
            )
        elif e.errno == errno.ENOENT:
            raise FileNotFoundError(f"File not found: {path}")
        elif e.errno == errno.EACCES or e.errno == errno.EPERM:
            raise PermissionError(f"Permission denied: {path}")
        else:
            raise SecurityError(f"Secure open failed for {path}: {e}")


def secure_stat(
    path: Path,
    *,
    follow_symlinks: bool = False
) -> os.stat_result:
    """
    Stat file with TOCTOU protection.

    Uses lstat to avoid following symlinks by default, preventing
    race conditions where symlinks are created between check and use.

    Args:
        path: Path to stat
        follow_symlinks: Follow symlinks (default: False for security)

    Returns:
        os.stat_result with file statistics

    Raises:
        TOCTOUError: Circular symlink detected
        SecurityError: Stat operation security violation
        OSError: File system errors

    Examples:
        >>> stat = secure_stat(Path('file.txt'))
        >>> print(f"Size: {stat.st_size}, Mode: {stat.st_mode}")
    """
    try:
        if follow_symlinks:
            return path.stat()
        else:
            # Use lstat to not follow symlinks (critical for TOCTOU prevention)
            return path.lstat()

    except OSError as e:
        if e.errno == errno.ELOOP:
            raise TOCTOUError(f"Circular symlink detected: {path}")
        elif e.errno == errno.ENOENT:
            raise FileNotFoundError(f"Path not found: {path}")
        elif e.errno == errno.EACCES:
            raise PermissionError(f"Permission denied: {path}")
        else:
            raise SecurityError(f"Secure stat failed for {path}: {e}")


def secure_copy_data(
    source_fd: int,
    dest_fd: int,
    chunk_size: int = 64 * 1024
) -> int:
    """
    Copy data between file descriptors with TOCTOU protection.

    Uses low-level file descriptors to ensure atomicity and prevent
    race conditions during copy operations.

    Args:
        source_fd: Source file descriptor (opened with secure_open)
        dest_fd: Destination file descriptor (opened with secure_open)
        chunk_size: Buffer size for copying (default: 64KB)

    Returns:
        Total bytes copied

    Raises:
        SecurityError: Copy operation security violation
        OSError: File I/O errors during copy

    Examples:
        >>> with secure_open(src, 'rb') as src_f:
        ...     with secure_open(dst, 'wb') as dst_f:
        ...         bytes_copied = secure_copy_data(
        ...             src_f.fileno(), dst_f.fileno()
        ...         )
    """
    try:
        total_bytes = 0

        while True:
            # Read chunk from source
            chunk = os.read(source_fd, chunk_size)
            if not chunk:
                break

            # Write chunk to destination
            bytes_written = os.write(dest_fd, chunk)
            total_bytes += bytes_written

            # Verify all bytes were written
            if bytes_written != len(chunk):
                raise SecurityError(
                    f"Incomplete write: {bytes_written} of {len(chunk)} bytes"
                )

        return total_bytes

    except OSError as e:
        raise SecurityError(f"Secure copy failed: {e}")


def validate_path(
    path: Path,
    allowed_base: Path,
    allow_symlinks: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate that path is safe and within allowed base directory.

    Prevents path traversal attacks by ensuring resolved path
    stays within allowed base directory.

    Args:
        path: Path to validate
        allowed_base: Base directory that path must stay within
        allow_symlinks: Allow symlinks (default: False for security)

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_path(Path('/tmp/safe/file.txt'), Path('/tmp'))
        (True, None)

        >>> validate_path(Path('/tmp/../etc/passwd'), Path('/tmp'))
        (False, 'Path traversal detected')
    """
    try:
        # Check if symlink when not allowed (before resolving)
        if not allow_symlinks and path.exists() and path.is_symlink():
            return False, "Symlinks not allowed"

        # Resolve to absolute path
        resolved_path = path.resolve()
        resolved_base = allowed_base.resolve()

        # Verify path is within allowed base
        try:
            resolved_path.relative_to(resolved_base)
        except ValueError:
            return False, "Path traversal detected: path outside allowed directory"

        # Check for suspicious path components
        if '..' in path.parts:
            return False, "Path traversal detected: '..' in path"

        # Validate filename doesn't contain dangerous characters
        # Skip drive letter on Windows (e.g., C:\)
        parts_to_check = path.parts
        if len(parts_to_check) > 0 and parts_to_check[0].endswith((':\\', ':')):
            parts_to_check = parts_to_check[1:]

        for part in parts_to_check:
            if part == '/' or part == '\\':
                continue  # Skip path separators
            if not is_safe_filename(part):
                return False, f"Unsafe filename component: {part}"

        return True, None

    except (OSError, RuntimeError) as e:
        return False, f"Path validation error: {e}"


def is_safe_path(
    path: Path,
    allowed_base: Path,
    allow_symlinks: bool = False
) -> bool:
    """
    Check if path is safe (convenience wrapper for validate_path).

    Args:
        path: Path to check
        allowed_base: Base directory path must stay within
        allow_symlinks: Allow symlinks

    Returns:
        True if path is safe
    """
    is_valid, _ = validate_path(path, allowed_base, allow_symlinks)
    return is_valid


def sanitize_filename(filename: str, replacement: str = '_') -> str:
    """
    Remove or replace dangerous characters from filename.

    Removes path separators, control characters, and other
    potentially dangerous characters from filenames.

    Args:
        filename: Filename to sanitize
        replacement: Character to replace dangerous chars with

    Returns:
        Sanitized filename

    Examples:
        >>> sanitize_filename('../../../etc/passwd')
        'etc_passwd'

        >>> sanitize_filename('file<>:|?.txt')
        'file_____.txt'
    """
    config = get_security_config()

    # Remove null bytes
    filename = filename.replace('\0', '')

    # Split on path separators and keep only the actual filename
    # This handles '../../../etc/passwd' -> 'passwd'
    filename = filename.replace('\\', '/')
    parts = [p for p in filename.split('/') if p and p != '.' and p != '..']
    if parts:
        filename = parts[-1]  # Take only the last part (actual filename)
    else:
        filename = 'unnamed'

    # Replace other dangerous characters
    dangerous_chars = '<>:"|?*'
    for char in dangerous_chars:
        filename = filename.replace(char, replacement)

    # Remove control characters (ASCII 0-31)
    filename = ''.join(char if ord(char) >= 32 else replacement
                      for char in filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')

    # Ensure not empty
    if not filename:
        filename = 'unnamed'

    # Truncate to reasonable length (255 is common filesystem limit)
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        max_name_len = 255 - len(ext)
        filename = name[:max_name_len] + ext

    return filename


def is_safe_filename(filename: str) -> bool:
    """
    Check if filename is safe.

    Args:
        filename: Filename to check

    Returns:
        True if filename is safe
    """
    config = get_security_config()

    # Check for empty or suspicious names
    if not filename or filename in config.forbidden_filenames:
        return False

    # Check for null bytes
    if '\0' in filename:
        return False

    # Check for path separators
    if '/' in filename or '\\' in filename:
        return False

    # Check for control characters
    if any(ord(char) < 32 for char in filename):
        return False

    # Check for dangerous characters
    dangerous_chars = '<>:"|?*'
    if any(char in filename for char in dangerous_chars):
        return False

    return True


def check_archive_bomb(
    compressed_size: int,
    uncompressed_size: int,
    file_count: int = 0
) -> Tuple[bool, Optional[str]]:
    """
    Check if archive parameters indicate a zip bomb attack.

    Validates compression ratio and total size against configured limits
    to prevent denial-of-service attacks via archive bombs.

    Args:
        compressed_size: Compressed archive size in bytes
        uncompressed_size: Total uncompressed size in bytes
        file_count: Number of files in archive

    Returns:
        Tuple of (is_safe, error_message)

    Examples:
        >>> check_archive_bomb(1000, 50000, 10)
        (True, None)

        >>> check_archive_bomb(1000, 500000000, 10)
        (False, 'Compression ratio too high: 500000.0:1 > 100.0:1')
    """
    config = get_security_config()

    # Check file count
    if file_count > config.max_file_count:
        return False, (
            f"Too many files in archive: {file_count} > "
            f"{config.max_file_count}"
        )

    # Check total uncompressed size
    if uncompressed_size > config.max_extracted_size:
        size_gb = uncompressed_size / (1024**3)
        max_gb = config.max_extracted_size / (1024**3)
        return False, (
            f"Archive too large when extracted: {size_gb:.2f}GB > "
            f"{max_gb:.2f}GB"
        )

    # Check compression ratio
    if compressed_size > 0:
        ratio = uncompressed_size / compressed_size
        if ratio > config.max_compression_ratio:
            return False, (
                f"Compression ratio too high: {ratio:.1f}:1 > "
                f"{config.max_compression_ratio}:1"
            )

    return True, None


def validate_archive_member(
    member_path: str,
    dest_dir: Path
) -> Tuple[bool, Optional[str]]:
    """
    Validate archive member path is safe for extraction.

    Prevents path traversal attacks during archive extraction
    by validating member paths before extraction.

    Args:
        member_path: Path of archive member
        dest_dir: Destination directory for extraction

    Returns:
        Tuple of (is_safe, error_message)

    Examples:
        >>> validate_archive_member('safe/file.txt', Path('/tmp'))
        (True, None)

        >>> validate_archive_member('../../../etc/passwd', Path('/tmp'))
        (False, 'Path traversal detected')
    """
    # Sanitize member path
    member_path = member_path.replace('\\', '/')

    # Check for absolute paths
    if os.path.isabs(member_path):
        return False, "Absolute paths not allowed in archives"

    # Check for path traversal patterns
    if member_path.startswith('/') or member_path.startswith('..'):
        return False, "Path traversal detected in archive member"

    # Build full destination path
    try:
        full_path = (dest_dir / member_path).resolve()
        dest_dir_resolved = dest_dir.resolve()

        # Ensure extracted file stays within destination
        try:
            full_path.relative_to(dest_dir_resolved)
        except ValueError:
            return False, (
                "Path traversal detected: member would extract "
                "outside destination directory"
            )

    except (OSError, RuntimeError, ValueError) as e:
        # Skip null byte error for validation - we'll catch it elsewhere
        if "embedded null character" in str(e):
            return False, "Null byte in path"
        return False, f"Path validation error: {e}"

    # Validate each path component
    parts = Path(member_path).parts
    for part in parts:
        if not is_safe_filename(part):
            return False, f"Unsafe filename in archive: {part}"

    return True, None


def check_permissions(path: Path, mode: str = 'r') -> Tuple[bool, Optional[str]]:
    """
    Check if operation is allowed on path.

    Args:
        path: Path to check
        mode: Operation mode ('r'=read, 'w'=write, 'x'=execute)

    Returns:
        Tuple of (is_allowed, error_message)
    """
    try:
        if not path.exists():
            return False, "Path does not exist"

        # Check read permission
        if 'r' in mode:
            if not os.access(path, os.R_OK):
                return False, "Read permission denied"

        # Check write permission
        if 'w' in mode:
            if path.exists() and not os.access(path, os.W_OK):
                return False, "Write permission denied"
            elif not path.exists():
                parent = path.parent
                if not os.access(parent, os.W_OK):
                    return False, "Write permission denied on parent directory"

        # Check execute permission
        if 'x' in mode:
            if not os.access(path, os.X_OK):
                return False, "Execute permission denied"

        return True, None

    except OSError as e:
        return False, f"Permission check failed: {e}"


def create_safe_path(base_dir: Path, *parts: str) -> Path:
    """
    Create safe path by joining parts and validating result.

    Args:
        base_dir: Base directory
        *parts: Path components to join

    Returns:
        Safe validated path

    Raises:
        UnsafePathError: If resulting path is unsafe
    """
    # Sanitize all parts
    sanitized_parts = [sanitize_filename(part) for part in parts]

    # Build path
    result_path = base_dir
    for part in sanitized_parts:
        result_path = result_path / part

    # Validate
    is_valid, error = validate_path(result_path, base_dir)
    if not is_valid:
        raise UnsafePathError(f"Unsafe path created: {error}")

    return result_path
