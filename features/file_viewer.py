"""File viewer (F3) for Modern Commander.

Provides comprehensive file viewing capabilities with syntax highlighting,
hex viewing, and advanced navigation features.
"""

from pathlib import Path
from typing import Optional, List, Tuple
import mimetypes
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Footer, Header
from textual.containers import Container, Vertical
from textual.binding import Binding
from rich.syntax import Syntax
from rich.text import Text


# --------------------------------------------------------------------------- #
# Binary-file type detection (Sprint 3 S3.6)
# --------------------------------------------------------------------------- #

# Ordered list of (magic bytes, human label).  First match wins.
# Keep prefixes short (<= 8 bytes) so we only need to peek the header.
_MAGIC_SIGNATURES: Tuple[Tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "PNG image"),
    (b"\xff\xd8\xff", "JPEG image"),
    (b"GIF87a", "GIF image"),
    (b"GIF89a", "GIF image"),
    (b"GIF8", "GIF image"),  # Fallback for odd GIF8 headers
    (b"PK\x03\x04", "ZIP archive"),
    (b"PK\x05\x06", "ZIP archive (empty)"),
    (b"PK\x07\x08", "ZIP archive (spanned)"),
    (b"\x1f\x8b", "gzip archive"),
    (b"BZh", "bzip2 archive"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip archive"),
    (b"Rar!\x1a\x07", "RAR archive"),
    (b"\x7fELF", "ELF executable (Linux)"),
    (b"MZ", "Windows executable"),
    (b"%PDF-", "PDF document"),
    (b"\xca\xfe\xba\xbe", "Java class file"),
    (b"RIFF", "RIFF container (WAV/AVI)"),
)

# Extension fallback when no magic signature matches.
_EXT_LABELS: dict = {
    ".exe": "Windows executable",
    ".dll": "Windows DLL",
    ".so": "Shared library",
    ".dylib": "macOS dynamic library",
    ".o": "Object file",
    ".obj": "Object file",
    ".class": "Java class file",
    ".pyc": "Python bytecode",
    ".wasm": "WebAssembly binary",
    ".bin": "Binary data",
    ".dat": "Binary data",
    ".iso": "ISO image",
    ".mp3": "MP3 audio",
    ".mp4": "MP4 video",
    ".mkv": "Matroska video",
    ".flac": "FLAC audio",
    ".webp": "WebP image",
}


def detect_binary_type(path: Path, header: Optional[bytes] = None) -> str:
    """Detect a human-readable label for a binary file.

    Args:
        path: File path (used for the extension fallback).
        header: Optional pre-read header bytes (first 8+ bytes).  If
            ``None`` the function reads up to 16 bytes from ``path``.

    Returns:
        Short description such as ``"PNG image"``, ``"Windows executable"``,
        or ``"Binary data"`` when nothing matches.
    """
    if header is None:
        try:
            with open(path, "rb") as f:
                header = f.read(16)
        except OSError:
            header = b""

    for signature, label in _MAGIC_SIGNATURES:
        if header.startswith(signature):
            return label

    # Extension fallback
    ext_label = _EXT_LABELS.get(path.suffix.lower())
    if ext_label is not None:
        return ext_label

    return "Binary data"


def format_binary_size(size: int) -> str:
    """Human-readable file size used in the viewer banner.

    Kept as a module-level helper so tests can exercise it without
    instantiating the Textual screen.
    """
    value: float = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


def build_binary_banner(path: Path, size: int, binary_type: str) -> str:
    """Build the banner line shown above a hex dump.

    Example: ``"Binary file: PNG image, 1.2 KB"``.
    """
    return f"Binary file: {binary_type}, {format_binary_size(size)}"


@dataclass
class ViewerState:
    """Current viewer state."""
    file_path: Path
    total_lines: int
    current_line: int = 0
    view_mode: str = "text"  # "text" or "hex"
    encoding: str = "utf-8"
    search_term: str = ""
    search_matches: List[int] = None
    binary_type: str = ""  # Populated for binary files: "PNG image", etc.


