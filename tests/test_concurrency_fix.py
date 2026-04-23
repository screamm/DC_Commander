"""Test concurrency fix for progress_dialog race condition.

This test verifies that the thread-safe property accessor prevents
race conditions during concurrent access to progress_dialog.

NOTE: This file previously used module-level sys.modules patching which
poisoned the shared module cache for all subsequent test files in the
same pytest session, causing 'ValueError: I/O operation on closed file'
in pytest's capture teardown. The patching is now scoped to a fixture
using monkeypatch so it is automatically restored after each test.

TODO(sprint-3): Consider creating a dedicated AppTestHarness fixture in
conftest.py so other test files that import ModernCommanderApp can share
the same safe patching pattern instead of each rolling their own.
"""

import threading
import time
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEXTUAL_MODULES = [
    "textual.app",
    "textual.containers",
    "textual.binding",
    "textual.screen",
    "textual.widget",
    "textual.worker",
]

_COMPONENT_MODULES = [
    "components.file_panel",
    "components.command_bar",
    "components.top_menu_bar",
    "components.dialogs",
    "components.menu_screen",
    "components.find_file_dialog",
    "components.quick_view_widget",
]

_FEATURE_MODULES = [
    "features.file_viewer",
    "features.file_editor",
    "features.config_manager",
    "features.theme_manager",
]

_MODEL_MODULES = [
    "models.file_item",
]

_SERVICE_MODULES = [
    "services.file_service",
    "services.file_service_async",
]

_ALL_MOCK_MODULES = (
    _TEXTUAL_MODULES
    + _COMPONENT_MODULES
    + _FEATURE_MODULES
    + _MODEL_MODULES
    + _SERVICE_MODULES
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_with_mocked_deps(monkeypatch):
    """Provide a ModernCommanderApp instance with all external deps mocked.

    Uses monkeypatch so the sys.modules patches are automatically reverted
    when the test finishes — preventing module-cache pollution across the
    rest of the test session.
    """
    # Patch every dependency module before importing the app.
    for mod_name in _ALL_MOCK_MODULES:
        monkeypatch.setitem(sys.modules, mod_name, MagicMock())

    # Also evict modern_commander from the cache so it re-imports cleanly
    # against the mocked deps (in case a previous test already imported it).
    monkeypatch.delitem(sys.modules, "modern_commander", raising=False)

    from modern_commander import ModernCommanderApp  # noqa: PLC0415
    app = ModernCommanderApp()
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_progress_dialog_thread_safety(app_with_mocked_deps):
    """Test that progress_dialog property is thread-safe."""
    app = app_with_mocked_deps

    # Track race condition attempts
    race_conditions_detected = []
    successful_operations = []

    def reader_thread():
        """Thread that reads progress_dialog repeatedly."""
        for _ in range(1000):
            dialog = app.progress_dialog
            if dialog is not None:
                successful_operations.append("read")
            time.sleep(0.0001)

    def writer_thread():
        """Thread that sets progress_dialog repeatedly."""
        for i in range(500):
            mock_dialog = Mock()
            mock_dialog.update_progress = Mock()
            app.progress_dialog = mock_dialog
            successful_operations.append("write_set")

            time.sleep(0.0001)

            app.progress_dialog = None
            successful_operations.append("write_none")
            time.sleep(0.0001)

    def updater_thread():
        """Thread that updates progress using the safe method."""
        for i in range(1000):
            try:
                app._update_progress_safely(i % 100, f"Test message {i}")
                successful_operations.append("update")
            except AttributeError as e:
                race_conditions_detected.append(str(e))
            time.sleep(0.0001)

    threads = []
    for _ in range(5):
        threads.append(threading.Thread(target=reader_thread))
    for _ in range(2):
        threads.append(threading.Thread(target=writer_thread))
    for _ in range(3):
        threads.append(threading.Thread(target=updater_thread))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not race_conditions_detected, (
        f"Race conditions detected: {race_conditions_detected[:10]}"
    )


def test_property_accessor(app_with_mocked_deps):
    """Test that property accessor works correctly."""
    app = app_with_mocked_deps

    assert app.progress_dialog is None, "Initial state should be None"

    mock_dialog = Mock()
    app.progress_dialog = mock_dialog
    assert app.progress_dialog is mock_dialog, "Property should return set value"

    app.progress_dialog = None
    assert app.progress_dialog is None, "Property should return None after clearing"


def test_safe_update_method(app_with_mocked_deps):
    """Test that _update_progress_safely handles None correctly."""
    app = app_with_mocked_deps

    # Should not crash when dialog is None
    app._update_progress_safely(50, "Test message")

    # Should call update_progress when dialog exists
    mock_dialog = Mock()
    mock_dialog.update_progress = Mock()
    app.progress_dialog = mock_dialog

    app._update_progress_safely(75, "Test message 2")

    mock_dialog.update_progress.assert_called_once_with(75, "Test message 2")
