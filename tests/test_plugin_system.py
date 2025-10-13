"""
Comprehensive Test Suite for Plugin System

Tests plugin loading, lifecycle, security, and integration.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile
import shutil

from src.plugins.plugin_interface import PluginInterface, PluginMetadata
from src.plugins.action_registry import ActionRegistry, ActionInfo
from src.plugins.plugin_loader import PluginLoader, PluginLoadError
from src.plugins.plugin_manager import PluginManager, PluginState


# Test fixtures

@pytest.fixture
def temp_plugins_dir():
    """Create temporary plugins directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def action_registry():
    """Create action registry instance."""
    return ActionRegistry()


@pytest.fixture
def plugin_loader(temp_plugins_dir):
    """Create plugin loader instance."""
    return PluginLoader(temp_plugins_dir)


@pytest.fixture
def plugin_manager(temp_plugins_dir, action_registry):
    """Create plugin manager instance."""
    return PluginManager(temp_plugins_dir, action_registry)


@pytest.fixture
def mock_app():
    """Create mock application instance."""
    app = Mock()
    app.notify = Mock()
    app._get_active_panel = Mock()
    return app


# Helper to create test plugin file

def create_test_plugin(
    plugins_dir: Path,
    filename: str,
    plugin_code: str
) -> Path:
    """
    Create a test plugin file.

    Args:
        plugins_dir: Plugins directory
        filename: Plugin filename
        plugin_code: Python code for plugin

    Returns:
        Path to created plugin file
    """
    plugin_file = plugins_dir / filename
    plugin_file.write_text(plugin_code, encoding="utf-8")
    return plugin_file


# Test PluginMetadata

class TestPluginMetadata:
    """Test plugin metadata class."""

    def test_metadata_creation_success(self):
        """Test creating valid metadata."""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test Author",
            description="Test plugin"
        )

        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test Author"
        assert metadata.description == "Test plugin"
        assert metadata.dependencies == []
        assert metadata.min_app_version == "1.0.0"

    def test_metadata_with_dependencies(self):
        """Test metadata with dependencies."""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test",
            description="Test",
            dependencies=["dep1", "dep2"]
        )

        assert metadata.dependencies == ["dep1", "dep2"]

    def test_metadata_invalid_name_empty(self):
        """Test metadata validation for empty name."""
        with pytest.raises(ValueError, match="Plugin name must be non-empty"):
            PluginMetadata(
                name="",
                version="1.0.0",
                author="Test",
                description="Test"
            )

    def test_metadata_invalid_name_spaces(self):
        """Test metadata validation for name with spaces."""
        with pytest.raises(ValueError, match="contain no spaces"):
            PluginMetadata(
                name="test plugin",
                version="1.0.0",
                author="Test",
                description="Test"
            )

    def test_metadata_invalid_version(self):
        """Test metadata validation for empty version."""
        with pytest.raises(ValueError, match="version is required"):
            PluginMetadata(
                name="test_plugin",
                version="",
                author="Test",
                description="Test"
            )


# Test ActionRegistry

