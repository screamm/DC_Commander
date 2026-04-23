"""
Tests for central logging setup (Sprint 1 / S1.1).

Validates that ``src.utils.logging_config.setup_logging`` is idempotent,
creates the configured log directory, and that loggers returned by
``get_logger`` write through to the configured rotating file handler.

All tests use pytest's ``tmp_path`` fixture so the user's real
``~/.modern_commander/logs`` directory is never touched.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pytest

from src.utils import logging_config as logging_config_module
from src.utils.logging_config import get_logger, setup_logging


@pytest.fixture(autouse=True)
def _reset_root_logger():
    """Snapshot / restore the root logger around each test.

    ``setup_logging`` mutates the process-wide root logger. Without this
    fixture a failing test could leave handlers attached that then break
    pytest's own log capture or other tests in the suite.
    """
    root = logging.getLogger()
    saved_level = root.level
    saved_handlers = list(root.handlers)

    # Detach existing handlers (but don't close them — they belong to pytest
    # or previous tests). We'll reattach them in teardown.
    for handler in saved_handlers:
        root.removeHandler(handler)

    # Clear module-level singleton so each test starts from a known state.
    logging_config_module._logging_config = None

    try:
        yield
    finally:
        # Close any handlers the test added, then restore the originals.
        for handler in list(root.handlers):
            try:
                handler.close()
            except Exception:
                pass
            root.removeHandler(handler)

        for handler in saved_handlers:
            root.addHandler(handler)
        root.setLevel(saved_level)
        logging_config_module._logging_config = None


def test_setup_logging_creates_log_directory(tmp_path: Path) -> None:
    """setup_logging() must create the target directory if it doesn't exist."""
    log_dir = tmp_path / "nested" / "logs"
    assert not log_dir.exists()

    setup_logging(log_dir=log_dir)

    assert log_dir.is_dir(), "setup_logging() did not create the log directory"


def test_setup_logging_is_idempotent(tmp_path: Path) -> None:
    """Calling setup_logging() twice must not duplicate root handlers."""
    log_dir = tmp_path / "logs"

    setup_logging(log_dir=log_dir)
    first_count = len(logging.getLogger().handlers)

    setup_logging(log_dir=log_dir)
    second_count = len(logging.getLogger().handlers)

    assert first_count == second_count, (
        f"Handler count changed between calls: {first_count} vs {second_count}"
    )
    # Sanity: we expect at least the console + file + error-file handlers.
    assert first_count >= 3, (
        f"Expected >= 3 handlers (console + file + error), got {first_count}"
    )


def test_get_logger_returns_configured_logger(tmp_path: Path) -> None:
    """get_logger() must return a logger that inherits the configured level."""
    setup_logging(log_dir=tmp_path / "logs", log_level=logging.DEBUG)

    log = get_logger("dc_commander.test_module")

    assert isinstance(log, logging.Logger)
    # Child logger has NOTSET by default and inherits from root.
    assert log.getEffectiveLevel() == logging.DEBUG


def test_startup_message_logged(tmp_path: Path) -> None:
    """A log message emitted after setup must land in the rotating log file."""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir=log_dir, log_level=logging.INFO)

    log = get_logger("dc_commander.startup_test")
    sentinel = "STARTUP_SENTINEL_7A3C9E2F"
    log.info("DC Commander starting up: %s", sentinel)

    # Flush everything so we read a complete file.
    for handler in logging.getLogger().handlers:
        handler.flush()

    expected_file = log_dir / f"dc_commander_{datetime.now().strftime('%Y%m%d')}.log"
    assert expected_file.exists(), (
        f"Expected log file not created: {expected_file}. "
        f"Files present: {list(log_dir.iterdir())}"
    )

    contents = expected_file.read_text(encoding="utf-8")
    assert sentinel in contents, (
        f"Sentinel {sentinel!r} not found in log file. "
        f"File contents: {contents!r}"
    )
