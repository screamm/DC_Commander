"""
Dependency Injection Container for Modern Commander.

Provides comprehensive DI support with:
- Service registration (singleton, transient, scoped)
- Automatic dependency resolution via constructor injection
- Factory function support
- Instance registration for existing objects
- Lifecycle management for different service patterns
"""

from typing import Dict, Type, TypeVar, Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum
import inspect

T = TypeVar('T')


class Lifecycle(Enum):
    """Service lifecycle options."""
    SINGLETON = "singleton"  # One instance for application lifetime
    TRANSIENT = "transient"  # New instance every resolve
    SCOPED = "scoped"        # One instance per scope (future use)


@dataclass
class ServiceRegistration:
    """
    Service registration details.

    Attributes:
        service_type: Interface or abstract type (protocol)
        implementation: Concrete implementation class
        factory: Factory function to create instance
        instance: Pre-created instance (for instance registration)
        lifecycle: Service lifecycle management strategy
    """
    service_type: Type
    implementation: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    lifecycle: Lifecycle = Lifecycle.SINGLETON


class DependencyContainer:
    """
    Dependency injection container with full DI support.

    Features:
    - Constructor injection with automatic parameter resolution
    - Multiple lifecycle strategies (singleton, transient, scoped)
    - Factory function support for complex initialization
    - Instance registration for pre-created objects
    - Type-safe service resolution

    Example:
        >>> container = DependencyContainer()
        >>> container.register_singleton(IConfigManager, ConfigManager)
        >>> container.register_transient(IFileService, FileService)
        >>> config = container.resolve(IConfigManager)
    """

    def __init__(self):
        """Initialize dependency container."""
        self._registrations: Dict[Type, ServiceRegistration] = {}
        self._instances: Dict[Type, Any] = {}
        self._scopes: Dict[str, Dict[Type, Any]] = {}
        self._resolution_stack: list[Type] = []  # Circular dependency detection

    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> None:
        """
        Register a singleton service (one instance for app lifetime).

        Args:
            service_type: Interface or protocol type
            implementation: Concrete implementation class
            factory: Factory function to create instance

        Raises:
            ValueError: If neither implementation nor factory provided

        Example:
            >>> container.register_singleton(IConfigManager, ConfigManager)
        """
        if implementation is None and factory is None:
            raise ValueError(
                f"Must provide either implementation or factory for {service_type.__name__}"
            )

        self._registrations[service_type] = ServiceRegistration(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            lifecycle=Lifecycle.SINGLETON
        )

    def register_transient(
        self,
        service_type: Type[T],
        implementation: Type[T]
    ) -> None:
        """
        Register a transient service (new instance on every resolve).

        Args:
            service_type: Interface or protocol type
            implementation: Concrete implementation class

        Example:
            >>> container.register_transient(IFileService, FileService)
        """
        self._registrations[service_type] = ServiceRegistration(
            service_type=service_type,
            implementation=implementation,
            lifecycle=Lifecycle.TRANSIENT
        )

    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """
        Register an existing instance (singleton behavior).

        Args:
            service_type: Interface or protocol type
            instance: Pre-created instance to register

        Example:
            >>> config = ConfigManager()
            >>> container.register_instance(IConfigManager, config)
        """
        self._registrations[service_type] = ServiceRegistration(
            service_type=service_type,
            instance=instance,
            lifecycle=Lifecycle.SINGLETON
        )
        self._instances[service_type] = instance

    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service instance with automatic dependency injection.

        Args:
            service_type: Interface or protocol type to resolve

        Returns:
            Service instance with all dependencies injected

        Raises:
            ValueError: If service not registered
            RuntimeError: If circular dependency detected

        Example:
            >>> config = container.resolve(IConfigManager)
        """
        # Check registration
        if service_type not in self._registrations:
            raise ValueError(f"Service not registered: {service_type.__name__}")

        # Circular dependency detection
        if service_type in self._resolution_stack:
            cycle = " -> ".join(t.__name__ for t in self._resolution_stack)
            raise RuntimeError(
                f"Circular dependency detected: {cycle} -> {service_type.__name__}"
            )

        registration = self._registrations[service_type]

        # Check for existing singleton instance
        if registration.lifecycle == Lifecycle.SINGLETON:
            if service_type in self._instances:
                return self._instances[service_type]

        # Create instance with dependency injection
        try:
            self._resolution_stack.append(service_type)
            instance = self._create_instance(registration)
        finally:
            self._resolution_stack.pop()

        # Store singleton instance
        if registration.lifecycle == Lifecycle.SINGLETON:
            self._instances[service_type] = instance

        return instance

    def _create_instance(self, registration: ServiceRegistration) -> Any:
        """
        Create service instance with constructor injection.

        Args:
            registration: Service registration details

        Returns:
            Service instance with dependencies injected
        """
        # Use factory if provided
        if registration.factory:
            return registration.factory()

        # Use existing instance
        if registration.instance:
            return registration.instance

        # Create new instance with DI
        impl = registration.implementation or registration.service_type

        # Get constructor signature
        sig = inspect.signature(impl.__init__)
        params = {}

        # Resolve each constructor parameter
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            # Handle optional parameters
            if param.default != inspect.Parameter.empty:
                # Has default value, skip DI
                continue

            # Resolve dependency if type annotation present
            if param.annotation != inspect.Parameter.empty:
                param_type = param.annotation

                # Skip basic types (str, int, etc.)
                if param_type in (str, int, float, bool, list, dict):
                    continue

                # Resolve dependency if registered
                if param_type in self._registrations:
                    params[param_name] = self.resolve(param_type)

        # Create instance with resolved dependencies
        return impl(**params)

    def is_registered(self, service_type: Type) -> bool:
        """
        Check if service is registered.

        Args:
            service_type: Interface or protocol type

        Returns:
            True if service is registered
        """
        return service_type in self._registrations

    def clear(self) -> None:
        """Clear all registrations and cached instances."""
        self._registrations.clear()
        self._instances.clear()
        self._scopes.clear()
        self._resolution_stack.clear()