class TestActionRegistry:
    """Test action registry class."""

    def test_register_action_success(self, action_registry):
        """Test registering an action."""
        handler = Mock()

        result = action_registry.register_action(
            "test_action",
            handler,
            "test_plugin",
            "Test action"
        )

        assert result is True
        assert "test_action" in action_registry._actions
        assert action_registry.get_action("test_action") == handler

    def test_register_action_duplicate(self, action_registry):
        """Test registering duplicate action fails."""
        handler1 = Mock()
        handler2 = Mock()

        action_registry.register_action("test_action", handler1, "plugin1")
        result = action_registry.register_action("test_action", handler2, "plugin2")

        assert result is False
        assert action_registry.get_action("test_action") == handler1

    def test_unregister_action(self, action_registry):
        """Test unregistering an action."""
        handler = Mock()

        action_registry.register_action("test_action", handler, "test_plugin")
        result = action_registry.unregister_action("test_action")

        assert result is True
        assert action_registry.get_action("test_action") is None

    def test_unregister_nonexistent_action(self, action_registry):
        """Test unregistering nonexistent action."""
        result = action_registry.unregister_action("nonexistent")
        assert result is False

    def test_get_action_info(self, action_registry):
        """Test getting action information."""
        handler = Mock()

        action_registry.register_action(
            "test_action",
            handler,
            "test_plugin",
            "Test description"
        )

        info = action_registry.get_action_info("test_action")

        assert info is not None
        assert info.name == "test_action"
        assert info.handler == handler
        assert info.plugin_name == "test_plugin"
        assert info.description == "Test description"

    def test_list_actions(self, action_registry):
        """Test listing all actions."""
        action_registry.register_action("action1", Mock(), "plugin1")
        action_registry.register_action("action2", Mock(), "plugin2")
        action_registry.register_action("action3", Mock(), "plugin1")

        all_actions = action_registry.list_actions()
        assert len(all_actions) == 3
        assert set(all_actions) == {"action1", "action2", "action3"}

    def test_list_actions_by_plugin(self, action_registry):
        """Test listing actions filtered by plugin."""
        action_registry.register_action("action1", Mock(), "plugin1")
        action_registry.register_action("action2", Mock(), "plugin2")
        action_registry.register_action("action3", Mock(), "plugin1")

        plugin1_actions = action_registry.list_actions("plugin1")
        assert len(plugin1_actions) == 2
        assert set(plugin1_actions) == {"action1", "action3"}

    def test_register_command_mapping(self, action_registry):
        """Test registering command mapping."""
        handler = Mock()

        action_registry.register_action("test_action", handler, "test_plugin")
        result = action_registry.register_command_mapping("ctrl+x", "test_action")

        assert result is True
        assert action_registry.get_action_for_command("ctrl+x") == handler

    def test_register_command_mapping_duplicate(self, action_registry):
        """Test registering duplicate command mapping fails."""
        action_registry.register_action("action1", Mock(), "plugin1")
        action_registry.register_action("action2", Mock(), "plugin2")

        action_registry.register_command_mapping("ctrl+x", "action1")
        result = action_registry.register_command_mapping("ctrl+x", "action2")

        assert result is False

    def test_register_command_mapping_unknown_action(self, action_registry):
        """Test registering command for unknown action fails."""
        result = action_registry.register_command_mapping("ctrl+x", "unknown_action")
        assert result is False

    def test_unregister_command_mapping(self, action_registry):
        """Test unregistering command mapping."""
        action_registry.register_action("test_action", Mock(), "test_plugin")
        action_registry.register_command_mapping("ctrl+x", "test_action")

        result = action_registry.unregister_command_mapping("ctrl+x")

        assert result is True
        assert action_registry.get_action_for_command("ctrl+x") is None

    def test_register_menu_items(self, action_registry):
        """Test registering menu items."""
        menu_items = {
            "File": {
                "Action 1": "action1",
                "Action 2": "action2"
            }
        }

        action_registry.register_menu_items("test_plugin", menu_items)

        all_items = action_registry.get_menu_items()
        assert "File" in all_items
        assert all_items["File"]["Action 1"] == "action1"
        assert all_items["File"]["Action 2"] == "action2"

    def test_unregister_plugin_actions(self, action_registry):
        """Test unregistering all actions from a plugin."""
        action_registry.register_action("action1", Mock(), "plugin1")
        action_registry.register_action("action2", Mock(), "plugin1")
        action_registry.register_action("action3", Mock(), "plugin2")

        count = action_registry.unregister_plugin_actions("plugin1")

        assert count == 2
        assert action_registry.get_action("action1") is None
        assert action_registry.get_action("action2") is None
        assert action_registry.get_action("action3") is not None

    def test_execute_action_success(self, action_registry):
        """Test executing an action."""
        handler = Mock()
        action_registry.register_action("test_action", handler, "test_plugin")

        result = action_registry.execute_action("test_action", "arg1", key="value")

        assert result is True
        handler.assert_called_once_with("arg1", key="value")

    def test_execute_action_not_found(self, action_registry):
        """Test executing nonexistent action."""
        result = action_registry.execute_action("nonexistent")
        assert result is False

    def test_execute_action_handler_error(self, action_registry):
        """Test executing action that raises exception."""
        handler = Mock(side_effect=Exception("Handler error"))
        action_registry.register_action("test_action", handler, "test_plugin")

        result = action_registry.execute_action("test_action")

        assert result is False


