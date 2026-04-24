"""
Global Crash Reporter for DC Commander

Installs a process-wide ``sys.excepthook`` so that any uncaught exception
produces:

1. An ERROR log entry via the central logger.
2. A crash-dump file in ``~/.modern_commander/crashes/YYYY-MM-DD_HHMMSS.txt``
   containing environment info, the full traceback, and the tail of today's
   log file.
3. A clear message to stderr, followed by the normal interpreter traceback
   (the original excepthook is chained after the dump is written).

Privacy: no network upload, no telemetry. Crash reports stay on disk.

Defensive rule: the handler itself MUST NOT raise. File-I/O failures are
logged and swallowed -- a broken reporter must never mask the underlying
crash that triggered it.
"""

from __future__ import annotations

import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Callable, Optional, Type

from .logging_config import get_logger

# --------------------------------------------------------------------------- #
# Module state
# --------------------------------------------------------------------------- #

# The excepthook that was active before install_crash_handler() ran. Kept so
# uninstall_crash_handler() can restore it and so our handler can chain to it
# after writing the dump (preserving the default stderr traceback).
_original_excepthook: Optional[
    Callable[[Type[BaseException], BaseException, Optional[TracebackType]], None]
] = None

# Directory where crash reports are written. Populated at install time so the
# hook itself does not need to re-resolve it on every crash.
_crash_dir: Optional[Path] = None

# Version string embedded in the crash-dump header. Passed in by run.py.
_version: str = "unknown"

# Maximum suffixed retries when the timestamp-based filename collides.
_MAX_FILENAME_RETRIES = 100

# Number of trailing log lines to include in the crash dump.
_LOG_TAIL_LINES = 100


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def install_crash_handler(
    crash_dir: Optional[Path] = None,
    version: str = "unknown",
) -> None:
    """Install the global ``sys.excepthook`` crash handler.

    Safe to call multiple times; subsequent calls simply re-bind to the
    currently active excepthook (which may already be ours).

    Args:
        crash_dir: Directory for crash reports. Defaults to
            ``~/.modern_commander/crashes/``. Created if missing.
        version: DC Commander version string recorded in the dump header.
    """
    global _original_excepthook, _crash_dir, _version

    _crash_dir = crash_dir or (Path.home() / ".modern_commander" / "crashes")
    _version = version

    # Ensure the crash directory exists up-front. If this fails (e.g. a file
    # already exists at that path, permission denied) we log the problem but
    # still install the hook: _write_crash_dump will handle the directory
    # being absent by swallowing its own I/O errors.
    try:
        _crash_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # noqa: BLE001 - directory creation is best-effort
        get_logger(__name__).error(
            "Could not create crash directory %s: %s", _crash_dir, exc
        )

    # Preserve whatever excepthook is currently live (usually the default
    # sys.__excepthook__, but could be pytest's or an IDE's). Only capture it
    # once so repeat install calls stay idempotent.
    if _original_excepthook is None:
        _original_excepthook = sys.excepthook

    sys.excepthook = _handle_exception


def uninstall_crash_handler() -> None:
    """Restore the excepthook that was active before ``install_crash_handler``.

    Primarily useful for tests so pytest's own excepthook is not polluted
    across test cases.
    """
    global _original_excepthook

    if _original_excepthook is not None:
        sys.excepthook = _original_excepthook
        _original_excepthook = None


# --------------------------------------------------------------------------- #
# Internal handler
# --------------------------------------------------------------------------- #


def _handle_exception(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_tb: Optional[TracebackType],
) -> None:
    """``sys.excepthook`` replacement.

    Writes a crash dump, logs the exception, prints a user-friendly pointer
    to stderr, then chains to the original excepthook so the developer still
    sees the normal Python traceback.
    """
    # Ctrl+C is a user action, not a crash. Let the default handler produce
    # its concise KeyboardInterrupt message and exit cleanly.
    if issubclass(exc_type, KeyboardInterrupt):
        if _original_excepthook is not None:
            _original_excepthook(exc_type, exc_value, exc_tb)
        else:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    dump_path: Optional[Path] = None

    # Everything below is wrapped defensively: a bug in the reporter must not
    # mask the real crash. If anything here raises, fall through to the
    # original excepthook so the user still sees their stack trace.
    try:
        if _crash_dir is not None:
            dump_path = _write_crash_dump(
                exc_type, exc_value, exc_tb, _crash_dir, _version
            )
    except Exception as reporter_exc:  # noqa: BLE001 - must not raise
        # Last-resort notification; do not re-raise.
        try:
            get_logger(__name__).error(
                "Crash reporter failed while writing dump: %s", reporter_exc
            )
        except Exception:  # noqa: BLE001 - logger itself must not raise
            pass

    try:
        logger = get_logger(__name__)
        logger.error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_tb),
        )
    except Exception:  # noqa: BLE001 - logging must not raise
        pass

    # Tell the user where the dump went. This message is intentionally simple
    # and never contains PII beyond the absolute path to their own file.
    try:
        if dump_path is not None:
            sys.stderr.write(
                "\nDC Commander crashed. A crash report was saved to:\n"
                f"  {dump_path}\n"
                "Please include this file if you report the issue.\n"
            )
        else:
            sys.stderr.write(
                "\nDC Commander crashed. (Crash report could not be saved.)\n"
            )
    except Exception:  # noqa: BLE001 - stderr write must not raise
        pass

    # Finally chain to the original excepthook so the normal stack trace
    # still appears on stderr (invaluable during development).
    try:
        if _original_excepthook is not None:
            _original_excepthook(exc_type, exc_value, exc_tb)
        else:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
    except Exception:  # noqa: BLE001 - final fallback
        pass


