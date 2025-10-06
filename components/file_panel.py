"""File panel component for Modern Commander.

Displays directory contents with navigation, selection, and sorting capabilities.
"""

from pathlib import Path
from typing import Optional, List, Set
from dataclasses import dataclass
from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static
from textual.reactive import reactive
from textual.message import Message


@dataclass
class FileItem:
    """Represents a file or directory entry."""
    name: str
    path: Path
    size: int
    modified: datetime
    is_dir: bool
    is_parent: bool = False


class FilePanel(Container):
    """File panel widget displaying directory contents."""

    DEFAULT_CSS = """
    FilePanel {
        border: solid $accent;
        background: $surface;
    }

    FilePanel:focus-within {
        border: solid $primary;
    }

    FilePanel .panel-header {
        background: $primary;
        color: $text;
        text-align: center;
        height: 1;
        padding: 0 1;
    }

    FilePanel DataTable {
        height: 1fr;
    }

    FilePanel DataTable > .datatable--cursor {
        background: $primary 50%;
    }

    FilePanel DataTable > .datatable--selected {
        background: $warning 30%;
    }

    FilePanel DataTable > .datatable--header {
        background: $accent;
        color: $text;
    }
    """

    # Reactive properties
    current_path: reactive[Path] = reactive(Path.cwd)
    selected_files: reactive[Set[str]] = reactive(set)
    sort_column: reactive[str] = reactive("name")
    sort_reverse: reactive[bool] = reactive(False)

    class DirectoryChanged(Message):
        """Emitted when directory changes."""
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    class FileSelected(Message):
        """Emitted when file is selected/deselected."""
        def __init__(self, path: Path, selected: bool) -> None:
            self.path = path
            self.selected = selected
            super().__init__()

    class FileActivated(Message):
        """Emitted when file is activated (Enter key)."""
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def __init__(
        self,
        path: Optional[Path] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize file panel.

        Args:
            path: Initial directory path
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        if path:
            self.current_path = path.resolve()
        self._file_items: List[FileItem] = []

    def compose(self) -> ComposeResult:
        """Compose panel widgets."""
        yield Static(str(self.current_path), classes="panel-header")

        table = DataTable(
            zebra_stripes=True,
            cursor_type="row",
            show_cursor=True,
        )
        table.add_columns("Name", "Size", "Modified")
        yield table

    def on_mount(self) -> None:
        """Initialize panel on mount."""
        self.refresh_directory()

    def watch_current_path(self, path: Path) -> None:
        """React to path changes."""
        # Only update if mounted (compose has run)
        if self.is_mounted:
            try:
                header = self.query_one(".panel-header", Static)
                header.update(str(path))
                self.refresh_directory()
                self.post_message(self.DirectoryChanged(path))
            except Exception:
                # Widget not yet composed
                pass

    def watch_sort_column(self) -> None:
        """React to sort column changes."""
        self._sort_and_display()

    def watch_sort_reverse(self) -> None:
        """React to sort direction changes."""
        self._sort_and_display()

    def refresh_directory(self) -> None:
        """Refresh directory contents."""
        try:
            self._file_items = self._load_directory()
            self._sort_and_display()
        except PermissionError:
            self.notify("Permission denied", severity="error")
        except Exception as e:
            self.notify(f"Error loading directory: {e}", severity="error")

    def _load_directory(self) -> List[FileItem]:
        """Load directory contents.

        Returns:
            List of file items
        """
        items: List[FileItem] = []

        # Add parent directory entry
        if self.current_path.parent != self.current_path:
            items.append(FileItem(
                name="..",
                path=self.current_path.parent,
                size=0,
                modified=datetime.now(),
                is_dir=True,
                is_parent=True,
            ))

        # Add directory contents
        for entry in self.current_path.iterdir():
            try:
                stat = entry.stat()
                items.append(FileItem(
                    name=entry.name,
                    path=entry,
                    size=stat.st_size if entry.is_file() else 0,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    is_dir=entry.is_dir(),
                ))
            except (PermissionError, OSError):
                # Skip inaccessible entries
                continue

        return items

    def _sort_and_display(self) -> None:
        """Sort items and update display."""
        # Sort items
        sort_key_map = {
            "name": lambda x: (not x.is_parent, not x.is_dir, x.name.lower()),
            "size": lambda x: (not x.is_parent, not x.is_dir, x.size),
            "modified": lambda x: (not x.is_parent, not x.is_dir, x.modified),
        }

        key_func = sort_key_map.get(self.sort_column, sort_key_map["name"])
        sorted_items = sorted(
            self._file_items,
            key=key_func,
            reverse=self.sort_reverse,
        )

        # Update table
        table = self.query_one(DataTable)
        table.clear()

        for item in sorted_items:
            name_display = f"[bold cyan]{item.name}/[/bold cyan]" if item.is_dir else item.name
            size_display = self._format_size(item.size) if not item.is_dir else "<DIR>"
            modified_display = item.modified.strftime("%Y-%m-%d %H:%M")

            # Check if file is selected
            style = "bold yellow" if str(item.path) in self.selected_files else None

            table.add_row(
                name_display,
                size_display,
                modified_display,
                key=str(item.path),
            )

            if style:
                row_key = table.get_row_at(table.row_count - 1)

    def _format_size(self, size: int) -> str:
        """Format file size for display.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:3.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def get_current_item(self) -> Optional[FileItem]:
        """Get currently highlighted item.

        Returns:
            Current file item or None
        """
        table = self.query_one(DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self._file_items):
            return None

        cursor_key = table.get_row_at(table.cursor_row)
        for item in self._file_items:
            if str(item.path) == cursor_key:
                return item
        return None

    def toggle_selection(self) -> None:
        """Toggle selection of current item."""
        item = self.get_current_item()
        if not item or item.is_parent:
            return

        path_str = str(item.path)
        if path_str in self.selected_files:
            self.selected_files.remove(path_str)
            self.post_message(self.FileSelected(item.path, False))
        else:
            self.selected_files.add(path_str)
            self.post_message(self.FileSelected(item.path, True))

        self._sort_and_display()

    def clear_selection(self) -> None:
        """Clear all selections."""
        self.selected_files.clear()
        self._sort_and_display()

    def get_selected_items(self) -> List[FileItem]:
        """Get all selected items.

        Returns:
            List of selected file items
        """
        return [item for item in self._file_items if str(item.path) in self.selected_files]

    def navigate_to(self, path: Path) -> None:
        """Navigate to specified path.

        Args:
            path: Target directory path
        """
        if path.is_dir():
            self.current_path = path.resolve()
            self.clear_selection()

    def navigate_up(self) -> None:
        """Navigate to parent directory."""
        if self.current_path.parent != self.current_path:
            self.navigate_to(self.current_path.parent)

    def activate_current(self) -> None:
        """Activate current item (navigate or emit event)."""
        item = self.get_current_item()
        if not item:
            return

        if item.is_dir:
            self.navigate_to(item.path)
        else:
            self.post_message(self.FileActivated(item.path))

    def cycle_sort(self) -> None:
        """Cycle through sort columns."""
        columns = ["name", "size", "modified"]
        current_index = columns.index(self.sort_column)
        next_index = (current_index + 1) % len(columns)
        self.sort_column = columns[next_index]

    def toggle_sort_direction(self) -> None:
        """Toggle sort direction."""
        self.sort_reverse = not self.sort_reverse

    # Keyboard bindings
    BINDINGS = [
        ("enter", "activate", "Open"),
        ("backspace", "navigate_up", "Parent"),
        ("insert", "toggle_selection", "Select"),
        ("ctrl+r", "refresh", "Refresh"),
        ("ctrl+s", "cycle_sort", "Sort"),
        ("ctrl+d", "toggle_sort_direction", "Reverse"),
    ]

    def action_activate(self) -> None:
        """Handle activate action."""
        self.activate_current()

    def action_navigate_up(self) -> None:
        """Handle navigate up action."""
        self.navigate_up()

    def action_toggle_selection(self) -> None:
        """Handle toggle selection action."""
        self.toggle_selection()

        # Move cursor down after selection
        table = self.query_one(DataTable)
        if table.cursor_row < table.row_count - 1:
            table.cursor_row += 1

    def action_refresh(self) -> None:
        """Handle refresh action."""
        self.refresh_directory()
        self.notify("Directory refreshed")

    def action_cycle_sort(self) -> None:
        """Handle cycle sort action."""
        self.cycle_sort()

    def action_toggle_sort_direction(self) -> None:
        """Handle toggle sort direction action."""
        self.toggle_sort_direction()
