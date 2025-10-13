"""Top menu bar component for Modern Commander.

Norton Commander style menu: Left Files Commands Options Right
"""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static
from textual.reactive import reactive
from textual.message import Message


class MenuItem(Static):
    """Individual menu item in the top bar."""

    DEFAULT_CSS = """
    MenuItem {
        width: auto;
        height: 1;
        padding: 0 2;
        background: #00FFFF;
        color: #000055;
        text-style: bold;
    }

    MenuItem:hover {
        background: #0000AA;
        color: #FFFF00;
    }

    MenuItem.active {
        background: #0000AA;
        color: #FFFF00;
    }

    MenuItem.highlighted {
        background: #0000AA;
        color: #FFFF00;
    }
    """

    is_highlighted: reactive[bool] = reactive(False)

    class Clicked(Message):
        """Message posted when menu item is clicked."""

        def __init__(self, menu_id: str) -> None:
            """Initialize clicked message.

            Args:
                menu_id: ID of the clicked menu item
            """
            super().__init__()
            self.menu_id = menu_id

    def __init__(self, label: str, name: Optional[str] = None, id: Optional[str] = None):
        """Initialize menu item.

        Args:
            label: Display text for menu item
            name: Optional name for the widget
            id: Optional ID for the widget
        """
        super().__init__(label, name=name, id=id)
        self.label = label

    def watch_is_highlighted(self, highlighted: bool) -> None:
        """React to highlight state changes.

        Args:
            highlighted: Whether the item is highlighted
        """
        if highlighted:
            self.add_class("highlighted")
        else:
            self.remove_class("highlighted")

    def on_enter(self) -> None:
        """Handle mouse enter event."""
        self.is_highlighted = True

    def on_leave(self) -> None:
        """Handle mouse leave event."""
        self.is_highlighted = False

    def on_click(self) -> None:
        """Handle click event by posting Clicked message."""
        if self.id:
            self.post_message(self.Clicked(self.id))


class TopMenuBar(Horizontal):
    """Norton Commander style top menu bar."""

    DEFAULT_CSS = """
    TopMenuBar {
        height: 1;
        background: #00FFFF;
        dock: top;
        padding: 0;
    }
    """

    active_menu: reactive[Optional[str]] = reactive(None)

    class MenuSelected(Message):
        """Message posted when a menu is selected."""

        def __init__(self, menu_id: str) -> None:
            """Initialize menu selected message.

            Args:
                menu_id: ID of the selected menu
            """
            super().__init__()
            self.menu_id = menu_id

    def compose(self) -> ComposeResult:
        """Compose menu items."""
        yield MenuItem("Left", id="menu-left")
        yield MenuItem("Files", id="menu-files")
        yield MenuItem("Commands", id="menu-commands")
        yield MenuItem("Options", id="menu-options")
        yield MenuItem("Right", id="menu-right")

    def watch_active_menu(self, menu_id: Optional[str]) -> None:
        """React to active menu changes.

        Args:
            menu_id: ID of the active menu or None
        """
        # Update styling for all menu items
        for item in self.query(MenuItem):
            if item.id == menu_id:
                item.add_class("active")
            else:
                item.remove_class("active")

    def on_menu_item_clicked(self, event: MenuItem.Clicked) -> None:
        """Handle menu item clicked event.

        Args:
            event: MenuItem.Clicked event containing menu_id
        """
        # Update active menu for visual feedback
        self.active_menu = event.menu_id

        # Re-emit as MenuSelected for app-level handling
        self.post_message(self.MenuSelected(event.menu_id))

        # Stop event propagation
        event.stop()
