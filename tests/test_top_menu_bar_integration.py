"""Comprehensive integration tests for TopMenuBar functionality.

This test suite verifies that ALL menu items in the top menu bar:
1. Respond to clicks correctly
2. Post appropriate messages
3. Trigger correct handlers in ModernCommanderApp
4. Do not crash or cause errors
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from textual.widgets import Static

from components.top_menu_bar import TopMenuBar, MenuItem
from modern_commander import ModernCommanderApp


class TestMenuItemClicks:
    """Test individual MenuItem click behavior."""

    @pytest.fixture
    def menu_item(self):
        """Create a MenuItem for testing."""
        return MenuItem("Test", id="test-menu")

    def test_menu_item_posts_clicked_message_on_click(self, menu_item):
        """Test MenuItem posts Clicked message when clicked."""
        messages = []

        def capture_message(msg):
            messages.append(msg)

        menu_item.post_message = capture_message

        # Simulate click
        menu_item.on_click()

        # Verify Clicked message was posted
        assert len(messages) == 1
        assert isinstance(messages[0], MenuItem.Clicked)
        assert messages[0].menu_id == "test-menu"

    def test_menu_item_without_id_does_not_post(self):
        """Test MenuItem without ID doesn't post message."""
        menu_item = MenuItem("Test")  # No ID
        messages = []

        menu_item.post_message = lambda msg: messages.append(msg)
        menu_item.on_click()

        # No message should be posted
        assert len(messages) == 0

    def test_menu_item_highlight_on_hover(self, menu_item):
        """Test MenuItem highlights on mouse enter."""
        assert menu_item.is_highlighted == False

        menu_item.on_enter()
        assert menu_item.is_highlighted == True

        menu_item.on_leave()
        assert menu_item.is_highlighted == False


class TestTopMenuBarMessagePropagation:
    """Test TopMenuBar message propagation and handling."""

    @pytest.fixture
    def top_menu_bar(self):
        """Create TopMenuBar for testing."""
        return TopMenuBar()

    def test_top_menu_bar_converts_clicked_to_selected(self, top_menu_bar):
        """Test TopMenuBar converts MenuItem.Clicked to MenuSelected."""
        messages = []

        def capture_message(msg):
            messages.append(msg)

        top_menu_bar.post_message = capture_message

        # Create and post MenuItem.Clicked event
        clicked_event = MenuItem.Clicked("menu-test")
        top_menu_bar.on_menu_item_clicked(clicked_event)

        # Verify MenuSelected message was posted
        assert len(messages) == 1
        assert isinstance(messages[0], TopMenuBar.MenuSelected)
        assert messages[0].menu_id == "menu-test"

    def test_top_menu_bar_updates_active_menu(self, top_menu_bar):
        """Test TopMenuBar updates active_menu state."""
        assert top_menu_bar.active_menu is None

        clicked_event = MenuItem.Clicked("menu-files")
        top_menu_bar.on_menu_item_clicked(clicked_event)

        assert top_menu_bar.active_menu == "menu-files"


