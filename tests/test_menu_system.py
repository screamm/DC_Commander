"""
Menu System Tests for DC Commander (F2 Menu)

Comprehensive testing of the F2 menu system including:
- Menu structure and initialization
- Category navigation (Left/Right arrows)
- Item navigation (Up/Down arrows)
- Action execution (Enter key)
- Keyboard shortcuts
- Menu state management
- Disabled action handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from components.menu_screen import MenuScreen, MenuCategory, MenuAction


class TestMenuAction:
    """Test MenuAction data class."""

    def test_menu_action_creation_basic(self):
        """Test basic MenuAction creation."""
        action = MenuAction(
            label="Test Action",
            key="T",
            action="test_action"
        )

        assert action.label == "Test Action"
        assert action.key == "T"
        assert action.action == "test_action"
        assert action.enabled  # Default True
        assert not action.separator_after  # Default False

    def test_menu_action_creation_full(self):
        """Test MenuAction with all parameters."""
        action = MenuAction(
            label="Disabled Action",
            key="D",
            action="disabled_action",
            enabled=False,
            separator_after=True
        )

        assert action.label == "Disabled Action"
        assert action.key == "D"
        assert action.action == "disabled_action"
        assert not action.enabled
        assert action.separator_after

    def test_menu_action_enabled_state(self):
        """Test enabled/disabled state."""
        enabled_action = MenuAction("Enabled", "E", "enabled", enabled=True)
        disabled_action = MenuAction("Disabled", "D", "disabled", enabled=False)

        assert enabled_action.enabled
        assert not disabled_action.enabled


class TestMenuCategory:
    """Test MenuCategory widget."""

    def test_menu_category_creation(self):
        """Test MenuCategory initialization."""
        actions = [
            MenuAction("Action 1", "1", "action1"),
            MenuAction("Action 2", "2", "action2"),
            MenuAction("Action 3", "3", "action3"),
        ]

        category = MenuCategory(title="Test Menu", actions=actions)

        assert category.title == "Test Menu"
        assert len(category.actions) == 3
        assert category.selected_index == 0

    def test_menu_category_empty_actions(self):
        """Test MenuCategory with no actions."""
        category = MenuCategory(title="Empty", actions=[])

        assert category.title == "Empty"
        assert len(category.actions) == 0

    def test_menu_category_select_next(self):
        """Test selecting next item in category."""
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

        # Should wrap around
        category.select_next()
        assert category.selected_index == 0

    def test_menu_category_select_previous(self):
        """Test selecting previous item in category."""
        actions = [
            MenuAction("Action 1", "1", "action1"),
            MenuAction("Action 2", "2", "action2"),
            MenuAction("Action 3", "3", "action3"),
        ]

        category = MenuCategory(title="Test", actions=actions)

        assert category.selected_index == 0

        # Should wrap around to last
        category.select_previous()
        assert category.selected_index == 2

        category.select_previous()
        assert category.selected_index == 1

        category.select_previous()
        assert category.selected_index == 0

    def test_menu_category_select_item_by_index(self):
        """Test selecting specific item by index."""
        actions = [
            MenuAction("Action 1", "1", "action1"),
            MenuAction("Action 2", "2", "action2"),
            MenuAction("Action 3", "3", "action3"),
        ]

        category = MenuCategory(title="Test", actions=actions)

        category.select_item(1)
        assert category.selected_index == 1

        category.select_item(2)
        assert category.selected_index == 2

        category.select_item(0)
        assert category.selected_index == 0

    def test_menu_category_select_item_out_of_bounds(self):
        """Test selecting item with invalid index."""
        actions = [
            MenuAction("Action 1", "1", "action1"),
            MenuAction("Action 2", "2", "action2"),
        ]

        category = MenuCategory(title="Test", actions=actions)

        # Out of bounds should not crash
        category.select_item(10)
        # Selection should remain unchanged or be clamped

        category.select_item(-1)
        # Should handle gracefully

    def test_menu_category_get_selected_action(self):
        """Test getting currently selected action."""
        actions = [
            MenuAction("Action 1", "1", "action1"),
            MenuAction("Action 2", "2", "action2"),
            MenuAction("Action 3", "3", "action3"),
        ]

        category = MenuCategory(title="Test", actions=actions)

        # Initially first action
        selected = category.get_selected_action()
        assert selected is not None
        assert selected.action == "action1"

        # Move to second
        category.select_next()
        selected = category.get_selected_action()
        assert selected.action == "action2"

        # Move to third
        category.select_next()
        selected = category.get_selected_action()
        assert selected.action == "action3"

    def test_menu_category_with_disabled_actions(self):
        """Test category with disabled actions."""
        actions = [
            MenuAction("Enabled 1", "1", "enabled1", enabled=True),
            MenuAction("Disabled", "2", "disabled", enabled=False),
            MenuAction("Enabled 2", "3", "enabled2", enabled=True),
        ]

        category = MenuCategory(title="Test", actions=actions)

        # Should be able to navigate to disabled actions
        # (execution filtering happens elsewhere)
        category.select_item(1)
        selected = category.get_selected_action()
        assert selected.action == "disabled"
        assert not selected.enabled


class TestMenuScreen:
    """Test MenuScreen main component."""

    def test_menu_screen_initialization(self):
        """Test MenuScreen basic initialization."""
        menu = MenuScreen(active_panel="left")

        assert menu.active_panel == "left"
        assert hasattr(menu, 'categories')
        assert len(menu.categories) == 5

    def test_menu_screen_categories_structure(self):
        """Test menu categories are properly structured."""
        menu = MenuScreen()

        assert menu.categories[0] == menu.left_menu
        assert menu.categories[1] == menu.files_menu
        assert menu.categories[2] == menu.commands_menu
        assert menu.categories[3] == menu.options_menu
        assert menu.categories[4] == menu.right_menu

    def test_menu_screen_left_menu_structure(self):
        """Test left panel menu structure."""
        menu = MenuScreen()
        left_menu = menu.left_menu

        assert left_menu.title == "Left"
        assert len(left_menu.actions) > 0

        # Check for expected actions
        action_ids = [a.action for a in left_menu.actions]
        assert "left_brief" in action_ids
        assert "left_full" in action_ids
        assert "left_sort_name" in action_ids
        assert "left_refresh" in action_ids

    def test_menu_screen_files_menu_structure(self):
        """Test files menu structure."""
        menu = MenuScreen()
        files_menu = menu.files_menu

        assert files_menu.title == "Files"

        action_ids = [a.action for a in files_menu.actions]
        assert "view_file" in action_ids
        assert "edit_file" in action_ids
        assert "copy_files" in action_ids
        assert "move_files" in action_ids
        assert "create_dir" in action_ids
        assert "delete_files" in action_ids

    def test_menu_screen_commands_menu_structure(self):
        """Test commands menu structure."""
        menu = MenuScreen()
        commands_menu = menu.commands_menu

        assert commands_menu.title == "Commands"

        action_ids = [a.action for a in commands_menu.actions]
        assert "find_file" in action_ids
        assert "toggle_quick_view" in action_ids
        assert "refresh_panels" in action_ids

    def test_menu_screen_options_menu_structure(self):
        """Test options menu structure."""
        menu = MenuScreen()
        options_menu = menu.options_menu

        assert options_menu.title == "Options"

        action_ids = [a.action for a in options_menu.actions]
        assert "show_config" in action_ids
        assert "cycle_theme" in action_ids
        assert "toggle_hidden" in action_ids

    def test_menu_screen_right_menu_structure(self):
        """Test right panel menu structure."""
        menu = MenuScreen()
        right_menu = menu.right_menu

        assert right_menu.title == "Right"

        action_ids = [a.action for a in right_menu.actions]
        assert "right_brief" in action_ids
        assert "right_full" in action_ids
        assert "right_sort_name" in action_ids
        assert "right_refresh" in action_ids

    def test_menu_screen_initial_selection(self):
        """Test initial category selection."""
        menu = MenuScreen()

        # Should start with Files menu (index 1)
        assert menu.selected_category == 1

    def test_menu_screen_select_left_category(self):
        """Test selecting left category."""
        menu = MenuScreen()
        menu.selected_category = 2  # Commands

        menu.action_select_left()

        assert menu.selected_category == 1  # Files

    def test_menu_screen_select_right_category(self):
        """Test selecting right category."""
        menu = MenuScreen()
        menu.selected_category = 1  # Files

        menu.action_select_right()

        assert menu.selected_category == 2  # Commands

    def test_menu_screen_category_wrap_around_right(self):
        """Test category selection wraps around right."""
        menu = MenuScreen()
        menu.selected_category = 4  # Last category

        menu.action_select_right()

        assert menu.selected_category == 0  # Wraps to first

    def test_menu_screen_category_wrap_around_left(self):
        """Test category selection wraps around left."""
        menu = MenuScreen()
        menu.selected_category = 0  # First category

        menu.action_select_left()

        assert menu.selected_category == 4  # Wraps to last

    def test_menu_screen_select_up_item(self):
        """Test selecting previous item in category."""
        menu = MenuScreen()
        current_category = menu.categories[menu.selected_category]

        initial_index = current_category.selected_index

        menu.action_select_up()

        # Should have moved up (or wrapped)
        assert current_category.selected_index != initial_index or len(current_category.actions) == 1

    def test_menu_screen_select_down_item(self):
        """Test selecting next item in category."""
        menu = MenuScreen()
        current_category = menu.categories[menu.selected_category]

        initial_index = current_category.selected_index

        menu.action_select_down()

        # Should have moved down (or wrapped)
        new_index = current_category.selected_index
        expected_index = (initial_index + 1) % len(current_category.actions)
        assert new_index == expected_index

    def test_menu_screen_execute_action(self):
        """Test executing selected action."""
        menu = MenuScreen()

        # Select Files menu, first item (View)
        menu.selected_category = 1
        menu.files_menu.select_item(0)

        # Get the action that would be executed
        current_category = menu.categories[menu.selected_category]
        action = current_category.get_selected_action()

        assert action is not None
        assert action.action == "view_file"

    def test_menu_screen_execute_disabled_action(self):
        """Test that disabled actions can be identified."""
        menu = MenuScreen()

        # Find a disabled action in commands menu
        commands_menu = menu.commands_menu

        disabled_actions = [a for a in commands_menu.actions if not a.enabled]

        if disabled_actions:
            # Select a disabled action
            disabled_index = commands_menu.actions.index(disabled_actions[0])
            commands_menu.select_item(disabled_index)

            action = commands_menu.get_selected_action()
            assert not action.enabled


class TestMenuNavigation:
    """Test menu navigation workflows."""

    def test_full_navigation_cycle(self):
        """Test complete navigation cycle through menu."""
        menu = MenuScreen()

        # Start at Files
        assert menu.selected_category == 1

        # Navigate through all categories
        menu.action_select_right()  # Commands
        assert menu.selected_category == 2

        menu.action_select_right()  # Options
        assert menu.selected_category == 3

        menu.action_select_right()  # Right
        assert menu.selected_category == 4

        menu.action_select_right()  # Wraps to Left
        assert menu.selected_category == 0

        menu.action_select_right()  # Back to Files
        assert menu.selected_category == 1

    def test_navigation_within_category(self):
        """Test navigating all items in a category."""
        menu = MenuScreen()
        files_menu = menu.files_menu

        num_actions = len(files_menu.actions)

        # Navigate through all items
        for i in range(num_actions):
            files_menu.select_item(i)
            assert files_menu.selected_index == i

            action = files_menu.get_selected_action()
            assert action is not None

    def test_jump_to_specific_action(self):
        """Test jumping directly to specific actions."""
        menu = MenuScreen()

        # Jump to Commands menu
        menu.selected_category = 2
        commands_menu = menu.commands_menu

        # Find "Find File" action
        find_file_index = next(
            i for i, a in enumerate(commands_menu.actions)
            if a.action == "find_file"
        )

        commands_menu.select_item(find_file_index)
        action = commands_menu.get_selected_action()

        assert action.action == "find_file"


class TestMenuActionShortcuts:
    """Test keyboard shortcuts for menu actions."""

    def test_f_key_shortcuts(self):
        """Test F-key shortcuts in files menu."""
        menu = MenuScreen()
        files_menu = menu.files_menu

        # Find F3 (View)
        f3_action = next(a for a in files_menu.actions if a.key == "F3")
        assert f3_action.action == "view_file"

        # Find F4 (Edit)
        f4_action = next(a for a in files_menu.actions if a.key == "F4")
        assert f4_action.action == "edit_file"

        # Find F5 (Copy)
        f5_action = next(a for a in files_menu.actions if a.key == "F5")
        assert f5_action.action == "copy_files"

        # Find F6 (Move)
        f6_action = next(a for a in files_menu.actions if a.key == "F6")
        assert f6_action.action == "move_files"

        # Find F7 (Create Dir)
        f7_action = next(a for a in files_menu.actions if a.key == "F7")
        assert f7_action.action == "create_dir"

        # Find F8 (Delete)
        f8_action = next(a for a in files_menu.actions if a.key == "F8")
        assert f8_action.action == "delete_files"

    def test_letter_shortcuts(self):
        """Test letter key shortcuts."""
        menu = MenuScreen()
        left_menu = menu.left_menu

        # Find sort shortcuts
        sort_actions = [a for a in left_menu.actions if "sort" in a.action.lower()]

        assert len(sort_actions) > 0

        # Check sort by name has 'N' shortcut
        sort_name = next(a for a in left_menu.actions if a.action == "left_sort_name")
        assert sort_name.key == "N"

    def test_symbol_shortcuts(self):
        """Test symbol key shortcuts for selection."""
        menu = MenuScreen()
        files_menu = menu.files_menu

        # Find selection actions
        select_group = next(a for a in files_menu.actions if a.action == "select_group")
        assert select_group.key == "+"

        deselect_group = next(a for a in files_menu.actions if a.action == "deselect_group")
        assert deselect_group.key == "-"

        invert = next(a for a in files_menu.actions if a.action == "invert_selection")
        assert invert.key == "*"


class TestMenuStateManagement:
    """Test menu state management."""

    def test_menu_remembers_category_selection(self):
        """Test category selection is maintained."""
        menu = MenuScreen()

        menu.selected_category = 3

        assert menu.selected_category == 3

    def test_menu_category_remembers_item_selection(self):
        """Test item selection within category is maintained."""
        menu = MenuScreen()
        files_menu = menu.files_menu

        files_menu.select_item(2)

        assert files_menu.selected_index == 2

    def test_switching_categories_preserves_selections(self):
        """Test selections are preserved when switching categories."""
        menu = MenuScreen()

        # Set selection in Files menu
        menu.selected_category = 1
        menu.files_menu.select_item(2)

        # Switch to Commands menu
        menu.selected_category = 2
        menu.commands_menu.select_item(1)

        # Switch back to Files menu
        menu.selected_category = 1

        # Selection should be preserved
        assert menu.files_menu.selected_index == 2


class TestMenuEdgeCases:
    """Test menu edge cases and error conditions."""

    def test_empty_category(self):
        """Test handling of empty category."""
        actions = []
        category = MenuCategory(title="Empty", actions=actions)

        # Should not crash
        selected = category.get_selected_action()
        assert selected is None

    def test_single_item_category(self):
        """Test category with single item."""
        actions = [MenuAction("Only Action", "O", "only")]
        category = MenuCategory(title="Single", actions=actions)

        # Navigation should work but stay on same item
        category.select_next()
        assert category.selected_index == 0

        category.select_previous()
        assert category.selected_index == 0

    def test_all_disabled_actions(self):
        """Test category with all disabled actions."""
        actions = [
            MenuAction("Disabled 1", "1", "dis1", enabled=False),
            MenuAction("Disabled 2", "2", "dis2", enabled=False),
        ]
        category = MenuCategory(title="All Disabled", actions=actions)

        # Should be able to navigate
        category.select_next()

        # But actions should be disabled
        action = category.get_selected_action()
        assert not action.enabled

    def test_menu_with_separators(self):
        """Test menu items with separators."""
        actions = [
            MenuAction("Action 1", "1", "action1", separator_after=True),
            MenuAction("Action 2", "2", "action2"),
            MenuAction("Action 3", "3", "action3", separator_after=True),
        ]
        category = MenuCategory(title="With Separators", actions=actions)

        # Separators shouldn't affect navigation
        category.select_next()
        assert category.selected_index == 1


class TestMenuIntegration:
    """Test menu integration with main application."""

    def test_menu_action_mapping_to_app_actions(self):
        """Test menu actions map correctly to application methods."""
        menu = MenuScreen()

        # Files menu actions
        files_actions = {
            "view_file": "action_view_file",
            "edit_file": "action_edit_file",
            "copy_files": "action_copy_files",
            "move_files": "action_move_files",
            "create_dir": "action_create_directory",
            "delete_files": "action_delete_files",
        }

        for menu_action, app_method in files_actions.items():
            # Verify action exists in menu
            action = next(
                (a for a in menu.files_menu.actions if a.action == menu_action),
                None
            )
            assert action is not None

    def test_panel_specific_actions(self):
        """Test left/right panel specific actions."""
        menu = MenuScreen()

        # Left panel actions should have "left_" prefix
        left_actions = [a.action for a in menu.left_menu.actions]
        assert all(action.startswith("left_") for action in left_actions)

        # Right panel actions should have "right_" prefix
        right_actions = [a.action for a in menu.right_menu.actions]
        assert all(action.startswith("right_") for action in right_actions)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
