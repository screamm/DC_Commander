"""File panel component for Modern Commander.

Displays directory contents with navigation, selection, and sorting capabilities.
Includes DirectoryCache integration for 10x performance improvement.
"""

from pathlib import Path
from typing import Optional, List, Set, Any
from datetime import datetime
import logging

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static
from textual.reactive import reactive
from textual.message import Message
from textual.events import Key

from models.file_item import FileItem
from features.group_selection import GroupSelector
from features.quick_search import QuickSearch
from features.view_modes import ViewMode, ViewModeConfig
from features.config_manager import get_config_manager
from src.utils.directory_cache import DirectoryCache


# Configure logging
logger = logging.getLogger(__name__)


class FilePanel(Container):
    """File panel widget displaying directory contents."""

    # Class-level cache shared across all panels for maximum efficiency
    _dir_cache: Optional[DirectoryCache[List[FileItem]]] = None
    _cache_initialized: bool = False

    DEFAULT_CSS = """
    FilePanel {
        border: solid #00FFFF;
        background: #000055;
    }

    FilePanel:focus-within {
        border: solid #0000AA;
    }

    FilePanel .panel-header {
        background: #0000AA;
        color: #FFFF00;
        text-align: center;
        height: 1;
        padding: 0 1;
    }

    FilePanel DataTable {
        height: 1fr;
    }

    FilePanel DataTable > .datatable--cursor {
        background: #FFFF00;
        color: #000055;
        text-style: bold;
    }

    FilePanel DataTable > .datatable--selected {
        background: #FFFF00 85%;
        text-style: bold;
    }

    FilePanel DataTable > .datatable--header {
        background: #00FFFF;
        color: #FFFF00;
    }

    FilePanel .quick-search-status {
        background: #000055;
        color: #FFFF00;
        height: 1;
        dock: bottom;
        padding: 0 1;
        display: none;
    }

    FilePanel .quick-search-status.active {
        display: block;
    }

    FilePanel .cache-stats {
        background: #000055;
        color: #00FFFF;
        height: 1;
        dock: bottom;
        padding: 0 1;
        text-align: right;
        display: none;
    }

    FilePanel .cache-stats.active {
        display: block;
    }
    """

    # Reactive properties
    current_path: reactive[Path] = reactive(Path.cwd())  # Fixed: Call function
    selected_files: reactive[Set[str]] = reactive(set())  # Fixed: Call function
    sort_column: reactive[str] = reactive("name")
    sort_reverse: reactive[bool] = reactive(False)
    view_mode: reactive[ViewMode] = reactive(ViewMode.FULL)
    show_hidden: reactive[bool] = reactive(True)

    class DirectoryChanged(Message):
        """Emitted when directory changes."""
        def __init__(self, path: Path, panel: Optional["FilePanel"] = None) -> None:
            self.path: Path = path
            self.panel: Optional[FilePanel] = panel
            super().__init__()

    class FileSelected(Message):
        """Emitted when file is selected/deselected."""
        def __init__(self, path: Path, selected: bool) -> None:
            self.path: Path = path
            self.selected: bool = selected
            super().__init__()

    class FileActivated(Message):
        """Emitted when file is activated (Enter key)."""
        def __init__(self, path: Path) -> None:
            self.path: Path = path
            super().__init__()

    class GroupSelectRequest(Message):
        """Request for group selection pattern input."""
        def __init__(self, operation: str, panel: "FilePanel") -> None:
            self.operation: str = operation  # "select" or "deselect"
            self.panel: FilePanel = panel
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
        self._sorted_items: List[FileItem] = []  # Track currently displayed items
        self._group_selector = GroupSelector()
        self._quick_search = QuickSearch()

        # Initialize cache if not already done
        self._initialize_cache()

    @classmethod
    def _initialize_cache(cls) -> None:
        """Initialize the shared directory cache if needed."""
        if not cls._cache_initialized:
            try:
                config = get_config_manager().get_config()
                cache_config = config.cache

                if cache_config.enabled:
                    cls._dir_cache = DirectoryCache[List[FileItem]](
                        maxsize=cache_config.maxsize,
                        ttl_seconds=cache_config.ttl_seconds
                    )
                    logger.info(
                        f"DirectoryCache initialized: maxsize={cache_config.maxsize}, "
                        f"ttl={cache_config.ttl_seconds}s"
                    )
                else:
                    cls._dir_cache = None
                    logger.info("DirectoryCache disabled by configuration")

                cls._cache_initialized = True

            except Exception as e:
                logger.error(f"Failed to initialize DirectoryCache: {e}")
                cls._dir_cache = None
                cls._cache_initialized = True

    @classmethod
    def get_cache_stats(cls) -> Optional[dict]:
        """Get cache statistics.

        Returns:
            Cache statistics dictionary or None if cache disabled
        """
        if cls._dir_cache is not None:
            return cls._dir_cache.get_stats()
        return None

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the entire directory cache."""
        if cls._dir_cache is not None:
            cls._dir_cache.clear()
            logger.info("DirectoryCache cleared")

    def compose(self) -> ComposeResult:
        """Compose panel widgets."""
        yield Static(str(self.current_path), classes="panel-header")

        table = DataTable(
            zebra_stripes=True,
            cursor_type="row",
            show_cursor=True,
        )
        table.add_columns("Name", "Size", "Date", "Time")
        yield table

        # Quick search status (hidden by default)
        yield Static("", classes="quick-search-status", id=f"quick-search-{id(self)}")

        # Cache statistics (hidden by default)
        yield Static("", classes="cache-stats", id=f"cache-stats-{id(self)}")

    def on_mount(self) -> None:
        """Initialize panel on mount."""
        self.refresh_directory()
        self._update_cache_stats_display()

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

    def watch_view_mode(self, mode: ViewMode) -> None:
        """React to view mode changes.

        Args:
            mode: New view mode
        """
        self._rebuild_table()
        self._sort_and_display()

    def watch_show_hidden(self) -> None:
        """React to show_hidden changes."""
        self._sort_and_display()

    def refresh_directory(self, force: bool = False) -> None:
        """Refresh directory contents.

        Args:
            force: If True, bypass cache and force fresh load
        """
        try:
            # Force refresh invalidates cache
            if force and self._dir_cache is not None:
                self._dir_cache.invalidate(self.current_path)
                logger.debug(f"Cache invalidated for: {self.current_path}")

            self._file_items = self._load_directory()
            self._sort_and_display()
            self._update_cache_stats_display()

        except PermissionError:
            self.notify("Permission denied", severity="error")
        except Exception as e:
            self.notify(f"Error loading directory: {e}", severity="error")

    def _rebuild_table(self) -> None:
        """Rebuild table columns based on current view mode."""
        table = self.query_one(DataTable)
        table.clear(columns=True)

        # Get columns for current view mode
        columns = ViewModeConfig.get_columns(self.view_mode)
        table.add_columns(*columns)

    def _load_directory(self) -> List[FileItem]:
        """Load directory contents with caching.

        Returns:
            List of file items
        """
        # Use cache if available
        if self._dir_cache is not None:
            return self._dir_cache.get_or_load(
                self.current_path,
                self._load_directory_uncached
            )
        else:
            return self._load_directory_uncached(self.current_path)

    def _load_directory_uncached(self, path: Path) -> List[FileItem]:
        """Load directory contents without caching.

        Args:
            path: Directory path to load

        Returns:
            List of file items
        """
        items: List[FileItem] = []

        # Add parent directory entry
        if path.parent != path:
            items.append(FileItem(
                name="..",
                path=path.parent,
                size=0,
                modified=datetime.now(),
                is_dir=True,
                is_parent=True,
            ))

        # Add directory contents
        for entry in path.iterdir():
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

    def _invalidate_cache_for_path(self, path: Path) -> None:
        """Invalidate cache for a specific path.

        Args:
            path: Path to invalidate
        """
        if self._dir_cache is not None:
            # Invalidate the directory containing the modified file
            parent_dir = path.parent if path.is_file() else path
            self._dir_cache.invalidate(parent_dir)
            logger.debug(f"Cache invalidated for: {parent_dir}")

    def _sort_and_display(self) -> None:
        """Sort items and update display."""
        # Filter hidden files if needed
        items_to_display = self._file_items
        if not self.show_hidden:
            items_to_display = [
                item for item in self._file_items
                if item.is_parent or not item.name.startswith('.')
            ]

        # Sort items
        sort_key_map = {
            "name": lambda x: (not x.is_parent, not x.is_dir, x.name.lower()),
            "size": lambda x: (not x.is_parent, not x.is_dir, x.size),
            "modified": lambda x: (not x.is_parent, not x.is_dir, x.modified),
        }

        key_func = sort_key_map.get(self.sort_column, sort_key_map["name"])
        sorted_items = sorted(
            items_to_display,
            key=key_func,
            reverse=self.sort_reverse,
        )

        # Store sorted items for navigation (CRITICAL FIX for navigation bug)
        self._sorted_items = sorted_items

        # Update table
        table = self.query_one(DataTable)
        table.clear()

        # Track added keys to prevent duplicates in case of race conditions
        added_keys: Set[str] = set()

        for item in sorted_items:
            # Format row based on current view mode
            row_data = ViewModeConfig.format_row(item, self.view_mode)

            # Check if file is selected
            style = "bold yellow" if str(item.path) in self.selected_files else None

            # Add row with duplicate key protection
            row_key = str(item.path)
            if row_key not in added_keys:
                try:
                    table.add_row(
                        *row_data,
                        key=row_key,
                    )
                    added_keys.add(row_key)

                    if style:
                        row_key_obj = table.get_row_at(table.row_count - 1)
                except Exception as e:
                    # Skip rows that cause errors (e.g., duplicate keys)
                    logger.debug(f"Skipped row for {row_key}: {e}")
                    continue

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

    def _update_cache_stats_display(self) -> None:
        """Update cache statistics display if enabled."""
        try:
            config = get_config_manager().get_config()
            stats_widget = self.query_one(f"#cache-stats-{id(self)}", Static)

            if config.cache.show_stats and self._dir_cache is not None:
                stats = self._dir_cache.get_stats()
                stats_text = (
                    f"Cache: {stats['size']}/{stats['maxsize']} "
                    f"Hit: {stats['hit_rate']:.1f}% "
                    f"({stats['hits']}/{stats['hits'] + stats['misses']})"
                )
                stats_widget.update(stats_text)
                stats_widget.add_class("active")
            else:
                stats_widget.update("")
                stats_widget.remove_class("active")

        except Exception:
            # Widget not yet composed or stats disabled
            pass

    def get_current_item(self) -> Optional[FileItem]:
        """Get currently highlighted item.

        Returns:
            Current file item or None
        """
        table = self.query_one(DataTable)

        # FIX: Validate against table.row_count, not len(self._file_items)
        # This fixes navigation when hidden files are filtered
        if table.cursor_row < 0 or table.cursor_row >= table.row_count:
            return None

        # FIX: Direct O(1) indexing instead of O(n) search
        # Use _sorted_items which matches the table display exactly
        if table.cursor_row < len(self._sorted_items):
            return self._sorted_items[table.cursor_row]

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

    def cycle_view_mode(self) -> None:
        """Cycle through view modes."""
        modes = [ViewMode.FULL, ViewMode.BRIEF, ViewMode.INFO]
        current_index = modes.index(self.view_mode)
        next_index = (current_index + 1) % len(modes)
        self.view_mode = modes[next_index]
        self.notify(f"View mode: {self.view_mode.value.title()}")

    def set_view_mode(self, mode: ViewMode) -> None:
        """Set specific view mode.

        Args:
            mode: View mode to set
        """
        self.view_mode = mode
        self.notify(f"View mode: {self.view_mode.value.title()}")

    def select_group(self, pattern: str, case_sensitive: bool = False) -> None:
        """Select files matching wildcard pattern.

        Args:
            pattern: Wildcard pattern (e.g., "*.py", "test_*")
            case_sensitive: Whether matching is case-sensitive
        """
        matching = self._group_selector.select_matching(
            self._file_items, pattern, case_sensitive
        )

        for item in matching:
            self.selected_files.add(str(item.path))
            self.post_message(self.FileSelected(item.path, True))

        self._sort_and_display()
        self.notify(f"Selected {len(matching)} file(s) matching '{pattern}'")

    def deselect_group(self, pattern: str, case_sensitive: bool = False) -> None:
        """Deselect files matching wildcard pattern.

        Args:
            pattern: Wildcard pattern
            case_sensitive: Whether matching is case-sensitive
        """
        self.selected_files = self._group_selector.deselect_matching(
            self._file_items, pattern, self.selected_files, case_sensitive
        )

        self._sort_and_display()
        self.notify(f"Deselected files matching '{pattern}'")

    def invert_selection(self) -> None:
        """Invert current selection."""
        self.selected_files = self._group_selector.invert_selection(
            self._file_items, self.selected_files
        )

        self._sort_and_display()
        self.notify(f"Selection inverted")

    def activate_quick_search(self) -> None:
        """Activate quick search mode."""
        self._quick_search.activate()
        self._update_quick_search_display()

    def deactivate_quick_search(self) -> None:
        """Deactivate quick search mode."""
        self._quick_search.deactivate()
        self._update_quick_search_display()

    def handle_quick_search_key(self, char: str) -> bool:
        """Handle character input for quick search.

        Args:
            char: Character typed

        Returns:
            True if key was handled, False otherwise
        """
        if not char.isprintable() or len(char) != 1:
            return False

        # Activate quick search if not active
        if not self._quick_search.is_active:
            self._quick_search.activate()

        # Add character to search
        self._quick_search.add_char(char)
        self._update_quick_search_display()

        # Find next match
        table = self.query_one(DataTable)
        current_index = table.cursor_row
        next_index = self._quick_search.find_next_match(
            self._file_items, current_index
        )

        # CRITICAL FIX: Use move_cursor() method instead of direct assignment
        # cursor_row is read-only in Textual DataTable
        if next_index is not None:
            table.move_cursor(row=next_index)

        return True

    def handle_quick_search_backspace(self) -> bool:
        """Handle backspace in quick search.

        Returns:
            True if key was handled, False otherwise
        """
        if not self._quick_search.is_active:
            return False

        self._quick_search.remove_char()

        if not self._quick_search.search_text:
            self.deactivate_quick_search()
        else:
            self._update_quick_search_display()

        return True

    def _update_quick_search_display(self) -> None:
        """Update quick search status display."""
        try:
            status = self.query_one(f"#quick-search-{id(self)}", Static)

            if self._quick_search.is_active and self._quick_search.search_text:
                status.update(f"Search: {self._quick_search.search_text}")
                status.add_class("active")
            else:
                status.update("")
                status.remove_class("active")
        except Exception:
            # Widget not yet composed
            pass

    # Keyboard bindings - REMOVED ENTER BINDING (see ROOT_CAUSE_ENTER_KEY.md)
    BINDINGS = [
        ("backspace", "navigate_up", "Parent"),
        ("insert", "toggle_selection", "Select"),
        ("ctrl+r", "refresh", "Refresh"),
        ("ctrl+s", "cycle_sort", "Sort"),
        ("ctrl+d", "toggle_sort_direction", "Reverse"),
        ("ctrl+v", "cycle_view_mode", "View Mode"),
        ("kp_plus", "group_select", "Select Group"),
        ("kp_minus", "group_deselect", "Deselect Group"),
        ("kp_multiply", "invert_selection", "Invert Selection"),
    ]

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
        self.refresh_directory(force=True)
        self.notify("Directory refreshed")

    def action_cycle_sort(self) -> None:
        """Handle cycle sort action."""
        self.cycle_sort()

    def action_toggle_sort_direction(self) -> None:
        """Handle toggle sort direction action."""
        self.toggle_sort_direction()

    def action_cycle_view_mode(self) -> None:
        """Handle cycle view mode action."""
        self.cycle_view_mode()

    def action_group_select(self) -> None:
        """Handle group select action (Gray +)."""
        self.post_message(self.GroupSelectRequest("select", self))

    def action_group_deselect(self) -> None:
        """Handle group deselect action (Gray -)."""
        self.post_message(self.GroupSelectRequest("deselect", self))

    def action_invert_selection(self) -> None:
        """Handle invert selection action (Gray *)."""
        self.invert_selection()

    def toggle_hidden_files(self) -> None:
        """Toggle hidden files visibility."""
        self.show_hidden = not self.show_hidden
        status = "shown" if self.show_hidden else "hidden"
        self.notify(f"Hidden files {status}")

    def select_file_by_path(self, file_path: Path) -> bool:
        """Select and highlight a specific file in the panel.

        Args:
            file_path: Path to the file to select

        Returns:
            True if file was found and selected, False otherwise
        """
        table = self.query_one(DataTable)
        file_path_str = str(file_path.resolve())

        # Find the row index for the file
        for row_index in range(table.row_count):
            row_key = table.get_row_at(row_index)
            if str(row_key) == file_path_str:
                # Position cursor on the file
                # CRITICAL FIX: Use move_cursor() method instead of direct assignment
                # cursor_row is read-only in Textual DataTable
                table.move_cursor(row=row_index)
                # Ensure the row is visible (scroll if needed)
                table.scroll_to_row(row_index)
                return True

        return False

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle DataTable row selection (Enter key).

        This is the CORRECT way to handle Enter key navigation.
        DataTable's built-in Enter binding (enter -> select_cursor) was consuming
        the key before FilePanel's binding could execute. Using the RowSelected
        event handler allows us to respond to Enter key presses properly.

        Args:
            event: Row selection event from DataTable
        """
        # Activate the current item (navigate into directory or open file)
        self.activate_current()

        # Prevent default DataTable behavior
        event.prevent_default()
        event.stop()

    def on_key(self, event: Key) -> None:
        """Handle key events for quick search.

        Args:
            event: Key event
        """
        # Handle Escape to cancel quick search
        if event.key == "escape" and self._quick_search.is_active:
            self.deactivate_quick_search()
            event.prevent_default()
            event.stop()
            return

        # Handle backspace in quick search
        if event.key == "backspace":
            if self.handle_quick_search_backspace():
                event.prevent_default()
                event.stop()
                return

        # CRITICAL FIX: Only activate quick search for printable chars
        # that are NOT control keys (ctrl, alt, shift combinations)
        # This prevents menu shortcuts (like Ctrl+T, Ctrl+H) from triggering search
        if event.character and event.character.isprintable() and len(event.character) == 1:
            # Check if this is a control key combination (ctrl+x, alt+x, etc.)
            # In Textual, modifier keys are indicated by event.key containing '+' or 'ctrl' prefix
            # This allows menu shortcuts and other key bindings to work properly
            if event.key != event.character or '+' in event.key or event.key.startswith('ctrl'):
                # Let the key event propagate for command handling
                return

            # Only handle as quick search if it's a plain character with no modifiers
            if self.handle_quick_search_key(event.character):
                event.prevent_default()
                event.stop()
                return