# --------------------------------------------------------------------------- #
# Crash-dump rendering
# --------------------------------------------------------------------------- #


def _write_crash_dump(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_tb: Optional[TracebackType],
    crash_dir: Path,
    version: str,
) -> Optional[Path]:
    """Serialise a crash report to disk. Never raises.

    Returns the path written, or ``None`` if the dump could not be saved.
    """
    try:
        crash_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        # crash_dir is unusable (e.g. a file exists at that path). Give up --
        # but do so quietly, we are already inside a crash handler.
        try:
            get_logger(__name__).error(
                "Crash directory unavailable (%s): %s", crash_dir, exc
            )
        except Exception:  # noqa: BLE001
            pass
        return None

    dump_path = _resolve_dump_path(crash_dir)
    if dump_path is None:
        return None

    content = _render_crash_dump(exc_type, exc_value, exc_tb, version)

    try:
        dump_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        try:
            get_logger(__name__).error(
                "Could not write crash dump to %s: %s", dump_path, exc
            )
        except Exception:  # noqa: BLE001
            pass
        return None

    return dump_path


def _resolve_dump_path(crash_dir: Path) -> Optional[Path]:
    """Pick a non-colliding filename under ``crash_dir``.

    Uses ``YYYY-MM-DD_HHMMSS.txt``; if that already exists (two crashes in
    the same second), appends ``_1``, ``_2`` ... up to ``_MAX_FILENAME_RETRIES``.
    Returns ``None`` if we run out of attempts.
    """
    base = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    candidate = crash_dir / f"{base}.txt"
    if not candidate.exists():
        return candidate

    for suffix in range(1, _MAX_FILENAME_RETRIES + 1):
        candidate = crash_dir / f"{base}_{suffix}.txt"
        if not candidate.exists():
            return candidate

    # 100 collisions in the same second is pathological. Give up rather
    # than spin forever.
    return None


def _render_crash_dump(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_tb: Optional[TracebackType],
    version: str,
) -> str:
    """Build the crash-dump body string. Pure function, never raises."""
    # Each subsection is computed independently so a failure in one (e.g. log
    # tail read) does not hide the rest of the report.
    timestamp = _safe_call(lambda: datetime.now().isoformat(timespec="seconds"))
    python_version = _safe_call(lambda: sys.version.replace("\n", " "))
    platform_str = _safe_call(platform.platform)
    executable = _safe_call(lambda: sys.executable)

    traceback_str = _safe_call(
        lambda: "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    )

    log_tail = _safe_call(_read_log_tail)

    return (
        "=== DC Commander Crash Report ===\n"
        f"Timestamp:       {timestamp}\n"
        f"DC Commander:    {version}\n"
        f"Python:          {python_version}\n"
        f"Platform:        {platform_str}\n"
        f"Executable:      {executable}\n"
        "\n"
        "--- Exception ---\n"
        f"{traceback_str}\n"
        "--- Last 100 log lines ---\n"
        f"{log_tail}\n"
        "--- End of report ---\n"
    )


def _safe_call(fn: Callable[[], str]) -> str:
    """Run ``fn`` and return its string result, or ``<unavailable>`` on error."""
    try:
        result = fn()
    except Exception:  # noqa: BLE001 - crash-dump section must never raise
        return "<unavailable>"
    if result is None or result == "":
        return "<unavailable>"
    return str(result)


def _read_log_tail() -> str:
    """Return the last ``_LOG_TAIL_LINES`` lines of today's log file.

    Returns ``<unavailable>`` if the file is absent or cannot be read. Keeps
    memory bounded by using a deque; acceptable for 100 lines.
    """
    log_file = (
        Path.home()
        / ".modern_commander"
        / "logs"
        / f"dc_commander_{datetime.now().strftime('%Y%m%d')}.log"
    )

    if not log_file.exists():
        return "<unavailable>"

    try:
        # errors="replace" so a stray byte cannot crash the crash handler.
        with log_file.open("r", encoding="utf-8", errors="replace") as fh:
            from collections import deque

            tail = deque(fh, maxlen=_LOG_TAIL_LINES)
    except OSError:
        return "<unavailable>"

    if not tail:
        return "<unavailable>"

    return "".join(tail).rstrip("\n")
