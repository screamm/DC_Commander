"""
Dependency Injection infrastructure for Modern Commander.

Provides:
- DependencyContainer: Service registration and resolution
- Service protocols: Interface definitions for dependency injection
- Lifecycle management: Singleton, Transient, Scoped lifecycles
"""

from .di_container import DependencyContainer, Lifecycle, ServiceRegistration
from .protocols import (
    IConfigManager,
    IThemeManager,
    IFileService,
    IAsyncFileService,
)

__all__ = [
    "DependencyContainer",
    "Lifecycle",
    "ServiceRegistration",
    "IConfigManager",
    "IThemeManager",
    "IFileService",
    "IAsyncFileService",
]