class FileViewer(Screen):
    """File viewer screen with syntax highlighting and hex view."""

    CSS = """
    FileViewer {
        background: $surface;
    }

    FileViewer Header {
        background: $primary;
        color: $text;
    }

    FileViewer Footer {
        background: $panel;
    }

    FileViewer .viewer-container {
        height: 1fr;
        border: solid $accent;
        background: $surface;
    }

    FileViewer .content-view {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }

    FileViewer .status-bar {
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
    }

    FileViewer .error-message {
        color: $error;
        padding: 1 2;
    }

    FileViewer .hex-view {
        /* terminal font only — font-family is not a valid Textual CSS property */
    }
    """

    BINDINGS = [
        Binding("escape,q", "quit", "Quit", priority=True),
        Binding("down,j", "scroll_down", "Down", show=False),
        Binding("up,k", "scroll_up", "Up", show=False),
        Binding("pagedown,space", "page_down", "Page Down"),
        Binding("pageup", "page_up", "Page Up"),
        Binding("home,g", "goto_start", "Start"),
        Binding("end", "goto_end", "End"),
        Binding("ctrl+g", "goto_line", "Go to Line"),
        Binding("slash,ctrl+f", "search", "Search"),
        Binding("n", "next_match", "Next Match", show=False),
        Binding("shift+n", "prev_match", "Prev Match", show=False),
        Binding("h", "toggle_hex", "Hex View"),
        Binding("w", "toggle_wrap", "Wrap Lines"),
        Binding("f3", "quit", "Close", priority=True),
    ]

    def __init__(self, file_path: Path, name: Optional[str] = None) -> None:
        """Initialize file viewer.

        Args:
            file_path: Path to file to view
            name: Screen name
        """
        super().__init__(name=name)
        self.file_path = file_path.resolve()
        self.state: Optional[ViewerState] = None
        self.content_lines: List[str] = []
        self.wrap_lines: bool = False
        self._content_scroll_y: int = 0
        self.is_binary: bool = False

    def compose(self) -> ComposeResult:
        """Compose viewer widgets."""
        yield Header()

        with Vertical(classes="viewer-container"):
            yield Static(id="content-view", classes="content-view")
            yield Static(id="status-bar", classes="status-bar")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize viewer on mount."""
        header = self.query_one(Header)
        header.tall = False

        try:
            self._load_file()
            self._update_display()
        except Exception as e:
            self._show_error(f"Failed to load file: {e}")

    def _load_file(self) -> None:
        """Load file content."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        if not self.file_path.is_file():
            raise ValueError(f"Not a file: {self.file_path}")

        # Check if file is binary
        self.is_binary = self._is_binary_file()

        if self.is_binary:
            self._load_binary()
        else:
            self._load_text()

    def _is_binary_file(self) -> bool:
        """Check if file is binary.

        Returns:
            True if file is binary
        """
        try:
            # Read first 8KB to check for binary content
            with open(self.file_path, 'rb') as f:
                chunk = f.read(8192)

            # Check for null bytes (common in binary files)
            if b'\x00' in chunk:
                return True

            # Try to decode as text
            try:
                chunk.decode('utf-8')
                return False
            except UnicodeDecodeError:
                # Try other common encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        chunk.decode(encoding)
                        return False
                    except UnicodeDecodeError:
                        continue
                return True

        except Exception:
            return True

    def _load_text(self) -> None:
        """Load text file content."""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        content = None

        for encoding in encodings:
            try:
                with open(self.file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                self.state = ViewerState(
                    file_path=self.file_path,
                    total_lines=0,
                    encoding=encoding
                )
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            # Fallback to binary view
            self.is_binary = True
            self._load_binary()
            return

        self.content_lines = content.splitlines()
        self.state.total_lines = len(self.content_lines)

    def _load_binary(self) -> None:
        """Load binary file for hex view."""
        with open(self.file_path, 'rb') as f:
            data = f.read()

        # Detect the binary type using magic-byte comparison.
        binary_type = detect_binary_type(self.file_path, header=data[:16])
        banner = build_binary_banner(self.file_path, len(data), binary_type)

        # Prepend banner + blank separator line above the hex dump.
        hex_lines = self._format_hex(data)
        self.content_lines = [banner, ""] + hex_lines

        self.state = ViewerState(
            file_path=self.file_path,
            total_lines=len(self.content_lines),
            view_mode="hex",
            binary_type=binary_type,
        )

    def _format_hex(self, data: bytes) -> List[str]:
        """Format binary data as hex dump.

        Args:
            data: Binary data

        Returns:
            List of formatted hex lines
        """
        lines = []
        bytes_per_line = 16

        for offset in range(0, len(data), bytes_per_line):
            chunk = data[offset:offset + bytes_per_line]

            # Offset
            hex_offset = f"{offset:08x}"

            # Hex bytes
            hex_bytes = ' '.join(f"{b:02x}" for b in chunk)
            hex_bytes = hex_bytes.ljust(bytes_per_line * 3 - 1)

            # ASCII representation
            ascii_repr = ''.join(
                chr(b) if 32 <= b < 127 else '.'
                for b in chunk
            )

            line = f"{hex_offset}  {hex_bytes}  |{ascii_repr}|"
            lines.append(line)

        return lines

    def _update_display(self) -> None:
        """Update content display."""
        if not self.state:
            return

        content_view = self.query_one("#content-view", Static)
        status_bar = self.query_one("#status-bar", Static)

        # Determine visible lines
        visible_height = content_view.size.height - 2  # Account for padding
        if visible_height < 1:
            visible_height = 20

        start_line = self._content_scroll_y
        end_line = min(start_line + visible_height, self.state.total_lines)

        # Get visible content
        visible_lines = self.content_lines[start_line:end_line]

        # Apply syntax highlighting for text files
        if self.state.view_mode == "text" and not self.is_binary:
            content = self._render_text_content(visible_lines, start_line)
        else:
            content = Text("\n".join(visible_lines), style="white on black")

        content_view.update(content)

        # Update status bar
        status = self._format_status()
        status_bar.update(status)

    def _render_text_content(self, lines: List[str], start_line: int) -> Text:
        """Render text content with syntax highlighting.

        Args:
            lines: Lines to render
            start_line: Starting line number

        Returns:
            Rendered text
        """
        content = "\n".join(lines)

        # Try to detect language for syntax highlighting
        lexer_name = self._detect_language()

        if lexer_name and len(content) < 100000:  # Don't highlight huge files
            try:
                syntax = Syntax(
                    content,
                    lexer_name,
                    theme="monokai",
                    line_numbers=True,
                    start_line=start_line + 1,
                    word_wrap=self.wrap_lines
                )
                return syntax
            except Exception:
                pass

        # Fallback to plain text
        if self.wrap_lines:
            return Text(content)
        else:
            return Text(content, overflow="ellipsis")

    def _detect_language(self) -> Optional[str]:
        """Detect programming language from file extension.

        Returns:
            Lexer name or None
        """
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sh': 'bash',
            '.sql': 'sql',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.java': 'java',
            '.rs': 'rust',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
        }

        return ext_map.get(self.file_path.suffix.lower())

    def _format_status(self) -> str:
        """Format status bar text.

        Returns:
            Status text
        """
        if not self.state:
            return ""

        file_name = self.file_path.name
        file_size = self.file_path.stat().st_size
        size_str = self._format_size(file_size)

        current_line = self._content_scroll_y + 1
        total_lines = self.state.total_lines
        percentage = int((current_line / total_lines * 100)) if total_lines > 0 else 0

        mode = "HEX" if self.state.view_mode == "hex" else self.state.encoding.upper()
        wrap = "WRAP" if self.wrap_lines else "NOWRAP"

        status_parts = [
            f"{file_name}",
            f"{size_str}",
            f"Line {current_line}/{total_lines}",
            f"{percentage}%",
            mode,
            wrap
        ]

        return "  |  ".join(status_parts)

    def _format_size(self, size: int) -> str:
        """Format file size.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        return format_binary_size(size)

    def _show_error(self, message: str) -> None:
        """Show error message.

        Args:
            message: Error message
        """
        content_view = self.query_one("#content-view", Static)
        content_view.update(
            Text(message, style="bold red"),
            classes="error-message"
        )

    # Actions
    def action_quit(self) -> None:
        """Quit viewer."""
        self.app.pop_screen()

    def action_scroll_down(self) -> None:
        """Scroll down one line."""
        if self._content_scroll_y < self.state.total_lines - 1:
            self._content_scroll_y += 1
            self._update_display()

    def action_scroll_up(self) -> None:
        """Scroll up one line."""
        if self._content_scroll_y > 0:
            self._content_scroll_y -= 1
            self._update_display()

    def action_page_down(self) -> None:
        """Scroll down one page."""
        content_view = self.query_one("#content-view", Static)
        page_size = max(1, content_view.size.height - 2)

        self._content_scroll_y = min(
            self._content_scroll_y + page_size,
            max(0, self.state.total_lines - page_size)
        )
        self._update_display()

    def action_page_up(self) -> None:
        """Scroll up one page."""
        content_view = self.query_one("#content-view", Static)
        page_size = max(1, content_view.size.height - 2)

        self._content_scroll_y = max(0, self._content_scroll_y - page_size)
        self._update_display()

    def action_goto_start(self) -> None:
        """Go to start of file."""
        self._content_scroll_y = 0
        self._update_display()

    def action_goto_end(self) -> None:
        """Go to end of file."""
        content_view = self.query_one("#content-view", Static)
        page_size = max(1, content_view.size.height - 2)

        self._content_scroll_y = max(0, self.state.total_lines - page_size)
        self._update_display()

    def action_toggle_hex(self) -> None:
        """Toggle hex <-> text view manually.

        Users can press ``h`` to flip between hex and text rendering even
        when the auto-detector disagrees — useful when a file has no null
        bytes but is still mostly binary, or when a binary file happens to
        contain readable text the user wants to see.
        """
        if self.state is None:
            return

        if self.state.view_mode == "text":
            # Switch to hex: read raw bytes, build banner, swap mode
            with open(self.file_path, 'rb') as f:
                data = f.read()
            binary_type = detect_binary_type(self.file_path, header=data[:16])
            banner = build_binary_banner(self.file_path, len(data), binary_type)
            self.content_lines = [banner, ""] + self._format_hex(data)
            self.state.view_mode = "hex"
            self.state.total_lines = len(self.content_lines)
            self.state.binary_type = binary_type
            self._content_scroll_y = 0
        else:
            # Switch back to text.  If detection flagged the file as binary,
            # we still attempt a text load so the user can see what's there.
            self._load_text()
            # _load_text may fall back to binary (sets is_binary=True) if the
            # file genuinely cannot be decoded — handle that gracefully.
            if self.state.view_mode == "text":
                self.is_binary = False
            self._content_scroll_y = 0

        self._update_display()

    def action_toggle_wrap(self) -> None:
        """Toggle line wrapping."""
        self.wrap_lines = not self.wrap_lines
        self._update_display()

    def action_goto_line(self) -> None:
        """Go to specific line number."""
        def handle_line_input(line_num: str) -> None:
            try:
                target = int(line_num) - 1  # Convert to 0-based index
                if 0 <= target < self.state.total_lines:
                    self._content_scroll_y = target
                    self._update_display()
                else:
                    self.notify(
                        f"Line number must be between 1 and {self.state.total_lines}",
                        severity="error"
                    )
            except ValueError:
                self.notify("Invalid line number", severity="error")

        self.app.push_screen(
            "input",
            callback=handle_line_input
        )

    def action_search(self) -> None:
        """Search for text in file."""
        def handle_search(term: str) -> None:
            if not term:
                return

            self.state.search_term = term
            self.state.search_matches = []

            # Find all matches
            for i, line in enumerate(self.content_lines):
                if term.lower() in line.lower():
                    self.state.search_matches.append(i)

            if self.state.search_matches:
                self._content_scroll_y = self.state.search_matches[0]
                self._update_display()
                self.notify(
                    f"Found {len(self.state.search_matches)} matches",
                    severity="information"
                )
            else:
                self.notify("No matches found", severity="warning")

        self.app.push_screen(
            "input",
            callback=handle_search
        )

    def action_next_match(self) -> None:
        """Go to next search match."""
        if not self.state.search_matches:
            self.notify("No search results", severity="warning")
            return

        # Find next match after current position
        next_match = None
        for match in self.state.search_matches:
            if match > self._content_scroll_y:
                next_match = match
                break

        # Wrap around if needed
        if next_match is None:
            next_match = self.state.search_matches[0]

        self._content_scroll_y = next_match
        self._update_display()

    def action_prev_match(self) -> None:
        """Go to previous search match."""
        if not self.state.search_matches:
            self.notify("No search results", severity="warning")
            return

        # Find previous match before current position
        prev_match = None
        for match in reversed(self.state.search_matches):
            if match < self._content_scroll_y:
                prev_match = match
                break

        # Wrap around if needed
        if prev_match is None:
            prev_match = self.state.search_matches[-1]

        self._content_scroll_y = prev_match
        self._update_display()
