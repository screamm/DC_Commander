"""File editor (F4) for Modern Commander.

Provides comprehensive text editing capabilities with undo/redo,
search/replace, syntax highlighting, and auto-save functionality.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import threading
import time

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, TextArea, Static
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual.message import Message


@dataclass
class EditorState:
    """Current editor state."""
    file_path: Path
    original_content: str
    is_modified: bool = False
    last_saved: Optional[datetime] = None
    encoding: str = "utf-8"
    line_count: int = 0
    cursor_line: int = 1
    cursor_column: int = 1


class FileEditor(Screen):
    """File editor screen with full editing capabilities."""

    CSS = """
    FileEditor {
        background: $surface;
    }

    FileEditor Header {
        background: $primary;
        color: $text;
    }

    FileEditor Footer {
        background: $panel;
    }

    FileEditor .editor-container {
        height: 1fr;
        border: solid $accent;
        background: $surface;
    }

    FileEditor TextArea {
        height: 1fr;
        border: none;
        background: $surface;
    }

    FileEditor TextArea:focus {
        border: none;
    }

    FileEditor .status-bar {
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
    }

    FileEditor .modified-indicator {
        color: $warning;
    }

    FileEditor .saved-indicator {
        color: $success;
    }

    FileEditor .error-message {
        color: $error;
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("escape", "quit_check", "Quit", priority=True),
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("ctrl+q", "quit_check", "Quit", priority=True),
        Binding("ctrl+z", "undo", "Undo"),
        Binding("ctrl+y,ctrl+shift+z", "redo", "Redo"),
        Binding("ctrl+f", "find", "Find"),
        Binding("ctrl+h", "replace", "Replace"),
        Binding("ctrl+g", "goto_line", "Go to Line"),
        Binding("ctrl+a", "select_all", "Select All"),
        Binding("f3", "find_next", "Find Next", show=False),
        Binding("shift+f3", "find_prev", "Find Prev", show=False),
        Binding("f4", "quit_check", "Close", priority=True),
    ]

    def __init__(
        self,
        file_path: Path,
        name: Optional[str] = None,
        create_new: bool = False
    ) -> None:
        """Initialize file editor.

        Args:
            file_path: Path to file to edit
            name: Screen name
            create_new: Create new file if it doesn't exist
        """
        super().__init__(name=name)
        self.file_path = file_path.resolve()
        self.create_new = create_new
        self.state: Optional[EditorState] = None
        self.auto_save_enabled: bool = True
        self.auto_save_interval: int = 30  # seconds
        self.auto_save_thread: Optional[threading.Thread] = None
        self.auto_save_running: bool = False
        self.search_term: str = ""
        self.replace_term: str = ""

    def compose(self) -> ComposeResult:
        """Compose editor widgets."""
        yield Header()

        with Vertical(classes="editor-container"):
            yield TextArea(id="text-area", language="python")
            yield Static(id="status-bar", classes="status-bar")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize editor on mount."""
        header = self.query_one(Header)
        header.tall = False

        try:
            self._load_file()
            self._update_status()
            self._start_auto_save()

            # Set up text area event handlers
            text_area = self.query_one(TextArea)
            text_area.focus()

        except Exception as e:
            self._show_error(f"Failed to load file: {e}")

    def on_unmount(self) -> None:
        """Clean up on unmount."""
        self._stop_auto_save()

    def _load_file(self) -> None:
        """Load file content."""
        if self.file_path.exists():
            if not self.file_path.is_file():
                raise ValueError(f"Not a file: {self.file_path}")

            # Try to load with different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            content = None
            used_encoding = None

            for encoding in encodings:
                try:
                    with open(self.file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    used_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                raise ValueError("Unable to decode file with supported encodings")

            # Initialize state
            self.state = EditorState(
                file_path=self.file_path,
                original_content=content,
                encoding=used_encoding,
                line_count=content.count('\n') + 1,
                last_saved=datetime.fromtimestamp(self.file_path.stat().st_mtime)
            )

            # Load into text area
            text_area = self.query_one(TextArea)
            text_area.text = content

            # Detect and set language for syntax highlighting
            language = self._detect_language()
            if language:
                text_area.language = language

        elif self.create_new:
            # Create new empty file
            self.state = EditorState(
                file_path=self.file_path,
                original_content="",
                is_modified=True,
                line_count=1
            )

            text_area = self.query_one(TextArea)
            text_area.text = ""

            # Set language based on extension
            language = self._detect_language()
            if language:
                text_area.language = language

        else:
            raise FileNotFoundError(f"File not found: {self.file_path}")

    def _detect_language(self) -> Optional[str]:
        """Detect programming language from file extension.

        Returns:
            Language name or None
        """
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sh': 'bash',
            '.sql': 'sql',
            '.toml': 'toml',
            '.ini': 'ini',
            '.txt': 'text',
        }

        return ext_map.get(self.file_path.suffix.lower())

    def _save_file(self) -> bool:
        """Save file content.

        Returns:
            True if save succeeded
        """
        try:
            text_area = self.query_one(TextArea)
            content = text_area.text

            # Create parent directories if needed
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(self.file_path, 'w', encoding=self.state.encoding) as f:
                f.write(content)

            # Update state
            self.state.original_content = content
            self.state.is_modified = False
            self.state.last_saved = datetime.now()
            self.state.line_count = content.count('\n') + 1

            self._update_status()
            return True

        except Exception as e:
            self.notify(f"Failed to save file: {e}", severity="error")
            return False

    def _update_status(self) -> None:
        """Update status bar."""
        if not self.state:
            return

        status_bar = self.query_one("#status-bar", Static)
        text_area = self.query_one(TextArea)

        # Get cursor position
        cursor = text_area.cursor_location
        line = cursor[0] + 1
        column = cursor[1] + 1

        # File info
        file_name = self.file_path.name
        file_size = self._format_size(len(text_area.text.encode(self.state.encoding)))

        # Modified indicator
        if self.state.is_modified:
            modified = "[modified]"
            modified_class = "modified-indicator"
        else:
            modified = "[saved]"
            modified_class = "saved-indicator"

        # Last saved time
        if self.state.last_saved:
            last_saved = self.state.last_saved.strftime("%H:%M:%S")
        else:
            last_saved = "Never"

        # Build status
        status_parts = [
            f"{file_name}",
            f"{file_size}",
            f"Line {line}/{self.state.line_count}",
            f"Col {column}",
            self.state.encoding.upper(),
            f"Saved: {last_saved}",
            modified
        ]

        status_bar.update("  |  ".join(status_parts))

    def _format_size(self, size: int) -> str:
        """Format file size.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def _show_error(self, message: str) -> None:
        """Show error message.

        Args:
            message: Error message
        """
        content_view = self.query_one(TextArea)
        content_view.load_text("")
        self.notify(message, severity="error")

    def _check_modified(self) -> bool:
        """Check if content has been modified.

        Returns:
            True if modified
        """
        text_area = self.query_one(TextArea)
        current_content = text_area.text
        return current_content != self.state.original_content

    def _start_auto_save(self) -> None:
        """Start auto-save thread."""
        if not self.auto_save_enabled:
            return

        self.auto_save_running = True

        def auto_save_worker():
            while self.auto_save_running:
                time.sleep(self.auto_save_interval)
                if self.auto_save_running and self.state.is_modified:
                    self.call_from_thread(self._auto_save)

        self.auto_save_thread = threading.Thread(
            target=auto_save_worker,
            daemon=True
        )
        self.auto_save_thread.start()

    def _stop_auto_save(self) -> None:
        """Stop auto-save thread."""
        self.auto_save_running = False
        if self.auto_save_thread:
            self.auto_save_thread.join(timeout=1)

    def _auto_save(self) -> None:
        """Perform auto-save."""
        if self._save_file():
            self.notify("Auto-saved", timeout=1)

    # Text area event handlers
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes.

        Args:
            event: Change event
        """
        if self.state:
            self.state.is_modified = self._check_modified()
            self.state.line_count = event.text_area.text.count('\n') + 1
            self._update_status()

    # Actions
    def action_save(self) -> None:
        """Save file."""
        if self._save_file():
            self.notify("File saved successfully", severity="information")

    def action_quit_check(self) -> None:
        """Check for unsaved changes before quitting."""
        if self.state and self.state.is_modified:
            def handle_response(save: bool) -> None:
                if save:
                    if self._save_file():
                        self.app.pop_screen()
                else:
                    self.app.pop_screen()

            self.app.push_screen(
                "confirm",
                callback=handle_response
            )
        else:
            self.app.pop_screen()

    def action_undo(self) -> None:
        """Undo last change."""
        text_area = self.query_one(TextArea)
        # TextArea has built-in undo
        # This is handled by Ctrl+Z naturally
        pass

    def action_redo(self) -> None:
        """Redo last undone change."""
        text_area = self.query_one(TextArea)
        # TextArea has built-in redo
        # This is handled by Ctrl+Y naturally
        pass

    def action_find(self) -> None:
        """Find text in document."""
        def handle_search(term: str) -> None:
            if not term:
                return

            self.search_term = term
            text_area = self.query_one(TextArea)

            # Search for term
            content = text_area.text
            pos = content.find(term)

            if pos >= 0:
                # Calculate line and column
                lines_before = content[:pos].count('\n')
                line_start = content.rfind('\n', 0, pos) + 1
                column = pos - line_start

                # Move cursor to match
                text_area.move_cursor((lines_before, column))
                text_area.select((lines_before, column), (lines_before, column + len(term)))

                self.notify(f"Found: {term}", severity="information")
            else:
                self.notify("Not found", severity="warning")

        self.app.push_screen(
            "input",
            callback=handle_search
        )

    def action_replace(self) -> None:
        """Replace text in document."""
        def handle_find(find_term: str) -> None:
            if not find_term:
                return

            self.search_term = find_term

            def handle_replace(replace_term: str) -> None:
                self.replace_term = replace_term
                text_area = self.query_one(TextArea)

                # Replace all occurrences
                content = text_area.text
                new_content = content.replace(self.search_term, self.replace_term)
                count = content.count(self.search_term)

                if count > 0:
                    text_area.text = new_content
                    self.state.is_modified = True
                    self._update_status()
                    self.notify(
                        f"Replaced {count} occurrence(s)",
                        severity="information"
                    )
                else:
                    self.notify("No matches found", severity="warning")

            self.app.push_screen(
                "input",
                callback=handle_replace
            )

        self.app.push_screen(
            "input",
            callback=handle_find
        )

    def action_goto_line(self) -> None:
        """Go to specific line number."""
        def handle_line_input(line_num: str) -> None:
            try:
                target = int(line_num) - 1  # Convert to 0-based index
                if 0 <= target < self.state.line_count:
                    text_area = self.query_one(TextArea)
                    text_area.move_cursor((target, 0))
                    self.notify(f"Jumped to line {line_num}", severity="information")
                else:
                    self.notify(
                        f"Line number must be between 1 and {self.state.line_count}",
                        severity="error"
                    )
            except ValueError:
                self.notify("Invalid line number", severity="error")

        self.app.push_screen(
            "input",
            callback=handle_line_input
        )

    def action_select_all(self) -> None:
        """Select all text."""
        text_area = self.query_one(TextArea)
        lines = text_area.text.count('\n')
        last_line_len = len(text_area.text.split('\n')[-1])
        text_area.select((0, 0), (lines, last_line_len))

    def action_find_next(self) -> None:
        """Find next occurrence of search term."""
        if not self.search_term:
            self.notify("No search term", severity="warning")
            return

        text_area = self.query_one(TextArea)
        content = text_area.text
        cursor = text_area.cursor_location

        # Calculate current position
        lines_before = content[:cursor[0]].count('\n')
        current_pos = sum(len(line) + 1 for line in content.split('\n')[:lines_before])
        current_pos += cursor[1]

        # Search from current position
        pos = content.find(self.search_term, current_pos + 1)

        if pos < 0:
            # Wrap around
            pos = content.find(self.search_term)

        if pos >= 0:
            # Calculate line and column
            lines_before = content[:pos].count('\n')
            line_start = content.rfind('\n', 0, pos) + 1
            column = pos - line_start

            # Move cursor to match
            text_area.move_cursor((lines_before, column))
            text_area.select((lines_before, column), (lines_before, column + len(self.search_term)))
        else:
            self.notify("No more matches", severity="information")

    def action_find_prev(self) -> None:
        """Find previous occurrence of search term."""
        if not self.search_term:
            self.notify("No search term", severity="warning")
            return

        text_area = self.query_one(TextArea)
        content = text_area.text
        cursor = text_area.cursor_location

        # Calculate current position
        lines_before = content[:cursor[0]].count('\n')
        current_pos = sum(len(line) + 1 for line in content.split('\n')[:lines_before])
        current_pos += cursor[1]

        # Search backwards from current position
        pos = content.rfind(self.search_term, 0, current_pos - 1)

        if pos < 0:
            # Wrap around
            pos = content.rfind(self.search_term)

        if pos >= 0:
            # Calculate line and column
            lines_before = content[:pos].count('\n')
            line_start = content.rfind('\n', 0, pos) + 1
            column = pos - line_start

            # Move cursor to match
            text_area.move_cursor((lines_before, column))
            text_area.select((lines_before, column), (lines_before, column + len(self.search_term)))
        else:
            self.notify("No more matches", severity="information")
