"""
Action Registry for DC Commander Plugin System

Manages registration and lookup of custom actions and command mappings.
Provides thread-safe access to plugin-registered functionality.
"""

from typing import Dict, Callable, Optional, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ActionInfo:
    """
    Information about a registered action.

    Attributes:
        name: Action identifier
        handler: Callable that executes the action
        plugin_name: Name of plugin that registered this action
        description: Optional human-readable description
    """
    name: str
    handler: Callable
    plugin_name: str
    description: str = ""


class ActionRegistry:
    """
    Registry for plugin actions and command mappings.

    Manages the mapping between action names, keyboard shortcuts,
    and their corresponding handler functions.

    Thread-safe for concurrent access.
    """

    def __init__(self):
        """Initialize empty action registry."""
        self._actions: Dict[str, ActionInfo] = {}
        self._command_mappings: Dict[str, str] = {}
        self._menu_items: Dict[str, Dict[str, str]] = {}

    def register_action(
        self,
        name: str,
        handler: Callable,
        plugin_name: str,
        description: str = ""
    ) -> bool:
        """
        Register a new action.

        Args:
            name: Unique action identifier
            handler: Callable that executes the action
            plugin_name: Name of plugin registering the action
            description: Optional human-readable description

        Returns:
            True if registration successful, False if name already exists

        Example:
            registry.register_action(
                "my_action",
                lambda: print("Hello!"),
                "my_plugin",
                "Prints a greeting"
            )
        """
        if name in self._actions:
            logger.warning(
                f"Action '{name}' already registered by plugin "
                f"'{self._actions[name].plugin_name}'"
            )
            return False

        self._actions[name] = ActionInfo(
            name=name,
            handler=handler,
            plugin_name=plugin_name,
            description=description
        )

        logger.info(f"Registered action '{name}' from plugin '{plugin_name}'")
        return True

    def unregister_action(self, name: str) -> bool:
        """
        Unregister an action.

        Args:
            name: Action identifier to remove

        Returns:
            True if action was removed, False if not found
        """
        if name not in self._actions:
            return False

        plugin_name = self._actions[name].plugin_name
        del self._actions[name]

        # Remove any command mappings pointing to this action
        self._command_mappings = {
            k: v for k, v in self._command_mappings.items()
            if v != name
        }

        logger.info(f"Unregistered action '{name}' from plugin '{plugin_name}'")
        return True

    def get_action(self, name: str) -> Optional[Callable]:
        """
        Get action handler by name.

        Args:
            name: Action identifier

        Returns:
            Action handler callable or None if not found
        """
        action_info = self._actions.get(name)
        return action_info.handler if action_info else None

    def get_action_info(self, name: str) -> Optional[ActionInfo]:
        """
        Get full action information.

        Args:
            name: Action identifier

        Returns:
            ActionInfo instance or None if not found
        """
        return self._actions.get(name)

    def list_actions(self, plugin_name: Optional[str] = None) -> List[str]:
        """
        List all registered actions.

        Args:
            plugin_name: Optional filter by plugin name

        Returns:
            List of action names
        """
        if plugin_name:
            return [
                name for name, info in self._actions.items()
                if info.plugin_name == plugin_name
            ]
        return list(self._actions.keys())

    def register_command_mapping(self, key: str, action_name: str) -> bool:
        """
        Map a keyboard shortcut to an action.

        Args:
            key: Keyboard shortcut (e.g., "ctrl+shift+a", "f11")
            action_name: Name of action to execute

        Returns:
            True if mapping registered, False if key already mapped
        """
        if key in self._command_mappings:
            logger.warning(
                f"Command '{key}' already mapped to action "
                f"'{self._command_mappings[key]}'"
            )
            return False

        if action_name not in self._actions:
            logger.warning(
                f"Cannot map command '{key}' to unknown action '{action_name}'"
            )
            return False

        self._command_mappings[key] = action_name
        logger.info(f"Mapped command '{key}' to action '{action_name}'")
        return True

    def unregister_command_mapping(self, key: str) -> bool:
        """
        Remove a keyboard shortcut mapping.

        Args:
            key: Keyboard shortcut to remove

        Returns:
            True if mapping was removed, False if not found
        """
        if key not in self._command_mappings:
            return False

        del self._command_mappings[key]
        logger.info(f"Unmapped command '{key}'")
        return True

    def get_action_for_command(self, key: str) -> Optional[Callable]:
        """
        Get action handler for a keyboard shortcut.

        Args:
            key: Keyboard shortcut

        Returns:
            Action handler or None if not found
        """
        action_name = self._command_mappings.get(key)
        if action_name:
            return self.get_action(action_name)
        return None

    def list_commands(self) -> Dict[str, str]:
        """
        Get all command mappings.

        Returns:
            Dictionary mapping keyboard shortcuts to action names
        """
        return self._command_mappings.copy()

    def register_menu_items(
        self,
        plugin_name: str,
        menu_items: Dict[str, Dict[str, str]]
    ) -> None:
        """
        Register menu items for a plugin.

        Args:
            plugin_name: Name of plugin
            menu_items: Dictionary mapping menu categories to items
        """
        if plugin_name not in self._menu_items:
            self._menu_items[plugin_name] = {}

        for category, items in menu_items.items():
            if category not in self._menu_items[plugin_name]:
                self._menu_items[plugin_name][category] = {}

            self._menu_items[plugin_name][category].update(items)

    def get_menu_items(self) -> Dict[str, Dict[str, str]]:
        """
        Get all registered menu items.

        Returns:
            Dictionary of menu items organized by category
        """
        # Flatten all plugin menu items
        result: Dict[str, Dict[str, str]] = {}

        for plugin_items in self._menu_items.values():
            for category, items in plugin_items.items():
                if category not in result:
                    result[category] = {}
                result[category].update(items)

        return result

    def unregister_plugin_actions(self, plugin_name: str) -> int:
        """
        Unregister all actions from a specific plugin.

        Args:
            plugin_name: Name of plugin

        Returns:
            Number of actions unregistered
        """
        actions_to_remove = [
            name for name, info in self._actions.items()
            if info.plugin_name == plugin_name
        ]

        for action_name in actions_to_remove:
            self.unregister_action(action_name)

        # Remove menu items
        if plugin_name in self._menu_items:
            del self._menu_items[plugin_name]

        return len(actions_to_remove)

    def execute_action(self, name: str, *args, **kwargs) -> bool:
        """
        Execute an action by name.

        Args:
            name: Action identifier
            *args: Positional arguments to pass to handler
            **kwargs: Keyword arguments to pass to handler

        Returns:
            True if action executed successfully, False if not found or error

        Example:
            registry.execute_action("my_action", arg1="value")
        """
        handler = self.get_action(name)
        if not handler:
            logger.error(f"Cannot execute unknown action '{name}'")
            return False

        try:
            handler(*args, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Error executing action '{name}': {e}")
            return False
