"""
Plugin Loader for DC Commander

Discovers, validates, and loads plugins from the plugins directory.
Provides security validation and dependency resolution.
"""

import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Type

from src.plugins.plugin_interface import PluginInterface, PluginMetadata

logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """Exception raised when plugin loading fails."""
    pass


class PluginLoader:
    """
    Plugin discovery and loading system.

    Scans the plugins directory for valid plugin modules,
    validates them for security, and instantiates plugin classes.
    """

    # Security: Disallowed imports for plugin sandbox
    DISALLOWED_IMPORTS = {
        "subprocess", "os", "sys", "importlib", "__import__",
        "eval", "exec", "compile", "open"
    }

    # Security: Maximum plugin file size (1MB)
    MAX_PLUGIN_SIZE = 1024 * 1024

    def __init__(self, plugins_dir: Path):
        """
        Initialize plugin loader.

        Args:
            plugins_dir: Directory containing plugin files
        """
        self.plugins_dir = plugins_dir
        self._loaded_modules: Dict[str, object] = {}

    def discover_plugins(self) -> List[Path]:
        """
        Discover plugin files in plugins directory.

        Returns:
            List of plugin file paths

        Example:
            >>> loader = PluginLoader(Path("plugins"))
            >>> plugins = loader.discover_plugins()
            >>> print(f"Found {len(plugins)} plugins")
        """
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory does not exist: {self.plugins_dir}")
            return []

        plugin_files = []

        for file_path in self.plugins_dir.glob("*.py"):
            # Skip __init__.py and hidden files
            if file_path.name.startswith("_") or file_path.name.startswith("."):
                continue

            # Security: Check file size
            if file_path.stat().st_size > self.MAX_PLUGIN_SIZE:
                logger.warning(
                    f"Plugin file too large (>{self.MAX_PLUGIN_SIZE} bytes): {file_path.name}"
                )
                continue

            plugin_files.append(file_path)

        logger.info(f"Discovered {len(plugin_files)} plugin(s)")
        return plugin_files

    def validate_plugin_security(self, file_path: Path) -> bool:
        """
        Validate plugin for security concerns.

        Performs static analysis to detect dangerous imports and patterns.

        Args:
            file_path: Path to plugin file

        Returns:
            True if plugin passes security validation, False otherwise

        Security checks:
        - No dangerous imports (subprocess, os, eval, etc.)
        - No dynamic code execution patterns
        - File size within limits
        """
        try:
            # Read plugin source code
            source_code = file_path.read_text(encoding="utf-8")

            # Check for disallowed imports
            for disallowed in self.DISALLOWED_IMPORTS:
                # Check both "import x" and "from x import"
                if f"import {disallowed}" in source_code:
                    logger.error(
                        f"Security: Plugin '{file_path.name}' contains "
                        f"disallowed import: {disallowed}"
                    )
                    return False

            # Check for dangerous patterns
            dangerous_patterns = [
                "eval(", "exec(", "compile(", "__import__(",
                "globals()", "locals()", "vars("
            ]

            for pattern in dangerous_patterns:
                if pattern in source_code:
                    logger.error(
                        f"Security: Plugin '{file_path.name}' contains "
                        f"dangerous pattern: {pattern}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Security validation failed for {file_path.name}: {e}")
            return False

    def load_plugin_module(self, file_path: Path) -> Optional[object]:
        """
        Load plugin module from file.

        Args:
            file_path: Path to plugin file

        Returns:
            Loaded module object or None on failure

        Raises:
            PluginLoadError: If module loading fails
        """
        try:
            # Create module name from filename
            module_name = f"plugins.{file_path.stem}"

            # Check if already loaded
            if module_name in self._loaded_modules:
                return self._loaded_modules[module_name]

            # Load module spec
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                raise PluginLoadError(f"Failed to load spec for {file_path.name}")

            # Create module
            module = importlib.util.module_from_spec(spec)

            # Add to sys.modules before execution
            sys.modules[module_name] = module

            # Execute module
            spec.loader.exec_module(module)

            # Cache loaded module
            self._loaded_modules[module_name] = module

            logger.info(f"Loaded plugin module: {module_name}")
            return module

        except Exception as e:
            logger.error(f"Failed to load plugin module {file_path.name}: {e}")
            raise PluginLoadError(f"Module load failed: {e}") from e

    def find_plugin_class(self, module: object) -> Optional[Type[PluginInterface]]:
        """
        Find PluginInterface subclass in module.

        Args:
            module: Loaded plugin module

        Returns:
            Plugin class or None if not found
        """
        for name, obj in inspect.getmembers(module):
            # Skip imported classes and private members
            if name.startswith("_"):
                continue

            # Check if class
            if not inspect.isclass(obj):
                continue

            # Check if PluginInterface subclass (but not PluginInterface itself)
            if (issubclass(obj, PluginInterface) and
                obj is not PluginInterface):
                logger.info(f"Found plugin class: {name}")
                return obj

        return None

    def instantiate_plugin(self, plugin_class: Type[PluginInterface]) -> Optional[PluginInterface]:
        """
        Create plugin instance and validate metadata.

        Args:
            plugin_class: Plugin class to instantiate

        Returns:
            Plugin instance or None on failure

        Raises:
            PluginLoadError: If instantiation fails
        """
        try:
            # Create instance
            plugin = plugin_class()

            # Validate metadata
            metadata = plugin.metadata

            if not isinstance(metadata, PluginMetadata):
                raise PluginLoadError("Invalid metadata type")

            # Validate required metadata fields
            if not metadata.name:
                raise PluginLoadError("Plugin name is required")

            if not metadata.version:
                raise PluginLoadError("Plugin version is required")

            logger.info(
                f"Instantiated plugin: {metadata.name} v{metadata.version} "
                f"by {metadata.author}"
            )

            return plugin

        except Exception as e:
            logger.error(f"Failed to instantiate plugin: {e}")
            raise PluginLoadError(f"Instantiation failed: {e}") from e

    def load_plugin(self, file_path: Path) -> Optional[PluginInterface]:
        """
        Load and validate a single plugin.

        Complete plugin loading pipeline:
        1. Security validation
        2. Module loading
        3. Plugin class discovery
        4. Plugin instantiation

        Args:
            file_path: Path to plugin file

        Returns:
            Loaded plugin instance or None on failure

        Example:
            >>> loader = PluginLoader(Path("plugins"))
            >>> plugin = loader.load_plugin(Path("plugins/my_plugin.py"))
            >>> if plugin:
            ...     print(f"Loaded: {plugin.metadata.name}")
        """
        try:
            # 1. Security validation
            if not self.validate_plugin_security(file_path):
                logger.error(f"Plugin failed security validation: {file_path.name}")
                return None

            # 2. Load module
            module = self.load_plugin_module(file_path)
            if not module:
                return None

            # 3. Find plugin class
            plugin_class = self.find_plugin_class(module)
            if not plugin_class:
                logger.error(f"No PluginInterface subclass found in {file_path.name}")
                return None

            # 4. Instantiate plugin
            plugin = self.instantiate_plugin(plugin_class)

            return plugin

        except PluginLoadError as e:
            logger.error(f"Plugin load error for {file_path.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading {file_path.name}: {e}")
            return None

    def load_all_plugins(self) -> Dict[str, PluginInterface]:
        """
        Discover and load all plugins from plugins directory.

        Returns:
            Dictionary mapping plugin names to plugin instances

        Example:
            >>> loader = PluginLoader(Path("plugins"))
            >>> plugins = loader.load_all_plugins()
            >>> print(f"Loaded {len(plugins)} plugins")
        """
        plugins: Dict[str, PluginInterface] = {}

        # Discover plugin files
        plugin_files = self.discover_plugins()

        # Load each plugin
        for file_path in plugin_files:
            plugin = self.load_plugin(file_path)

            if plugin:
                # Check for name conflicts
                if plugin.metadata.name in plugins:
                    logger.error(
                        f"Plugin name conflict: {plugin.metadata.name} "
                        f"in {file_path.name}"
                    )
                    continue

                plugins[plugin.metadata.name] = plugin

        logger.info(f"Successfully loaded {len(plugins)} plugin(s)")
        return plugins

    def validate_dependencies(
        self,
        plugins: Dict[str, PluginInterface]
    ) -> List[str]:
        """
        Validate plugin dependencies are satisfied.

        Args:
            plugins: Dictionary of loaded plugins

        Returns:
            List of plugin names with missing dependencies

        Example:
            >>> plugins = loader.load_all_plugins()
            >>> missing = loader.validate_dependencies(plugins)
            >>> if missing:
            ...     print(f"Plugins with missing deps: {missing}")
        """
        missing_deps = []

        for plugin_name, plugin in plugins.items():
            # Check each dependency
            for dep in plugin.metadata.dependencies:
                if dep not in plugins:
                    logger.error(
                        f"Plugin '{plugin_name}' depends on missing plugin: '{dep}'"
                    )
                    missing_deps.append(plugin_name)
                    break

        return missing_deps

    def get_dependency_order(
        self,
        plugins: Dict[str, PluginInterface]
    ) -> List[str]:
        """
        Calculate plugin load order based on dependencies.

        Uses topological sort to ensure dependencies load before dependents.
        Returns list where dependencies appear before plugins that depend on them.

        Args:
            plugins: Dictionary of loaded plugins

        Returns:
            List of plugin names in load order (dependencies first)

        Raises:
            PluginLoadError: If circular dependencies detected

        Example:
            If plugin2 depends on plugin1, returns ['plugin1', 'plugin2']
        """
        # Build dependency graph: name -> set of dependencies
        graph: Dict[str, Set[str]] = {}

        for name, plugin in plugins.items():
            graph[name] = set(plugin.metadata.dependencies)

        # Track processed plugins
        result = []
        processing = set()  # Currently being processed (for cycle detection)
        visited = set()     # Completely processed

        def visit(name: str):
            """Visit a plugin and its dependencies recursively."""
            if name in visited:
                return  # Already processed

            if name in processing:
                raise PluginLoadError("Circular dependencies detected")

            processing.add(name)

            # Visit all dependencies first
            for dep in graph[name]:
                if dep in graph:  # Only visit if dependency exists
                    visit(dep)

            processing.remove(name)
            visited.add(name)
            result.append(name)

        # Visit all plugins
        for name in plugins:
            if name not in visited:
                visit(name)

        return result
