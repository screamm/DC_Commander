"""Status bar component for Modern Commander.

Displays file information, selection stats, and disk space.
"""

from typing import Optional, List
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static
from textual.reactive import reactive


class StatusSegment(Static):
    """Individual segment in the status bar."""

    DEFAULT_CSS = """
    StatusSegment {
        width: auto;
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text;
    }

    StatusSegment.highlight {
        background: $primary;
        color: $text;
        text-style: bold;
    }

    StatusSegment .label {
        color: $accent;
    }

    StatusSegment .value {
        color: $text;
        text-style: bold;
    }
    """

    value: reactive[str] = reactive("")

    def __init__(
        self,
        label: str = "",
        value: str = "",
        highlight: bool = False,
        name: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        """Initialize status segment.

        Args:
            label: Segment label
            value: Segment value
            highlight: Use highlight styling
            name: Widget name
            id: Widget ID
        """
        super().__init__(name=name, id=id)
        self.segment_label = label
        self.value = value
        self.set_class(highlight, "highlight")

    def render(self) -> str:
        """Render segment content.

        Returns:
            Formatted segment text
        """
        if self.segment_label:
            return f"[cyan]{self.segment_label}:[/cyan] [bold]{self.value}[/bold]"
        return f"[bold]{self.value}[/bold]"

    def watch_value(self, value: str) -> None:
        """React to value changes.

        Args:
            value: New value
        """
        self.refresh()


class StatusBar(Horizontal):
    """Status bar displaying file information and statistics."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $panel;
        dock: bottom;
        padding: 0;
    }

    StatusBar StatusSegment {
        margin: 0 1;
    }

    StatusBar .separator {
        color: $accent;
        background: $panel;
    }
    """

    # Reactive properties
    current_file: reactive[Optional[str]] = reactive(None)
    selected_count: reactive[int] = reactive(0)
    selected_size: reactive[int] = reactive(0)
    total_count: reactive[int] = reactive(0)
    total_size: reactive[int] = reactive(0)
    free_space: reactive[int] = reactive(0)
    current_path: reactive[Optional[Path]] = reactive(None)

    def __init__(
        self,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize status bar.

        Args:
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)

    def compose(self) -> ComposeResult:
        """Compose status bar segments."""
        yield StatusSegment(label="File", value="", id="file_segment")
        yield Static("|", classes="separator")
        yield StatusSegment(label="Selected", value="0", id="selected_segment")
        yield Static("|", classes="separator")
        yield StatusSegment(label="Total", value="0", id="total_segment")
        yield Static("|", classes="separator")
        yield StatusSegment(label="Free", value="0 B", id="free_segment")

    def watch_current_file(self, filename: Optional[str]) -> None:
        """React to current file changes.

        Args:
            filename: Current filename
        """
        segment = self.query_one("#file_segment", StatusSegment)
        segment.value = filename or ""
        segment.set_class(bool(filename), "highlight")

    def watch_selected_count(self, count: int) -> None:
        """React to selected count changes.

        Args:
            count: Number of selected files
        """
        self._update_selection_info()

    def watch_selected_size(self, size: int) -> None:
        """React to selected size changes.

        Args:
            size: Total size of selected files
        """
        self._update_selection_info()

    def watch_total_count(self, count: int) -> None:
        """React to total count changes.

        Args:
            count: Total number of files
        """
        self._update_total_info()

    def watch_total_size(self, size: int) -> None:
        """React to total size changes.

        Args:
            size: Total size of all files
        """
        self._update_total_info()

    def watch_free_space(self, space: int) -> None:
        """React to free space changes.

        Args:
            space: Free disk space in bytes
        """
        segment = self.query_one("#free_segment", StatusSegment)
        segment.value = self._format_size(space)

    def watch_current_path(self, path: Optional[Path]) -> None:
        """React to current path changes.

        Args:
            path: Current directory path
        """
        if path:
            self._update_disk_space(path)

    def _update_selection_info(self) -> None:
        """Update selection information display."""
        segment = self.query_one("#selected_segment", StatusSegment)

        if self.selected_count > 0:
            value = f"{self.selected_count} ({self._format_size(self.selected_size)})"
            segment.set_class(True, "highlight")
        else:
            value = "0"
            segment.set_class(False, "highlight")

        segment.value = value

    def _update_total_info(self) -> None:
        """Update total information display."""
        segment = self.query_one("#total_segment", StatusSegment)
        value = f"{self.total_count} ({self._format_size(self.total_size)})"
        segment.value = value

    def _update_disk_space(self, path: Path) -> None:
        """Update disk space information.

        Args:
            path: Path to check disk space for
        """
        try:
            import shutil
            usage = shutil.disk_usage(path)
            self.free_space = usage.free
        except Exception:
            self.free_space = 0

    def _format_size(self, size: int) -> str:
        """Format file size for display.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        if size < 0:
            return "0 B"

        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:3.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def update_from_panel(
        self,
        current_file: Optional[str] = None,
        selected_items: Optional[List] = None,
        total_items: Optional[List] = None,
        path: Optional[Path] = None,
    ) -> None:
        """Update status bar from file panel state.

        Args:
            current_file: Currently highlighted filename
            selected_items: List of selected file items
            total_items: List of all file items
            path: Current directory path
        """
        # Update current file
        if current_file is not None:
            self.current_file = current_file

        # Update selection
        if selected_items is not None:
            self.selected_count = len(selected_items)
            self.selected_size = sum(
                item.size for item in selected_items if not item.is_dir
            )

        # Update totals
        if total_items is not None:
            self.total_count = sum(1 for item in total_items if not item.is_parent)
            self.total_size = sum(
                item.size for item in total_items if not item.is_dir
            )

        # Update path
        if path is not None:
            self.current_path = path

    def clear(self) -> None:
        """Clear all status information."""
        self.current_file = None
        self.selected_count = 0
        self.selected_size = 0
        self.total_count = 0
        self.total_size = 0

    def set_message(self, message: str, highlight: bool = False) -> None:
        """Set a temporary message in the status bar.

        Args:
            message: Message to display
            highlight: Use highlight styling
        """
        segment = self.query_one("#file_segment", StatusSegment)
        segment.value = message
        segment.set_class(highlight, "highlight")


class DetailedStatusBar(StatusBar):
    """Extended status bar with additional information."""

    DEFAULT_CSS = """
    DetailedStatusBar {
        height: 1;
    }

    DetailedStatusBar .info-segment {
        color: $accent;
    }
    """

    file_permissions: reactive[str] = reactive("")
    file_owner: reactive[str] = reactive("")
    file_modified: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        """Compose extended status bar segments."""
        # Base segments
        yield from super().compose()

        # Additional segments
        yield Static("|", classes="separator")
        yield StatusSegment(label="Perms", value="", id="perms_segment", classes="info-segment")
        yield Static("|", classes="separator")
        yield StatusSegment(label="Modified", value="", id="modified_segment", classes="info-segment")

    def watch_file_permissions(self, perms: str) -> None:
        """React to permissions changes.

        Args:
            perms: File permissions string
        """
        segment = self.query_one("#perms_segment", StatusSegment)
        segment.value = perms

    def watch_file_modified(self, modified: str) -> None:
        """React to modified date changes.

        Args:
            modified: File modification date
        """
        segment = self.query_one("#modified_segment", StatusSegment)
        segment.value = modified

    def update_file_details(
        self,
        permissions: Optional[str] = None,
        owner: Optional[str] = None,
        modified: Optional[str] = None,
    ) -> None:
        """Update detailed file information.

        Args:
            permissions: File permissions
            owner: File owner
            modified: Modification date
        """
        if permissions is not None:
            self.file_permissions = permissions

        if owner is not None:
            self.file_owner = owner

        if modified is not None:
            self.file_modified = modified
