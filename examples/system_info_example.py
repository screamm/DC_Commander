"""
Example usage of system information and configuration modules.

Demonstrates how to use the Modern Commander system info and config features.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.system_info import (
    get_system_info,
    get_cpu_info,
    get_memory_info,
    get_disk_info,
    get_all_disk_info,
    get_environment_info,
    clear_cache
)
from features.config_manager import get_config_manager
from features.system_info_screen import create_system_info_screen


def example_basic_system_info():
    """Example: Get basic system information"""
    print("\n" + "=" * 60)
    print("BASIC SYSTEM INFORMATION")
    print("=" * 60)

    info = get_system_info()

    print(f"OS: {info['os_name']} {info['os_version']}")
    print(f"Platform: {info['platform']}")
    print(f"Processor: {info['processor']}")
    print(f"CPU Cores: {info['cpu_count']} logical, {info['cpu_count_physical']} physical")
    print(f"Python: {info['python_version']}")
    print(f"Memory: {info['total_memory_gb']:.2f} GB total, "
          f"{info['available_memory_gb']:.2f} GB available ({info['memory_percent']:.1f}% used)")


def example_cpu_info():
    """Example: Get detailed CPU information"""
    print("\n" + "=" * 60)
    print("CPU INFORMATION")
    print("=" * 60)

    cpu = get_cpu_info()

    print(f"Processor: {cpu['processor_model']}")
    print(f"Architecture: {cpu['architecture']}")
    print(f"Physical Cores: {cpu['physical_cores']}")
    print(f"Logical Cores: {cpu['logical_cores']}")

    if cpu['current_frequency_mhz'] > 0:
        print(f"Current Frequency: {cpu['current_frequency_mhz']:.0f} MHz")
        print(f"Min Frequency: {cpu['min_frequency_mhz']:.0f} MHz")
        print(f"Max Frequency: {cpu['max_frequency_mhz']:.0f} MHz")

    print(f"CPU Usage: {cpu['cpu_percent']:.1f}%")


def example_memory_info():
    """Example: Get detailed memory information"""
    print("\n" + "=" * 60)
    print("MEMORY INFORMATION")
    print("=" * 60)

    mem = get_memory_info()

    print("RAM:")
    print(f"  Total: {mem['total_gb']:.2f} GB")
    print(f"  Used: {mem['used_gb']:.2f} GB ({mem['percent_used']:.1f}%)")
    print(f"  Available: {mem['available_gb']:.2f} GB")
    print(f"  Free: {mem['free_gb']:.2f} GB")

    print("\nSwap:")
    if mem['swap_total_gb'] > 0:
        print(f"  Total: {mem['swap_total_gb']:.2f} GB")
        print(f"  Used: {mem['swap_used_gb']:.2f} GB ({mem['swap_percent_used']:.1f}%)")
        print(f"  Free: {mem['swap_free_gb']:.2f} GB")
    else:
        print("  No swap configured")


def example_disk_info():
    """Example: Get disk information"""
    print("\n" + "=" * 60)
    print("DISK INFORMATION")
    print("=" * 60)

    disks = get_all_disk_info()

    for i, disk in enumerate(disks, 1):
        print(f"\nDisk {i}: {disk.get('path', 'Unknown')}")
        print(f"  Device: {disk.get('device', 'Unknown')}")
        print(f"  Filesystem: {disk.get('filesystem', 'Unknown')}")
        print(f"  Total: {disk.get('total_gb', 0):.2f} GB")
        print(f"  Used: {disk.get('used_gb', 0):.2f} GB ({disk.get('percent_used', 0):.1f}%)")
        print(f"  Free: {disk.get('free_gb', 0):.2f} GB")


def example_environment_info():
    """Example: Get environment information"""
    print("\n" + "=" * 60)
    print("ENVIRONMENT INFORMATION")
    print("=" * 60)

    env = get_environment_info()

    print(f"Hostname: {env['hostname']}")
    print(f"Username: {env['username']}")
    print(f"Boot Time: {env['boot_time']}")
    print(f"Uptime: {env['uptime_hours']:.2f} hours")


def example_config_manager():
    """Example: Using configuration manager"""
    print("\n" + "=" * 60)
    print("CONFIGURATION MANAGER")
    print("=" * 60)

    # Get config manager
    config_mgr = get_config_manager()

    # Load configuration
    config = config_mgr.load_config()

    print(f"Config file: {config_mgr.config_path}")
    print(f"\nLeft panel start path: {config.left_panel.start_path}")
    print(f"Right panel start path: {config.right_panel.start_path}")
    print(f"Color scheme: {config.color_scheme.name}")
    print(f"Editor tab size: {config.editor.tab_size}")
    print(f"Show hidden files: {config.view.show_hidden_files}")

    # Validate configuration
    issues = config_mgr.validate_config()
    if issues:
        print(f"\nConfiguration issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\nConfiguration is valid")

    # Update and save
    print("\nUpdating color scheme to 'dark'...")
    config_mgr.update_color_scheme("dark")
    config_mgr.save_config()
    print("Configuration saved")


def example_system_info_screen():
    """Example: System info screen with tabs"""
    print("\n" + "=" * 60)
    print("SYSTEM INFO SCREEN (TABBED INTERFACE)")
    print("=" * 60)

    screen = create_system_info_screen()

    # Show all tabs
    for i, tab_name in enumerate(screen.TABS):
        screen.set_tab(i)
        print(f"\n{'=' * 60}")
        print(f"TAB: {tab_name}")
        print(f"{'=' * 60}")
        print(screen.get_tab_content())


def example_caching():
    """Example: Demonstrate caching behavior"""
    print("\n" + "=" * 60)
    print("CACHING DEMONSTRATION")
    print("=" * 60)

    import time

    # First call - no cache
    start = time.time()
    info1 = get_system_info()
    time1 = time.time() - start
    print(f"First call (no cache): {time1*1000:.2f}ms")

    # Second call - from cache
    start = time.time()
    info2 = get_system_info()
    time2 = time.time() - start
    print(f"Second call (cached): {time2*1000:.2f}ms")

    print(f"Speedup: {time1/time2:.1f}x faster")

    # Clear cache
    print("\nClearing cache...")
    clear_cache()

    # Third call - cache cleared
    start = time.time()
    info3 = get_system_info()
    time3 = time.time() - start
    print(f"Third call (cache cleared): {time3*1000:.2f}ms")


def main():
    """Run all examples"""
    print("\nMODERN COMMANDER - System Info & Config Examples")
    print("=" * 60)

    try:
        example_basic_system_info()
        example_cpu_info()
        example_memory_info()
        example_disk_info()
        example_environment_info()
        example_config_manager()
        example_system_info_screen()
        example_caching()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
