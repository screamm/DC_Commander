"""Minimal test application for QuickViewWidget.

Run this standalone to test the Quick View functionality before integration.
"""

from pathlib import Path
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DirectoryTree

from components.quick_view_widget import QuickViewWidget


class QuickViewTestApp(App):
    """Test application for Quick View widget."""

    CSS = """
    Screen {
        background: #000055;
    }

    Horizontal {
        height: 1fr;
    }

    DirectoryTree {
        width: 50%;
        border: solid cyan;
    }

    QuickViewWidget {
        width: 50%;
    }

    .test-header {
        background: cyan;
        color: black;
        text-align: center;
        height: 1;
        dock: top;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "reload", "Reload"),
    ]

    def compose(self) -> ComposeResult:
        """Compose test app widgets."""
        yield Header()
        yield Static("Quick View Test App - Select files to preview", classes="test-header")

        with Horizontal():
            yield DirectoryTree(Path.cwd(), id="tree")
            yield QuickViewWidget(id="preview")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize on mount."""
        self.title = "Quick View Test"

    def on_directory_tree_file_selected(self, event) -> None:
        """Handle file selection in tree.

        Args:
            event: File selected event
        """
        quick_view = self.query_one("#preview", QuickViewWidget)
        quick_view.set_file(event.path)

    def on_directory_tree_directory_selected(self, event) -> None:
        """Handle directory selection in tree.

        Args:
            event: Directory selected event
        """
        quick_view = self.query_one("#preview", QuickViewWidget)
        quick_view.set_file(event.path)

    def action_quit(self) -> None:
        """Quit application."""
        self.exit()

    def action_reload(self) -> None:
        """Reload current file."""
        tree = self.query_one("#tree", DirectoryTree)
        if tree.cursor_node:
            path = tree.cursor_node.data.path
            quick_view = self.query_one("#preview", QuickViewWidget)
            quick_view.set_file(None)  # Clear first
            quick_view.set_file(path)  # Reload
            self.notify("Preview reloaded")


if __name__ == "__main__":
    app = QuickViewTestApp()
    app.run()
