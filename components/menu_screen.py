"""Menu screen component for Modern Commander F2 functionality.

Interactive dropdown menu system with keyboard navigation for:
- Left panel operations
- File operations
- Commands
- Options
- Right panel operations
"""

from typing import Optional, Callable, List, Dict, Tuple
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Label
from textual.screen import ModalScreen
from textual.reactive import reactive
from textual.binding import Binding
from textual.message import Message


@dataclass
class MenuAction:
    """Menu action definition."""

    label: str
    key: str
    action: str
    enabled: bool = True
    separator_after: bool = False


class MenuCategory(Vertical):
    """Single menu category with items."""

    DEFAULT_CSS = """
    MenuCategory {
        width: 20;
        height: auto;
        border: solid #0000AA;
        background: #000055;
        padding: 0;
    }

    MenuCategory .menu-header {
        background: #0000AA;
        color: #FFFF00;
        text-style: bold;
        text-align: center;
        width: 100%;
        height: 1;
        padding: 0;
    }

    MenuCategory .menu-item {
        width: 100%;
        height: 1;
        padding: 0 1;
        background: #000055;
        color: #FFFF00;
    }

    MenuCategory .menu-item:hover {
        background: #00FFFF;
        color: #000055;
    }

    MenuCategory .menu-item.selected {
        background: #0000AA;
        color: #FFFF00;
    }

    MenuCategory .menu-item.disabled {
        color: #00FFFF 50%;
    }

    MenuCategory .menu-separator {
        width: 100%;
        height: 1;
        padding: 0 1;
        color: #00FFFF 50%;
    }
    """

    def __init__(
        self,
        title: str,
        actions: List[MenuAction],
        name: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        """Initialize menu category.

        Args:
            title: Category title
            actions: List of menu actions
            name: Widget name
            id: Widget ID
        """
        super().__init__(name=name, id=id)
        self.title = title
        self.actions = actions
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        """Compose menu widgets."""
        yield Static(self.title, classes="menu-header")

        for idx, action in enumerate(self.actions):
            classes = "menu-item"
            if idx == self.selected_index:
                classes += " selected"
            if not action.enabled:
                classes += " disabled"

            # Format label with key shortcut
            label_text = f"{action.key}  {action.label}"
            yield Static(label_text, id=f"item_{idx}", classes=classes)

            if action.separator_after:
                yield Static("─────────────────", classes="menu-separator")

    def select_item(self, index: int) -> None:
        """Select menu item by index.

        Args:
            index: Item index
        """
        if 0 <= index < len(self.actions):
            self.selected_index = index
            self._update_selection()

    def select_next(self) -> None:
        """Select next menu item."""
        self.selected_index = (self.selected_index + 1) % len(self.actions)
        self._update_selection()

    def select_previous(self) -> None:
        """Select previous menu item."""
        self.selected_index = (self.selected_index - 1) % len(self.actions)
        self._update_selection()

    def get_selected_action(self) -> Optional[MenuAction]:
        """Get currently selected action.

        Returns:
            Selected MenuAction or None
        """
        if 0 <= self.selected_index < len(self.actions):
            return self.actions[self.selected_index]
        return None

    def _update_selection(self) -> None:
        """Update visual selection state."""
        for idx, action in enumerate(self.actions):
            try:
                item = self.query_one(f"#item_{idx}", Static)
                if idx == self.selected_index:
                    item.add_class("selected")
                else:
                    item.remove_class("selected")
            except:
                pass


class MenuScreen(ModalScreen):
    """F2 Menu screen with dropdown menus."""

    DEFAULT_CSS = """
    MenuScreen {
        align: center top;
        background: #000055 80%;
    }

    MenuScreen > Container {
        width: auto;
        height: auto;
        margin-top: 1;
        padding: 0;
    }

    MenuScreen .menu-container {
        layout: horizontal;
        height: auto;
        width: auto;
    }

    MenuScreen .menu-hint {
        text-align: center;
        color: #00FFFF;
        margin-top: 1;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding("escape", "close_menu", "Close", priority=True),
        Binding("left", "select_left", "Left", show=False),
        Binding("right", "select_right", "Right", show=False),
        Binding("up", "select_up", "Up", show=False),
        Binding("down", "select_down", "Down", show=False),
        Binding("enter", "execute_action", "Execute", priority=True),
    ]

    selected_category: reactive[int] = reactive(1)  # Start with "Files"

    class ActionSelected(Message):
        """Action selected message."""

        def __init__(self, action: str) -> None:
            """Initialize message.

            Args:
                action: Action identifier
            """
            super().__init__()
            self.action = action

    def __init__(
        self,
        active_panel: str = "left",
        name: Optional[str] = None,
    ) -> None:
        """Initialize menu screen.

        Args:
            active_panel: Currently active panel ("left" or "right")
            name: Widget name
        """
        super().__init__(name=name)
        self.active_panel = active_panel
        self._build_menus()

    def _build_menus(self) -> None:
        """Build menu categories and actions."""
        # Left panel menu
        self.left_menu = MenuCategory(
            title="Left",
            actions=[
                MenuAction("Brief", "1", "left_brief"),
                MenuAction("Full", "2", "left_full"),
                MenuAction("Tree", "3", "left_tree"),
                MenuAction("Info", "4", "left_info", separator_after=True),
                MenuAction("Sort by Name", "N", "left_sort_name"),
                MenuAction("Sort by Ext", "E", "left_sort_ext"),
                MenuAction("Sort by Size", "S", "left_sort_size"),
                MenuAction("Sort by Date", "D", "left_sort_date", separator_after=True),
                MenuAction("Refresh", "R", "left_refresh"),
            ],
            id="left_category"
        )

        # Files menu
        self.files_menu = MenuCategory(
            title="Files",
            actions=[
                MenuAction("View", "F3", "view_file"),
                MenuAction("Edit", "F4", "edit_file", separator_after=True),
                MenuAction("Copy", "F5", "copy_files"),
                MenuAction("Move", "F6", "move_files"),
                MenuAction("Create Dir", "F7", "create_dir"),
                MenuAction("Delete", "F8", "delete_files", separator_after=True),
                MenuAction("Select Group", "+", "select_group"),
                MenuAction("Deselect Group", "-", "deselect_group"),
                MenuAction("Invert Selection", "*", "invert_selection"),
            ],
            id="files_category"
        )

        # Commands menu
        self.commands_menu = MenuCategory(
            title="Commands",
            actions=[
                MenuAction("Find File", "F", "find_file"),
                MenuAction("Quick View", "Q", "toggle_quick_view", separator_after=True),
                MenuAction("Refresh Panels", "R", "refresh_panels"),
                MenuAction("Compare Dirs", "C", "compare_dirs"),
                MenuAction("Swap Panels", "W", "swap_panels", separator_after=True),
                MenuAction("Panel History", "H", "panel_history"),
                MenuAction("Go to Dir", "G", "goto_dir"),
            ],
            id="commands_category"
        )

        # Options menu
        self.options_menu = MenuCategory(
            title="Options",
            actions=[
                MenuAction("Configuration", "F9", "show_config"),
                MenuAction("Change Theme", "T", "cycle_theme", separator_after=True),
                MenuAction("Hidden Files", "H", "toggle_hidden"),
                MenuAction("Show Sizes", "S", "toggle_sizes"),
                MenuAction("Show Dates", "D", "toggle_dates", separator_after=True),
                MenuAction("Save Setup", "V", "save_setup"),
            ],
            id="options_category"
        )

        # Right panel menu
        self.right_menu = MenuCategory(
            title="Right",
            actions=[
                MenuAction("Brief", "1", "right_brief"),
                MenuAction("Full", "2", "right_full"),
                MenuAction("Tree", "3", "right_tree"),
                MenuAction("Info", "4", "right_info", separator_after=True),
                MenuAction("Sort by Name", "N", "right_sort_name"),
                MenuAction("Sort by Ext", "E", "right_sort_ext"),
                MenuAction("Sort by Size", "S", "right_sort_size"),
                MenuAction("Sort by Date", "D", "right_sort_date", separator_after=True),
                MenuAction("Refresh", "R", "right_refresh"),
            ],
            id="right_category"
        )

        self.categories = [
            self.left_menu,
            self.files_menu,
            self.commands_menu,
            self.options_menu,
            self.right_menu,
        ]

    def compose(self) -> ComposeResult:
        """Compose menu screen widgets."""
        with Container():
            with Horizontal(classes="menu-container"):
                for category in self.categories:
                    yield category

            yield Static(
                "Use ← → to change menu, ↑ ↓ to select, Enter to execute, Esc to close",
                classes="menu-hint"
            )

    def watch_selected_category(self, index: int) -> None:
        """React to category selection changes.

        Args:
            index: New selected category index
        """
        # Update visual state for categories
        for idx, category in enumerate(self.categories):
            if idx == index:
                category.add_class("selected")
            else:
                category.remove_class("selected")

    def action_select_left(self) -> None:
        """Select previous category."""
        self.selected_category = (self.selected_category - 1) % len(self.categories)

    def action_select_right(self) -> None:
        """Select next category."""
        self.selected_category = (self.selected_category + 1) % len(self.categories)

    def action_select_up(self) -> None:
        """Select previous item in current category."""
        current_category = self.categories[self.selected_category]
        current_category.select_previous()

    def action_select_down(self) -> None:
        """Select next item in current category."""
        current_category = self.categories[self.selected_category]
        current_category.select_next()

    def action_execute_action(self) -> None:
        """Execute selected action."""
        current_category = self.categories[self.selected_category]
        action = current_category.get_selected_action()

        if action and action.enabled:
            # Post message for parent to handle
            self.post_message(self.ActionSelected(action.action))
            self.dismiss(action.action)

    def action_close_menu(self) -> None:
        """Close menu screen."""
        self.dismiss(None)

    def on_key(self, event) -> None:
        """Handle keyboard shortcuts for direct action execution.

        Args:
            event: Key event
        """
        key = event.key.lower()

        # Check current category for matching shortcut
        current_category = self.categories[self.selected_category]
        for idx, action in enumerate(current_category.actions):
            if action.key.lower() == key and action.enabled:
                current_category.select_item(idx)
                self.action_execute_action()
                event.prevent_default()
                return
