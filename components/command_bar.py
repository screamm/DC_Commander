"""Command bar component for Modern Commander.

Displays F-key shortcuts with dynamic updates based on context.
"""

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static
from textual.reactive import reactive
from textual.binding import Binding


@dataclass
class Command:
    """Represents a command bar action."""
    key: str
    label: str
    action: Optional[str] = None
    enabled: bool = True
    visible: bool = True


class CommandButton(Static):
    """Individual command button in the command bar."""

    DEFAULT_CSS = """
    CommandButton {
        width: auto;
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text;
    }

    CommandButton.enabled:hover {
        background: $primary;
        color: $text;
    }

    CommandButton.disabled {
        color: $text-disabled;
    }

    CommandButton .key {
        color: $warning;
        text-style: bold;
    }

    CommandButton .separator {
        color: $accent;
    }
    """

    enabled: reactive[bool] = reactive(True)

    def __init__(
        self,
        command: Command,
        name: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        """Initialize command button.

        Args:
            command: Command configuration
            name: Widget name
            id: Widget ID
        """
        self.command = command
        super().__init__(name=name, id=id)
        self.enabled = command.enabled

    def render(self) -> str:
        """Render button content.

        Returns:
            Formatted button text
        """
        # Extract number from F-key (F1 → 1)
        key_num = self.command.key.replace("F", "")
        key = f"[bold yellow]{key_num}[/bold yellow]"
        label = self.command.label

        return f"{key}{label}"

    def watch_enabled(self, enabled: bool) -> None:
        """React to enabled state changes.

        Args:
            enabled: New enabled state
        """
        self.set_class(enabled, "enabled")
        self.set_class(not enabled, "disabled")

    def on_click(self) -> None:
        """Handle button click."""
        if self.enabled and self.command.action:
            self.app.action(self.command.action)


class CommandBar(Horizontal):
    """Command bar displaying F-key shortcuts."""

    DEFAULT_CSS = """
    CommandBar {
        height: 1;
        background: $panel;
        dock: bottom;
        padding: 0 1;
    }

    CommandBar CommandButton {
        margin: 0 1;
    }
    """

    commands: reactive[Dict[str, Command]] = reactive(dict)

    # Default command set
    DEFAULT_COMMANDS = {
        "f1": Command("F1", "Help", "show_help"),
        "f2": Command("F2", "Menu", "show_menu"),
        "f3": Command("F3", "View", "view_file"),
        "f4": Command("F4", "Edit", "edit_file"),
        "f5": Command("F5", "Copy", "copy_files"),
        "f6": Command("F6", "RenMov", "move_files"),
        "f7": Command("F7", "Mkdir", "create_directory"),
        "f8": Command("F8", "Delete", "delete_files"),
        "f9": Command("F9", "PullDn", "show_config"),
        "f10": Command("F10", "Quit", "quit"),
    }

    def __init__(
        self,
        commands: Optional[Dict[str, Command]] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize command bar.

        Args:
            commands: Custom command configuration
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self.commands = commands or self.DEFAULT_COMMANDS.copy()

    def compose(self) -> ComposeResult:
        """Compose command buttons."""
        for key in sorted(self.commands.keys()):
            command = self.commands[key]
            if command.visible:
                yield CommandButton(command, id=f"cmd_{key}")

    def watch_commands(self, commands: Dict[str, Command]) -> None:
        """React to command changes.

        Args:
            commands: New command configuration
        """
        self._update_buttons()

    def _update_buttons(self) -> None:
        """Update button states and visibility."""
        for key, command in self.commands.items():
            button_id = f"cmd_{key}"
            try:
                button = self.query_one(f"#{button_id}", CommandButton)
                button.command = command
                button.enabled = command.enabled
                button.display = command.visible
                button.refresh()
            except Exception:
                # Button not found, might need to recreate
                pass

    def update_command(
        self,
        key: str,
        label: Optional[str] = None,
        action: Optional[str] = None,
        enabled: Optional[bool] = None,
        visible: Optional[bool] = None,
    ) -> None:
        """Update a specific command.

        Args:
            key: Command key (e.g., 'f1')
            label: New label
            action: New action
            enabled: New enabled state
            visible: New visibility state
        """
        if key not in self.commands:
            return

        command = self.commands[key]

        if label is not None:
            command.label = label
        if action is not None:
            command.action = action
        if enabled is not None:
            command.enabled = enabled
        if visible is not None:
            command.visible = visible

        self._update_buttons()

    def set_context(self, context: str) -> None:
        """Set command bar context for dynamic updates.

        Args:
            context: Context identifier (e.g., 'file_panel', 'dialog')
        """
        context_commands = self._get_context_commands(context)

        for key, updates in context_commands.items():
            self.update_command(key, **updates)

    def _get_context_commands(self, context: str) -> Dict[str, Dict[str, bool]]:
        """Get command updates for specific context.

        Args:
            context: Context identifier

        Returns:
            Command update dictionary
        """
        contexts = {
            "file_panel": {
                "f3": {"enabled": True},
                "f4": {"enabled": True},
                "f5": {"enabled": True},
                "f6": {"enabled": True},
                "f8": {"enabled": True},
            },
            "file_panel_empty": {
                "f3": {"enabled": False},
                "f4": {"enabled": False},
                "f5": {"enabled": False},
                "f6": {"enabled": False},
                "f8": {"enabled": False},
            },
            "dialog": {
                "f3": {"enabled": False},
                "f4": {"enabled": False},
                "f5": {"enabled": False},
                "f6": {"enabled": False},
                "f7": {"enabled": False},
                "f8": {"enabled": False},
            },
            "view_mode": {
                "f3": {"label": "Close", "action": "close_viewer"},
                "f4": {"enabled": False},
                "f5": {"enabled": False},
                "f6": {"enabled": False},
                "f8": {"enabled": False},
            },
        }

        return contexts.get(context, {})

    def enable_command(self, key: str) -> None:
        """Enable a command.

        Args:
            key: Command key
        """
        self.update_command(key, enabled=True)

    def disable_command(self, key: str) -> None:
        """Disable a command.

        Args:
            key: Command key
        """
        self.update_command(key, enabled=False)

    def show_command(self, key: str) -> None:
        """Show a command.

        Args:
            key: Command key
        """
        self.update_command(key, visible=True)

    def hide_command(self, key: str) -> None:
        """Hide a command.

        Args:
            key: Command key
        """
        self.update_command(key, visible=False)

    def set_commands(self, commands: Dict[str, Command]) -> None:
        """Replace all commands.

        Args:
            commands: New command configuration
        """
        self.commands = commands
        self.remove_children()
        self.compose_add_child(*list(self.compose()))

    def reset_to_default(self) -> None:
        """Reset to default command configuration."""
        self.set_commands(self.DEFAULT_COMMANDS.copy())
