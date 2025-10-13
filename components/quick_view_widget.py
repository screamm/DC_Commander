"""Quick View widget for DC Commander.

Provides file preview functionality similar to Norton Commander's Ctrl+Q feature.
Shows text previews, file info, and image dimensions in the opposite panel.
"""

from pathlib import Path
from typing import Optional, List, Dict, Union, Any
from datetime import datetime
import mimetypes

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table

from src.utils.encoding import is_binary_file, detect_encoding


class QuickViewWidget(Container):
    """Widget for previewing file contents in Quick View mode."""

    DEFAULT_CSS = """
    QuickViewWidget {
        border: solid $accent;
        background: $surface;
        height: 1fr;
    }

    QuickViewWidget .quick-view-header {
        background: $primary;
        color: $text;
        text-align: center;
        height: 1;
        padding: 0 1;
        dock: top;
    }

    QuickViewWidget .quick-view-content {
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }

    QuickViewWidget .quick-view-content VerticalScroll {
        height: 1fr;
        background: #0000AA;
    }

    QuickViewWidget .error-text {
        color: #FFFF77;
        background: #0000AA;
        padding: 2;
    }

    QuickViewWidget .info-table {
        background: #0000AA;
        color: #00FFFF;
    }

    QuickViewWidget .text-preview {
        background: #0000AA;
        color: #00FFFF;
    }

    QuickViewWidget .binary-indicator {
        color: #FFFF77;
        background: #0000AA;
        text-align: center;
        padding: 2;
    }
    """

    # Reactive properties
    current_file: reactive[Optional[Path]] = reactive(None)

    # Constants
    MAX_PREVIEW_LINES = 100
    MAX_PREVIEW_SIZE = 1024 * 1024  # 1MB
    MAX_LINE_LENGTH = 200

    def __init__(
        self,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize Quick View widget.

        Args:
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self._content_cache: Dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Compose Quick View widgets."""
        yield Static("Quick View", classes="quick-view-header")

        with VerticalScroll(classes="quick-view-content"):
            yield Static(
                self._create_empty_view(),
                id=f"qv-content-{id(self)}",
                classes="text-preview"
            )

    def watch_current_file(self, file_path: Optional[Path]) -> None:
        """React to file selection changes.

        Args:
            file_path: Selected file path
        """
        if not self.is_mounted:
            return

        try:
            header = self.query_one(".quick-view-header", Static)
            content = self.query_one(f"#qv-content-{id(self)}", Static)

            if not file_path or not file_path.exists():
                header.update("Quick View")
                content.update(self._create_empty_view())
                return

            # Update header with filename
            header.update(f"Quick View: {file_path.name}")

            # Generate and display preview
            preview = self._generate_preview(file_path)
            content.update(preview)

        except Exception as e:
            self._show_error(f"Preview error: {e}")

    def set_file(self, file_path: Optional[Path]) -> None:
        """Set the file to preview.

        Args:
            file_path: Path to file to preview
        """
        self.current_file = file_path

    def _generate_preview(self, file_path: Path) -> Union[Text, Syntax, Panel]:
        """Generate preview content for file.

        Args:
            file_path: Path to file

        Returns:
            Preview content as Rich renderable
        """
        # Check if file is a directory
        if file_path.is_dir():
            return self._create_directory_info(file_path)

        # Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > self.MAX_PREVIEW_SIZE:
                return self._create_large_file_info(file_path)
        except Exception as e:
            return self._create_error_view(f"Cannot access file: {e}")

        # Check if binary
        if is_binary_file(file_path):
            return self._create_binary_info(file_path)

        # Check if image
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and mime_type.startswith('image/'):
            return self._create_image_info(file_path)

        # Generate text preview
        return self._create_text_preview(file_path)

    def _create_text_preview(self, file_path: Path) -> Union[Syntax, Text]:
        """Create preview for text files.

        Args:
            file_path: Path to text file

        Returns:
            Text preview with syntax highlighting if applicable
        """
        try:
            # Detect encoding
            encoding = detect_encoding(file_path)
            if not encoding:
                encoding = 'utf-8'

            # Read file content (limited to first N lines)
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= self.MAX_PREVIEW_LINES:
                        break
                    # Truncate very long lines
                    if len(line) > self.MAX_LINE_LENGTH:
                        line = line[:self.MAX_LINE_LENGTH] + '...\n'
                    lines.append(line.rstrip('\n'))

            content = '\n'.join(lines)

            # Try syntax highlighting
            lexer = self._detect_lexer(file_path)
            if lexer and len(content) < 100000:
                try:
                    return Syntax(
                        content,
                        lexer,
                        theme="monokai",
                        line_numbers=True,
                        word_wrap=False,
                        background_color="#0000AA"
                    )
                except Exception:
                    pass

            # Fallback to plain text with Norton Commander colors
            text = Text(content)
            text.stylize("cyan on #0000AA")

            # Add truncation notice if needed
            total_lines = sum(1 for _ in open(file_path, 'r', encoding=encoding, errors='replace'))
            if total_lines > self.MAX_PREVIEW_LINES:
                text.append(f"\n\n[yellow]... {total_lines - self.MAX_PREVIEW_LINES} more lines ...[/yellow]")

            return text

        except Exception as e:
            return self._create_error_view(f"Cannot read file: {e}")

    def _create_binary_info(self, file_path: Path) -> Panel:
        """Create info panel for binary files.

        Args:
            file_path: Path to binary file

        Returns:
            Info panel with file details
        """
        try:
            stat = file_path.stat()

            # Create info table
            table = Table.grid(padding=(0, 2))
            table.add_column(style="yellow", justify="right")
            table.add_column(style="cyan")

            table.add_row("File:", file_path.name)
            table.add_row("Type:", "Binary File")
            table.add_row("Size:", self._format_size(stat.st_size))
            table.add_row("Modified:", datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))

            # Try to get MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type:
                table.add_row("MIME Type:", mime_type)

            # Read first 256 bytes for hex preview
            try:
                with open(file_path, 'rb') as f:
                    header_bytes = f.read(256)
                    hex_preview = self._format_hex_preview(header_bytes)
                    table.add_row("", "")
                    table.add_row("Hex Preview:", "")
                    for line in hex_preview.split('\n'):
                        table.add_row("", line)
            except Exception:
                pass

            return Panel(
                table,
                title="Binary File Information",
                border_style="cyan",
                style="on #0000AA"
            )

        except Exception as e:
            return self._create_error_view(f"Cannot read file info: {e}")

    def _create_image_info(self, file_path: Path) -> Panel:
        """Create info panel for image files.

        Args:
            file_path: Path to image file

        Returns:
            Info panel with image details
        """
        try:
            stat = file_path.stat()

            # Create info table
            table = Table.grid(padding=(0, 2))
            table.add_column(style="yellow", justify="right")
            table.add_column(style="cyan")

            table.add_row("File:", file_path.name)
            table.add_row("Type:", "Image File")
            table.add_row("Size:", self._format_size(stat.st_size))
            table.add_row("Modified:", datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))

            # Try to get MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type:
                table.add_row("Format:", mime_type.split('/')[1].upper())

            # Try to get image dimensions using PIL if available
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    table.add_row("Dimensions:", f"{img.width} x {img.height} pixels")
                    if hasattr(img, 'mode'):
                        table.add_row("Mode:", img.mode)
            except ImportError:
                table.add_row("Dimensions:", "Install Pillow for image info")
            except Exception:
                table.add_row("Dimensions:", "Cannot read image data")

            return Panel(
                table,
                title="Image File Information",
                border_style="cyan",
                style="on #0000AA"
            )

        except Exception as e:
            return self._create_error_view(f"Cannot read image info: {e}")

    def _create_directory_info(self, dir_path: Path) -> Panel:
        """Create info panel for directories.

        Args:
            dir_path: Path to directory

        Returns:
            Info panel with directory statistics
        """
        try:
            stat = dir_path.stat()

            # Count directory contents
            file_count = 0
            dir_count = 0
            total_size = 0

            try:
                for entry in dir_path.iterdir():
                    try:
                        if entry.is_file():
                            file_count += 1
                            total_size += entry.stat().st_size
                        elif entry.is_dir():
                            dir_count += 1
                    except (PermissionError, OSError):
                        continue
            except (PermissionError, OSError):
                pass

            # Create info table
            table = Table.grid(padding=(0, 2))
            table.add_column(style="yellow", justify="right")
            table.add_column(style="cyan")

            table.add_row("Directory:", dir_path.name or str(dir_path))
            table.add_row("Type:", "Directory")
            table.add_row("Files:", str(file_count))
            table.add_row("Subdirectories:", str(dir_count))
            table.add_row("Total Size:", self._format_size(total_size))
            table.add_row("Modified:", datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))

            return Panel(
                table,
                title="Directory Information",
                border_style="cyan",
                style="on #0000AA"
            )

        except Exception as e:
            return self._create_error_view(f"Cannot read directory info: {e}")

    def _create_large_file_info(self, file_path: Path) -> Panel:
        """Create info panel for files too large to preview.

        Args:
            file_path: Path to large file

        Returns:
            Info panel with file details
        """
        try:
            stat = file_path.stat()

            table = Table.grid(padding=(0, 2))
            table.add_column(style="yellow", justify="right")
            table.add_column(style="cyan")

            table.add_row("File:", file_path.name)
            table.add_row("Size:", self._format_size(stat.st_size))
            table.add_row("Modified:", datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))
            table.add_row("", "")
            table.add_row("Notice:", "[yellow]File too large for preview[/yellow]")
            table.add_row("", f"Maximum preview size: {self._format_size(self.MAX_PREVIEW_SIZE)}")

            return Panel(
                table,
                title="File Information",
                border_style="yellow",
                style="on #0000AA"
            )

        except Exception as e:
            return self._create_error_view(f"Cannot read file info: {e}")

    def _create_empty_view(self) -> Text:
        """Create empty view when no file is selected.

        Returns:
            Empty view text
        """
        text = Text("\n\n")
        text.append("  No file selected", style="yellow on #0000AA")
        text.append("\n\n")
        text.append("  Select a file to preview its contents", style="cyan on #0000AA")
        return text

    def _create_error_view(self, message: str) -> Text:
        """Create error view.

        Args:
            message: Error message

        Returns:
            Error view text
        """
        text = Text("\n\n")
        text.append(f"  Error: {message}", style="bold red on #0000AA")
        return text

    def _show_error(self, message: str) -> None:
        """Show error in content area.

        Args:
            message: Error message
        """
        try:
            content = self.query_one(f"#qv-content-{id(self)}", Static)
            content.update(self._create_error_view(message))
        except Exception:
            pass

    def _format_hex_preview(self, data: bytes, lines: int = 8) -> str:
        """Format binary data as hex dump preview.

        Args:
            data: Binary data
            lines: Number of lines to show

        Returns:
            Formatted hex preview
        """
        result = []
        bytes_per_line = 16
        max_bytes = lines * bytes_per_line

        for offset in range(0, min(len(data), max_bytes), bytes_per_line):
            chunk = data[offset:offset + bytes_per_line]

            # Hex bytes
            hex_bytes = ' '.join(f"{b:02x}" for b in chunk)
            hex_bytes = hex_bytes.ljust(bytes_per_line * 3 - 1)

            # ASCII representation
            ascii_repr = ''.join(
                chr(b) if 32 <= b < 127 else '.'
                for b in chunk
            )

            line = f"{hex_bytes}  {ascii_repr}"
            result.append(line)

        if len(data) > max_bytes:
            result.append(f"... {len(data) - max_bytes} more bytes ...")

        return '\n'.join(result)

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

    def _detect_lexer(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension.

        Args:
            file_path: Path to file

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
            '.cs': 'csharp',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.m': 'matlab',
            '.pl': 'perl',
            '.lua': 'lua',
        }

        return ext_map.get(file_path.suffix.lower())
