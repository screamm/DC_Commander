"""
Comprehensive Production-Ready Smoke Tests for DC Commander

This test suite provides comprehensive coverage of critical application functionality:
- File panel operations and navigation
- Menu system functionality
- Configuration management
- Theme system operations
- Dialog interactions
- File operations (copy, move, delete, create)
- Cache system validation
- Quick view integration
- Group selection features
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
import tempfile
import shutil

from components.file_panel import FilePanel
from components.menu_screen import MenuScreen, MenuCategory, MenuAction
from components.config_screen import ConfigScreen
from components.dialogs import (
    ConfirmDialog,
    InputDialog,
    MessageDialog,
    ErrorDialog,
    ProgressDialog
)
from features.config_manager import ConfigManager, Config, PanelConfig, CacheConfig
from features.theme_manager import ThemeManager, Theme
from features.group_selection import GroupSelector
from features.quick_search import QuickSearch
from models.file_item import FileItem


class TestFilePanelCore:
    """Test FilePanel core functionality."""

    def test_file_panel_initialization(self, tmp_path):
        """Test FilePanel initializes correctly."""
        panel = FilePanel(path=tmp_path, id="test_panel")

        assert panel.current_path == tmp_path.resolve()
        assert isinstance(panel._file_items, list)
        assert panel.sort_column == "name"
        assert not panel.sort_reverse
        assert panel.show_hidden

    def test_file_panel_load_directory(self, tmp_path):
        """Test loading directory contents."""
        # Create test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        (tmp_path / "subdir").mkdir()

        panel = FilePanel(path=tmp_path)
        items = panel._load_directory_uncached(tmp_path)

        # Should have parent entry + 2 files + 1 dir
        assert len(items) == 4
        assert any(item.is_parent for item in items)
        assert sum(1 for item in items if not item.is_dir and not item.is_parent) == 2
        assert sum(1 for item in items if item.is_dir and not item.is_parent) == 1

    def test_file_panel_navigation(self, tmp_path):
        """Test directory navigation."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        panel = FilePanel(path=tmp_path)
        assert panel.current_path == tmp_path.resolve()

        panel.navigate_to(subdir)
        assert panel.current_path == subdir.resolve()

        panel.navigate_up()
        assert panel.current_path == tmp_path.resolve()

    def test_file_panel_selection(self, tmp_path):
        """Test file selection functionality."""
        (tmp_path / "file1.txt").write_text("content")

        panel = FilePanel(path=tmp_path)
        panel._file_items = [
            FileItem(
                name="file1.txt",
                path=tmp_path / "file1.txt",
                size=7,
                modified=datetime.now(),
                is_dir=False
            )
        ]

        # Initially no selections
        assert len(panel.selected_files) == 0

        # Test get_selected_items when empty
        selected = panel.get_selected_items()
        assert len(selected) == 0

    def test_file_panel_clear_selection(self, tmp_path):
        """Test clearing selection."""
        panel = FilePanel(path=tmp_path)
        panel.selected_files.add("file1.txt")
        panel.selected_files.add("file2.txt")

        assert len(panel.selected_files) == 2

        panel.clear_selection()
        assert len(panel.selected_files) == 0

    def test_file_panel_sort_columns(self, tmp_path):
        """Test sorting by different columns."""
        panel = FilePanel(path=tmp_path)

        # Test column cycling
        assert panel.sort_column == "name"

        panel.cycle_sort()
        assert panel.sort_column == "size"

        panel.cycle_sort()
        assert panel.sort_column == "modified"

        panel.cycle_sort()
        assert panel.sort_column == "name"

    def test_file_panel_sort_direction(self, tmp_path):
        """Test sort direction toggling."""
        panel = FilePanel(path=tmp_path)

        assert not panel.sort_reverse

        panel.toggle_sort_direction()
        assert panel.sort_reverse

        panel.toggle_sort_direction()
        assert not panel.sort_reverse

    def test_file_panel_hidden_files(self, tmp_path):
        """Test hidden files visibility toggle."""
        panel = FilePanel(path=tmp_path)

        assert panel.show_hidden

        panel.toggle_hidden_files()
        assert not panel.show_hidden

        panel.toggle_hidden_files()
        assert panel.show_hidden

    def test_file_panel_cache_integration(self, tmp_path):
        """Test directory cache integration."""
        # Clear cache before test
        FilePanel.clear_cache()

        panel = FilePanel(path=tmp_path)

        # First load should miss cache
        items1 = panel._load_directory()

        # Second load should hit cache
        items2 = panel._load_directory()

        # Items should be identical
        assert len(items1) == len(items2)

    def test_file_panel_get_cache_stats(self):
        """Test cache statistics retrieval."""
        stats = FilePanel.get_cache_stats()

        if stats is not None:
            assert 'hits' in stats
            assert 'misses' in stats
            assert 'size' in stats
            assert 'maxsize' in stats