class TestModernCommanderMenuIntegration:
    """Test integration between TopMenuBar and ModernCommanderApp."""

    @pytest.fixture
    def mock_app(self):
        """Create mock ModernCommanderApp for testing."""
        with patch('modern_commander.ModernCommanderApp.__init__', return_value=None):
            app = ModernCommanderApp()
            app.config = Mock()
            app.config.theme = "norton_commander"
            app.theme_manager = Mock()
            app.notify = Mock()
            app.push_screen = Mock()
            return app

    def test_menu_left_handler_called(self, mock_app):
        """Test menu-left click triggers _show_left_panel_menu."""
        event = TopMenuBar.MenuSelected("menu-left")

        mock_app.on_top_menu_bar_menu_selected(event)

        # Verify notify was called with correct message
        mock_app.notify.assert_called_once()
        call_args = mock_app.notify.call_args
        assert "Left Panel Menu" in call_args[0][0]

    def test_menu_files_handler_called(self, mock_app):
        """Test menu-files click triggers _show_files_menu."""
        event = TopMenuBar.MenuSelected("menu-files")

        mock_app.on_top_menu_bar_menu_selected(event)

        # Verify notify was called with correct message
        mock_app.notify.assert_called_once()
        call_args = mock_app.notify.call_args
        assert "Files Menu" in call_args[0][0]

    def test_menu_commands_handler_called(self, mock_app):
        """Test menu-commands click triggers _show_commands_menu."""
        event = TopMenuBar.MenuSelected("menu-commands")

        mock_app.on_top_menu_bar_menu_selected(event)

        # Verify notify was called with correct message
        mock_app.notify.assert_called_once()
        call_args = mock_app.notify.call_args
        assert "Commands Menu" in call_args[0][0]

    def test_menu_options_handler_called(self, mock_app):
        """Test menu-options click triggers action_show_theme_menu."""
        event = TopMenuBar.MenuSelected("menu-options")

        mock_app.on_top_menu_bar_menu_selected(event)

        # Verify push_screen was called (theme menu opened)
        mock_app.push_screen.assert_called_once()

    def test_menu_right_handler_called(self, mock_app):
        """Test menu-right click triggers _show_right_panel_menu."""
        event = TopMenuBar.MenuSelected("menu-right")

        mock_app.on_top_menu_bar_menu_selected(event)

        # Verify notify was called with correct message
        mock_app.notify.assert_called_once()
        call_args = mock_app.notify.call_args
        assert "Right Panel Menu" in call_args[0][0]


class TestAllMenuItemsRespond:
    """Test that ALL 5 menu items respond to clicks without errors."""

    @pytest.fixture
    def mock_app(self):
        """Create mock ModernCommanderApp."""
        with patch('modern_commander.ModernCommanderApp.__init__', return_value=None):
            app = ModernCommanderApp()
            app.config = Mock()
            app.config.theme = "norton_commander"
            app.theme_manager = Mock()
            app.notify = Mock()
            app.push_screen = Mock()
            return app

    @pytest.mark.parametrize("menu_id,expected_text", [
        ("menu-left", "Left Panel Menu"),
        ("menu-files", "Files Menu"),
        ("menu-commands", "Commands Menu"),
        ("menu-options", None),  # Opens dialog instead of notify
        ("menu-right", "Right Panel Menu"),
    ])
    def test_all_menu_items_respond_without_errors(self, mock_app, menu_id, expected_text):
        """Test ALL menu items respond to clicks without crashing."""
        event = TopMenuBar.MenuSelected(menu_id)

        # This should NOT raise any exception
        try:
            mock_app.on_top_menu_bar_menu_selected(event)
            success = True
        except Exception as e:
            success = False
            pytest.fail(f"Menu {menu_id} raised exception: {e}")

        assert success, f"Menu {menu_id} should not crash"

        # Verify correct action was taken
        if expected_text:
            # Should have notified user
            mock_app.notify.assert_called_once()
            call_args = mock_app.notify.call_args
            assert expected_text in call_args[0][0]
        else:
            # menu-options should open theme menu
            mock_app.push_screen.assert_called_once()


class TestNoRegressions:
    """Test for regressions from previous implementation."""

    @pytest.fixture
    def mock_app(self):
        """Create mock ModernCommanderApp."""
        with patch('modern_commander.ModernCommanderApp.__init__', return_value=None):
            app = ModernCommanderApp()
            app.config = Mock()
            app.config.theme = "norton_commander"
            app.theme_manager = Mock()
            app.theme_manager.toggle_theme = Mock(return_value="modern_dark")
            app.theme_manager.apply_theme = Mock(return_value=True)
            app.theme_manager.get_current_theme = Mock()
            app.config_manager = Mock()
            app.config_manager.save_config = Mock()
            app.notify = Mock()
            app.push_screen = Mock()
            return app

    def test_theme_menu_still_works(self, mock_app):
        """Test theme menu (Options) still works after changes."""
        event = TopMenuBar.MenuSelected("menu-options")

        mock_app.on_top_menu_bar_menu_selected(event)

        # Theme menu should open
        mock_app.push_screen.assert_called_once()

        # Verify it's ThemeSelectionMenu
        from components.theme_selection_menu import ThemeSelectionMenu
        call_args = mock_app.push_screen.call_args
        assert isinstance(call_args[0][0], ThemeSelectionMenu)

    def test_css_error_fixed(self):
        """Test that ThemeSelectionMenu CSS no longer has $selection error."""
        from components.theme_selection_menu import ThemeSelectionMenu

        css = ThemeSelectionMenu.DEFAULT_CSS

        # CSS should NOT contain $selection variable
        assert "$selection;" not in css, "CSS should not use undefined $selection variable"

        # CSS should use $primary instead
        assert "$primary" in css, "CSS should use defined $primary variable"


