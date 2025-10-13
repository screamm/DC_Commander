"""Coordinators package for ModernCommander.

This package contains specialized coordinator classes that handle
specific aspects of the application, following Single Responsibility Principle.
"""

from .panel_coordinator import PanelCoordinator
from .file_operation_coordinator import FileOperationCoordinator
from .dialog_coordinator import DialogCoordinator
from .config_coordinator import ConfigCoordinator
from .menu_coordinator import MenuCoordinator

__all__ = [
    "PanelCoordinator",
    "FileOperationCoordinator",
    "DialogCoordinator",
    "ConfigCoordinator",
    "MenuCoordinator",
]
