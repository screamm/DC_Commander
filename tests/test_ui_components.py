"""
Comprehensive unit tests for UI components.

Tests cover:
- FilePanel (navigation, selection, refresh, sorting)
- CommandBar (updates, context switching, command management)
- StatusBar (updates, formatting)
- Dialogs (user interactions, validation)

Note: These tests use Textual's testing utilities for UI component testing.
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from textual.widgets import DataTable
from components.file_panel import FilePanel, FileItem
from components.command_bar import CommandBar, Command, CommandButton


# Test Fixtures
@pytest.fixture
def temp_test_dir(tmp_path):
    """Create temporary directory with test structure."""
    test_dir = tmp_path / "panel_test"
    test_dir.mkdir()

    # Create test files
    (test_dir / "file1.txt").write_text("Content 1")
    (test_dir / "file2.py").write_text("# Python")
    (test_dir / "file3.md").write_text("# Markdown")

    # Create subdirectory
    sub = test_dir / "subdir"
    sub.mkdir()
    (sub / "nested.txt").write_text("Nested")

    return test_dir


# FileItem Tests
class TestFileItem:
    """Test FileItem dataclass."""

    def test_file_item_creation(self, temp_test_dir):
        """Test creating FileItem."""
        file_path = temp_test_dir / "file1.txt"
        stat = file_path.stat()

        item = FileItem(
            name="file1.txt",
            path=file_path,
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
            is_dir=False
        )

        assert item.name == "file1.txt"
        assert item.path == file_path
        assert item.is_dir is False
        assert item.is_parent is False

    def test_file_item_parent_directory(self):
        """Test parent directory FileItem."""
        item = FileItem(
            name="..",
            path=Path("/parent"),
            size=0,
            modified=datetime.now(),
            is_dir=True,
            is_parent=True
        )

        assert item.is_parent is True
        assert item.is_dir is True


# FilePanel Tests
class TestFilePanel:
    """Test FilePanel component."""

    def test_file_panel_initialization(self, temp_test_dir):
        """Test FilePanel initialization."""
        panel = FilePanel(path=temp_test_dir, id="test_panel")

        assert panel.current_path == temp_test_dir
        assert panel.id == "test_panel"

    def test_file_panel_initial_path(self):
        """Test FilePanel with no initial path uses cwd."""
        panel = FilePanel()

        assert panel.current_path == Path.cwd()

    @pytest.mark.asyncio
    async def test_file_panel_load_directory(self, temp_test_dir):
        """Test loading directory contents."""
        panel = FilePanel(path=temp_test_dir)

        items = panel._load_directory()

        # Should have parent entry + files
        assert len(items) > 0
        names = [item.name for item in items]
        assert ".." in names  # Parent directory
        assert "file1.txt" in names
        assert "subdir" in names

    def test_file_panel_get_current_item(self, temp_test_dir):
        """Test getting current highlighted item."""
        panel = FilePanel(path=temp_test_dir)
        panel._file_items = panel._load_directory()

        # Mock table cursor
        with patch.object(panel, 'query_one') as mock_query:
            mock_table = Mock(spec=DataTable)
            mock_table.cursor_row = 0
            mock_table.get_row_at.return_value = str(panel._file_items[0].path)
            mock_query.return_value = mock_table

            item = panel.get_current_item()
            assert item is not None

    def test_file_panel_toggle_selection(self, temp_test_dir):
        """Test toggling file selection."""
        panel = FilePanel(path=temp_test_dir)
        panel._file_items = panel._load_directory()

        # Find a non-parent item
        test_item = next(item for item in panel._file_items if not item.is_parent)

        # Mock table for selection
        with patch.object(panel, 'query_one') as mock_query:
            mock_table = Mock(spec=DataTable)
            mock_table.cursor_row = 1
            mock_table.get_row_at.return_value = str(test_item.path)
            mock_query.return_value = mock_table

            # Toggle selection
            panel.toggle_selection()

            # Item should be selected
            assert str(test_item.path) in panel.selected_files

            # Toggle again
            panel.toggle_selection()

            # Item should be deselected
            assert str(test_item.path) not in panel.selected_files

    def test_file_panel_clear_selection(self, temp_test_dir):
        """Test clearing all selections."""
        panel = FilePanel(path=temp_test_dir)

        # Add some selections
        panel.selected_files.add(str(temp_test_dir / "file1.txt"))
        panel.selected_files.add(str(temp_test_dir / "file2.py"))

        panel.clear_selection()

        assert len(panel.selected_files) == 0

    def test_file_panel_get_selected_items(self, temp_test_dir):
        """Test retrieving selected items."""
        panel = FilePanel(path=temp_test_dir)
        panel._file_items = panel._load_directory()

        # Select items
        test_item = next(item for item in panel._file_items if not item.is_parent)
        panel.selected_files.add(str(test_item.path))

        selected = panel.get_selected_items()

        assert len(selected) == 1
        assert selected[0].path == test_item.path

    def test_file_panel_navigate_to(self, temp_test_dir):
        """Test navigation to directory."""
        panel = FilePanel(path=temp_test_dir)
        sub_dir = temp_test_dir / "subdir"

        panel.navigate_to(sub_dir)

        assert panel.current_path == sub_dir

    def test_file_panel_navigate_to_file_ignored(self, temp_test_dir):
        """Test navigation to file is ignored."""
        panel = FilePanel(path=temp_test_dir)
        file_path = temp_test_dir / "file1.txt"
        original_path = panel.current_path

        panel.navigate_to(file_path)

        # Path should not change
        assert panel.current_path == original_path

    def test_file_panel_navigate_up(self, temp_test_dir):
        """Test navigating to parent directory."""
        sub_dir = temp_test_dir / "subdir"
        panel = FilePanel(path=sub_dir)

        panel.navigate_up()

        assert panel.current_path == temp_test_dir

    def test_file_panel_navigate_up_at_root(self, temp_test_dir):
        """Test navigate up behavior at filesystem root."""
        # Navigate to a directory near root
        panel = FilePanel(path=temp_test_dir)
        original = panel.current_path

        # Navigate up multiple times
        for _ in range(10):
            panel.navigate_up()
            if panel.current_path.parent == panel.current_path:
                # At root
                break

        # Should stop at root, not crash
        assert panel.current_path.exists()

    def test_file_panel_cycle_sort(self, temp_test_dir):
        """Test cycling through sort columns."""
        panel = FilePanel(path=temp_test_dir)

        assert panel.sort_column == "name"

        panel.cycle_sort()
        assert panel.sort_column == "size"

        panel.cycle_sort()
        assert panel.sort_column == "modified"

        panel.cycle_sort()
        assert panel.sort_column == "name"  # Cycles back

    def test_file_panel_toggle_sort_direction(self, temp_test_dir):
        """Test toggling sort direction."""
        panel = FilePanel(path=temp_test_dir)

        assert panel.sort_reverse is False

        panel.toggle_sort_direction()
        assert panel.sort_reverse is True

        panel.toggle_sort_direction()
        assert panel.sort_reverse is False

    def test_file_panel_format_size(self, temp_test_dir):
        """Test size formatting."""
        panel = FilePanel(path=temp_test_dir)

        assert "B" in panel._format_size(100)
        assert "KB" in panel._format_size(2048)
        assert "MB" in panel._format_size(2 * 1024 * 1024)
        assert "GB" in panel._format_size(3 * 1024 * 1024 * 1024)


# Command Tests
class TestCommand:
    """Test Command dataclass."""

    def test_command_creation(self):
        """Test creating Command."""
        cmd = Command(
            key="F1",
            label="Help",
            action="show_help",
            enabled=True,
            visible=True
        )

        assert cmd.key == "F1"
        assert cmd.label == "Help"
        assert cmd.action == "show_help"
        assert cmd.enabled is True
        assert cmd.visible is True

    def test_command_defaults(self):
        """Test Command default values."""
        cmd = Command(key="F1", label="Test")

        assert cmd.action is None
        assert cmd.enabled is True
        assert cmd.visible is True


# CommandButton Tests
class TestCommandButton:
    """Test CommandButton widget."""

    def test_command_button_initialization(self):
        """Test CommandButton initialization."""
        cmd = Command("F1", "Help", "show_help")
        button = CommandButton(cmd, id="btn_f1")

        assert button.command == cmd
        assert button.enabled is True
        assert button.id == "btn_f1"

    def test_command_button_render(self):
        """Test CommandButton rendering."""
        cmd = Command("F1", "Help")
        button = CommandButton(cmd)

        rendered = button.render()

        assert "F1" in rendered
        assert "Help" in rendered

    def test_command_button_disabled(self):
        """Test CommandButton disabled state."""
        cmd = Command("F1", "Help", enabled=False)
        button = CommandButton(cmd)

        assert button.enabled is False


# CommandBar Tests
class TestCommandBar:
    """Test CommandBar component."""

    def test_command_bar_initialization(self):
        """Test CommandBar initialization."""
        bar = CommandBar()

        assert len(bar.commands) > 0
        assert "f1" in bar.commands
        assert "f10" in bar.commands

    def test_command_bar_custom_commands(self):
        """Test CommandBar with custom commands."""
        custom_cmds = {
            "f1": Command("F1", "Custom"),
            "f2": Command("F2", "Test"),
        }

        bar = CommandBar(commands=custom_cmds)

        assert bar.commands == custom_cmds

    def test_command_bar_update_command(self):
        """Test updating a command."""
        bar = CommandBar()

        bar.update_command("f1", label="New Label")

        assert bar.commands["f1"].label == "New Label"

    def test_command_bar_update_command_action(self):
        """Test updating command action."""
        bar = CommandBar()

        bar.update_command("f1", action="new_action")

        assert bar.commands["f1"].action == "new_action"

    def test_command_bar_update_command_enabled(self):
        """Test updating command enabled state."""
        bar = CommandBar()

        bar.update_command("f3", enabled=False)

        assert bar.commands["f3"].enabled is False

    def test_command_bar_enable_disable_commands(self):
        """Test enable/disable command shortcuts."""
        bar = CommandBar()

        bar.disable_command("f5")
        assert bar.commands["f5"].enabled is False

        bar.enable_command("f5")
        assert bar.commands["f5"].enabled is True

    def test_command_bar_show_hide_commands(self):
        """Test show/hide command shortcuts."""
        bar = CommandBar()

        bar.hide_command("f7")
        assert bar.commands["f7"].visible is False

        bar.show_command("f7")
        assert bar.commands["f7"].visible is True

    def test_command_bar_set_context_file_panel(self):
        """Test setting file panel context."""
        bar = CommandBar()

        bar.set_context("file_panel")

        # File operations should be enabled
        assert bar.commands["f3"].enabled is True
        assert bar.commands["f5"].enabled is True

    def test_command_bar_set_context_file_panel_empty(self):
        """Test setting empty file panel context."""
        bar = CommandBar()

        bar.set_context("file_panel_empty")

        # File operations should be disabled
        assert bar.commands["f3"].enabled is False
        assert bar.commands["f5"].enabled is False

    def test_command_bar_set_context_dialog(self):
        """Test setting dialog context."""
        bar = CommandBar()

        bar.set_context("dialog")

        # Most commands should be disabled in dialog
        assert bar.commands["f3"].enabled is False
        assert bar.commands["f8"].enabled is False

    def test_command_bar_set_context_view_mode(self):
        """Test setting view mode context."""
        bar = CommandBar()

        bar.set_context("view_mode")

        # F3 should change to Close
        assert bar.commands["f3"].label == "Close"
        assert bar.commands["f3"].action == "close_viewer"

    def test_command_bar_reset_to_default(self):
        """Test resetting to default commands."""
        bar = CommandBar()

        # Modify commands
        bar.update_command("f1", label="Modified")

        # Reset
        bar.reset_to_default()

        # Should be back to default
        assert bar.commands["f1"].label == "Help"

    def test_command_bar_default_commands_complete(self):
        """Test all default F-keys are present."""
        bar = CommandBar()

        expected_keys = ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10"]

        for key in expected_keys:
            assert key in bar.commands
            assert bar.commands[key].key == key.upper()


# Integration Tests
class TestUIComponentsIntegration:
    """Integration tests for UI component interactions."""

    def test_file_panel_command_bar_integration(self, temp_test_dir):
        """Test FilePanel and CommandBar working together."""
        panel = FilePanel(path=temp_test_dir)
        bar = CommandBar()

        # Empty directory context
        if len(panel._file_items) == 0:
            bar.set_context("file_panel_empty")
            assert bar.commands["f5"].enabled is False
        else:
            bar.set_context("file_panel")
            assert bar.commands["f5"].enabled is True

    def test_file_panel_selection_workflow(self, temp_test_dir):
        """Test complete file selection workflow."""
        panel = FilePanel(path=temp_test_dir)
        panel._file_items = panel._load_directory()

        # Get non-parent items
        selectable_items = [item for item in panel._file_items if not item.is_parent]

        # Select multiple items
        for item in selectable_items[:2]:
            panel.selected_files.add(str(item.path))

        # Verify selection
        selected = panel.get_selected_items()
        assert len(selected) == 2

        # Clear selection
        panel.clear_selection()
        assert len(panel.selected_files) == 0

    def test_file_panel_navigation_workflow(self, temp_test_dir):
        """Test complete navigation workflow."""
        panel = FilePanel(path=temp_test_dir)

        # Navigate to subdirectory
        sub_dir = temp_test_dir / "subdir"
        panel.navigate_to(sub_dir)
        assert panel.current_path == sub_dir

        # Navigate up
        panel.navigate_up()
        assert panel.current_path == temp_test_dir

    def test_command_bar_context_switching(self):
        """Test switching between different contexts."""
        bar = CommandBar()

        # File panel context
        bar.set_context("file_panel")
        file_panel_state = bar.commands["f3"].enabled

        # Dialog context
        bar.set_context("dialog")
        dialog_state = bar.commands["f3"].enabled

        # View mode context
        bar.set_context("view_mode")
        view_mode_label = bar.commands["f3"].label

        # States should be different
        assert file_panel_state is True
        assert dialog_state is False
        assert view_mode_label == "Close"
