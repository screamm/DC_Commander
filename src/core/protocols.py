"""
Protocol definitions for DC Commander.

Provides interface contracts for dependency injection and platform abstraction.
Uses typing.Protocol for structural subtyping (duck typing with type hints).
"""

from typing import Protocol, List, Optional, Tuple, Callable, AsyncIterator, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass


@dataclass
class FileEntry:
    """File system entry metadata."""
    name: str
    path: Path
    size: int
    modified: datetime
    is_dir: bool
    is_symlink: bool = False
    permissions: Optional[int] = None
    owner: Optional[str] = None


# ============================================================================
# Configuration and Theme Protocols (for breaking circular dependencies)
# ============================================================================

class ConfigProvider(Protocol):
    """Protocol for configuration access without direct config_manager dependency."""

    def get_config(self) -> Any:
        """Get current configuration object.

        Returns:
            Config object with application settings
        """
        ...

    def update_config(self, section: str, key: str, value: Any) -> None:
        """Update configuration value.

        Args:
            section: Configuration section (e.g., "left_panel")
            key: Configuration key
            value: New value
        """
        ...

    def save_config(self) -> bool:
        """Save configuration to disk.

        Returns:
            True if successful, False otherwise
        """
        ...

    def update_theme(self, theme_name: str) -> None:
        """Update theme preference.

        Args:
            theme_name: Theme identifier
        """
        ...


class ThemeProvider(Protocol):
    """Protocol for theme access without direct theme_manager dependency."""

    def get_current_theme(self) -> Optional[Any]:
        """Get currently active theme.

        Returns:
            Theme object or None
        """
        ...

    def set_current_theme(self, theme_name: str) -> bool:
        """Set active theme by name.

        Args:
            theme_name: Theme identifier

        Returns:
            True if successful, False otherwise
        """
        ...

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names.

        Returns:
            List of theme identifiers
        """
        ...

    def get_next_theme_name(self, current_theme_name: str) -> str:
        """Get next theme name for cycling.

        Args:
            current_theme_name: Current theme identifier

        Returns:
            Next theme identifier
        """
        ...

    def generate_css(self, theme_name: Optional[str] = None) -> str:
        """Generate CSS for specified theme.

        Args:
            theme_name: Theme to generate CSS for

        Returns:
            CSS string with theme variables
        """
        ...


class NotificationProvider(Protocol):
    """Protocol for notification system without direct app dependency."""

    def notify(
        self,
        message: str,
        *,
        title: str = "",
        severity: str = "information",
        timeout: float = 3.0
    ) -> None:
        """Display notification to user.

        Args:
            message: Notification message
            title: Optional notification title
            severity: Severity level (information, warning, error)
            timeout: Display duration in seconds
        """
        ...


# ============================================================================
# Filesystem Protocols
# ============================================================================

class FileSystemProtocol(Protocol):
    """
    Protocol for filesystem operations.

    Implementations can be platform-specific (Windows, Linux, macOS)
    or provide special handling (network drives, virtual filesystems).
    """

    def list_directory(self, path: Path) -> List[FileEntry]:
        """
        List directory contents.

        Args:
            path: Directory to list

        Returns:
            List of file entries

        Raises:
            PermissionError: If directory is not readable
            FileNotFoundError: If directory doesn't exist
        """
        ...

    def copy_file(self, source: Path, dest: Path, *, overwrite: bool = False) -> None:
        """
        Copy file with platform-specific handling.

        Args:
            source: Source file path
            dest: Destination file path
            overwrite: Whether to overwrite existing destination

        Raises:
            FileExistsError: If dest exists and overwrite=False
            PermissionError: If insufficient permissions
            OSError: For other OS errors
        """
        ...

    def move_file(self, source: Path, dest: Path, *, overwrite: bool = False) -> None:
        """Move file with platform-specific handling."""
        ...

    def delete_file(self, path: Path) -> None:
        """Delete file or directory."""
        ...

    def create_directory(self, path: Path, *, parents: bool = False) -> None:
        """Create directory with platform-specific handling."""
        ...

    def get_file_info(self, path: Path) -> FileEntry:
        """Get detailed file information."""
        ...

    def validate_path(self, path: Path, allowed_base: Optional[Path] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate path for security and platform-specific issues.

        Args:
            path: Path to validate
            allowed_base: Optional base directory path must stay within

        Returns:
            Tuple of (is_valid, error_message)
        """
        ...


