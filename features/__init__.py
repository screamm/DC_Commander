"""Modern Commander Features Package"""

from .file_viewer import FileViewer
from .file_editor import FileEditor
from .system_info import (
    get_system_info,
    get_cpu_info,
    get_memory_info,
    get_disk_info,
    get_all_disk_info,
    get_environment_info,
    clear_cache
)
from .config_manager import ConfigManager, get_config_manager
from .system_info_screen import SystemInfoScreen, create_system_info_screen

__version__ = "1.0.0"
__all__ = [
    "FileViewer",
    "FileEditor",
    "get_system_info",
    "get_cpu_info",
    "get_memory_info",
    "get_disk_info",
    "get_all_disk_info",
    "get_environment_info",
    "clear_cache",
    "ConfigManager",
    "get_config_manager",
    "SystemInfoScreen",
    "create_system_info_screen"
]