# Test PluginLoader

class TestPluginLoader:
    """Test plugin loader class."""

    def test_discover_plugins_empty_dir(self, plugin_loader):
        """Test discovering plugins in empty directory."""
        plugins = plugin_loader.discover_plugins()
        assert plugins == []

    def test_discover_plugins_with_files(self, temp_plugins_dir, plugin_loader):
        """Test discovering plugin files."""
        create_test_plugin(temp_plugins_dir, "plugin1.py", "# Test plugin 1")
        create_test_plugin(temp_plugins_dir, "plugin2.py", "# Test plugin 2")
        create_test_plugin(temp_plugins_dir, "_hidden.py", "# Hidden")
        create_test_plugin(temp_plugins_dir, "__init__.py", "# Init")

        plugins = plugin_loader.discover_plugins()

        assert len(plugins) == 2
        assert any(p.name == "plugin1.py" for p in plugins)
        assert any(p.name == "plugin2.py" for p in plugins)

    def test_discover_plugins_skip_large_files(self, temp_plugins_dir, plugin_loader):
        """Test skipping files larger than MAX_PLUGIN_SIZE."""
        # Create large file
        large_file = temp_plugins_dir / "large.py"
        large_file.write_bytes(b"x" * (plugin_loader.MAX_PLUGIN_SIZE + 1))

        plugins = plugin_loader.discover_plugins()
        assert len(plugins) == 0

    def test_validate_plugin_security_safe_plugin(self, temp_plugins_dir, plugin_loader):
        """Test security validation for safe plugin."""
        safe_code = """
from src.plugins.plugin_interface import PluginInterface, PluginMetadata

class TestPlugin(PluginInterface):
    @property
    def metadata(self):
        return PluginMetadata(name="test", version="1.0", author="test", description="test")

    def initialize(self, app):
        pass

    def shutdown(self):
        pass
"""
        plugin_file = create_test_plugin(temp_plugins_dir, "safe.py", safe_code)

        result = plugin_loader.validate_plugin_security(plugin_file)
        assert result is True

    def test_validate_plugin_security_dangerous_import(self, temp_plugins_dir, plugin_loader):
        """Test security validation rejects dangerous imports."""
        dangerous_code = """
import subprocess
class BadPlugin:
    pass
"""
        plugin_file = create_test_plugin(temp_plugins_dir, "bad.py", dangerous_code)

        result = plugin_loader.validate_plugin_security(plugin_file)
        assert result is False

    def test_validate_plugin_security_eval_pattern(self, temp_plugins_dir, plugin_loader):
        """Test security validation rejects eval pattern."""
        dangerous_code = """
class BadPlugin:
    def do_something(self):
        eval("malicious code")
"""
        plugin_file = create_test_plugin(temp_plugins_dir, "bad.py", dangerous_code)

        result = plugin_loader.validate_plugin_security(plugin_file)
        assert result is False

    def test_load_plugin_module_success(self, temp_plugins_dir, plugin_loader):
        """Test loading valid plugin module."""
        code = """
test_value = "loaded"
"""
        plugin_file = create_test_plugin(temp_plugins_dir, "test.py", code)

        module = plugin_loader.load_plugin_module(plugin_file)

        assert module is not None
        assert hasattr(module, 'test_value')
        assert module.test_value == "loaded"

    def test_load_plugin_module_cached(self, temp_plugins_dir, plugin_loader):
        """Test plugin module is cached after first load."""
        code = "test_value = 42"
        plugin_file = create_test_plugin(temp_plugins_dir, "test.py", code)

        module1 = plugin_loader.load_plugin_module(plugin_file)
        module2 = plugin_loader.load_plugin_module(plugin_file)

        assert module1 is module2

    def test_find_plugin_class_success(self, plugin_loader):
        """Test finding plugin class in module."""
        # Create mock module
        module = Mock()

        class TestPlugin(PluginInterface):
            @property
            def metadata(self):
                return PluginMetadata(name="test", version="1.0", author="test", description="test")

            def initialize(self, app):
                pass

            def shutdown(self):
                pass

        # Add class to module
        module.TestPlugin = TestPlugin

        # Mock inspect.getmembers
        with patch('inspect.getmembers', return_value=[("TestPlugin", TestPlugin)]):
            plugin_class = plugin_loader.find_plugin_class(module)

        assert plugin_class == TestPlugin

    def test_find_plugin_class_not_found(self, plugin_loader):
        """Test finding plugin class when none exists."""
        module = Mock()

        with patch('inspect.getmembers', return_value=[]):
            plugin_class = plugin_loader.find_plugin_class(module)

        assert plugin_class is None

    def test_validate_dependencies_satisfied(self, plugin_loader):
        """Test dependency validation when all satisfied."""
        # Create mock plugins
        class Plugin1(PluginInterface):
            @property
            def metadata(self):
                return PluginMetadata(name="plugin1", version="1.0", author="test", description="test")

            def initialize(self, app):
                pass

            def shutdown(self):
                pass

        class Plugin2(PluginInterface):
            @property
            def metadata(self):
                return PluginMetadata(
                    name="plugin2",
                    version="1.0",
                    author="test",
                    description="test",
                    dependencies=["plugin1"]
                )

            def initialize(self, app):
                pass

            def shutdown(self):
                pass

        plugins = {
            "plugin1": Plugin1(),
            "plugin2": Plugin2()
        }

        missing = plugin_loader.validate_dependencies(plugins)
        assert missing == []

    def test_validate_dependencies_missing(self, plugin_loader):
        """Test dependency validation when dependencies missing."""
        class Plugin1(PluginInterface):
            @property
            def metadata(self):
                return PluginMetadata(
                    name="plugin1",
                    version="1.0",
                    author="test",
                    description="test",
                    dependencies=["nonexistent"]
                )

            def initialize(self, app):
                pass

            def shutdown(self):
                pass

        plugins = {"plugin1": Plugin1()}

        missing = plugin_loader.validate_dependencies(plugins)
        assert "plugin1" in missing

    def test_get_dependency_order_simple(self, plugin_loader):
        """Test dependency order calculation."""
        class Plugin1(PluginInterface):
            @property
            def metadata(self):
                return PluginMetadata(name="plugin1", version="1.0", author="test", description="test")

            def initialize(self, app):
                pass

            def shutdown(self):
                pass

        class Plugin2(PluginInterface):
            @property
            def metadata(self):
                return PluginMetadata(
                    name="plugin2",
                    version="1.0",
                    author="test",
                    description="test",
                    dependencies=["plugin1"]
                )

            def initialize(self, app):
                pass

            def shutdown(self):
                pass

        plugins = {
            "plugin1": Plugin1(),
            "plugin2": Plugin2()
        }

        order = plugin_loader.get_dependency_order(plugins)
        assert order.index("plugin1") < order.index("plugin2")