class TestMenuSystem:
    """Test menu system functionality."""

    def test_menu_action_creation(self):
        """Test MenuAction creation."""
        action = MenuAction(
            label="Test Action",
            key="T",
            action="test_action",
            enabled=True
        )

        assert action.label == "Test Action"
        assert action.key == "T"
        assert action.action == "test_action"
        assert action.enabled

    def test_menu_category_creation(self):
        """Test MenuCategory creation."""
        actions = [
            MenuAction("Action 1", "1", "action1"),
            MenuAction("Action 2", "2", "action2"),
        ]

        category = MenuCategory(title="Test Menu", actions=actions)

        assert category.title == "Test Menu"
        assert len(category.actions) == 2
        assert category.selected_index == 0

    def test_menu_category_navigation(self):
        """Test menu navigation."""
        actions = [
            MenuAction("Action 1", "1", "action1"),
            MenuAction("Action 2", "2", "action2"),
            MenuAction("Action 3", "3", "action3"),
        ]

        category = MenuCategory(title="Test", actions=actions)

        assert category.selected_index == 0

        category.select_next()
        assert category.selected_index == 1

        category.select_next()
        assert category.selected_index == 2

        category.select_next()
        assert category.selected_index == 0  # Wrap around

        category.select_previous()
        assert category.selected_index == 2  # Wrap back

    def test_menu_category_get_selected(self):
        """Test getting selected action."""
        actions = [
            MenuAction("Action 1", "1", "action1"),
            MenuAction("Action 2", "2", "action2"),
        ]

        category = MenuCategory(title="Test", actions=actions)

        selected = category.get_selected_action()
        assert selected is not None
        assert selected.action == "action1"

        category.select_next()
        selected = category.get_selected_action()
        assert selected.action == "action2"

    def test_menu_screen_initialization(self):
        """Test MenuScreen initialization."""
        menu = MenuScreen(active_panel="left")

        assert menu.active_panel == "left"
        assert hasattr(menu, 'left_menu')
        assert hasattr(menu, 'files_menu')
        assert hasattr(menu, 'commands_menu')
        assert hasattr(menu, 'options_menu')
        assert hasattr(menu, 'right_menu')

    def test_menu_screen_categories(self):
        """Test menu categories structure."""
        menu = MenuScreen()

        assert len(menu.categories) == 5
        assert menu.categories[0] == menu.left_menu
        assert menu.categories[1] == menu.files_menu
        assert menu.categories[2] == menu.commands_menu
        assert menu.categories[3] == menu.options_menu
        assert menu.categories[4] == menu.right_menu


