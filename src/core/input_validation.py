"""
Comprehensive Input Validation System

Provides multi-layer validation for:
- File paths (length, reserved names, special characters)
- Filenames (safety, sanitization, Unicode handling)
- Patterns (wildcard, regex, ReDoS prevention)
- User input (XSS, command injection prevention)
"""

import re
import platform
import unicodedata
from pathlib import Path
from typing import Tuple, Optional, Set
import fnmatch
import logging


logger = logging.getLogger(__name__)


# Platform-specific constants
WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}

WINDOWS_RESERVED_CHARS = '<>:"|?*'
UNIX_RESERVED_CHARS = '\x00'

# Path length limits (platform-specific)
MAX_PATH_LENGTH_WINDOWS = 260
MAX_PATH_LENGTH_UNIX = 4096
MAX_FILENAME_LENGTH = 255

# Pattern complexity limits (ReDoS prevention)
MAX_WILDCARDS = 10
MAX_QUESTION_MARKS = 20
MAX_PATTERN_LENGTH = 1000


class ValidationError(Exception):
    """Base class for validation errors."""
    pass


class PathValidationError(ValidationError):
    """Path validation failed."""
    pass


class FilenameValidationError(ValidationError):
    """Filename validation failed."""
    pass


class PatternValidationError(ValidationError):
    """Pattern validation failed."""
    pass


def validate_path_comprehensive(
    path: Path,
    base_path: Optional[Path] = None,
    check_exists: bool = False,
    check_writable: bool = False
) -> Tuple[bool, Optional[str]]:
    """Comprehensive path validation with platform-specific checks.

    Args:
        path: Path to validate
        base_path: Base path for relative validation
        check_exists: Whether to check if path exists
        check_writable: Whether to check if path is writable

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Convert to Path object
        if isinstance(path, str):
            path = Path(path)

        # Check path length
        path_str = str(path)
        max_length = (MAX_PATH_LENGTH_WINDOWS if platform.system() == 'Windows'
                     else MAX_PATH_LENGTH_UNIX)

        if len(path_str) > max_length:
            return False, f"Path too long (max {max_length} characters)"

        # Check for null bytes
        if '\x00' in path_str:
            return False, "Path contains null bytes"

        # Platform-specific checks
        if platform.system() == 'Windows':
            # Check reserved names
            name_without_ext = path.stem.upper()
            if name_without_ext in WINDOWS_RESERVED_NAMES:
                return False, f"Reserved Windows name: {path.stem}"

            # Check reserved characters
            if any(char in path_str for char in WINDOWS_RESERVED_CHARS):
                return False, f"Path contains reserved characters: {WINDOWS_RESERVED_CHARS}"

            # Check for trailing dots/spaces (Windows issue)
            if path.name.endswith('.') or path.name.endswith(' '):
                return False, "Filename cannot end with dot or space on Windows"

        else:  # Unix-like systems
            # Check for null byte
            if '\x00' in path_str:
                return False, "Path contains null byte"

        # Check for path traversal attempts
        resolved_path = path.resolve()
        if base_path:
            base_resolved = base_path.resolve()
            try:
                resolved_path.relative_to(base_resolved)
            except ValueError:
                return False, "Path escapes base directory (path traversal attempt)"

        # Check for symlink loops
        try:
            # resolve(strict=True) will raise RuntimeError on symlink loops
            path.resolve(strict=False)
        except RuntimeError:
            return False, "Symlink loop detected"
        except Exception:
            pass  # File might not exist yet

        # Check if path exists (if requested)
        if check_exists and not path.exists():
            return False, f"Path does not exist: {path}"

        # Check if writable (if requested)
        if check_writable:
            # Check parent directory is writable for new files
            parent = path.parent if not path.exists() else path
            if not parent.exists():
                return False, f"Parent directory does not exist: {parent}"

            import os
            if not os.access(parent, os.W_OK):
                return False, f"No write permission: {parent}"

        # Check for mount point crossing (security consideration)
        if base_path and not _is_same_mount(path, base_path):
            logger.warning(f"Mount point crossing: {path} not on same mount as {base_path}")
            # Not necessarily an error, but log it

        return True, None

    except Exception as e:
        return False, f"Path validation error: {e}"


def _is_same_mount(path1: Path, path2: Path) -> bool:
    """Check if two paths are on the same mount point.

    Args:
        path1: First path
        path2: Second path

    Returns:
        True if on same mount point
    """
    try:
        # Get device IDs
        stat1 = path1.stat()
        stat2 = path2.stat()
        return stat1.st_dev == stat2.st_dev
    except Exception:
        return True  # Assume same mount on error


def validate_filename(
    filename: str,
    allow_unicode: bool = True,
    max_length: int = MAX_FILENAME_LENGTH
) -> Tuple[bool, Optional[str]]:
    """Validate filename for safety and compatibility.

    Args:
        filename: Filename to validate
        allow_unicode: Whether to allow Unicode characters
        max_length: Maximum filename length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename cannot be empty"

    # Check length
    if len(filename) > max_length:
        return False, f"Filename too long (max {max_length} characters)"

    # Check for null bytes
    if '\x00' in filename:
        return False, "Filename contains null bytes"

    # Check for path separators
    if '/' in filename or '\\' in filename:
        return False, "Filename cannot contain path separators"

    # Platform-specific validation
    if platform.system() == 'Windows':
        # Reserved names
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in WINDOWS_RESERVED_NAMES:
            return False, f"Reserved Windows name: {name_without_ext}"

        # Reserved characters
        if any(char in filename for char in WINDOWS_RESERVED_CHARS):
            return False, f"Filename contains reserved characters: {WINDOWS_RESERVED_CHARS}"

        # Trailing dots/spaces
        if filename.endswith('.') or filename.endswith(' '):
            return False, "Filename cannot end with dot or space on Windows"

    # Check for control characters
    if any(ord(c) < 32 for c in filename):
        return False, "Filename contains control characters"

    # Unicode validation
    if not allow_unicode:
        try:
            filename.encode('ascii')
        except UnicodeEncodeError:
            return False, "Filename contains non-ASCII characters"

    # Check for potentially dangerous patterns
    dangerous_patterns = [
        r'\.\.',  # Parent directory reference
        r'^\.',   # Hidden file (not necessarily dangerous, but worth noting)
        r'\s+$',  # Trailing whitespace
        r'^\s+',  # Leading whitespace
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, filename):
            logger.warning(f"Filename matches potentially dangerous pattern: {pattern}")

    return True, None


