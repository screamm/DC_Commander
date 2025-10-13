"""Test concurrency fix for progress_dialog race condition.

This test verifies that the thread-safe property accessor prevents
race conditions during concurrent access to progress_dialog.
"""

import threading
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Mock the Textual imports for testing
import sys
sys.modules['textual.app'] = MagicMock()
sys.modules['textual.containers'] = MagicMock()
sys.modules['textual.binding'] = MagicMock()
sys.modules['textual.screen'] = MagicMock()
sys.modules['textual.widget'] = MagicMock()
sys.modules['textual.worker'] = MagicMock()

# Mock component imports
sys.modules['components.file_panel'] = MagicMock()
sys.modules['components.command_bar'] = MagicMock()
sys.modules['components.top_menu_bar'] = MagicMock()
sys.modules['components.dialogs'] = MagicMock()
sys.modules['components.menu_screen'] = MagicMock()
sys.modules['components.find_file_dialog'] = MagicMock()
sys.modules['components.quick_view_widget'] = MagicMock()

# Mock feature imports
sys.modules['features.file_viewer'] = MagicMock()
sys.modules['features.file_editor'] = MagicMock()
sys.modules['features.config_manager'] = MagicMock()
sys.modules['features.theme_manager'] = MagicMock()

# Mock model imports
sys.modules['models.file_item'] = MagicMock()

# Mock service imports
sys.modules['services.file_service'] = MagicMock()
sys.modules['services.file_service_async'] = MagicMock()

# Now we can import the app
from modern_commander import ModernCommanderApp


def test_progress_dialog_thread_safety():
    """Test that progress_dialog property is thread-safe."""

    # Create mock app
    app = ModernCommanderApp()

    # Track race condition attempts
    race_conditions_detected = []
    successful_operations = []

    def reader_thread():
        """Thread that reads progress_dialog repeatedly."""
        for _ in range(1000):
            # Read the property (this should always be safe)
            dialog = app.progress_dialog
            if dialog is not None:
                successful_operations.append("read")
            time.sleep(0.0001)

    def writer_thread():
        """Thread that sets progress_dialog repeatedly."""
        for i in range(500):
            # Set to mock dialog
            mock_dialog = Mock()
            mock_dialog.update_progress = Mock()
            app.progress_dialog = mock_dialog
            successful_operations.append("write_set")

            time.sleep(0.0001)

            # Set to None
            app.progress_dialog = None
            successful_operations.append("write_none")
            time.sleep(0.0001)

    def updater_thread():
        """Thread that updates progress using the safe method."""
        for i in range(1000):
            try:
                # Use the thread-safe update method
                app._update_progress_safely(i % 100, f"Test message {i}")
                successful_operations.append("update")
            except AttributeError as e:
                # This would indicate a race condition
                race_conditions_detected.append(str(e))
            time.sleep(0.0001)

    # Start multiple threads
    threads = []

    # Create 5 reader threads
    for _ in range(5):
        t = threading.Thread(target=reader_thread)
        threads.append(t)

    # Create 2 writer threads
    for _ in range(2):
        t = threading.Thread(target=writer_thread)
        threads.append(t)

    # Create 3 updater threads
    for _ in range(3):
        t = threading.Thread(target=updater_thread)
        threads.append(t)

    # Start all threads
    for t in threads:
        t.start()

    # Wait for completion
    for t in threads:
        t.join()

    # Verify no race conditions
    print(f"Successful operations: {len(successful_operations)}")
    print(f"Race conditions detected: {len(race_conditions_detected)}")

    if race_conditions_detected:
        print("\nRace conditions found:")
        for error in race_conditions_detected[:10]:  # Show first 10
            print(f"  - {error}")
        return False
    else:
        print("\n✓ No race conditions detected - Thread safety verified!")
        return True


def test_property_accessor():
    """Test that property accessor works correctly."""
    app = ModernCommanderApp()

    # Test initial state
    assert app.progress_dialog is None, "Initial state should be None"

    # Test setting value
    mock_dialog = Mock()
    app.progress_dialog = mock_dialog
    assert app.progress_dialog is mock_dialog, "Property should return set value"

    # Test setting to None
    app.progress_dialog = None
    assert app.progress_dialog is None, "Property should return None after clearing"

    print("✓ Property accessor working correctly!")
    return True


def test_safe_update_method():
    """Test that _update_progress_safely handles None correctly."""
    app = ModernCommanderApp()

    # Should not crash when dialog is None
    try:
        app._update_progress_safely(50, "Test message")
        print("✓ Safe update handles None correctly (no crash)")
    except Exception as e:
        print(f"✗ Safe update crashed: {e}")
        return False

    # Should call update_progress when dialog exists
    mock_dialog = Mock()
    mock_dialog.update_progress = Mock()
    app.progress_dialog = mock_dialog

    app._update_progress_safely(75, "Test message 2")

    mock_dialog.update_progress.assert_called_once_with(75, "Test message 2")
    print("✓ Safe update calls update_progress when dialog exists")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Progress Dialog Concurrency Fix")
    print("=" * 60)
    print()

    # Run tests
    test1 = test_property_accessor()
    print()

    test2 = test_safe_update_method()
    print()

    test3 = test_progress_dialog_thread_safety()
    print()

    # Summary
    print("=" * 60)
    if test1 and test2 and test3:
        print("✓ ALL TESTS PASSED - Race condition fixed!")
    else:
        print("✗ SOME TESTS FAILED - Review implementation")
    print("=" * 60)
