"""Theme Selection Menu for Modern Commander.

Interactive theme selection and management screen with support for:
- Built-in theme selection
- Custom theme creation
- Custom theme editing
- Custom theme deletion
"""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, ListView, ListItem, Label
from textual.screen import ModalScreen
from textual.reactive import reactive
from textual.message import Message

from features.theme_manager import ThemeManager, Theme


class ThemeSelectionMenu(ModalScreen):
    """Interactive theme selection menu with custom theme management."""

    DEFAULT_CSS = """
    ThemeSelectionMenu {
        align: center middle;
    }

    ThemeSelectionMenu > Container {
        width: 70;
        height: auto;
        max-height: 80%;
        border: heavy $primary;
        background: $surface;
        padding: 1 2;
    }

    ThemeSelectionMenu .menu-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        background: $surface-darken-1;
        padding: 0 1;
        margin-bottom: 1;
    }

    ThemeSelectionMenu .section-header {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 0;
        padding: 0 1;
    }

    ThemeSelectionMenu ListView {
        height: auto;
        max-height: 30;
        border: solid $accent;
        background: $panel;
        margin-bottom: 1;
    }

    ThemeSelectionMenu ListItem {
        padding: 0 1;
        color: $text;
    }

    ThemeSelectionMenu ListItem:hover {
        background: $surface-lighten-1;
    }

    ThemeSelectionMenu ListItem.-selected {
        background: $primary;
        color: $text;
    }

    ThemeSelectionMenu .theme-current {
        color: $success;
        text-style: bold;
    }

    ThemeSelectionMenu .theme-editable {
        color: $text-muted;
        text-style: italic;
    }

    ThemeSelectionMenu .menu-buttons {
        align: center middle;
        height: auto;
        margin-top: 1;
    }

    ThemeSelectionMenu Button {
        margin: 0 1;
        min-width: 14;
    }

    ThemeSelectionMenu .primary-button {
        background: $primary;
        color: $text;
    }

    ThemeSelectionMenu .danger-button {
        background: $error;
        color: $text;
    }

    ThemeSelectionMenu Button:disabled {
        background: $surface-darken-1;
        color: $text-muted;
        opacity: 0.5;
    }
    """

    # Custom messages
    class ThemeSelected(Message):
        """Message sent when theme is selected and applied."""

        def __init__(self, theme_id: str) -> None:
            """Initialize message.

            Args:
                theme_id: Selected theme identifier
            """
            super().__init__()
            self.theme_id = theme_id

    class CreateCustomTheme(Message):
        """Message sent when Create Custom button clicked."""
        pass

    class EditCustomTheme(Message):
        """Message sent when Edit Custom button clicked."""

        def __init__(self, theme_id: str) -> None:
            """Initialize message.

            Args:
                theme_id: Theme identifier to edit
            """
            super().__init__()
            self.theme_id = theme_id

    class DeleteCustomTheme(Message):
        """Message sent when Delete Custom button clicked."""

        def __init__(self, theme_id: str) -> None:
            """Initialize message.

            Args:
                theme_id: Theme identifier to delete
            """
            super().__init__()
            self.theme_id = theme_id

    # Reactive state
    selected_theme_id: reactive[Optional[str]] = reactive(None)

    def __init__(
        self,
        theme_manager: ThemeManager,
        current_theme_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        """Initialize theme selection menu.

        Args:
            theme_manager: Theme manager instance
            current_theme_id: Currently active theme identifier
            name: Widget name
        """
        super().__init__(name=name)
        self.theme_manager = theme_manager
        self.current_theme_id = current_theme_id or "norton_commander"
        self.selected_theme_id = None

    def compose(self) -> ComposeResult:
        """Compose theme selection menu widgets."""
        with Container():
            yield Static("Theme Selection", classes="menu-title")

            # Build theme list
            with Vertical():
                # Built-in themes section
                yield Static("Built-in Themes", classes="section-header")

                theme_list_items = []

                # Add built-in themes
                built_in_themes = self.theme_manager.get_built_in_themes()
                for theme in built_in_themes:
                    label = self._format_theme_label(theme)
                    theme_list_items.append(ListItem(Label(label), name=theme.name))

                # Custom themes section
                custom_themes = self.theme_manager.get_custom_themes()
                if custom_themes:
                    # Add separator/header
                    theme_list_items.append(
                        ListItem(Label(""), name="_separator")
                    )
                    theme_list_items.append(
                        ListItem(
                            Static("Custom Themes", classes="section-header"),
                            name="_custom_header"
                        )
                    )

                    # Add custom themes
                    for theme in custom_themes:
                        label = self._format_theme_label(theme)
                        theme_list_items.append(ListItem(Label(label), name=theme.name))

                # Create ListView
                list_view = ListView(*theme_list_items, id="theme_list")
                yield list_view

            # Buttons
            with Horizontal(classes="menu-buttons"):
                yield Button(
                    "Preview",
                    variant="default",
                    id="preview_button",
                    disabled=True
                )
                yield Button(
                    "Apply",
                    variant="primary",
                    id="apply_button",
                    classes="primary-button",
                    disabled=True
                )
                yield Button(
                    "Create Custom",
                    variant="default",
                    id="create_button"
                )
                yield Button(
                    "Edit Custom",
                    variant="default",
                    id="edit_button",
                    disabled=True
                )
                yield Button(
                    "Delete Custom",
                    variant="default",
                    id="delete_button",
                    classes="danger-button",
                    disabled=True
                )
                yield Button(
                    "Close",
                    variant="default",
                    id="close_button"
                )

    def _format_theme_label(self, theme: Theme) -> str:
        """Format theme label with indicators.

        Args:
            theme: Theme object

        Returns:
            Formatted label string
        """
        label_parts = []

        # Current theme indicator
        if theme.name == self.current_theme_id:
            label_parts.append("►")

        # Theme display name
        label_parts.append(theme.display_name)

        # Editable indicator for custom themes
        if theme.metadata and theme.metadata.is_editable:
            label_parts.append("[Editable]")

        return " ".join(label_parts)

    def on_mount(self) -> None:
        """Handle mount event."""
        # Pre-select current theme if it exists
        if self.current_theme_id:
            list_view = self.query_one("#theme_list", ListView)
            for item in list_view.children:
                if isinstance(item, ListItem) and item.name == self.current_theme_id:
                    list_view.index = list(list_view.children).index(item)
                    self.selected_theme_id = self.current_theme_id
                    break

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle theme selection in list.

        Args:
            event: ListView selected event
        """
        if event.item.name and not event.item.name.startswith("_"):
            self.selected_theme_id = event.item.name
            self._update_button_states()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle theme highlighting in list.

        Args:
            event: ListView highlighted event
        """
        if event.item and event.item.name and not event.item.name.startswith("_"):
            self.selected_theme_id = event.item.name
            self._update_button_states()

    def _update_button_states(self) -> None:
        """Update button enabled/disabled states based on selection."""
        preview_button = self.query_one("#preview_button", Button)
        apply_button = self.query_one("#apply_button", Button)
        edit_button = self.query_one("#edit_button", Button)
        delete_button = self.query_one("#delete_button", Button)

        # Preview & Apply buttons: enabled when theme selected
        has_selection = self.selected_theme_id is not None
        preview_button.disabled = not has_selection
        apply_button.disabled = not has_selection

        # Edit/Delete buttons: enabled only for custom themes
        is_custom_theme = (
            self.selected_theme_id is not None
            and self.selected_theme_id in self.theme_manager.CUSTOM_THEME_SLOTS
        )

        edit_button.disabled = not is_custom_theme
        delete_button.disabled = not is_custom_theme

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button pressed event
        """
        if event.button.id == "preview_button":
            self._preview_theme()
        elif event.button.id == "apply_button":
            self._apply_theme()
        elif event.button.id == "create_button":
            self._create_custom_theme()
        elif event.button.id == "edit_button":
            self._edit_custom_theme()
        elif event.button.id == "delete_button":
            self._delete_custom_theme()
        elif event.button.id == "close_button":
            self.dismiss()

    def on_key(self, event) -> None:
        """Handle keyboard input.

        Args:
            event: Key event
        """
        if event.key == "escape":
            self.dismiss()
        elif event.key == "enter":
            if self.selected_theme_id:
                self._apply_theme()
        elif event.key == "p":
            # Quick preview with 'p' key
            if self.selected_theme_id:
                self._preview_theme()

    def _preview_theme(self) -> None:
        """Preview selected theme temporarily."""
        if not self.selected_theme_id:
            self.app.notify("No theme selected", severity="warning")
            return

        # Get the main app (ModernCommanderApp)
        from modern_commander import ModernCommanderApp
        if isinstance(self.app, ModernCommanderApp):
            # Apply theme temporarily for preview
            self.app._apply_theme(self.selected_theme_id)

            # Get theme display name
            theme = self.theme_manager.load_theme(self.selected_theme_id)
            display_name = theme.display_name if theme else self.selected_theme_id

            self.app.notify(
                f"Preview: {display_name} (Press Apply to save)",
                severity="information",
                timeout=2
            )

    def _apply_theme(self) -> None:
        """Apply selected theme."""
        if not self.selected_theme_id:
            self.app.notify("No theme selected", severity="warning")
            return

        # Post message for parent to handle
        self.post_message(self.ThemeSelected(self.selected_theme_id))
        self.dismiss()

    def _create_custom_theme(self) -> None:
        """Create new custom theme."""
        # Check if slot available
        if not self.theme_manager.has_custom_slot_available():
            self.app.notify(
                f"Maximum {self.theme_manager.MAX_CUSTOM_THEMES} custom themes allowed",
                severity="error",
                timeout=3
            )
            return

        # Post message for parent to handle
        self.post_message(self.CreateCustomTheme())

    def _edit_custom_theme(self) -> None:
        """Edit selected custom theme."""
        if not self.selected_theme_id:
            self.app.notify("No theme selected", severity="warning")
            return

        # Verify it's a custom theme
        if self.selected_theme_id not in self.theme_manager.CUSTOM_THEME_SLOTS:
            self.app.notify("Only custom themes can be edited", severity="warning")
            return

        # Post message for parent to handle
        self.post_message(self.EditCustomTheme(self.selected_theme_id))

    def _delete_custom_theme(self) -> None:
        """Delete selected custom theme."""
        if not self.selected_theme_id:
            self.app.notify("No theme selected", severity="warning")
            return

        # Verify it's a custom theme
        if self.selected_theme_id not in self.theme_manager.CUSTOM_THEME_SLOTS:
            self.app.notify("Only custom themes can be deleted", severity="warning")
            return

        # Post message for parent to handle confirmation
        self.post_message(self.DeleteCustomTheme(self.selected_theme_id))
