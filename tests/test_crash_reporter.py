"""Tests for the global crash reporter (src.utils.crash_reporter).

Covers:
- install/uninstall toggles sys.excepthook correctly
- crash dumps are written with the expected sections
- KeyboardInterrupt is NOT reported (user-initiated, not a crash)
- a broken crash_dir does not propagate exceptions from the handler
- the tail of today's log file is embedded in the dump
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils import crash_reporter
from src.utils.crash_reporter import (
    _handle_exception,
    _write_crash_dump,
    install_crash_handler,
    uninstall_crash_handler,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _restore_excepthook():
    """Save/restore sys.excepthook around every test.

    Guarantees that a test which installs the handler cannot leak that hook
    into pytest's own infrastructure (which would mask unrelated test
    failures with crash dumps).
    """
    saved = sys.excepthook
    try:
        yield
    finally:
        uninstall_crash_handler()
        sys.excepthook = saved


def _make_exc_info(exc: BaseException):
    """Return a real (exc_type, exc_value, exc_tb) triple for ``exc``.

    Raising and catching the exception gives us a genuine traceback object
    -- much more realistic than passing ``None`` for exc_tb.
    """
    try:
        raise exc
    except BaseException:  # noqa: BLE001 - deliberate catch-all for test fixture
        return sys.exc_info()


# --------------------------------------------------------------------------- #
# install / uninstall
# --------------------------------------------------------------------------- #


def test_install_sets_excepthook(tmp_path):
    """install_crash_handler swaps sys.excepthook; uninstall restores it."""
    original = sys.excepthook

    install_crash_handler(crash_dir=tmp_path, version="test-1.0")
    assert sys.excepthook is not original
    assert sys.excepthook is crash_reporter._handle_exception

    uninstall_crash_handler()
    assert sys.excepthook is original


# --------------------------------------------------------------------------- #
# Crash-dump file creation
# --------------------------------------------------------------------------- #


def test_crash_dump_written_to_file(tmp_path):
    """A real exception triggers a dump file with the documented sections."""
    install_crash_handler(crash_dir=tmp_path, version="test-1.0")

    exc_info = _make_exc_info(ZeroDivisionError("division by zero"))

    # Swallow stderr output from chained default excepthook so it does not
    # pollute pytest's report.
    with patch.object(sys, "stderr"):
        _handle_exception(*exc_info)

    dumps = list(tmp_path.glob("*.txt"))
    assert len(dumps) == 1, f"Expected exactly one dump file, got: {dumps}"

    content = dumps[0].read_text(encoding="utf-8")
    assert "=== DC Commander Crash Report ===" in content
    assert "--- Exception ---" in content
    assert "--- Last 100 log lines ---" in content
    assert "--- End of report ---" in content
    assert "ZeroDivisionError" in content
    assert "division by zero" in content
    assert "DC Commander:    test-1.0" in content


def test_keyboard_interrupt_ignored(tmp_path):
    """Ctrl+C must not produce a crash dump (it is not a crash)."""
    install_crash_handler(crash_dir=tmp_path, version="test-1.0")

    exc_info = _make_exc_info(KeyboardInterrupt())

    with patch.object(sys, "stderr"):
        _handle_exception(*exc_info)

    dumps = list(tmp_path.glob("*.txt"))
    assert dumps == [], f"KeyboardInterrupt should not write a dump, got: {dumps}"


# --------------------------------------------------------------------------- #
# Defensive behaviour: handler must not raise
# --------------------------------------------------------------------------- #


def test_write_failure_does_not_raise(tmp_path):
    """If crash_dir points at a regular file, the handler still must not raise."""
    # A file at that path means mkdir(parents=True, exist_ok=True) will fail
    # with FileExistsError / NotADirectoryError depending on the platform.
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("I am a file, not a directory", encoding="utf-8")

    install_crash_handler(crash_dir=blocker, version="test-1.0")

    exc_info = _make_exc_info(RuntimeError("boom"))

    # The entire call must complete without propagating anything.
    with patch.object(sys, "stderr"):
        _handle_exception(*exc_info)

    # And it definitely must not have created anything under the blocker path.
    assert blocker.is_file(), "Blocker file was unexpectedly replaced"


def test_write_crash_dump_returns_none_on_bad_dir(tmp_path):
    """_write_crash_dump returns None (does not raise) on I/O failure."""
    blocker = tmp_path / "blocker"
    blocker.write_text("file not dir", encoding="utf-8")

    exc_info = _make_exc_info(ValueError("nope"))

    result = _write_crash_dump(
        exc_info[0], exc_info[1], exc_info[2], blocker, "test"
    )
    assert result is None


# --------------------------------------------------------------------------- #
# Log-tail inclusion
# --------------------------------------------------------------------------- #


def test_log_tail_included(tmp_path, monkeypatch):
    """The dump embeds the tail of today's log file if present."""
    # Point Path.home() at tmp_path so the reporter looks in
    # <tmp_path>/.modern_commander/logs/dc_commander_YYYYMMDD.log instead of
    # the real home directory.
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    log_dir = tmp_path / ".modern_commander" / "logs"
    log_dir.mkdir(parents=True)
    log_file = log_dir / f"dc_commander_{datetime.now().strftime('%Y%m%d')}.log"

    sentinel_line = "SENTINEL_LOG_LINE_FOR_CRASH_REPORTER_TEST"
    log_file.write_text(
        "\n".join([f"line {i}" for i in range(50)] + [sentinel_line]) + "\n",
        encoding="utf-8",
    )

    crash_dir = tmp_path / "crashes"
    install_crash_handler(crash_dir=crash_dir, version="test-1.0")

    exc_info = _make_exc_info(RuntimeError("log tail test"))

    with patch.object(sys, "stderr"):
        _handle_exception(*exc_info)

    dumps = list(crash_dir.glob("*.txt"))
    assert len(dumps) == 1

    content = dumps[0].read_text(encoding="utf-8")
    assert sentinel_line in content, (
        "Crash dump should contain the tail of today's log file; "
        f"got:\n{content}"
    )
