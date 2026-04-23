"""Tests for :mod:`src.core.error_messages`.

Covers exception-to-user-message mapping for every branch of
:func:`format_user_error` and verifies that the technical details
always include a full traceback when the exception was actually raised.
"""

from __future__ import annotations

import errno

import pytest

from src.core.error_messages import format_user_error
from src.core.error_boundary import (
    PermissionDeniedError,
    FileNotFoundError as BoundaryFileNotFoundError,
    DiskFullError,
    PathTooLongError,
    InvalidFileNameError,
    FileOperationError,
)


# --- Core mappings -------------------------------------------------------


def test_permission_error_message() -> None:
    user_msg, details = format_user_error(PermissionError("nope"))
    assert "Access denied" in user_msg
    assert "permission" in user_msg.lower()
    assert isinstance(details, str) and details  # non-empty


def test_permission_denied_custom_error_message() -> None:
    user_msg, _ = format_user_error(PermissionDeniedError("nope"))
    assert "Access denied" in user_msg


def test_file_not_found_message() -> None:
    user_msg, _ = format_user_error(FileNotFoundError("missing"))
    assert "no longer exists" in user_msg


def test_boundary_file_not_found_message() -> None:
    user_msg, _ = format_user_error(BoundaryFileNotFoundError("missing"))
    assert "no longer exists" in user_msg


def test_is_a_directory_message() -> None:
    user_msg, _ = format_user_error(IsADirectoryError("it is a dir"))
    assert "expects a file" in user_msg


def test_not_a_directory_message() -> None:
    user_msg, _ = format_user_error(NotADirectoryError("not a dir"))
    assert "expects a directory" in user_msg


def test_file_exists_message() -> None:
    user_msg, _ = format_user_error(FileExistsError("dupe"))
    assert "already exists" in user_msg


def test_disk_full_message_via_oserror_errno() -> None:
    exc = OSError(errno.ENOSPC, "No space left on device")
    user_msg, _ = format_user_error(exc)
    assert "disk is full" in user_msg.lower()
    assert "free some space" in user_msg.lower()


def test_disk_full_custom_error_message() -> None:
    user_msg, _ = format_user_error(DiskFullError("full"))
    assert "disk is full" in user_msg.lower()


def test_path_too_long_via_errno() -> None:
    exc = OSError(errno.ENAMETOOLONG, "File name too long")
    user_msg, _ = format_user_error(exc)
    assert "too long" in user_msg.lower()


def test_path_too_long_custom_error() -> None:
    user_msg, _ = format_user_error(PathTooLongError("long"))
    assert "too long" in user_msg.lower()


def test_invalid_filename_message() -> None:
    user_msg, _ = format_user_error(InvalidFileNameError("bad*name"))
    assert "invalid characters" in user_msg.lower()


def test_generic_oserror_fallback_uses_strerror() -> None:
    # errno 9999 is not any of the special-cased ones.
    exc = OSError(9999, "Something went wrong")
    user_msg, _ = format_user_error(exc)
    assert "Operating system error" in user_msg
    assert "Something went wrong" in user_msg


def test_generic_file_operation_error_fallback() -> None:
    user_msg, _ = format_user_error(FileOperationError("boom"))
    assert "File operation" in user_msg


def test_generic_exception_fallback() -> None:
    class SomeBusinessError(Exception):
        """A custom exception that does not match any mapping."""

    exc = SomeBusinessError("oh no")
    user_msg, _ = format_user_error(exc)
    assert "Unexpected error" in user_msg
    assert "SomeBusinessError" in user_msg
    assert "oh no" in user_msg


# --- Details payload -----------------------------------------------------


def test_details_contain_traceback() -> None:
    """Details should contain a real traceback when exception was raised."""
    try:
        raise RuntimeError("explode")
    except RuntimeError as exc:
        _, details = format_user_error(exc)

    assert "RuntimeError" in details
    assert "explode" in details
    assert "Traceback" in details


def test_details_nonempty_for_freshly_constructed_exception() -> None:
    """Even if no traceback is attached, details should not be empty."""
    exc = ValueError("no traceback")
    _, details = format_user_error(exc)
    assert details  # non-empty
    assert "ValueError" in details