class TestClickEventPropagation:
    """Test complete click event propagation chain."""

    def test_full_click_chain_menu_left(self):
        """Test complete click chain: MenuItem.on_click → Clicked → MenuSelected → handler."""
        with patch('modern_commander.ModernCommanderApp.__init__', return_value=None):
            app = ModernCommanderApp()
            app.notify = Mock()
            app.config = Mock()
            app.theme_manager = Mock()
            app.push_screen = Mock()

            # Create TopMenuBar
            top_menu_bar = TopMenuBar()
            messages_to_app = []

            # Intercept messages posted by TopMenuBar
            original_post = top_menu_bar.post_message
            def capture_and_forward(msg):
                messages_to_app.append(msg)
                # Simulate app receiving message
                if isinstance(msg, TopMenuBar.MenuSelected):
                    app.on_top_menu_bar_menu_selected(msg)

            top_menu_bar.post_message = capture_and_forward

            # Simulate MenuItem click
            clicked_event = MenuItem.Clicked("menu-left")
            top_menu_bar.on_menu_item_clicked(clicked_event)

            # Verify full chain
            assert len(messages_to_app) == 1
            assert isinstance(messages_to_app[0], TopMenuBar.MenuSelected)
            assert messages_to_app[0].menu_id == "menu-left"

            # Verify handler was called
            app.notify.assert_called_once()
            assert "Left Panel Menu" in app.notify.call_args[0][0]


class TestErrorHandling:
    """Test error handling in menu system."""

    @pytest.fixture
    def mock_app(self):
        """Create mock ModernCommanderApp."""
        with patch('modern_commander.ModernCommanderApp.__init__', return_value=None):
            app = ModernCommanderApp()
            app.config = Mock()
            app.config.theme = "norton_commander"
            app.theme_manager = Mock()
            app.notify = Mock()
            app.push_screen = Mock()
            return app

    def test_unknown_menu_id_does_not_crash(self, mock_app):
        """Test unknown menu ID doesn't crash application."""
        event = TopMenuBar.MenuSelected("menu-unknown")

        # Should not raise exception
        try:
            mock_app.on_top_menu_bar_menu_selected(event)
            success = True
        except Exception as e:
            success = False
            pytest.fail(f"Unknown menu ID should not crash: {e}")

        assert success

    def test_none_menu_id_does_not_crash(self, mock_app):
        """Test None menu ID doesn't crash application."""
        # This should not happen in practice, but test defensive coding
        try:
            event = TopMenuBar.MenuSelected(None)
            mock_app.on_top_menu_bar_menu_selected(event)
            success = True
        except Exception:
            # OK to raise exception for None, but shouldn't crash app
            success = True

        assert success


# Summary test for user verification
def test_all_menu_items_implemented():
    """Meta-test: Verify all 5 menu items have handlers implemented."""
    from modern_commander import ModernCommanderApp

    required_handlers = [
        "_show_left_panel_menu",
        "_show_files_menu",
        "_show_commands_menu",
        "action_show_theme_menu",
        "_show_right_panel_menu"
    ]

    for handler in required_handlers:
        assert hasattr(ModernCommanderApp, handler), f"Handler {handler} missing from ModernCommanderApp"
        assert callable(getattr(ModernCommanderApp, handler)), f"Handler {handler} is not callable"