class AsyncFileSystemProtocol(Protocol):
    """
    Async version of FileSystemProtocol for non-blocking I/O.

    To be implemented in Phase 2.1 (Async File Operations).
    """

    async def list_directory_async(self, path: Path) -> List[FileEntry]:
        """Async directory listing."""
        ...

    async def copy_file_async(
        self,
        source: Path,
        dest: Path,
        *,
        overwrite: bool = False,
        progress_callback: Optional[Callable[[int], None]] = None,
        chunk_size: int = 64 * 1024
    ) -> None:
        """
        Async file copy with progress reporting.

        Args:
            source: Source file
            dest: Destination file
            overwrite: Overwrite existing
            progress_callback: Called with bytes copied
            chunk_size: Chunk size for copying
        """
        ...

    async def copy_directory_async(
        self,
        source: Path,
        dest: Path,
        *,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> AsyncIterator[Tuple[Path, bool]]:
        """
        Async directory copy yielding progress.

        Yields:
            Tuple of (file_path, success)
        """
        ...


class ConfigurationProtocol(Protocol):
    """Protocol for configuration management."""

    def load(self) -> dict:
        """Load configuration from storage."""
        ...

    def save(self, config: dict) -> bool:
        """Save configuration to storage."""
        ...

    def get(self, key: str, default: Optional[any] = None) -> any:
        """Get configuration value."""
        ...

    def set(self, key: str, value: any) -> None:
        """Set configuration value."""
        ...


class ThemeProtocol(Protocol):
    """Protocol for theme management."""

    def apply_theme(self, theme_name: str) -> bool:
        """Apply theme by name."""
        ...

    def get_available_themes(self) -> List[str]:
        """Get list of available theme names."""
        ...

    def get_theme_css(self, theme_name: str) -> str:
        """Get CSS for specified theme."""
        ...


class SearchEngineProtocol(Protocol):
    """Protocol for file search functionality."""

    def search(
        self,
        base_path: Path,
        pattern: str,
        *,
        regex: bool = False,
        recursive: bool = True,
        max_depth: Optional[int] = None,
        include_hidden: bool = False
    ) -> List[Path]:
        """
        Search for files matching pattern.

        Args:
            base_path: Base directory to search
            pattern: Search pattern (wildcard or regex)
            regex: Use regex instead of wildcard
            recursive: Search subdirectories
            max_depth: Maximum recursion depth
            include_hidden: Include hidden files

        Returns:
            List of matching file paths
        """
        ...


class CommandProtocol(Protocol):
    """Protocol for command pattern (undo/redo)."""

    def execute(self) -> bool:
        """
        Execute the command.

        Returns:
            True if successful
        """
        ...

    def undo(self) -> bool:
        """
        Undo the command.

        Returns:
            True if successful
        """
        ...

    def description(self) -> str:
        """Get human-readable description."""
        ...


class CommandHistoryProtocol(Protocol):
    """Protocol for command history management."""

    def execute_command(self, command: CommandProtocol) -> bool:
        """Execute command and add to history."""
        ...

    def undo(self) -> bool:
        """Undo last command."""
        ...

    def redo(self) -> bool:
        """Redo undone command."""
        ...

    def can_undo(self) -> bool:
        """Check if undo is possible."""
        ...

    def can_redo(self) -> bool:
        """Check if redo is possible."""
        ...

    def clear(self) -> None:
        """Clear command history."""
        ...


class SecurityValidatorProtocol(Protocol):
    """Protocol for security validation."""

    def validate_path(
        self,
        path: Path,
        allowed_base: Path,
        *,
        allow_symlinks: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Validate path for security issues."""
        ...

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing dangerous characters."""
        ...

    def is_safe_filename(self, filename: str) -> bool:
        """Check if filename is safe."""
        ...

    def check_archive_bomb(
        self,
        compressed_size: int,
        uncompressed_size: int,
        file_count: int = 0
    ) -> Tuple[bool, Optional[str]]:
        """Check for archive bomb indicators."""
        ...


class ArchiveHandlerProtocol(Protocol):
    """Protocol for archive file handling."""

    def list_archive_contents(self, archive_path: Path) -> List[str]:
        """List contents of archive."""
        ...

    def extract_archive(
        self,
        archive_path: Path,
        dest_path: Path,
        *,
        validate_security: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Extract archive to destination.

        Args:
            archive_path: Archive file
            dest_path: Extraction destination
            validate_security: Validate for security issues

        Returns:
            Tuple of (success, error_list)
        """
        ...

    def create_archive(
        self,
        source_paths: List[Path],
        archive_path: Path,
        *,
        compression: str = "zip"
    ) -> bool:
        """Create archive from source paths."""
        ...


# Type aliases for convenience
ProgressCallback = Callable[[int, str], None]
ErrorHandler = Callable[[Exception, Path], None]


# Example usage in components:
"""
from src.core.protocols import FileSystemProtocol, ConfigProvider

class FilePanel:
    def __init__(
        self,
        filesystem: FileSystemProtocol,
        config_provider: Optional[ConfigProvider] = None
    ):
        self.fs = filesystem  # Can be injected with any implementation
        self._config_provider = config_provider

    def refresh_directory(self):
        entries = self.fs.list_directory(self.current_path)
        self._display_entries(entries)

# Dependency injection in main app:
container = DependencyContainer()
container.register(ConfigManager, config_manager)
container.register(ThemeManager, theme_manager)

panel = FilePanel(
    filesystem=WindowsFileSystem(),
    config_provider=container.resolve(ConfigManager)
)
"""