# Test PluginManager

class TestPluginManager:
    """Test plugin manager class."""

    def test_set_app(self, plugin_manager, mock_app):
        """Test setting app reference."""
        plugin_manager.set_app(mock_app)
        assert plugin_manager._app == mock_app

    def test_initialize_plugin_without_app(self, plugin_manager):
        """Test initializing plugin without app reference fails."""
        count = plugin_manager.initialize_all_plugins()
        assert count == 0

    def test_get_plugin(self, plugin_manager):
        """Test getting plugin by name."""
        class TestPlugin(PluginInterface):
            @property
            def metadata(self):
                return PluginMetadata(name="test", version="1.0", author="test", description="test")

            def initialize(self, app):
                pass

            def shutdown(self):
                pass

        plugin = TestPlugin()
        plugin_manager._plugins["test"] = PluginState(plugin)

        retrieved = plugin_manager.get_plugin("test")
        assert retrieved == plugin

    def test_get_plugin_not_found(self, plugin_manager):
        """Test getting nonexistent plugin."""
        plugin = plugin_manager.get_plugin("nonexistent")
        assert plugin is None

    def test_get_plugin_metadata(self, plugin_manager):
        """Test getting plugin metadata."""
        class TestPlugin(PluginInterface):
            @property
            def metadata(self):
                return PluginMetadata(name="test", version="1.0.0", author="test", description="test")

            def initialize(self, app):
                pass

            def shutdown(self):
                pass

        plugin = TestPlugin()
        plugin_manager._plugins["test"] = PluginState(plugin)

        metadata = plugin_manager.get_plugin_metadata("test")
        assert metadata is not None
        assert metadata.name == "test"
        assert metadata.version == "1.0.0"

    def test_list_plugins(self, plugin_manager):
        """Test listing plugins with status."""
        class TestPlugin(PluginInterface):
            @property
            def metadata(self):
                return PluginMetadata(
                    name="test",
                    version="1.0.0",
                    author="Test Author",
                    description="Test Description"
                )

            def initialize(self, app):
                pass

            def shutdown(self):
                pass

        plugin = TestPlugin()
        state = PluginState(plugin)
        state.initialized = True
        state.enabled = True

        plugin_manager._plugins["test"] = state

        plugins = plugin_manager.list_plugins()

        assert len(plugins) == 1
        assert plugins[0]["name"] == "test"
        assert plugins[0]["version"] == "1.0.0"
        assert plugins[0]["author"] == "Test Author"
        assert plugins[0]["initialized"] is True
        assert plugins[0]["enabled"] is True


