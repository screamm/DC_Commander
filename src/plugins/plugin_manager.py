"""
Plugin Manager for DC Commander

Manages the plugin lifecycle: loading, initialization, enabling, disabling, and unloading.
Coordinates plugin hooks and integrates plugins with the application.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable

from src.plugins.plugin_interface import PluginInterface, PluginMetadata
from src.plugins.plugin_loader import PluginLoader, PluginLoadError
from src.plugins.action_registry import ActionRegistry

logger = logging.getLogger(__name__)


class PluginState:
    """Tracks plugin state during lifecycle."""

    def __init__(self, plugin: PluginInterface):
        """
        Initialize plugin state tracker.

        Args:
            plugin: Plugin instance
        """
        self.plugin = plugin
        self.enabled = False
        self.initialized = False
        self.error: Optional[str] = None


class PluginManager:
    """
    Central plugin management system.

    Handles complete plugin lifecycle:
    - Discovery and loading
    - Initialization and configuration
    - Enable/disable state management
    - Hook execution and event dispatch
    - Action registration and command binding
    - Clean shutdown and resource cleanup
    """

    def __init__(self, plugins_dir: Path, action_registry: ActionRegistry):
        """
        Initialize plugin manager.

        Args:
            plugins_dir: Directory containing plugin files
            action_registry: Registry for plugin actions and commands
        """
        self.plugins_dir = plugins_dir
        self.action_registry = action_registry
        self.loader = PluginLoader(plugins_dir)

        # Plugin state tracking
        self._plugins: Dict[str, PluginState] = {}

        # Application reference (set during initialization)
        self._app = None

    def set_app(self, app) -> None:
        """
        Set application reference for plugins.

        Args:
            app: ModernCommanderApp instance
        """
        self._app = app

    def load_all_plugins(self) -> Dict[str, PluginInterface]:
        """
        Discover and load all plugins.

        Returns:
            Dictionary mapping plugin names to plugin instances

        Example:
            >>> manager = PluginManager(Path("plugins"), ActionRegistry())
            >>> plugins = manager.load_all_plugins()
            >>> print(f"Loaded {len(plugins)} plugins")
        """
        # Load plugins using loader
        loaded_plugins = self.loader.load_all_plugins()

        # Validate dependencies
        missing_deps = self.loader.validate_dependencies(loaded_plugins)
        if missing_deps:
            logger.warning(
                f"Plugins with missing dependencies will not be enabled: "
                f"{', '.join(missing_deps)}"
            )

        # Create state tracking for each plugin
        for name, plugin in loaded_plugins.items():
            self._plugins[name] = PluginState(plugin)

        logger.info(f"Loaded {len(loaded_plugins)} plugins into manager")
        return loaded_plugins

    def initialize_all_plugins(self) -> int:
        """
        Initialize all loaded plugins.

        Calls initialize() on each plugin in dependency order.

        Returns:
            Number of successfully initialized plugins

        Example:
            >>> manager.load_all_plugins()
            >>> count = manager.initialize_all_plugins()
            >>> print(f"Initialized {count} plugins")
        """
        if not self._app:
            logger.error("Cannot initialize plugins: app reference not set")
            return 0

        # Get initialization order based on dependencies
        try:
            plugins_dict = {name: state.plugin for name, state in self._plugins.items()}
            init_order = self.loader.get_dependency_order(plugins_dict)
        except PluginLoadError as e:
            logger.error(f"Failed to resolve dependencies: {e}")
            return 0

        success_count = 0

        # Initialize plugins in order
        for plugin_name in init_order:
            if self.initialize_plugin(plugin_name):
                success_count += 1

        logger.info(f"Initialized {success_count}/{len(self._plugins)} plugins")
        return success_count

    def initialize_plugin(self, plugin_name: str) -> bool:
        """
        Initialize a specific plugin.

        Args:
            plugin_name: Name of plugin to initialize

        Returns:
            True if initialization successful, False otherwise
        """
        if plugin_name not in self._plugins:
            logger.error(f"Plugin not found: {plugin_name}")
            return False

        state = self._plugins[plugin_name]

        if state.initialized:
            logger.warning(f"Plugin already initialized: {plugin_name}")
            return True

        try:
            # Call plugin's initialize method
            state.plugin.initialize(self._app)
            state.initialized = True
            state.error = None

            logger.info(f"Initialized plugin: {plugin_name}")
            return True

        except Exception as e:
            state.error = str(e)
            logger.error(f"Failed to initialize plugin {plugin_name}: {e}")
            return False

    def enable_plugin(self, plugin_name: str) -> bool:
        """
        Enable a plugin and register its actions.

        Args:
            plugin_name: Name of plugin to enable

        Returns:
            True if enabled successfully, False otherwise

        Example:
            >>> manager.enable_plugin("file_hash_plugin")
            True
        """
        if plugin_name not in self._plugins:
            logger.error(f"Plugin not found: {plugin_name}")
            return False

        state = self._plugins[plugin_name]

        if not state.initialized:
            logger.error(f"Plugin not initialized: {plugin_name}")
            return False

        if state.enabled:
            logger.warning(f"Plugin already enabled: {plugin_name}")
            return True

        try:
            plugin = state.plugin

            # Register actions
            actions = plugin.register_actions()
            for action_name, handler in actions.items():
                self.action_registry.register_action(
                    action_name,
                    handler,
                    plugin_name,
                    description=f"Action from {plugin_name}"
                )

            # Register command mappings
            commands = plugin.register_commands()
            for key, action_name in commands.items():
                self.action_registry.register_command_mapping(key, action_name)

            # Register menu items
            menu_items = plugin.register_menu_items()
            if menu_items:
                self.action_registry.register_menu_items(plugin_name, menu_items)

            state.enabled = True
            logger.info(f"Enabled plugin: {plugin_name}")
            return True

        except Exception as e:
            state.error = str(e)
            logger.error(f"Failed to enable plugin {plugin_name}: {e}")
            return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """
        Disable a plugin and unregister its actions.

        Args:
            plugin_name: Name of plugin to disable

        Returns:
            True if disabled successfully, False otherwise
        """
        if plugin_name not in self._plugins:
            logger.error(f"Plugin not found: {plugin_name}")
            return False

        state = self._plugins[plugin_name]

        if not state.enabled:
            logger.warning(f"Plugin not enabled: {plugin_name}")
            return True

        try:
            # Unregister all plugin actions and commands
            self.action_registry.unregister_plugin_actions(plugin_name)

            state.enabled = False
            logger.info(f"Disabled plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to disable plugin {plugin_name}: {e}")
            return False

    def shutdown_plugin(self, plugin_name: str) -> bool:
        """
        Shutdown a plugin and clean up resources.

        Args:
            plugin_name: Name of plugin to shutdown

        Returns:
            True if shutdown successful, False otherwise
        """
        if plugin_name not in self._plugins:
            logger.error(f"Plugin not found: {plugin_name}")
            return False

        state = self._plugins[plugin_name]

        try:
            # Disable first if enabled
            if state.enabled:
                self.disable_plugin(plugin_name)

            # Call plugin's shutdown method
            if state.initialized:
                state.plugin.shutdown()
                state.initialized = False

            logger.info(f"Shutdown plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to shutdown plugin {plugin_name}: {e}")
            return False

    def shutdown_all_plugins(self) -> int:
        """
        Shutdown all plugins.

        Returns:
            Number of successfully shutdown plugins
        """
        success_count = 0

        for plugin_name in list(self._plugins.keys()):
            if self.shutdown_plugin(plugin_name):
                success_count += 1

        logger.info(f"Shutdown {success_count}/{len(self._plugins)} plugins")
        return success_count

    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """
        Get plugin instance by name.

        Args:
            plugin_name: Name of plugin

        Returns:
            Plugin instance or None if not found
        """
        if plugin_name not in self._plugins:
            return None

        return self._plugins[plugin_name].plugin

    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        Get plugin metadata.

        Args:
            plugin_name: Name of plugin

        Returns:
            Plugin metadata or None if not found
        """
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return plugin.metadata
        return None

    def list_plugins(self) -> List[Dict[str, any]]:
        """
        List all plugins with their status.

        Returns:
            List of plugin information dictionaries

        Example:
            >>> plugins = manager.list_plugins()
            >>> for info in plugins:
            ...     print(f"{info['name']}: {info['status']}")
        """
        result = []

        for name, state in self._plugins.items():
            metadata = state.plugin.metadata

            info = {
                "name": metadata.name,
                "version": metadata.version,
                "author": metadata.author,
                "description": metadata.description,
                "dependencies": metadata.dependencies,
                "initialized": state.initialized,
                "enabled": state.enabled,
                "error": state.error,
                "status": self._get_plugin_status(state)
            }

            result.append(info)

        return result

    def _get_plugin_status(self, state: PluginState) -> str:
        """
        Get human-readable plugin status.

        Args:
            state: Plugin state

        Returns:
            Status string
        """
        if state.error:
            return f"Error: {state.error}"
        elif state.enabled:
            return "Enabled"
        elif state.initialized:
            return "Initialized"
        else:
            return "Loaded"

    # Hook execution methods

    def on_file_selected(self, file_path: str) -> None:
        """
        Dispatch file selected hook to all enabled plugins.

        Args:
            file_path: Path to selected file
        """
        for name, state in self._plugins.items():
            if state.enabled:
                try:
                    state.plugin.on_file_selected(file_path)
                except Exception as e:
                    logger.error(
                        f"Error in plugin {name} on_file_selected hook: {e}"
                    )

    def on_directory_changed(self, directory_path: str) -> None:
        """
        Dispatch directory changed hook to all enabled plugins.

        Args:
            directory_path: Path to new directory
        """
        for name, state in self._plugins.items():
            if state.enabled:
                try:
                    state.plugin.on_directory_changed(directory_path)
                except Exception as e:
                    logger.error(
                        f"Error in plugin {name} on_directory_changed hook: {e}"
                    )

    def get_menu_items(self) -> Dict[str, Dict[str, str]]:
        """
        Get all menu items from plugins.

        Returns:
            Dictionary of menu items organized by category
        """
        return self.action_registry.get_menu_items()

    def execute_action(self, action_name: str, *args, **kwargs) -> bool:
        """
        Execute a plugin action by name.

        Args:
            action_name: Name of action to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            True if action executed successfully, False otherwise
        """
        return self.action_registry.execute_action(action_name, *args, **kwargs)