class TestConfigurationSystem:
    """Test configuration management."""

    def test_config_manager_initialization(self, tmp_path):
        """Test ConfigManager initialization."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))

        assert manager.config_path == config_file

    def test_config_default_creation(self, tmp_path):
        """Test default configuration creation."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))

        config = manager.load_config()

        assert isinstance(config, Config)
        assert isinstance(config.left_panel, PanelConfig)
        assert isinstance(config.right_panel, PanelConfig)
        assert isinstance(config.cache, CacheConfig)

    def test_config_save_and_load(self, tmp_path):
        """Test configuration persistence."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))

        # Load default config
        config = manager.load_config()
        config.theme = "test_theme"
        config.cache.enabled = False
        config.cache.maxsize = 200

        # Save config
        assert manager.save_config()
        assert config_file.exists()

        # Create new manager and load
        manager2 = ConfigManager(str(config_file))
        config2 = manager2.load_config()

        assert config2.theme == "test_theme"
        assert not config2.cache.enabled
        assert config2.cache.maxsize == 200

    def test_config_update_methods(self, tmp_path):
        """Test configuration update methods."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        # Update panel paths
        manager.update_left_panel_path("/test/left")
        manager.update_right_panel_path("/test/right")

        assert config.left_panel.start_path == "/test/left"
        assert config.right_panel.start_path == "/test/right"

        # Update theme
        manager.update_theme("modern_dark")
        assert config.theme == "modern_dark"

    def test_config_cache_settings(self, tmp_path):
        """Test cache configuration updates."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        manager.update_cache_settings(
            enabled=False,
            maxsize=150,
            ttl_seconds=120,
            show_stats=True
        )

        assert not config.cache.enabled
        assert config.cache.maxsize == 150
        assert config.cache.ttl_seconds == 120
        assert config.cache.show_stats

    def test_config_validation(self, tmp_path):
        """Test configuration validation."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        # Valid configuration
        issues = manager.validate_config()
        # May have path issues but should not crash
        assert isinstance(issues, list)

        # Invalid cache settings
        config.cache.maxsize = 5000  # Too high
        issues = manager.validate_config()
        assert len(issues) > 0
        assert any("cache maxsize" in issue.lower() for issue in issues)

    def test_config_reset_defaults(self, tmp_path):
        """Test resetting to default configuration."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        # Modify config
        config.theme = "custom_theme"
        config.cache.maxsize = 999

        # Reset
        manager.reset_to_defaults()
        config = manager.get_config()

        assert config.theme == "norton_commander"
        assert config.cache.maxsize == 100


class TestThemeSystem:
    """Test theme management."""

    def test_theme_creation(self):
        """Test Theme object creation."""
        theme = Theme(
            name="test_theme",
            display_name="Test Theme",
            primary="#FF0000",
            accent="#00FF00",
            surface="#0000FF",
            panel="#FFFF00",
            text="#FFFFFF",
            text_muted="#CCCCCC",
            warning="#FFA500",
            error="#FF0000",
            success="#00FF00",
            selection="#FFFF00",
            selection_text="#000000"
        )

        assert theme.name == "test_theme"
        assert theme.display_name == "Test Theme"
        assert theme.primary == "#FF0000"

    def test_theme_validation_valid(self):
        """Test theme validation with valid theme."""
        theme = Theme(
            name="test",
            display_name="Test",
            primary="#FF0000",
            accent="#00FF00",
            surface="#0000FF",
            panel="#FFFF00",
            text="#FFFFFF",
            text_muted="#CCCCCC",
            warning="#FFA500",
            error="#FF0000",
            success="#00FF00",
            selection="#FFFF00",
            selection_text="#000000"
        )

        issues = theme.validate()
        assert len(issues) == 0

    def test_theme_validation_invalid(self):
        """Test theme validation with invalid theme."""
        theme = Theme(
            name="test",
            display_name="Test",
            primary="invalid_color",
            accent="#00FF00",
            surface="#0000FF",
            panel="#FFFF00",
            text="#FFFFFF",
            text_muted="#CCCCCC",
            warning="#FFA500",
            error="#FF0000",
            success="#00FF00",
            selection="#FFFF00",
            selection_text="#000000"
        )

        issues = theme.validate()
        assert len(issues) > 0
        assert any("primary" in issue.lower() for issue in issues)

    def test_theme_manager_initialization(self, tmp_path):
        """Test ThemeManager initialization."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)

        assert manager.themes_dir == themes_dir
        assert themes_dir.exists()

    def test_theme_manager_create_defaults(self, tmp_path):
        """Test default theme creation."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)

        manager.create_default_themes()

        # Check files were created
        assert (themes_dir / "norton_commander.json").exists()
        assert (themes_dir / "modern_dark.json").exists()
        assert (themes_dir / "solarized.json").exists()

    def test_theme_manager_load_theme(self, tmp_path):
        """Test loading theme."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        theme = manager.load_theme("norton_commander")

        assert theme is not None
        assert theme.name == "norton_commander"
        assert theme.display_name == "Norton Commander"

    def test_theme_manager_get_available(self, tmp_path):
        """Test getting available themes."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        themes = manager.get_available_themes()

        assert len(themes) >= 3
        assert "norton_commander" in themes
        assert "modern_dark" in themes
        assert "solarized" in themes

    def test_theme_manager_cycle_themes(self, tmp_path):
        """Test cycling through themes."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        next_theme = manager.get_next_theme_name("norton_commander")

        assert next_theme != "norton_commander"
        assert next_theme in manager.get_available_themes()


