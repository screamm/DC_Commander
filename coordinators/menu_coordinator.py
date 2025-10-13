"""Menu coordination for ModernCommander.

Coordinates menu display, keyboard shortcuts, and action execution.
Provides centralized menu and action management.
"""

from typing import Callable, Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from textual.app import App


class MenuCoordinator:
    """Coordinates menu and keyboard actions.

    Responsibilities:
    - Display and manage menu screens
    - Handle keyboard shortcuts
    - Execute menu actions
    - Route actions to appropriate handlers
    """

    def __init__(self, app: "App", action_executor: Callable[[str], None]):
        """Initialize menu coordinator.

        Args:
            app: Application instance
            action_executor: Function to execute menu actions
        """
        self.app = app
        self.action_executor = action_executor
        self._menu_stack = []
        self._action_handlers = {}

    def show_menu(self, active_panel: str = "left") -> None:
        """Show F2 menu screen.

        Args:
            active_panel: Currently active panel ("left" or "right")
        """
        from components.menu_screen import MenuScreen

        menu = MenuScreen(active_panel=active_panel)

        def handle_menu_result(action: Optional[str]) -> None:
            self._menu_stack.pop() if self._menu_stack else None
            if action:
                self.execute_action(action)

        self._menu_stack.append(menu)
        self.app.push_screen(menu, callback=handle_menu_result)

    def hide_menu(self) -> None:
        """Hide current menu screen."""
        if self._menu_stack:
            menu = self._menu_stack.pop()
            try:
                menu.dismiss()
            except:
                pass

    def execute_action(self, action: str) -> None:
        """Execute menu action.

        Args:
            action: Action identifier
        """
        # Check for registered handlers first
        if action in self._action_handlers:
            handler = self._action_handlers[action]
            handler()
        else:
            # Delegate to main action executor
            self.action_executor(action)

    def register_action_handler(self, action: str, handler: Callable[[], None]) -> None:
        """Register custom action handler.

        Args:
            action: Action identifier
            handler: Handler function
        """
        self._action_handlers[action] = handler

    def unregister_action_handler(self, action: str) -> None:
        """Unregister action handler.

        Args:
            action: Action identifier
        """
        if action in self._action_handlers:
            del self._action_handlers[action]

    def handle_keyboard_shortcut(self, key: str) -> bool:
        """Handle keyboard shortcut.

        Args:
            key: Key identifier

        Returns:
            True if shortcut was handled
        """
        # Map keyboard shortcuts to actions
        shortcut_map = {
            "f1": "show_help",
            "f2": "show_menu",
            "f3": "view_file",
            "f4": "edit_file",
            "f5": "copy_files",
            "f6": "move_files",
            "f7": "create_dir",
            "f8": "delete_files",
            "f9": "show_config",
            "f10": "quit_app",
            "ctrl+f": "find_file",
            "ctrl+t": "cycle_theme",
            "ctrl+q": "toggle_quick_view",
            "ctrl+r": "refresh_panels",
            "ctrl+h": "toggle_hidden",
        }

        if key in shortcut_map:
            action = shortcut_map[key]
            self.execute_action(action)
            return True

        return False

    def get_registered_actions(self) -> list[str]:
        """Get list of registered custom actions.

        Returns:
            List of action identifiers
        """
        return list(self._action_handlers.keys())

    def clear_menu_stack(self) -> None:
        """Clear menu stack and hide all menus."""
        while self._menu_stack:
            self.hide_menu()
