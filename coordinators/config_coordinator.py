"""Configuration coordination for ModernCommander.

Manages configuration and theme coordination, providing unified interface
for configuration management and theme application.
"""

from typing import Optional, Any, TYPE_CHECKING
from pathlib import Path

from features.config_manager import ConfigManager, Config
from features.theme_manager import ThemeManager

if TYPE_CHECKING:
    from textual.app import App


class ConfigCoordinator:
    """Manages configuration and theme coordination.

    Responsibilities:
    - Load and save configuration
    - Update configuration values
    - Manage theme selection and application
    - Coordinate config changes with theme updates
    """

    def __init__(self, app: "App", config_manager: ConfigManager, theme_manager: ThemeManager):
        """Initialize config coordinator.

        Args:
            app: Application instance for notifications
            config_manager: Configuration manager instance
            theme_manager: Theme manager instance
        """
        self.app = app
        self.config_manager = config_manager
        self.theme_manager = theme_manager

    def get_config(self) -> Config:
        """Get current configuration.

        Returns:
            Current configuration object
        """
        return self.config_manager.get_config()

    def update_config(self, section: str, key: str, value: Any) -> None:
        """Update configuration value.

        Args:
            section: Configuration section
            key: Configuration key
            value: New value
        """
        self.config_manager.update_config(section, key, value)

    def save_config(self) -> bool:
        """Save configuration to disk.

        Returns:
            True if save successful
        """
        try:
            self.config_manager.save_config()
            return True
        except Exception as e:
            self.app.notify(f"Failed to save configuration: {e}", severity="error")
            return False

    def reload_config(self) -> None:
        """Reload configuration from disk."""
        self.config_manager.load_config()

    def cycle_theme(self) -> None:
        """Cycle to next theme and apply it."""
        current_theme = self.get_config().theme
        next_theme = self.theme_manager.get_next_theme_name(current_theme)

        self.config_manager.update_theme(next_theme)
        self.config_manager.save_config()
        self.apply_theme(next_theme)

    def apply_theme(self, theme_name: str) -> bool:
        """Apply theme to application.

        Args:
            theme_name: Name of theme to apply

        Returns:
            True if theme applied successfully
        """
        if self.theme_manager.set_current_theme(theme_name):
            theme = self.theme_manager.get_current_theme()
            if theme:
                self.app.notify(f"Theme: {theme.display_name}", timeout=1)
                return True

        self.app.notify(f"Theme not found: {theme_name}", severity="error")
        return False

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names.

        Returns:
            List of theme names
        """
        return self.theme_manager.get_available_themes()

    def update_panel_path(self, panel: str, path: Path) -> None:
        """Update panel path in configuration.

        Args:
            panel: Panel identifier ("left" or "right")
            path: Directory path
        """
        if panel == "left":
            self.config_manager.update_left_panel_path(str(path))
        elif panel == "right":
            self.config_manager.update_right_panel_path(str(path))

    def update_panel_sort(self, panel: str, sort_by: str, ascending: bool) -> None:
        """Update panel sort configuration.

        Args:
            panel: Panel identifier ("left" or "right")
            sort_by: Sort column
            ascending: Sort direction
        """
        self.config_manager.update_config(f"{panel}_panel", "sort_by", sort_by)
        self.config_manager.update_config(f"{panel}_panel", "sort_ascending", ascending)

    def save_current_state(self, left_path: Path, right_path: Path) -> None:
        """Save current application state to configuration.

        Args:
            left_path: Current left panel path
            right_path: Current right panel path
        """
        self.update_panel_path("left", left_path)
        self.update_panel_path("right", right_path)
        self.save_config()
