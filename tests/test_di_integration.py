"""
Dependency Injection Integration Tests

Demonstrates the benefits of DI:
1. Easy mocking of dependencies
2. Isolated unit testing
3. Flexible service implementations
4. Clear dependency graph
"""

import pytest
from unittest.mock import Mock, MagicMock, call
from pathlib import Path
from typing import Any, List, Optional

from src.di import (
    DependencyContainer,
    Lifecycle,
    IConfigManager,
    IThemeManager,
    IFileService,
    IAsyncFileService
)


# ============================================================================
# Mock Service Implementations
# ============================================================================

class MockConfigManager:
    """Mock config manager for testing."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._config = MagicMock()
        self._config.left_panel.start_path = "/mock/left"
        self._config.right_panel.start_path = "/mock/right"
        self._config.theme = "mock_theme"

    def load_config(self) -> Any:
        return self._config

    def save_config(self) -> bool:
        return True

    def get_config(self) -> Any:
        return self._config

    def update_left_panel_path(self, path: str) -> None:
        self._config.left_panel.start_path = path

    def update_right_panel_path(self, path: str) -> None:
        self._config.right_panel.start_path = path

    def update_theme(self, theme_name: str) -> None:
        self._config.theme = theme_name

    def update_config(self, section: str, key: str, value: Any) -> None:
        pass


class MockThemeManager:
    """Mock theme manager for testing."""

    def __init__(self):
        self.themes = ["norton_commander", "modern_dark", "solarized", "mock_theme"]
        self._current_theme_name = None
        self._current_theme_obj = None

    def get_available_themes(self) -> List[str]:
        return self.themes

    def load_theme(self, theme_name: str) -> Optional[Any]:
        if theme_name in self.themes:
            # Create simple object with name attribute
            theme_obj = type('Theme', (), {'name': theme_name})()
            return theme_obj
        return None

    def get_current_theme(self) -> Optional[Any]:
        return self._current_theme_obj

    def set_current_theme(self, theme_name: str) -> bool:
        if theme_name in self.themes:
            self._current_theme_name = theme_name
            # Create simple object with name attribute
            self._current_theme_obj = type('Theme', (), {'name': theme_name})()
            return True
        return False

    def get_next_theme_name(self, current_theme_name: str) -> str:
        try:
            idx = self.themes.index(current_theme_name)
            return self.themes[(idx + 1) % len(self.themes)]
        except ValueError:
            return self.themes[0]

    def generate_css(self, theme_name: Optional[str] = None) -> str:
        return f"/* Mock CSS for {theme_name} */"


# ============================================================================
# DI Container Tests
# ============================================================================

class TestDependencyContainer:
    """Test DI container basic functionality."""

    def test_singleton_registration(self):
        """Test singleton service registration."""
        container = DependencyContainer()

        # Register singleton
        container.register_singleton(IConfigManager, MockConfigManager)

        # Resolve twice - should return same instance
        instance1 = container.resolve(IConfigManager)
        instance2 = container.resolve(IConfigManager)

        assert instance1 is instance2

    def test_transient_registration(self):
        """Test transient service registration (new instance each time)."""
        container = DependencyContainer()

        # Register transient
        container.register_transient(IThemeManager, MockThemeManager)

        # Resolve twice - should return different instances
        instance1 = container.resolve(IThemeManager)
        instance2 = container.resolve(IThemeManager)

        assert instance1 is not instance2

    def test_instance_registration(self):
        """Test registering existing instance."""
        container = DependencyContainer()

        # Create instance
        config_manager = MockConfigManager()

        # Register instance
        container.register_instance(IConfigManager, config_manager)

        # Resolve - should return same instance
        resolved = container.resolve(IConfigManager)

        assert resolved is config_manager

    def test_factory_registration(self):
        """Test factory function for service creation."""
        container = DependencyContainer()

        # Register with factory
        container.register_singleton(
            IConfigManager,
            factory=lambda: MockConfigManager("/custom/path")
        )

        # Resolve
        config = container.resolve(IConfigManager)

        assert config.config_path == "/custom/path"

    def test_unregistered_service_raises_error(self):
        """Test that resolving unregistered service raises error."""
        container = DependencyContainer()

        with pytest.raises(ValueError, match="Service not registered"):
            container.resolve(IConfigManager)

    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        container = DependencyContainer()

        # Create circular dependency (A -> B -> A)
        # Note: These classes have type hints that will cause circular resolution
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            class ServiceB: pass

        class ServiceA:
            def __init__(self, service_b: 'ServiceB'):
                self.service_b = service_b

        class ServiceB:
            def __init__(self, service_a: ServiceA):
                self.service_a = service_a

        container.register_singleton(ServiceA, ServiceA)
        container.register_singleton(ServiceB, ServiceB)

        # Try to resolve - should detect circular dependency
        # Note: The actual error depends on DI container implementation
        # It might fail during resolution or during instantiation
        try:
            container.resolve(ServiceA)
            pytest.fail("Expected RuntimeError or TypeError for circular dependency")
        except (RuntimeError, TypeError) as e:
            # Expected - circular dependency detected
            assert True

    def test_clear_container(self):
        """Test clearing container."""
        container = DependencyContainer()

        # Register and resolve
        container.register_singleton(IConfigManager, MockConfigManager)
        instance1 = container.resolve(IConfigManager)

        # Clear container
        container.clear()

        # Should not be registered anymore
        with pytest.raises(ValueError):
            container.resolve(IConfigManager)


# ============================================================================
# Service Integration Tests
# ============================================================================

class TestServiceIntegration:
    """Test service integration with DI."""

    def test_config_manager_mock_injection(self):
        """Test injecting mock config manager."""
        # Create mock
        mock_config = Mock(spec=IConfigManager)
        mock_config.load_config.return_value = MagicMock()
        mock_config.get_config.return_value = MagicMock(theme="test_theme")

        # Register and resolve
        container = DependencyContainer()
        container.register_instance(IConfigManager, mock_config)

        resolved = container.resolve(IConfigManager)

        # Verify mock behavior
        config = resolved.get_config()
        assert config.theme == "test_theme"
        mock_config.get_config.assert_called_once()

    def test_theme_manager_integration(self):
        """Test theme manager with real-like behavior."""
        container = DependencyContainer()
        container.register_singleton(IThemeManager, MockThemeManager)

        theme_manager = container.resolve(IThemeManager)

        # Test functionality
        themes = theme_manager.get_available_themes()
        assert "norton_commander" in themes
        assert "modern_dark" in themes

        # Test theme switching
        success = theme_manager.set_current_theme("modern_dark")
        assert success is True

        current = theme_manager.get_current_theme()
        assert current is not None
        assert current.name == "modern_dark"

    def test_service_composition(self):
        """Test composing multiple services together."""
        container = DependencyContainer()

        # Register all services
        container.register_singleton(IConfigManager, MockConfigManager)
        container.register_singleton(IThemeManager, MockThemeManager)

        # Resolve services
        config = container.resolve(IConfigManager)
        themes = container.resolve(IThemeManager)

        # Test interaction
        config_data = config.get_config()
        current_theme = config_data.theme

        # Apply theme
        success = themes.set_current_theme(current_theme)
        assert success is True

        # Verify theme was applied
        applied_theme = themes.get_current_theme()
        assert applied_theme is not None
        assert applied_theme.name == current_theme

    def test_multiple_service_resolution(self):
        """Test resolving multiple services in sequence."""
        container = DependencyContainer()

        # Register services
        container.register_singleton(IConfigManager, MockConfigManager)
        container.register_singleton(IThemeManager, MockThemeManager)

        # Resolve in different order
        theme_manager1 = container.resolve(IThemeManager)
        config_manager1 = container.resolve(IConfigManager)
        theme_manager2 = container.resolve(IThemeManager)
        config_manager2 = container.resolve(IConfigManager)

        # Singletons should return same instances
        assert theme_manager1 is theme_manager2
        assert config_manager1 is config_manager2


# ============================================================================
# Testing Benefits Demonstration
# ============================================================================

class TestDIBenefits:
    """Demonstrate the benefits of DI for testing."""

    def test_isolated_unit_testing(self):
        """Show how DI enables true unit testing without real dependencies."""
        # Create completely isolated mock
        mock_config = Mock(spec=IConfigManager)
        mock_config.get_config.return_value = MagicMock(
            left_panel=MagicMock(start_path="/isolated/test"),
            theme="isolated_theme"
        )

        # No file system access, no real config files
        container = DependencyContainer()
        container.register_instance(IConfigManager, mock_config)

        # Test code that uses config
        config_manager = container.resolve(IConfigManager)
        config = config_manager.get_config()

        # Verify isolated behavior
        assert config.left_panel.start_path == "/isolated/test"
        assert config.theme == "isolated_theme"

        # Verify no side effects
        mock_config.get_config.assert_called_once()

    def test_flexible_implementation_swapping(self):
        """Show how DI allows swapping implementations without code changes."""
        container = DependencyContainer()

        # Initially use MockConfigManager
        container.register_singleton(IConfigManager, MockConfigManager)
        config1 = container.resolve(IConfigManager)
        theme1 = config1.get_config().theme

        assert theme1 == "mock_theme"

        # Create new container with different implementation
        container2 = DependencyContainer()

        # Create alternative implementation
        class AlternativeConfigManager(MockConfigManager):
            def __init__(self):
                super().__init__()
                self._config.theme = "alternative_theme"

        container2.register_singleton(IConfigManager, AlternativeConfigManager)
        config2 = container2.resolve(IConfigManager)
        theme2 = config2.get_config().theme

        assert theme2 == "alternative_theme"

    def test_dependency_tracking_for_debugging(self):
        """Show how DI makes dependency tracking explicit."""
        container = DependencyContainer()

        # Register services
        container.register_singleton(IConfigManager, MockConfigManager)
        container.register_singleton(IThemeManager, MockThemeManager)

        # Check what's registered
        assert container.is_registered(IConfigManager)
        assert container.is_registered(IThemeManager)
        assert not container.is_registered(IFileService)

        # Clear understanding of dependencies
        config = container.resolve(IConfigManager)
        themes = container.resolve(IThemeManager)

        assert config is not None
        assert themes is not None


# ============================================================================
# Integration Scenarios
# ============================================================================

class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_app_initialization_scenario(self):
        """Simulate application initialization with DI."""
        # Setup container
        container = DependencyContainer()

        # Register core services
        container.register_singleton(
            IConfigManager,
            factory=lambda: MockConfigManager("/app/config")
        )

        container.register_singleton(IThemeManager, MockThemeManager)

        # Simulate app initialization
        config_manager = container.resolve(IConfigManager)
        theme_manager = container.resolve(IThemeManager)

        # Load config
        config = config_manager.load_config()

        # Apply theme from config
        success = theme_manager.set_current_theme(config.theme)
        assert success is True

        # Verify initialization
        assert config_manager.config_path == "/app/config"

        # Verify theme was set
        current_theme = theme_manager.get_current_theme()
        assert current_theme is not None
        assert current_theme.name == config.theme

    def test_theme_switching_scenario(self):
        """Simulate theme switching workflow."""
        container = DependencyContainer()

        # Setup services
        container.register_singleton(IConfigManager, MockConfigManager)
        container.register_singleton(IThemeManager, MockThemeManager)

        # Resolve services
        config_manager = container.resolve(IConfigManager)
        theme_manager = container.resolve(IThemeManager)

        # Get available themes
        themes = theme_manager.get_available_themes()
        assert len(themes) > 0

        # Switch to next theme
        current = "norton_commander"
        next_theme = theme_manager.get_next_theme_name(current)

        # Apply theme
        success = theme_manager.set_current_theme(next_theme)
        assert success is True

        # Update config
        config_manager.update_theme(next_theme)

        # Verify
        config = config_manager.get_config()
        assert config.theme == next_theme

    def test_error_handling_scenario(self):
        """Test error handling with DI."""
        container = DependencyContainer()

        # Mock that raises error
        mock_config = Mock(spec=IConfigManager)
        mock_config.load_config.side_effect = IOError("Config file not found")

        container.register_instance(IConfigManager, mock_config)

        # Resolve and handle error
        config_manager = container.resolve(IConfigManager)

        with pytest.raises(IOError, match="Config file not found"):
            config_manager.load_config()

        # Verify error was from mock
        mock_config.load_config.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