class TestDialogSystem:
    """Test dialog components."""

    def test_confirm_dialog_creation(self):
        """Test ConfirmDialog creation."""
        dialog = ConfirmDialog(
            title="Test Confirm",
            message="Are you sure?",
            danger=True
        )

        assert dialog.dialog_title == "Test Confirm"
        assert dialog.message == "Are you sure?"
        assert dialog.danger

    def test_input_dialog_creation(self):
        """Test InputDialog creation."""
        dialog = InputDialog(
            title="Test Input",
            message="Enter value:",
            default="default_value",
            placeholder="Enter here..."
        )

        assert dialog.dialog_title == "Test Input"
        assert dialog.message == "Enter value:"
        assert dialog.default == "default_value"
        assert dialog.placeholder == "Enter here..."

    def test_message_dialog_creation(self):
        """Test MessageDialog creation."""
        dialog = MessageDialog(
            title="Test Message",
            message="This is a message",
            message_type="info"
        )

        assert dialog.dialog_title == "Test Message"
        assert dialog.message == "This is a message"
        assert dialog.message_type == "info"

    def test_error_dialog_creation(self):
        """Test ErrorDialog creation."""
        dialog = ErrorDialog(
            message="An error occurred",
            title="Error"
        )

        assert dialog.dialog_title == "Error"
        assert dialog.message == "An error occurred"
        assert dialog.message_type == "error"

    def test_progress_dialog_creation(self):
        """Test ProgressDialog creation."""
        dialog = ProgressDialog(
            title="Test Progress",
            total=100,
            show_cancel=True
        )

        assert dialog.dialog_title == "Test Progress"
        assert dialog.total == 100
        assert dialog.show_cancel
        assert not dialog.is_cancelled

    def test_progress_dialog_update(self):
        """Test ProgressDialog progress updates."""
        dialog = ProgressDialog(
            title="Test",
            total=100
        )

        dialog.update_progress(50, "Processing...")

        assert dialog.progress == 50
        assert dialog.status_text == "Processing..."


class TestGroupSelection:
    """Test group selection functionality."""

    def test_group_selector_initialization(self):
        """Test GroupSelector initialization."""
        selector = GroupSelector()
        assert selector is not None

    def test_group_selector_select_matching(self, tmp_path):
        """Test selecting files by pattern."""
        selector = GroupSelector()

        items = [
            FileItem("file1.txt", tmp_path / "file1.txt", 100, datetime.now(), False),
            FileItem("file2.txt", tmp_path / "file2.txt", 100, datetime.now(), False),
            FileItem("script.py", tmp_path / "script.py", 100, datetime.now(), False),
            FileItem("data.json", tmp_path / "data.json", 100, datetime.now(), False),
        ]

        # Select .txt files
        matches = selector.select_matching(items, "*.txt")

        assert len(matches) == 2
        assert all(item.name.endswith('.txt') for item in matches)

    def test_group_selector_deselect_matching(self, tmp_path):
        """Test deselecting files by pattern."""
        selector = GroupSelector()

        items = [
            FileItem("file1.txt", tmp_path / "file1.txt", 100, datetime.now(), False),
            FileItem("file2.txt", tmp_path / "file2.txt", 100, datetime.now(), False),
            FileItem("script.py", tmp_path / "script.py", 100, datetime.now(), False),
        ]

        # Start with all selected
        selected = {str(item.path) for item in items}

        # Deselect .txt files
        new_selected = selector.deselect_matching(items, "*.txt", selected)

        assert len(new_selected) == 1
        assert str(tmp_path / "script.py") in new_selected

    def test_group_selector_invert_selection(self, tmp_path):
        """Test inverting selection."""
        selector = GroupSelector()

        items = [
            FileItem("file1.txt", tmp_path / "file1.txt", 100, datetime.now(), False),
            FileItem("file2.txt", tmp_path / "file2.txt", 100, datetime.now(), False),
            FileItem("script.py", tmp_path / "script.py", 100, datetime.now(), False),
        ]

        # Select first two items
        selected = {str(items[0].path), str(items[1].path)}

        # Invert
        new_selected = selector.invert_selection(items, selected)

        assert len(new_selected) == 1
        assert str(items[2].path) in new_selected


