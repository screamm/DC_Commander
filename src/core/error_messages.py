"""User-friendly error message formatting for file operations.

Maps Python exceptions (both built-in and the custom
:mod:`src.core.error_boundary` exceptions) to short human-readable
messages suitable for display in the UI, plus a technical-details
string containing the full traceback for logging or an expandable
"Details" section in ``ErrorDialog``.
"""

from __future__ import annotations

import errno
import traceback
from typing import Tuple

# Import the custom exceptions from the error boundary module. These
# names intentionally shadow ``FileNotFoundError`` from builtins in the
# boundary module, so we alias them explicitly.
from src.core.error_boundary import (
    FileOperationError,
    PermissionDeniedError,
    FileNotFoundError as BoundaryFileNotFoundError,
    DiskFullError,
    PathTooLongError,
    InvalidFileNameError,
)


def _format_traceback(exc: BaseException) -> str:
    """Return the formatted traceback for the given exception.

    Uses ``__traceback__`` when available so that exceptions constructed
    outside of an ``except`` block (e.g. in tests) still produce useful
    output.
    """
    tb = getattr(exc, "__traceback__", None)
    formatted = "".join(traceback.format_exception(type(exc), exc, tb))
    return formatted


def format_user_error(exc: BaseException) -> Tuple[str, str]:
    """Return a ``(user_message, technical_details)`` pair for an exception.

    The user message is short, English, and free of traceback noise.
    The technical details string is the full formatted traceback and
    should be fed into logs and into the ``ErrorDialog(..., details=...)``
    collapsible section.

    Args:
        exc: The exception to format. Any ``BaseException`` is accepted,
            but callers should normally not hand in ``KeyboardInterrupt``
            or ``SystemExit`` — those should propagate.

    Returns:
        A tuple ``(user_message, technical_details)``. Both strings are
        always non-empty.
    """
    details = _format_traceback(exc)

    # Custom file-operation exceptions first. Order matters: the
    # boundary subclasses inherit from FileOperationError, and
    # PermissionDeniedError must be checked before PermissionError
    # only because it is a separate type — they are unrelated.

    if isinstance(exc, PermissionDeniedError):
        return (
            "Access denied. You don't have permission to "
            "perform this operation.",
            details,
        )

    if isinstance(exc, BoundaryFileNotFoundError):
        return (
            "The file or directory no longer exists.",
            details,
        )

    if isinstance(exc, DiskFullError):
        return (
            "The disk is full. Free some space and try again.",
            details,
        )

    if isinstance(exc, PathTooLongError):
        return (
            "The path is too long for the filesystem.",
            details,
        )

    if isinstance(exc, InvalidFileNameError):
        return (
            "The filename contains invalid characters.",
            details,
        )

    # Built-in PermissionError (distinct class from OSError subclass
    # above). It IS a subclass of OSError so we must check it first.
    if isinstance(exc, PermissionError):
        return (
            "Access denied. You don't have permission to "
            "perform this operation.",
            details,
        )

    # Built-in FileNotFoundError (different class from the boundary
    # one imported above).
    import builtins
    if isinstance(exc, builtins.FileNotFoundError):
        return (
            "The file or directory no longer exists.",
            details,
        )

    if isinstance(exc, IsADirectoryError):
        return (
            "This operation expects a file, not a directory.",
            details,
        )

    if isinstance(exc, NotADirectoryError):
        return (
            "This operation expects a directory, not a file.",
            details,
        )

    if isinstance(exc, FileExistsError):
        return (
            "A file or directory with that name already exists.",
            details,
        )

    # Generic OSError — inspect errno for common cases.
    if isinstance(exc, OSError):
        exc_errno = getattr(exc, "errno", None)
        if exc_errno == errno.ENOSPC:
            return (
                "The disk is full. Free some space and try again.",
                details,
            )
        if exc_errno == errno.ENAMETOOLONG:
            return (
                "The path is too long for the filesystem.",
                details,
            )
        # Fallback OSError message — strerror is usually populated on
        # Windows and POSIX both. If not, fall back to str(exc).
        strerror = getattr(exc, "strerror", None) or str(exc) or "unknown"
        return (
            f"Operating system error: {strerror}",
            details,
        )

    # Custom FileOperationError subclasses not matched above (future
    # additions / third-party subclasses).
    if isinstance(exc, FileOperationError):
        return (
            f"File operation error: {exc}" if str(exc)
            else "File operation failed.",
            details,
        )

    # Fallback for anything else.
    return (
        f"Unexpected error: {type(exc).__name__}: {exc}",
        details,
    )


__all__ = ["format_user_error"]
