"""
Service interface protocols for dependency injection.

Defines abstract interfaces (protocols) for all major services in Modern Commander.
These protocols enable:
- Loose coupling between components
- Easy mocking for unit tests
- Interface-based programming
- Implementation flexibility
"""

from typing import Protocol, List, Optional, Dict, Any, Callable
from pathlib import Path


class IConfigManager(Protocol):
    """
    Configuration management service interface.

    Manages application configuration with file persistence,
    validation, and type-safe access.
    """

    def load_config(self) -> Any:
        """
        Load configuration from file.

        Returns:
            Config object with settings
        """
        ...

    def save_config(self) -> bool:
        """
        Save current configuration to file.

        Returns:
            True if save successful
        """
        ...

    def get_config(self) -> Any:
        """
        Get current configuration.

        Returns:
            Config object
        """
        ...

    def update_left_panel_path(self, path: str) -> None:
        """
        Update left panel start path.

        Args:
            path: Directory path
        """
        ...

    def update_right_panel_path(self, path: str) -> None:
        """
        Update right panel start path.

        Args:
            path: Directory path
        """
        ...

    def update_theme(self, theme_name: str) -> None:
        """
        Update theme preference.

        Args:
            theme_name: Name of theme to apply
        """
        ...

    def update_config(self, section: str, key: str, value: Any) -> None:
        """
        Update configuration value.

        Args:
            section: Config section (e.g., "left_panel")
            key: Config key
            value: New value
        """
        ...


class IThemeManager(Protocol):
    """
    Theme management service interface.

    Handles theme loading, switching, and CSS generation
    for dynamic application styling.
    """

    def get_available_themes(self) -> List[str]:
        """
        Get list of available theme names.

        Returns:
            List of theme identifiers
        """
        ...

    def load_theme(self, theme_name: str) -> Optional[Any]:
        """
        Load theme by name.

        Args:
            theme_name: Theme identifier

        Returns:
            Theme object if successful
        """
        ...

    def get_current_theme(self) -> Optional[Any]:
        """
        Get currently active theme.

        Returns:
            Current Theme object or None
        """
        ...

    def set_current_theme(self, theme_name: str) -> bool:
        """
        Set active theme by name.

        Args:
            theme_name: Theme identifier to activate

        Returns:
            True if successful
        """
        ...

    def get_next_theme_name(self, current_theme_name: str) -> str:
        """
        Get next theme name for cycling.

        Args:
            current_theme_name: Current theme identifier

        Returns:
            Next theme identifier
        """
        ...

    def generate_css(self, theme_name: Optional[str] = None) -> str:
        """
        Generate CSS for specified theme.

        Args:
            theme_name: Theme to generate CSS for

        Returns:
            CSS string with theme variables
        """
        ...


class IFileService(Protocol):
    """
    Synchronous file operations service interface.

    Handles basic file operations like copy, move, delete
    for small files and simple operations.
    """

    def copy_files(self, items: List[Any], dest: Path) -> bool:
        """
        Copy files to destination.

        Args:
            items: List of FileItem objects
            dest: Destination directory

        Returns:
            True if all operations successful
        """
        ...

    def move_files(self, items: List[Any], dest: Path) -> bool:
        """
        Move files to destination.

        Args:
            items: List of FileItem objects
            dest: Destination directory

        Returns:
            True if all operations successful
        """
        ...

    def delete_files(self, items: List[Any]) -> bool:
        """
        Delete files and directories.

        Args:
            items: List of FileItem objects

        Returns:
            True if all operations successful
        """
        ...


class IAsyncFileService(Protocol):
    """
    Asynchronous file operations service interface.

    Handles large file operations with progress tracking
    and cancellation support.
    """

    def should_use_async(self, items: List[Path]) -> bool:
        """
        Determine if async operations should be used.

        Args:
            items: List of paths to operate on

        Returns:
            True if async recommended for these items
        """
        ...

    async def copy_files_async(
        self,
        items: List[Path],
        dest_path: Path,
        overwrite: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Any:
        """
        Copy files asynchronously with progress.

        Args:
            items: List of paths to copy
            dest_path: Destination directory
            overwrite: Allow overwriting existing files
            progress_callback: Progress update callback

        Returns:
            Operation result with success/error counts
        """
        ...

    async def move_files_async(
        self,
        items: List[Path],
        dest_path: Path,
        overwrite: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Any:
        """
        Move files asynchronously with progress.

        Args:
            items: List of paths to move
            dest_path: Destination directory
            overwrite: Allow overwriting existing files
            progress_callback: Progress update callback

        Returns:
            Operation result with success/error counts
        """
        ...

    async def delete_files_async(
        self,
        items: List[Path],
        progress_callback: Optional[Callable] = None
    ) -> Any:
        """
        Delete files asynchronously with progress.

        Args:
            items: List of paths to delete
            progress_callback: Progress update callback

        Returns:
            Operation result with success/error counts
        """
        ...

    def cancel(self) -> None:
        """Cancel ongoing async operation."""
        ...