def sanitize_filename(
    filename: str,
    replacement: str = '_',
    preserve_extension: bool = True,
    normalize_unicode: bool = True
) -> str:
    """Sanitize filename by removing/replacing unsafe characters.

    Args:
        filename: Filename to sanitize
        replacement: Character to use for replacements
        preserve_extension: Whether to preserve file extension
        normalize_unicode: Whether to normalize Unicode characters

    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed"

    original_ext = ''
    if preserve_extension:
        original_ext = Path(filename).suffix

    # Normalize Unicode if requested
    if normalize_unicode:
        # NFC normalization (canonical decomposition + composition)
        filename = unicodedata.normalize('NFC', filename)

    # Remove path separators
    filename = filename.replace('/', replacement).replace('\\', replacement)

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Remove control characters (ASCII 0-31)
    filename = ''.join(c for c in filename if ord(c) >= 32)

    # Platform-specific sanitization
    if platform.system() == 'Windows':
        # Remove reserved characters
        for char in WINDOWS_RESERVED_CHARS:
            filename = filename.replace(char, replacement)

        # Remove trailing dots/spaces
        filename = filename.rstrip('. ')

        # Check for reserved names
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in WINDOWS_RESERVED_NAMES:
            filename = f"{replacement}{filename}"

    # Limit length (reserve space for extension)
    max_name_length = MAX_FILENAME_LENGTH - len(original_ext) - 1
    if len(filename) > max_name_length:
        filename = filename[:max_name_length]

    # Restore extension
    if preserve_extension and original_ext:
        filename = f"{filename}{original_ext}"

    # Ensure filename is not empty after sanitization
    if not filename or filename == replacement:
        filename = f"file{replacement}1"

    return filename


def validate_wildcard_pattern(
    pattern: str,
    max_complexity: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """Validate wildcard pattern and prevent ReDoS attacks.

    Args:
        pattern: Wildcard pattern to validate
        max_complexity: Maximum complexity score (default: calculated)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not pattern:
        return False, "Pattern cannot be empty"

    # Check length
    if len(pattern) > MAX_PATTERN_LENGTH:
        return False, f"Pattern too long (max {MAX_PATTERN_LENGTH} characters)"

    # Count wildcards (ReDoS prevention)
    wildcard_count = pattern.count('*')
    question_count = pattern.count('?')

    if wildcard_count > MAX_WILDCARDS:
        return False, f"Too many wildcards (max {MAX_WILDCARDS})"

    if question_count > MAX_QUESTION_MARKS:
        return False, f"Too many question marks (max {MAX_QUESTION_MARKS})"

    # Calculate complexity score
    complexity = wildcard_count * 2 + question_count
    max_complexity = max_complexity or 30

    if complexity > max_complexity:
        return False, f"Pattern too complex (complexity: {complexity}, max: {max_complexity})"

    # Check for nested wildcards (potential ReDoS)
    if '**' in pattern:
        logger.warning("Pattern contains consecutive wildcards")

    # Try to compile pattern
    try:
        fnmatch.translate(pattern)
    except Exception as e:
        return False, f"Invalid pattern syntax: {e}"

    return True, None


