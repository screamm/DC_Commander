"""Security validation helpers for UI input.

Wraps src.core.security functions with UX-friendly error messages
and structured logging suitable for input dialogs.

All validation failures are logged via ``logger.warning`` with the
offending input (``repr``-ed so control characters are visible) and a
short reason, producing a security-auditable trail without exposing
stack traces to end users.

The public surface is intentionally small:

    - :class:`UIValidationError` — exception with a user-facing message
      plus technical details suitable for an ``ErrorDialog``.
    - :func:`validate_user_filename` — for filename prompts (F7 mkdir,
      rename, save-as, etc.).
    - :func:`validate_user_path` — for path prompts (Goto directory,
      path-based Find, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.core.security import (
    PathTraversalError,
    SecurityError,
    UnsafePathError,
    is_safe_filename,
    validate_path,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Filesystem-level filename length cap. 255 is the common NAME_MAX on
# ext4/NTFS/APFS for a single path component; entries longer than this
# cannot be created on any mainstream filesystem.
MAX_FILENAME_LENGTH = 255


class UIValidationError(Exception):
    """Raised when user input fails security/sanity check.

    Attributes:
        user_message: Short, user-facing reason (one line, English) —
            intended for the top of an ``ErrorDialog``.
        technical_details: Longer description including which check
            failed — intended for the collapsible "Details" section.
    """

    def __init__(self, user_message: str, technical_details: str = "") -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.technical_details = technical_details


def validate_user_filename(filename: str) -> str:
    """Validate a user-entered filename.

    Returns the filename unchanged on success. Raises
    :class:`UIValidationError` (and emits a ``logger.warning``) when the
    input fails any of the following checks:

    - not empty and not pure whitespace
    - not ``.`` or ``..``
    - :func:`src.core.security.is_safe_filename` passes (rejects path
      separators, null bytes, control characters, reserved Windows
      names such as ``CON``/``NUL``/``COM1``, and characters
      ``<>:"|?*``)
    - length <= :data:`MAX_FILENAME_LENGTH` (255)

    Args:
        filename: Raw user input from an :class:`InputDialog`.

    Returns:
        The same string, unchanged, if it is safe to use directly as a
        single path component.

    Raises:
        UIValidationError: If the filename fails any validation check.
    """
    # Normalize type — InputDialog always returns str but be defensive.
    if not isinstance(filename, str):
        # TODO Sprint 3.5: remove defensive isinstance once callers are typed end-to-end
        reason = f"non-string input (type={type(filename).__name__})"  # type: ignore[unreachable]
        logger.warning("Filename validation failed: %r — %s", filename, reason)
        raise UIValidationError(
            "Name must be text.",
            f"Expected str, got {type(filename).__name__}.",
        )

    if not filename or not filename.strip():
        reason = "empty or whitespace-only"
        logger.warning("Filename validation failed: %r — %s", filename, reason)
        raise UIValidationError(
            "Name cannot be empty.",
            "The filename was empty or contained only whitespace.",
        )

    if filename in (".", ".."):
        reason = "reserved relative-path name"
        logger.warning("Filename validation failed: %r — %s", filename, reason)
        raise UIValidationError(
            "Name cannot be '.' or '..'.",
            "The names '.' and '..' refer to the current and parent "
            "directory and cannot be used as filenames.",
        )

    if len(filename) > MAX_FILENAME_LENGTH:
        reason = f"too long ({len(filename)} > {MAX_FILENAME_LENGTH})"
        logger.warning("Filename validation failed: %r — %s", filename, reason)
        raise UIValidationError(
            f"Name is too long (max {MAX_FILENAME_LENGTH} characters).",
            f"Filename length {len(filename)} exceeds filesystem "
            f"limit of {MAX_FILENAME_LENGTH}.",
        )

    if not is_safe_filename(filename):
        reason = "unsafe characters or reserved name"
        logger.warning("Filename validation failed: %r — %s", filename, reason)
        raise UIValidationError(
            "Name contains invalid characters: / \\ \\0 or reserved "
            "names (CON, NUL, ...).",
            "is_safe_filename() rejected the input. This covers path "
            "separators (/ \\), null bytes, control characters, "
            "characters <>:\"|?*, and reserved Windows device names "
            "(CON, PRN, AUX, NUL, COM1-9, LPT1-9).",
        )

    return filename


def validate_user_path(
    path_str: str,
    *,
    must_exist: bool = False,
    base_dir: Optional[Path] = None,
) -> Path:
    """Validate a user-entered path string.

    Returns a resolved absolute :class:`~pathlib.Path` on success.
    Raises :class:`UIValidationError` (and emits a ``logger.warning``)
    on failure.

    Performs, in order:

    1. Strip surrounding whitespace; reject empty.
    2. Expand a leading ``~`` (``expanduser``).
    3. Resolve to an absolute path (``resolve()``); this collapses
       ``..`` segments, which lets :func:`validate_path` detect
       traversal attempts against ``base_dir``.
    4. If ``base_dir`` is given, delegate to
       :func:`src.core.security.validate_path` to ensure the resolved
       path stays within ``base_dir``.
    5. If ``must_exist=True``, verify the path exists on disk.

    Args:
        path_str: Raw user input from an :class:`InputDialog`.
        must_exist: When ``True``, the resolved path must already
            exist on disk; otherwise :class:`UIValidationError` is
            raised.
        base_dir: Optional containment directory. When provided, the
            resolved path must be inside it (path-traversal guard).

    Returns:
        Resolved absolute :class:`~pathlib.Path`.

    Raises:
        UIValidationError: If the path fails any validation check.
    """
    if not isinstance(path_str, str):
        # TODO Sprint 3.5: remove defensive isinstance once callers are typed end-to-end
        reason = f"non-string input (type={type(path_str).__name__})"  # type: ignore[unreachable]
        logger.warning("Path validation failed: %r — %s", path_str, reason)
        raise UIValidationError(
            "Path must be text.",
            f"Expected str, got {type(path_str).__name__}.",
        )

    stripped = path_str.strip()
    if not stripped:
        logger.warning(
            "Path validation failed: %r — empty or whitespace-only", path_str
        )
        raise UIValidationError(
            "Name cannot be empty.",
            "The path was empty or contained only whitespace.",
        )

    # Reject null bytes early — Path() on Windows raises ValueError on
    # them, but the message is opaque ("embedded null character").
    if "\0" in stripped:
        logger.warning(
            "Path validation failed: %r — null byte in input", path_str
        )
        raise UIValidationError(
            "Name contains invalid characters: / \\ \\0 or reserved "
            "names (CON, NUL, ...).",
            "Path contained an embedded null byte.",
        )

    try:
        resolved = Path(stripped).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        logger.warning(
            "Path validation failed: %r — resolve() raised %s: %s",
            path_str,
            type(exc).__name__,
            exc,
        )
        raise UIValidationError(
            "Path is not allowed for security reasons.",
            f"Path could not be resolved: {type(exc).__name__}: {exc}",
        ) from exc

    if base_dir is not None:
        try:
            base_resolved = base_dir.resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning(
                "Path validation failed: base_dir=%r could not be "
                "resolved (%s)",
                base_dir,
                exc,
            )
            raise UIValidationError(
                "Path is not allowed for security reasons.",
                f"Base directory could not be resolved: {exc}",
            ) from exc

        is_valid, err = validate_path(resolved, base_resolved)
        if not is_valid:
            logger.warning(
                "Path validation failed: %r — path traversal/unsafe "
                "(%s)",
                path_str,
                err,
            )
            # validate_path reports both traversal and unsafe-filename
            # errors via the same tuple return. Surface the specific
            # reason in details.
            if err and "traversal" in err.lower():
                user_msg = "Path escapes the allowed directory."
            else:
                user_msg = "Path is not allowed for security reasons."
            raise UIValidationError(
                user_msg,
                f"validate_path rejected path: {err}",
            )

    if must_exist and not resolved.exists():
        logger.warning(
            "Path validation failed: %r — does not exist (resolved=%s)",
            path_str,
            resolved,
        )
        raise UIValidationError(
            "Path does not exist.",
            f"Resolved path {resolved} was not found on disk.",
        )

    return resolved
