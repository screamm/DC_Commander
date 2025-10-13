"""
Dependency Injection Container

Simple DI container for breaking circular dependencies through service registration.
Supports both eager instance registration and lazy factory-based initialization.
"""

from typing import Dict, Type, Any, Optional, Callable
import logging


logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Simple dependency injection container.

    Manages service instances and provides dependency resolution to break
    circular import dependencies. Supports both eager registration and
    lazy factory-based instantiation.

    Example:
        >>> container = DependencyContainer()
        >>> container.register(ConfigManager, config_manager_instance)
        >>> config = container.resolve(ConfigManager)
    """

    def __init__(self):
        """Initialize empty container."""
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._singletons: Dict[Type, Any] = {}

    def register(self, service_type: Type, instance: Any) -> None:
        """Register a service instance (eager registration).

        Args:
            service_type: Type identifier for the service
            instance: Service instance to register

        Example:
            >>> container.register(ConfigManager, ConfigManager())
        """
        self._services[service_type] = instance
        logger.debug(f"Registered service: {service_type.__name__}")

    def register_factory(
        self,
        service_type: Type,
        factory: Callable[[], Any],
        singleton: bool = True
    ) -> None:
        """Register a factory function for lazy instantiation.

        Args:
            service_type: Type identifier for the service
            factory: Factory function that creates the service instance
            singleton: If True, cache instance after first creation

        Example:
            >>> container.register_factory(
            ...     ConfigManager,
            ...     lambda: ConfigManager(),
            ...     singleton=True
            ... )
        """
        self._factories[service_type] = factory
        if singleton:
            self._singletons[service_type] = None
        logger.debug(f"Registered factory: {service_type.__name__} (singleton={singleton})")

    def resolve(self, service_type: Type) -> Any:
        """Resolve a service instance.

        Args:
            service_type: Type identifier for the service

        Returns:
            Service instance

        Raises:
            ValueError: If service not registered

        Example:
            >>> config_manager = container.resolve(ConfigManager)
        """
        # Check registered instances first
        if service_type in self._services:
            return self._services[service_type]

        # Check singleton cache
        if service_type in self._singletons:
            cached = self._singletons[service_type]
            if cached is not None:
                return cached

        # Check factories
        if service_type in self._factories:
            instance = self._factories[service_type]()

            # Cache if singleton
            if service_type in self._singletons:
                self._singletons[service_type] = instance

            logger.debug(f"Created instance: {service_type.__name__}")
            return instance

        raise ValueError(f"Service not registered: {service_type.__name__}")

    def has_service(self, service_type: Type) -> bool:
        """Check if service is registered.

        Args:
            service_type: Type identifier for the service

        Returns:
            True if service is registered
        """
        return (
            service_type in self._services
            or service_type in self._factories
        )

    def clear(self) -> None:
        """Clear all registered services and factories."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        logger.debug("Container cleared")

    def get_registered_services(self) -> list[str]:
        """Get list of registered service names.

        Returns:
            List of service type names
        """
        services = set()
        services.update(t.__name__ for t in self._services.keys())
        services.update(t.__name__ for t in self._factories.keys())
        return sorted(services)
