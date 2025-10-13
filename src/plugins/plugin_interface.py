"""
Plugin Interface for DC Commander

Defines the abstract base class that all plugins must implement.
Provides metadata structure and lifecycle hooks.
"""

from abc import ABC, abstractmethod
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass, field


@dataclass
class PluginMetadata:
    """
    Metadata describing a plugin.

    Attributes:
        name: Unique plugin identifier (lowercase, no spaces)
        version: Semantic version string (e.g., "1.0.0")
        author: Plugin author name
        description: Human-readable description of plugin functionality
        dependencies: Optional list of required plugin names
        min_app_version: Minimum DC Commander version required
    """
    name: str
    version: str
    author: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    min_app_version: str = "1.0.0"

    def __post_init__(self):
        """Validate metadata after initialization."""
        if not self.name or " " in self.name:
            raise ValueError("Plugin name must be non-empty and contain no spaces")

        if not self.version:
            raise ValueError("Plugin version is required")


class PluginInterface(ABC):
    """
    Abstract base class for DC Commander plugins.

    All plugins must inherit from this class and implement the required methods.
    Plugins can extend functionality by registering custom actions and commands.

    Example:
        class MyPlugin(PluginInterface):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="my_plugin",
                    version="1.0.0",
                    author="John Doe",
                    description="Does something useful"
                )

            def initialize(self, app) -> None:
                self.app = app
                print("Plugin loaded!")

            def shutdown(self) -> None:
                print("Plugin unloaded!")
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.

        Returns:
            PluginMetadata instance with plugin information
        """
        pass

    @abstractmethod
    def initialize(self, app) -> None:
        """
        Called when plugin is loaded.

        Use this method to:
        - Store reference to app instance
        - Set up plugin state
        - Register event listeners
        - Initialize resources

        Args:
            app: ModernCommanderApp instance
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Called when plugin is unloaded.

        Use this method to:
        - Clean up resources
        - Unregister event listeners
        - Save plugin state
        - Close connections
        """
        pass

    def register_actions(self) -> Dict[str, Callable]:
        """
        Return custom actions to register with the application.

        Actions are callable functions that can be invoked through
        the command system or bound to keyboard shortcuts.

        Returns:
            Dictionary mapping action names to callable handlers

        Example:
            return {
                "my_custom_action": self.handle_custom_action,
                "another_action": lambda: print("Hello!")
            }
        """
        return {}

    def register_commands(self) -> Dict[str, str]:
        """
        Return custom F-key or keyboard command mappings.

        Maps keyboard shortcuts to action names registered in register_actions().

        Returns:
            Dictionary mapping keyboard shortcuts to action names

        Example:
            return {
                "ctrl+shift+m": "my_custom_action",
                "f11": "another_action"
            }
        """
        return {}

    def register_menu_items(self) -> Dict[str, Dict[str, str]]:
        """
        Return custom menu items for the top menu bar.

        Returns:
            Dictionary mapping menu categories to items

        Example:
            return {
                "Commands": {
                    "My Command": "my_custom_action",
                    "Another Command": "another_action"
                }
            }
        """
        return {}

    def on_file_selected(self, file_path: str) -> None:
        """
        Optional hook called when a file is selected.

        Args:
            file_path: Path to selected file
        """
        pass

    def on_directory_changed(self, directory_path: str) -> None:
        """
        Optional hook called when directory changes.

        Args:
            directory_path: Path to new directory
        """
        pass

    def get_config_schema(self) -> Optional[Dict]:
        """
        Optional method to define plugin configuration schema.

        Returns:
            Dictionary defining configuration options and their types

        Example:
            return {
                "api_key": {"type": "string", "default": ""},
                "max_retries": {"type": "int", "default": 3}
            }
        """
        return None
