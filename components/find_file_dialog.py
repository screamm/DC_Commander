"""Find File dialog component for Modern Commander.

Provides comprehensive file search across directories with async streaming results.
"""

from pathlib import Path
from typing import Optional, Callable, List
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Input, Button, DataTable, Checkbox
from textual.binding import Binding
from textual.worker import Worker, WorkerState

from services.async_file_scanner import AsyncFileScanner, ScanProgress


class FindFileDialog(ModalScreen):
    """Find File dialog for searching files across directories with async support."""

    DEFAULT_CSS = """
    FindFileDialog {
        align: center middle;
    }

    FindFileDialog > Container {
        width: 80;
        height: 30;
        border: heavy $primary;
        background: $surface;
    }

    FindFileDialog .dialog-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        background: $primary;
        color: $text;
        height: 1;
    }

    FindFileDialog .dialog-content {
        width: 100%;
        height: 1fr;
        padding: 1;
    }

    FindFileDialog .search-options {
        height: auto;
        margin-bottom: 1;
    }

    FindFileDialog .progress-info {
        height: 2;
        margin-bottom: 1;
        background: $panel;
        padding: 0 1;
    }

    FindFileDialog .results-container {
        height: 1fr;
        border: solid $accent;
    }

    FindFileDialog .results-table {
        height: 1fr;
    }

    FindFileDialog .button-container {
        width: 100%;
        height: 3;
        align: center middle;
        background: $panel;
    }

    FindFileDialog Button {
        margin: 0 1;
    }

    FindFileDialog Input {
        width: 100%;
        margin-bottom: 1;
    }

    FindFileDialog Checkbox {
        margin-right: 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("enter", "go_to_file", "Go To File", priority=True),
        Binding("f5", "start_search", "Search", priority=True),
    ]

    def __init__(
        self,
        start_path: Path,
        on_file_selected: Optional[Callable[[Path], None]] = None,
        name: Optional[str] = None,
    ):
        """Initialize Find File dialog.

        Args:
            start_path: Starting directory for search
            on_file_selected: Callback when file is selected
            name: Widget name
        """
        super().__init__(name=name)
        self.start_path = start_path
        self.on_file_selected = on_file_selected
        self._scanner = AsyncFileScanner()
        self._search_results: List[Path] = []
        self._search_worker: Optional[Worker] = None
        self._is_searching = False

    def compose(self) -> ComposeResult:
        """Compose dialog widgets."""
        with Container():
            yield Static("Find File", classes="dialog-title")

            with Vertical(classes="dialog-content"):
                # Search pattern input
                yield Static("Search pattern:")
                yield Input(
                    placeholder="*.py, test_*, file.txt",
                    id="search-pattern"
                )

                # Search options
                with Horizontal(classes="search-options"):
                    yield Checkbox("Subdirectories", value=True, id="search-subdirs")
                    yield Checkbox("Case sensitive", value=False, id="search-case")

                # Progress info
                with Vertical(classes="progress-info"):
                    yield Static("Ready to search", id="progress-status")
                    yield Static("", id="progress-details")

                # Results area
                yield Static("Results:")
                with Container(classes="results-container"):
                    table = DataTable(
                        zebra_stripes=True,
                        cursor_type="row",
                        show_cursor=True,
                        classes="results-table",
                        id="results-table"
                    )
                    table.add_columns("Name", "Path", "Size")
                    yield table

            # Buttons
            with Horizontal(classes="button-container"):
                yield Button("Search [F5]", variant="primary", id="search-btn")
                yield Button("Cancel Search", variant="error", id="cancel-search-btn", disabled=True)
                yield Button("Go To File [Enter]", variant="success", id="goto-btn")
                yield Button("Close [Esc]", variant="default", id="close-btn")

    def on_mount(self) -> None:
        """Initialize dialog on mount."""
        # Focus search pattern input
        self.query_one("#search-pattern", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button pressed event
        """
        if event.button.id == "search-btn":
            self.action_start_search()
        elif event.button.id == "cancel-search-btn":
            self._cancel_search()
        elif event.button.id == "goto-btn":
            self.action_go_to_file()
        elif event.button.id == "close-btn":
            self.action_cancel()

    def action_start_search(self) -> None:
        """Start async file search with streaming results."""
        if self._is_searching:
            self.notify("Search already in progress", severity="warning")
            return

        pattern_input = self.query_one("#search-pattern", Input)
        pattern = pattern_input.value.strip()

        if not pattern:
            self.notify("Please enter a search pattern", severity="warning")
            return

        # Get search options
        subdirs_checkbox = self.query_one("#search-subdirs", Checkbox)
        case_checkbox = self.query_one("#search-case", Checkbox)

        # Clear previous results
        self._search_results.clear()
        table = self.query_one("#results-table", DataTable)
        table.clear()

        # Update UI state
        self._is_searching = True
        self._update_search_ui(searching=True)
        self._update_progress("Searching...", "Initializing search...")

        # Reset scanner
        self._scanner.reset()

        # Start async search worker
        self._search_worker = self.run_worker(
            self._async_search(
                pattern,
                recursive=subdirs_checkbox.value,
                case_sensitive=case_checkbox.value
            ),
            exclusive=False,
            name="file_search",
            description=f"Searching for {pattern}"
        )

    async def _async_search(
        self,
        pattern: str,
        recursive: bool,
        case_sensitive: bool
    ) -> None:
        """Async search worker with streaming results.

        Args:
            pattern: Search pattern
            recursive: Search subdirectories
            case_sensitive: Case-sensitive matching
        """
        try:
            # Progress callback for UI updates
            def update_progress(progress: ScanProgress):
                self.app.call_from_thread(
                    self._update_progress,
                    f"Scanned {progress.files_scanned} files, found {progress.matches_found} matches",
                    f"Current: {progress.current_directory}"
                )

            match_count = 0

            # Stream results
            async for file_path in self._scanner.search_files(
                self.start_path,
                pattern,
                case_sensitive=case_sensitive,
                recursive=recursive,
                progress_callback=update_progress
            ):
                # Add result
                self._search_results.append(file_path)
                match_count += 1

                # Update UI with new result (every 10 matches for performance)
                if match_count % 10 == 0:
                    self.app.call_from_thread(self._add_result_to_table, file_path)
                else:
                    # Queue for batch update
                    self.app.call_from_thread(self._add_result_to_table, file_path)

            # Final update
            self.app.call_from_thread(
                self._search_complete,
                match_count,
                cancelled=False
            )

        except Exception as e:
            self.app.call_from_thread(
                self.notify,
                f"Search error: {e}",
                severity="error"
            )
            self.app.call_from_thread(
                self._search_complete,
                0,
                cancelled=False
            )

    def _add_result_to_table(self, file_path: Path) -> None:
        """Add search result to table (called from worker thread).

        Args:
            file_path: File path to add
        """
        table = self.query_one("#results-table", DataTable)

        # Format file size
        try:
            size = file_path.stat().st_size
            size_str = self._format_size(size)
        except (OSError, PermissionError):
            size_str = "N/A"

        # Get relative path
        try:
            rel_path = file_path.relative_to(self.start_path)
            path_str = str(rel_path.parent) if rel_path.parent.name else "."
        except ValueError:
            path_str = str(file_path.parent)

        table.add_row(
            file_path.name,
            path_str,
            size_str,
            key=str(file_path)
        )

    def _search_complete(self, result_count: int, cancelled: bool) -> None:
        """Handle search completion (called from worker thread).

        Args:
            result_count: Number of results found
            cancelled: True if search was cancelled
        """
        self._is_searching = False
        self._update_search_ui(searching=False)

        if cancelled:
            self._update_progress("Search cancelled", f"Found {result_count} files before cancellation")
            self.notify(f"Search cancelled - {result_count} files found", severity="warning")
        else:
            self._update_progress("Search complete", f"Found {result_count} files")
            self.notify(f"Found {result_count} file(s)", severity="information")

    def _cancel_search(self) -> None:
        """Cancel ongoing search operation."""
        if not self._is_searching:
            return

        self._scanner.cancel()
        self._update_progress("Cancelling search...", "Please wait...")
        self.notify("Cancelling search...", severity="information")

    def _update_search_ui(self, searching: bool) -> None:
        """Update UI elements based on search state.

        Args:
            searching: True if search is in progress
        """
        search_btn = self.query_one("#search-btn", Button)
        cancel_btn = self.query_one("#cancel-search-btn", Button)

        search_btn.disabled = searching
        cancel_btn.disabled = not searching

    def _update_progress(self, status: str, details: str) -> None:
        """Update progress information display.

        Args:
            status: Status message
            details: Detailed progress information
        """
        status_label = self.query_one("#progress-status", Static)
        details_label = self.query_one("#progress-details", Static)

        status_label.update(status)
        details_label.update(details)

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

    def action_go_to_file(self) -> None:
        """Navigate to selected file."""
        table = self.query_one("#results-table", DataTable)

        if table.cursor_row < 0 or table.cursor_row >= len(self._search_results):
            self.notify("No file selected", severity="warning")
            return

        selected_path = self._search_results[table.cursor_row]

        if self.on_file_selected:
            self.on_file_selected(selected_path)

        self.dismiss(selected_path)

    def action_cancel(self) -> None:
        """Cancel dialog and cleanup."""
        # Cancel search if running
        if self._is_searching:
            self._scanner.cancel()

        self.dismiss(None)
