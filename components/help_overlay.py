"""
Keyboard Shortcut Help Overlay

Provides interactive keyboard shortcut reference with:
- Categorized shortcuts
- Searchable command palette
- Context-sensitive help
- Quick reference
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, DataTable
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.reactive import reactive
from typing import Dict, List, Tuple
import logging


logger = logging.getLogger(__name__)


# Comprehensive shortcut definitions
SHORTCUTS: Dict[str, List[Tuple[str, str, str]]] = {
    'Navigation': [
        ('↑↓', 'Navigate files', 'Move cursor up/down in file list'),
        ('Enter', 'Open directory/file', 'Enter selected directory or activate file'),
        ('Backspace', 'Parent directory', 'Navigate to parent directory'),
        ('Tab', 'Switch panels', 'Toggle focus between left and right panels'),
        ('Ctrl+F', 'Find file', 'Recursive file search with wildcards'),
        ('Ctrl+\\\\', 'Root directory', 'Jump to filesystem root'),
        ('~', 'Home directory', 'Jump to user home directory'),
    ],

    'File Operations': [
        ('F3', 'View file', 'Open file viewer with encoding detection'),
        ('F4', 'Edit file', 'Open file in built-in editor'),
        ('F5', 'Copy', 'Copy selected files to opposite panel'),
        ('F6', 'Move', 'Move selected files to opposite panel'),
        ('F7', 'Create directory', 'Create new directory'),
        ('F8', 'Delete', 'Delete selected files (with confirmation)'),
        ('Shift+F5', 'Copy (prompt)', 'Copy with destination prompt'),
        ('Shift+F6', 'Move (prompt)', 'Move with destination prompt'),
    ],

    'Selection': [
        ('Insert/Space', 'Toggle selection', 'Select/deselect current item'),
        ('Gray +', 'Select by pattern', 'Select files matching wildcard pattern'),
        ('Gray -', 'Deselect by pattern', 'Deselect files matching pattern'),
        ('Gray *', 'Invert selection', 'Invert current selection'),
        ('Ctrl+A', 'Select all', 'Select all files in panel'),
        ('Escape', 'Clear selection', 'Deselect all files'),
    ],

    'View & Display': [
        ('Ctrl+H', 'Toggle hidden files', 'Show/hide hidden files and directories'),
        ('Ctrl+Q', 'Quick View', 'Toggle file preview in opposite panel'),
        ('Ctrl+V', 'Cycle view mode', 'Switch between Full/Brief/Info views'),
        ('Ctrl+R', 'Refresh', 'Refresh current panel'),
        ('T', 'Cycle theme', 'Switch between available color themes'),
        ('Ctrl+S', 'Cycle sort', 'Change sorting column'),
        ('Ctrl+D', 'Toggle sort direction', 'Reverse sort order'),
    ],

    'Search & Filter': [
        ('Type', 'Quick search', 'Start incremental file search'),
        ('Backspace', 'Clear search', 'Remove last search character'),
        ('Escape', 'Cancel search', 'Exit quick search mode'),
        ('Ctrl+F', 'Find file', 'Open find file dialog'),
    ],

    'System': [
        ('F1', 'Help', 'Show this help screen'),
        ('F2', 'Menu', 'Open interactive dropdown menu'),
        ('F9', 'Configuration', 'Open configuration screen'),
        ('F10', 'Quit', 'Exit application'),
        ('Ctrl+Shift+D', 'Debug overlay', 'Show debug information'),
        ('Ctrl+L', 'Log viewer', 'Open log file viewer'),
    ],

    'Menu System (F2)': [
        ('Left', 'Left panel menu', 'View modes and sorting for left panel'),
        ('Right', 'Right panel menu', 'View modes and sorting for right panel'),
        ('Files', 'File operations', 'Group selection and file operations'),
        ('Commands', 'Advanced commands', 'Find file, Quick View, Compare'),
        ('Options', 'Configuration', 'Themes, settings, preferences'),
    ],

    'Advanced': [
        ('Ctrl+O', 'Command line', 'Execute shell command'),
        ('Ctrl+U', 'Swap panels', 'Exchange left and right panel paths'),
        ('Ctrl+\\\\', 'Go to root', 'Navigate to filesystem root'),
        ('Ctrl+[', 'Previous directory', 'Go to previously visited directory'),
        ('Ctrl+]', 'Next directory', 'Go to next visited directory'),
        ('Alt+F7', 'Find in files', 'Search file contents'),
        ('Ctrl+N', 'New file', 'Create new empty file'),
    ],
}


class HelpOverlay(Screen):
    """Interactive keyboard shortcut reference screen."""

    DEFAULT_CSS = """
    HelpOverlay {
        align: center middle;
        background: $background 85%;
    }

    HelpOverlay Container {
        width: 100;
        height: 40;
        border: thick $primary;
        background: $surface;
    }

    HelpOverlay .help-header {
        width: 100%;
        background: $primary;
        color: $text;
        text-align: center;
        padding: 1;
        text-style: bold;
        dock: top;
    }

    HelpOverlay .help-subtitle {
        width: 100%;
        text-align: center;
        color: $text-muted;
        padding: 0 0 1 0;
        dock: top;
    }

    HelpOverlay .search-container {
        width: 100%;
        height: auto;
        padding: 1;
        dock: top;
    }

    HelpOverlay Input {
        width: 100%;
    }

    HelpOverlay .shortcuts-container {
        width: 100%;
        height: 1fr;
        padding: 0 1;
    }

    HelpOverlay .category {
        width: 100%;
        background: $panel;
        color: $accent;
        text-style: bold;
        padding: 1;
        margin: 1 0 0 0;
    }

    HelpOverlay .shortcut-row {
        width: 100%;
        height: auto;
        padding: 0 2;
    }

    HelpOverlay .key {
        width: 20;
        color: $success;
        text-style: bold;
    }

    HelpOverlay .description {
        width: 30;
        color: $text;
    }

    HelpOverlay .details {
        width: 1fr;
        color: $text-muted;
    }

    HelpOverlay .button-container {
        width: 100%;
        height: auto;
        padding: 1;
        dock: bottom;
        align: center middle;
    }

    HelpOverlay Button {
        margin: 0 1;
    }
    """

    # Reactive properties
    search_query: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        """Compose help overlay widgets."""
        with Container():
            yield Static("⌨️ Keyboard Shortcuts", classes="help-header")
            yield Static(
                "Press ? or F1 anytime for help | Esc to close",
                classes="help-subtitle"
            )

            with Vertical(classes="search-container"):
                yield Input(
                    placeholder="Search shortcuts...",
                    id="search-input"
                )

            with ScrollableContainer(classes="shortcuts-container", id="shortcuts-scroll"):
                self._render_shortcuts()

            with Horizontal(classes="button-container"):
                yield Button("Print to PDF", id="export-button")
                yield Button("Quick Reference", id="quickref-button", variant="primary")
                yield Button("Close (Esc)", id="close-button", variant="error")

    def _render_shortcuts(self, filter_query: str = "") -> None:
        """Render shortcut list with optional filtering.

        Args:
            filter_query: Search query to filter shortcuts
        """
        container = self.query_one("#shortcuts-scroll")

        # Clear existing content
        container.remove_children()

        filter_lower = filter_query.lower()

        for category, shortcuts in SHORTCUTS.items():
            # Filter shortcuts if query provided
            if filter_query:
                filtered = [
                    (key, desc, details)
                    for key, desc, details in shortcuts
                    if filter_lower in key.lower() or
                       filter_lower in desc.lower() or
                       filter_lower in details.lower()
                ]
            else:
                filtered = shortcuts

            # Skip empty categories
            if not filtered:
                continue

            # Add category header
            container.mount(Static(category, classes="category"))

            # Add shortcuts
            for key, description, details in filtered:
                with container:
                    with Horizontal(classes="shortcut-row"):
                        container.mount(Static(key, classes="key"))
                        container.mount(Static(description, classes="description"))
                        container.mount(Static(details, classes="details"))

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes.

        Args:
            event: Input change event
        """
        self.search_query = event.value
        self._render_shortcuts(self.search_query)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button press event
        """
        button_id = event.button.id

        if button_id == "close-button":
            self.app.pop_screen()

        elif button_id == "quickref-button":
            # Show quick reference card
            self.app.push_screen(QuickReferenceCard())

        elif button_id == "export-button":
            # Export shortcuts to file
            try:
                self._export_shortcuts()
                self.notify("Shortcuts exported to dc_shortcuts.txt")
            except Exception as e:
                self.notify(f"Export failed: {e}", severity="error")

    def _export_shortcuts(self) -> None:
        """Export shortcuts to text file."""
        from pathlib import Path

        output_path = Path.home() / 'dc_shortcuts.txt'

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("DC Commander - Keyboard Shortcuts\n")
            f.write("=" * 70 + "\n\n")

            for category, shortcuts in SHORTCUTS.items():
                f.write(f"\n{category}\n")
                f.write("-" * 70 + "\n")

                for key, description, details in shortcuts:
                    f.write(f"{key:20} {description:30} {details}\n")

            f.write("\n\n" + "=" * 70 + "\n")
            f.write("Press ? or F1 anytime for help\n")

    def on_key(self, event) -> None:
        """Handle key events.

        Args:
            event: Key event
        """
        if event.key == "escape":
            # Close if search is empty, otherwise clear search
            if self.search_query:
                search_input = self.query_one("#search-input", Input)
                search_input.value = ""
            else:
                self.app.pop_screen()

        elif event.key == "question_mark":
            self.app.pop_screen()


class QuickReferenceCard(Screen):
    """Quick reference card with most common shortcuts."""

    DEFAULT_CSS = """
    QuickReferenceCard {
        align: center middle;
        background: $background 90%;
    }

    QuickReferenceCard Container {
        width: 60;
        height: 25;
        border: thick $accent;
        background: $panel;
    }

    QuickReferenceCard .qref-header {
        width: 100%;
        background: $accent;
        color: $text;
        text-align: center;
        padding: 1;
        text-style: bold;
    }

    QuickReferenceCard .qref-content {
        width: 100%;
        padding: 1 2;
    }

    QuickReferenceCard .qref-row {
        padding: 0 1;
    }
    """

    QUICK_SHORTCUTS = [
        ('F1', 'Help'),
        ('F3', 'View'),
        ('F4', 'Edit'),
        ('F5', 'Copy'),
        ('F6', 'Move'),
        ('F7', 'Mkdir'),
        ('F8', 'Delete'),
        ('F10', 'Quit'),
        ('Tab', 'Switch panels'),
        ('Insert', 'Select'),
        ('Ctrl+F', 'Find file'),
        ('Ctrl+Q', 'Quick View'),
        ('Ctrl+H', 'Hidden files'),
        ('T', 'Theme'),
    ]

    def compose(self) -> ComposeResult:
        """Compose quick reference card."""
        with Container():
            yield Static("⚡ Quick Reference", classes="qref-header")

            with ScrollableContainer(classes="qref-content"):
                for key, description in self.QUICK_SHORTCUTS:
                    with Horizontal(classes="qref-row"):
                        yield Static(f"{key:15}", classes="key")
                        yield Static(description, classes="description")

                yield Static("\nPress ? for full help", classes="qref-row")

            yield Button("Close (Esc)", id="close-qref", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press.

        Args:
            event: Button press event
        """
        self.app.pop_screen()

    def on_key(self, event) -> None:
        """Handle key events.

        Args:
            event: Key event
        """
        if event.key in ["escape", "question_mark"]:
            self.app.pop_screen()
