"""
System Information Module for Modern Commander

Provides cross-platform system information including CPU, memory, disk, and OS details.
Uses caching for performance optimization and psutil for reliable system metrics.
"""

import platform
import psutil
from typing import Dict, Any, Optional
from functools import lru_cache
from datetime import datetime, timedelta


class SystemInfoCache:
    """Cache manager for system information with time-based invalidation"""

    def __init__(self, ttl_seconds: int = 5):
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value if not expired"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                return value
        return None

    def set(self, key: str, value: Any) -> None:
        """Store value with current timestamp"""
        self._cache[key] = (value, datetime.now())

    def clear(self) -> None:
        """Clear all cached values"""
        self._cache.clear()


# Global cache instance
_cache = SystemInfoCache(ttl_seconds=5)


def get_system_info() -> Dict[str, Any]:
    """
    Get comprehensive system overview including OS, CPU, and memory.

    Returns:
        Dict containing:
            - os_name: Operating system name (Linux/Windows/macOS)
            - os_version: OS version string
            - platform: Platform architecture
            - processor: CPU model/name
            - python_version: Python version string
            - cpu_count: Number of CPU cores
            - total_memory_gb: Total RAM in GB
            - used_memory_gb: Used RAM in GB
            - available_memory_gb: Available RAM in GB
            - memory_percent: Memory usage percentage
    """
    cached = _cache.get("system_info")
    if cached:
        return cached

    try:
        # Operating System Information
        os_name = platform.system()
        os_version = platform.version()
        platform_info = platform.platform()

        # Processor Information
        try:
            processor = platform.processor()
            if not processor:  # Fallback for some systems
                processor = platform.machine()
        except Exception:
            processor = "Unknown"

        # Python Version
        python_version = platform.python_version()

        # CPU Information
        cpu_count = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)

        # Memory Information
        mem = psutil.virtual_memory()
        total_memory_gb = mem.total / (1024 ** 3)
        used_memory_gb = mem.used / (1024 ** 3)
        available_memory_gb = mem.available / (1024 ** 3)
        memory_percent = mem.percent

        info = {
            "os_name": os_name,
            "os_version": os_version,
            "platform": platform_info,
            "processor": processor,
            "python_version": python_version,
            "cpu_count": cpu_count,
            "cpu_count_physical": cpu_count_physical,
            "total_memory_gb": round(total_memory_gb, 2),
            "used_memory_gb": round(used_memory_gb, 2),
            "available_memory_gb": round(available_memory_gb, 2),
            "memory_percent": memory_percent
        }

        _cache.set("system_info", info)
        return info

    except Exception as e:
        # Return minimal fallback information on error
        return {
            "os_name": platform.system(),
            "os_version": "Unknown",
            "platform": platform.platform(),
            "processor": "Unknown",
            "python_version": platform.python_version(),
            "cpu_count": 0,
            "cpu_count_physical": 0,
            "total_memory_gb": 0.0,
            "used_memory_gb": 0.0,
            "available_memory_gb": 0.0,
            "memory_percent": 0.0,
            "error": str(e)
        }


def get_disk_info(path: str = "/") -> Dict[str, Any]:
    """
    Get disk information for specified path.

    Args:
        path: Filesystem path to query (default: root)

    Returns:
        Dict containing:
            - path: Query path
            - total_gb: Total disk space in GB
            - used_gb: Used disk space in GB
            - free_gb: Free disk space in GB
            - percent_used: Percentage of disk space used
            - filesystem: Filesystem type (if available)
            - device: Device name (if available)
    """
    try:
        usage = psutil.disk_usage(path)

        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        percent_used = usage.percent

        # Try to get partition info for filesystem type
        filesystem = "Unknown"
        device = "Unknown"

        try:
            for partition in psutil.disk_partitions():
                if path.startswith(partition.mountpoint):
                    filesystem = partition.fstype
                    device = partition.device
                    break
        except Exception:
            pass

        return {
            "path": path,
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "percent_used": percent_used,
            "filesystem": filesystem,
            "device": device
        }

    except (PermissionError, FileNotFoundError) as e:
        return {
            "path": path,
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "percent_used": 0.0,
            "filesystem": "Unknown",
            "device": "Unknown",
            "error": f"Access denied or path not found: {str(e)}"
        }
    except Exception as e:
        return {
            "path": path,
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "percent_used": 0.0,
            "filesystem": "Unknown",
            "device": "Unknown",
            "error": str(e)
        }


def get_all_disk_info() -> list[Dict[str, Any]]:
    """
    Get disk information for all mounted partitions.

    Returns:
        List of disk info dictionaries for each partition
    """
    cached = _cache.get("all_disk_info")
    if cached:
        return cached

    disks = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for partition in partitions:
            disk_info = get_disk_info(partition.mountpoint)
            disks.append(disk_info)
    except Exception as e:
        disks.append({
            "error": f"Failed to enumerate partitions: {str(e)}"
        })

    _cache.set("all_disk_info", disks)
    return disks