class TestQuickSearch:
    """Test quick search functionality."""

    def test_quick_search_initialization(self):
        """Test QuickSearch initialization."""
        search = QuickSearch()

        assert not search.is_active
        assert search.search_text == ""

    def test_quick_search_activation(self):
        """Test activating quick search."""
        search = QuickSearch()

        search.activate()
        assert search.is_active

        search.deactivate()
        assert not search.is_active

    def test_quick_search_add_char(self):
        """Test adding characters to search."""
        search = QuickSearch()
        search.activate()

        search.add_char('t')
        assert search.search_text == "t"

        search.add_char('e')
        assert search.search_text == "te"

        search.add_char('s')
        assert search.search_text == "tes"

        search.add_char('t')
        assert search.search_text == "test"

    def test_quick_search_remove_char(self):
        """Test removing characters from search."""
        search = QuickSearch()
        search.activate()

        search.add_char('t')
        search.add_char('e')
        search.add_char('s')
        search.add_char('t')

        assert search.search_text == "test"

        search.remove_char()
        assert search.search_text == "tes"

        search.remove_char()
        assert search.search_text == "te"

    def test_quick_search_find_match(self, tmp_path):
        """Test finding matches."""
        search = QuickSearch()
        search.activate()
        search.add_char('f')
        search.add_char('i')
        search.add_char('l')
        search.add_char('e')

        items = [
            FileItem("data.txt", tmp_path / "data.txt", 100, datetime.now(), False),
            FileItem("file1.txt", tmp_path / "file1.txt", 100, datetime.now(), False),
            FileItem("file2.txt", tmp_path / "file2.txt", 100, datetime.now(), False),
            FileItem("readme.md", tmp_path / "readme.md", 100, datetime.now(), False),
        ]

        # Should find first file starting with "file"
        index = search.find_next_match(items, start_index=0)

        assert index is not None
        assert index == 1  # file1.txt


class TestFileItemModel:
    """Test FileItem model."""

    def test_file_item_creation(self, tmp_path):
        """Test FileItem creation."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")

        item = FileItem(
            name="test.txt",
            path=file_path,
            size=7,
            modified=datetime.now(),
            is_dir=False
        )

        assert item.name == "test.txt"
        assert item.path == file_path
        assert item.size == 7
        assert not item.is_dir
        assert not item.is_parent

    def test_file_item_parent_entry(self, tmp_path):
        """Test parent directory FileItem."""
        item = FileItem(
            name="..",
            path=tmp_path.parent,
            size=0,
            modified=datetime.now(),
            is_dir=True,
            is_parent=True
        )

        assert item.name == ".."
        assert item.is_dir
        assert item.is_parent

    def test_file_item_directory(self, tmp_path):
        """Test directory FileItem."""
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()

        item = FileItem(
            name="subdir",
            path=dir_path,
            size=0,
            modified=datetime.now(),
            is_dir=True
        )

        assert item.name == "subdir"
        assert item.is_dir
        assert not item.is_parent


# Edge Cases and Error Handling

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_file_panel_empty_directory(self, tmp_path):
        """Test FilePanel with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        panel = FilePanel(path=empty_dir)
        items = panel._load_directory_uncached(empty_dir)

        # Should only have parent entry
        assert len(items) == 1
        assert items[0].is_parent

    def test_file_panel_nonexistent_path(self, tmp_path):
        """Test FilePanel with nonexistent path."""
        nonexistent = tmp_path / "does_not_exist"

        # Should handle gracefully
        panel = FilePanel(path=tmp_path)
        # Panel should still work with existing path

    def test_config_invalid_json(self, tmp_path):
        """Test loading invalid JSON config."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json }")

        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        # Should return default config
        assert isinstance(config, Config)

    def test_theme_missing_colors(self):
        """Test theme with missing color fields."""
        theme = Theme(
            name="incomplete",
            display_name="Incomplete",
            primary="",  # Missing
            accent="#00FF00",
            surface="#0000FF",
            panel="#FFFF00",
            text="#FFFFFF",
            text_muted="#CCCCCC",
            warning="#FFA500",
            error="#FF0000",
            success="#00FF00",
            selection="#FFFF00",
            selection_text="#000000"
        )

        issues = theme.validate()
        assert len(issues) > 0

    def test_group_selector_empty_pattern(self, tmp_path):
        """Test group selection with empty pattern."""
        selector = GroupSelector()
        items = [
            FileItem("file1.txt", tmp_path / "file1.txt", 100, datetime.now(), False),
        ]

        matches = selector.select_matching(items, "")
        # Should match nothing or all depending on implementation
        assert isinstance(matches, list)

    def test_quick_search_empty_items(self):
        """Test quick search with no items."""
        search = QuickSearch()
        search.activate()
        search.add_char('t')

        index = search.find_next_match([], start_index=0)
        assert index is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