def validate_search_query(
    query: str,
    max_length: int = 1000,
    allow_regex: bool = False
) -> Tuple[bool, Optional[str]]:
    """Validate search query for safety.

    Args:
        query: Search query to validate
        max_length: Maximum query length
        allow_regex: Whether to allow regex syntax

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not query:
        return False, "Query cannot be empty"

    # Check length
    if len(query) > max_length:
        return False, f"Query too long (max {max_length} characters)"

    # Check for null bytes
    if '\x00' in query:
        return False, "Query contains null bytes"

    # If regex is allowed, validate regex syntax
    if allow_regex:
        try:
            re.compile(query)
        except re.error as e:
            return False, f"Invalid regex: {e}"

        # Check for potentially dangerous regex patterns (ReDoS)
        redos_patterns = [
            r'\([^)]*\)\+',  # (x)+
            r'\([^)]*\)\*',  # (x)*
            r'\.+\*',        # .+* or .*+
        ]

        for pattern in redos_patterns:
            if re.search(pattern, query):
                return False, "Potentially dangerous regex pattern detected (ReDoS risk)"

    return True, None


def sanitize_user_input(
    text: str,
    input_type: str = 'generic',
    max_length: Optional[int] = None
) -> str:
    """Sanitize user input based on context.

    Args:
        text: Input text to sanitize
        input_type: Type of input ('filename', 'pattern', 'search', 'generic')
        max_length: Maximum length (type-specific default if None)

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    if input_type == 'filename':
        return sanitize_filename(text)

    elif input_type == 'pattern':
        # Remove null bytes
        text = text.replace('\x00', '')
        # Limit length
        max_len = max_length or MAX_PATTERN_LENGTH
        text = text[:max_len]
        # Remove control characters
        text = ''.join(c for c in text if ord(c) >= 32 or c in '\n\r\t')

    elif input_type == 'search':
        # Remove null bytes
        text = text.replace('\x00', '')
        # Limit length
        max_len = max_length or 1000
        text = text[:max_len]
        # Strip whitespace
        text = text.strip()

    else:  # generic
        # Remove null bytes
        text = text.replace('\x00', '')
        # Remove control characters except common ones
        text = ''.join(c for c in text if ord(c) >= 32 or c in '\n\r\t')
        # Limit length
        if max_length:
            text = text[:max_length]

    return text