def get_cpu_info() -> Dict[str, Any]:
    """
    Get detailed CPU information.

    Returns:
        Dict containing:
            - logical_cores: Number of logical CPU cores
            - physical_cores: Number of physical CPU cores
            - processor_model: CPU model name
            - architecture: System architecture (32/64-bit)
            - current_frequency_mhz: Current CPU frequency in MHz
            - min_frequency_mhz: Minimum CPU frequency
            - max_frequency_mhz: Maximum CPU frequency
            - cpu_percent: Current CPU usage percentage
    """
    cached = _cache.get("cpu_info")
    if cached:
        return cached

    try:
        logical_cores = psutil.cpu_count(logical=True)
        physical_cores = psutil.cpu_count(logical=False)

        processor_model = platform.processor()
        if not processor_model:
            processor_model = platform.machine()

        architecture = platform.machine()

        # CPU Frequency
        try:
            freq = psutil.cpu_freq()
            current_freq = freq.current if freq else 0.0
            min_freq = freq.min if freq else 0.0
            max_freq = freq.max if freq else 0.0
        except Exception:
            current_freq = min_freq = max_freq = 0.0

        # CPU Usage (interval for more accurate reading)
        cpu_percent = psutil.cpu_percent(interval=0.1)

        info = {
            "logical_cores": logical_cores,
            "physical_cores": physical_cores,
            "processor_model": processor_model,
            "architecture": architecture,
            "current_frequency_mhz": round(current_freq, 2) if current_freq else 0.0,
            "min_frequency_mhz": round(min_freq, 2) if min_freq else 0.0,
            "max_frequency_mhz": round(max_freq, 2) if max_freq else 0.0,
            "cpu_percent": cpu_percent
        }

        _cache.set("cpu_info", info)
        return info

    except Exception as e:
        return {
            "logical_cores": 0,
            "physical_cores": 0,
            "processor_model": "Unknown",
            "architecture": platform.machine(),
            "current_frequency_mhz": 0.0,
            "min_frequency_mhz": 0.0,
            "max_frequency_mhz": 0.0,
            "cpu_percent": 0.0,
            "error": str(e)
        }


def get_memory_info() -> Dict[str, Any]:
    """
    Get detailed memory information including RAM and swap.

    Returns:
        Dict containing:
            - total_gb: Total RAM in GB
            - available_gb: Available RAM in GB
            - used_gb: Used RAM in GB
            - free_gb: Free RAM in GB
            - percent_used: Memory usage percentage
            - swap_total_gb: Total swap space in GB
            - swap_used_gb: Used swap space in GB
            - swap_free_gb: Free swap space in GB
            - swap_percent_used: Swap usage percentage
    """
    cached = _cache.get("memory_info")
    if cached:
        return cached

    try:
        # Virtual Memory (RAM)
        mem = psutil.virtual_memory()

        # Swap Memory
        swap = psutil.swap_memory()

        info = {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "available_gb": round(mem.available / (1024 ** 3), 2),
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "free_gb": round(mem.free / (1024 ** 3), 2),
            "percent_used": mem.percent,
            "swap_total_gb": round(swap.total / (1024 ** 3), 2),
            "swap_used_gb": round(swap.used / (1024 ** 3), 2),
            "swap_free_gb": round(swap.free / (1024 ** 3), 2),
            "swap_percent_used": swap.percent
        }

        _cache.set("memory_info", info)
        return info

    except Exception as e:
        return {
            "total_gb": 0.0,
            "available_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "percent_used": 0.0,
            "swap_total_gb": 0.0,
            "swap_used_gb": 0.0,
            "swap_free_gb": 0.0,
            "swap_percent_used": 0.0,
            "error": str(e)
        }


def get_environment_info() -> Dict[str, Any]:
    """
    Get environment and runtime information.

    Returns:
        Dict containing:
            - hostname: Computer hostname
            - username: Current user
            - boot_time: System boot time
            - uptime_hours: System uptime in hours
    """
    cached = _cache.get("environment_info")
    if cached:
        return cached

    try:
        import os

        hostname = platform.node()
        username = os.getenv("USER") or os.getenv("USERNAME") or "Unknown"

        boot_timestamp = psutil.boot_time()
        boot_time = datetime.fromtimestamp(boot_timestamp)
        uptime_seconds = (datetime.now() - boot_time).total_seconds()
        uptime_hours = round(uptime_seconds / 3600, 2)

        info = {
            "hostname": hostname,
            "username": username,
            "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime_hours": uptime_hours
        }

        _cache.set("environment_info", info)
        return info

    except Exception as e:
        return {
            "hostname": "Unknown",
            "username": "Unknown",
            "boot_time": "Unknown",
            "uptime_hours": 0.0,
            "error": str(e)
        }


def clear_cache() -> None:
    """Clear all cached system information"""
    _cache.clear()
