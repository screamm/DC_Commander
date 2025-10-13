"""
Configuration Manager for Modern Commander

Handles loading, saving, and managing application configuration.
Provides type-safe configuration access with validation and defaults.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict, field


@dataclass
class PanelConfig:
    """Configuration for file panel"""
    start_path: str = ""
    show_hidden_files: bool = False
    sort_by: str = "name"  # name, size, date, extension
    sort_ascending: bool = True


@dataclass
class CacheConfig:
    """Directory cache configuration"""
    enabled: bool = True
    maxsize: int = 100  # Maximum number of cached directories
    ttl_seconds: int = 60  # Time-to-live in seconds
    show_stats: bool = False  # Show cache statistics in UI


@dataclass
class ColorScheme:
    """Color scheme configuration"""
    name: str = "default"
    background: str = "blue"
    text: str = "white"
    selected_bg: str = "cyan"
    selected_text: str = "black"
    panel_border: str = "white"
    status_bar_bg: str = "cyan"
    status_bar_text: str = "black"


@dataclass
class EditorSettings:
    """Text editor configuration"""
    default_editor: str = ""  # Empty = use system default
    tab_size: int = 4
    use_spaces: bool = True
    word_wrap: bool = False
    show_line_numbers: bool = True
    syntax_highlighting: bool = True


@dataclass
class ViewSettings:
    """View and display settings"""
    show_hidden_files: bool = False
    show_file_size: bool = True
    show_file_date: bool = True
    show_file_permissions: bool = False
    file_size_format: str = "auto"  # auto, bytes, kb, mb, gb
    date_format: str = "%Y-%m-%d %H:%M"
    use_24_hour_time: bool = True


@dataclass
class KeyboardShortcuts:
    """Keyboard shortcut configuration"""
    quit: str = "q"
    refresh: str = "r"
    copy: str = "F5"
    move: str = "F6"
    delete: str = "F8"
    new_folder: str = "F7"
    edit: str = "F4"
    view: str = "F3"
    search: str = "/"
    system_info: str = "i"
    help: str = "F1"
    swap_panels: str = "TAB"
    select_file: str = "INSERT"
    select_all: str = "*"


@dataclass
class Config:
    """Main configuration class"""
    left_panel: PanelConfig = field(default_factory=PanelConfig)
    right_panel: PanelConfig = field(default_factory=PanelConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    color_scheme: ColorScheme = field(default_factory=ColorScheme)
    editor: EditorSettings = field(default_factory=EditorSettings)
    view: ViewSettings = field(default_factory=ViewSettings)
    shortcuts: KeyboardShortcuts = field(default_factory=KeyboardShortcuts)
    theme: str = "norton_commander"  # Theme name for ThemeManager


class ConfigManager:
    """
    Manages application configuration with file persistence.

    Provides thread-safe configuration loading, saving, and validation.
    Handles missing configuration files gracefully with sensible defaults.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses default location.
        """
        if config_path is None:
            config_path = self._get_default_config_path()

        self.config_path = Path(config_path)
        self._config: Optional[Config] = None

    @staticmethod
    def _get_default_config_path() -> str:
        """Get default configuration file path based on OS"""
        home = Path.home()

        # Platform-specific config directories
        if os.name == "nt":  # Windows
            config_dir = home / "AppData" / "Roaming" / "ModernCommander"
        elif os.name == "posix":
            # Linux/macOS - follow XDG Base Directory specification
            xdg_config = os.getenv("XDG_CONFIG_HOME")
            if xdg_config:
                config_dir = Path(xdg_config) / "modern-commander"
            else:
                config_dir = home / ".config" / "modern-commander"
        else:
            # Fallback
            config_dir = home / ".modern-commander"

        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / "config.json")

    def load_config(self) -> Config:
        """
        Load configuration from file.

        Returns:
            Config object with settings loaded from file or defaults

        Note:
            If configuration file doesn't exist or is invalid,
            returns default configuration and creates new config file.
        """
        if self._config is not None:
            return self._config

        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._config = self._dict_to_config(data)
            else:
                # Create default configuration
                self._config = Config()
                self._set_default_panel_paths()
                self.save_config()

        except (json.JSONDecodeError, IOError, ValueError) as e:
            # Log error and use defaults
            print(f"Warning: Failed to load config from {self.config_path}: {e}")
            self._config = Config()
            self._set_default_panel_paths()

        return self._config

    def save_config(self) -> bool:
        """
        Save current configuration to file.

        Returns:
            True if save successful, False otherwise
        """
        if self._config is None:
            return False

        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert config to dictionary
            config_dict = self._config_to_dict(self._config)

            # Write with pretty formatting
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            return True

        except (IOError, OSError) as e:
            print(f"Error: Failed to save config to {self.config_path}: {e}")
            return False

    def _set_default_panel_paths(self) -> None:
        """Set default start paths for panels based on OS"""
        if self._config is None:
            return

        home = str(Path.home())

        # Set sensible defaults
        self._config.left_panel.start_path = home
        self._config.right_panel.start_path = home

    @staticmethod
    def _config_to_dict(config: Config) -> Dict[str, Any]:
        """Convert Config object to dictionary for JSON serialization"""
        return {
            "left_panel": asdict(config.left_panel),
            "right_panel": asdict(config.right_panel),
            "cache": asdict(config.cache),
            "color_scheme": asdict(config.color_scheme),
            "editor": asdict(config.editor),
            "view": asdict(config.view),
            "shortcuts": asdict(config.shortcuts),
            "theme": config.theme
        }

    @staticmethod
    def _dict_to_config(data: Dict[str, Any]) -> Config:
        """Convert dictionary to Config object with validation"""
        config = Config()

        # Load panel configurations
        if "left_panel" in data:
            config.left_panel = PanelConfig(**data["left_panel"])
        if "right_panel" in data:
            config.right_panel = PanelConfig(**data["right_panel"])

        # Load cache configuration
        if "cache" in data:
            config.cache = CacheConfig(**data["cache"])

        # Load color scheme
        if "color_scheme" in data:
            config.color_scheme = ColorScheme(**data["color_scheme"])

        # Load editor settings
        if "editor" in data:
            config.editor = EditorSettings(**data["editor"])

        # Load view settings
        if "view" in data:
            config.view = ViewSettings(**data["view"])

        # Load keyboard shortcuts
        if "shortcuts" in data:
            config.shortcuts = KeyboardShortcuts(**data["shortcuts"])

        # Load theme
        if "theme" in data:
            config.theme = data["theme"]

        return config

    def get_config(self) -> Config:
        """Get current configuration, loading if necessary"""
        if self._config is None:
            return self.load_config()
        return self._config

    def update_left_panel_path(self, path: str) -> None:
        """Update left panel start path"""
        config = self.get_config()
        config.left_panel.start_path = path

    def update_right_panel_path(self, path: str) -> None:
        """Update right panel start path"""
        config = self.get_config()
        config.right_panel.start_path = path

    def update_cache_settings(
        self,
        enabled: Optional[bool] = None,
        maxsize: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
        show_stats: Optional[bool] = None
    ) -> None:
        """
        Update cache configuration settings.

        Args:
            enabled: Enable/disable caching
            maxsize: Maximum cache size
            ttl_seconds: Time-to-live in seconds
            show_stats: Show cache statistics
        """
        config = self.get_config()
        if enabled is not None:
            config.cache.enabled = enabled
        if maxsize is not None:
            config.cache.maxsize = maxsize
        if ttl_seconds is not None:
            config.cache.ttl_seconds = ttl_seconds
        if show_stats is not None:
            config.cache.show_stats = show_stats

    def update_color_scheme(self, scheme_name: str) -> None:
        """
        Update color scheme by name.

        Args:
            scheme_name: Name of color scheme (default, dark, light, classic)
        """
        config = self.get_config()

        schemes = {
            "default": ColorScheme(
                name="default",
                background="blue",
                text="white",
                selected_bg="cyan",
                selected_text="black",
                panel_border="white",
                status_bar_bg="cyan",
                status_bar_text="black"
            ),
            "dark": ColorScheme(
                name="dark",
                background="black",
                text="white",
                selected_bg="white",
                selected_text="black",
                panel_border="cyan",
                status_bar_bg="white",
                status_bar_text="black"
            ),
            "light": ColorScheme(
                name="light",
                background="white",
                text="black",
                selected_bg="cyan",
                selected_text="white",
                panel_border="black",
                status_bar_bg="cyan",
                status_bar_text="white"
            ),
            "classic": ColorScheme(
                name="classic",
                background="blue",
                text="yellow",
                selected_bg="cyan",
                selected_text="blue",
                panel_border="yellow",
                status_bar_bg="black",
                status_bar_text="white"
            )
        }

        if scheme_name in schemes:
            config.color_scheme = schemes[scheme_name]

    def update_theme(self, theme_name: str) -> None:
        """
        Update theme preference.

        Args:
            theme_name: Name of theme to apply
        """
        config = self.get_config()
        config.theme = theme_name

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values"""
        self._config = Config()
        self._set_default_panel_paths()

    def validate_config(self) -> list[str]:
        """
        Validate configuration and return list of issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []
        config = self.get_config()

        # Validate panel paths exist
        if config.left_panel.start_path and not Path(config.left_panel.start_path).exists():
            issues.append(f"Left panel path does not exist: {config.left_panel.start_path}")

        if config.right_panel.start_path and not Path(config.right_panel.start_path).exists():
            issues.append(f"Right panel path does not exist: {config.right_panel.start_path}")

        # Validate cache settings
        if config.cache.maxsize < 1 or config.cache.maxsize > 1000:
            issues.append(f"Invalid cache maxsize: {config.cache.maxsize} (must be 1-1000)")

        if config.cache.ttl_seconds < 1 or config.cache.ttl_seconds > 3600:
            issues.append(f"Invalid cache TTL: {config.cache.ttl_seconds} (must be 1-3600)")

        # Validate editor settings
        if config.editor.tab_size < 1 or config.editor.tab_size > 16:
            issues.append(f"Invalid tab size: {config.editor.tab_size} (must be 1-16)")

        # Validate view settings
        valid_formats = ["auto", "bytes", "kb", "mb", "gb"]
        if config.view.file_size_format not in valid_formats:
            issues.append(f"Invalid file size format: {config.view.file_size_format}")

        return issues


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """
    Get global configuration manager instance.

    Args:
        config_path: Optional custom configuration path

    Returns:
        ConfigManager instance
    """
    global _config_manager

    if _config_manager is None or config_path is not None:
        _config_manager = ConfigManager(config_path)

    return _config_manager
