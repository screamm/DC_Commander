"""
DC Commander Plugin System

Provides extensibility through a plugin architecture with:
- Dynamic plugin discovery and loading
- Security validation and sandboxing
- Lifecycle management (load, initialize, enable, disable, shutdown)
- Action registration and command binding
- Hook system for file and directory events
- Menu integration

Usage:
    >>> from src.plugins import PluginManager, ActionRegistry
    >>> from pathlib import Path
    >>>
    >>> # Initialize plugin system
    >>> registry = ActionRegistry()
    >>> manager = PluginManager(Path("plugins"), registry)
    >>> manager.set_app(app_instance)
    >>>
    >>> # Load and initialize plugins
    >>> plugins = manager.load_all_plugins()
    >>> manager.initialize_all_plugins()
    >>>
    >>> # Enable specific plugin
    >>> manager.enable_plugin("file_hash_plugin")
"""

from src.plugins.plugin_interface import PluginInterface, PluginMetadata
from src.plugins.action_registry import ActionRegistry, ActionInfo
from src.plugins.plugin_loader import PluginLoader, PluginLoadError
from src.plugins.plugin_manager import PluginManager, PluginState

__all__ = [
    "PluginInterface",
    "PluginMetadata",
    "ActionRegistry",
    "ActionInfo",
    "PluginLoader",
    "PluginLoadError",
    "PluginManager",
    "PluginState",
]

__version__ = "1.0.0"