# Integration tests

class TestPluginIntegration:
    """Integration tests for plugin system."""

    def test_full_plugin_lifecycle(self, temp_plugins_dir, mock_app):
        """Test complete plugin lifecycle from loading to shutdown."""
        # Create test plugin
        plugin_code = """
from src.plugins.plugin_interface import PluginInterface, PluginMetadata

class TestLifecyclePlugin(PluginInterface):
    def __init__(self):
        self.initialized = False
        self.shutdown_called = False

    @property
    def metadata(self):
        return PluginMetadata(
            name="lifecycle_test",
            version="1.0.0",
            author="Test",
            description="Lifecycle test plugin"
        )

    def initialize(self, app):
        self.initialized = True
        self.app = app

    def shutdown(self):
        self.shutdown_called = True

    def register_actions(self):
        return {"test_action": lambda: "executed"}
"""
        create_test_plugin(temp_plugins_dir, "lifecycle.py", plugin_code)

        # Create manager
        action_registry = ActionRegistry()
        manager = PluginManager(temp_plugins_dir, action_registry)
        manager.set_app(mock_app)

        # Load plugins
        plugins = manager.load_all_plugins()
        assert len(plugins) == 1

        # Initialize plugins
        count = manager.initialize_all_plugins()
        assert count == 1

        # Enable plugin
        result = manager.enable_plugin("lifecycle_test")
        assert result is True

        # Check action registered
        assert action_registry.get_action("test_action") is not None

        # Disable plugin
        result = manager.disable_plugin("lifecycle_test")
        assert result is True

        # Check action unregistered
        assert action_registry.get_action("test_action") is None

        # Shutdown plugin
        result = manager.shutdown_plugin("lifecycle_test")
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
