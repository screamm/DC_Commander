"""
System Information Screen for Modern Commander

Provides Norton Commander-style tabbed interface for viewing system information.
Displays Summary, Memory, Disk, and Environment tabs with formatted data.
"""

from typing import Optional, Callable
from .system_info import (
    get_system_info,
    get_cpu_info,
    get_memory_info,
    get_all_disk_info,
    get_environment_info
)


class SystemInfoScreen:
    """
    Norton Commander-style system information screen with 4 tabs.

    Tabs:
        1. Summary - System overview
        2. Memory - RAM and swap information
        3. Disk - All disk partitions
        4. Environment - Runtime environment
    """

    TABS = ["Summary", "Memory", "Disk", "Environment"]

    def __init__(self):
        """Initialize system info screen"""
        self.current_tab = 0
        self._refresh_callback: Optional[Callable] = None

    def get_current_tab_name(self) -> str:
        """Get name of currently selected tab"""
        return self.TABS[self.current_tab]

    def next_tab(self) -> None:
        """Switch to next tab (circular)"""
        self.current_tab = (self.current_tab + 1) % len(self.TABS)

    def previous_tab(self) -> None:
        """Switch to previous tab (circular)"""
        self.current_tab = (self.current_tab - 1) % len(self.TABS)

    def set_tab(self, tab_index: int) -> None:
        """Set current tab by index"""
        if 0 <= tab_index < len(self.TABS):
            self.current_tab = tab_index

    def set_tab_by_name(self, tab_name: str) -> bool:
        """
        Set current tab by name.

        Args:
            tab_name: Name of tab to select

        Returns:
            True if tab found and selected, False otherwise
        """
        try:
            self.current_tab = self.TABS.index(tab_name)
            return True
        except ValueError:
            return False

    def set_refresh_callback(self, callback: Callable) -> None:
        """Set callback function for screen refresh requests"""
        self._refresh_callback = callback

    def get_tab_content(self) -> str:
        """
        Get formatted content for current tab.

        Returns:
            Formatted text content for display
        """
        tab_name = self.get_current_tab_name()

        if tab_name == "Summary":
            return self._format_summary_tab()
        elif tab_name == "Memory":
            return self._format_memory_tab()
        elif tab_name == "Disk":
            return self._format_disk_tab()
        elif tab_name == "Environment":
            return self._format_environment_tab()
        else:
            return "Unknown tab"

    def _format_summary_tab(self) -> str:
        """Format summary tab content"""
        sys_info = get_system_info()
        cpu_info = get_cpu_info()

        lines = []
        lines.append("=" * 60)
        lines.append("  SYSTEM SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        # Operating System
        lines.append("Operating System:")
        lines.append(f"  Name:     {sys_info.get('os_name', 'Unknown')}")
        lines.append(f"  Version:  {sys_info.get('os_version', 'Unknown')}")
        lines.append(f"  Platform: {sys_info.get('platform', 'Unknown')}")
        lines.append("")

        # Processor
        lines.append("Processor:")
        lines.append(f"  Model:      {cpu_info.get('processor_model', 'Unknown')}")
        lines.append(f"  Cores:      {cpu_info.get('physical_cores', 0)} physical, "
                    f"{cpu_info.get('logical_cores', 0)} logical")
        lines.append(f"  Arch:       {cpu_info.get('architecture', 'Unknown')}")

        freq = cpu_info.get('current_frequency_mhz', 0)
        if freq > 0:
            lines.append(f"  Frequency:  {freq:.0f} MHz")
        lines.append(f"  Usage:      {cpu_info.get('cpu_percent', 0):.1f}%")
        lines.append("")

        # Memory
        lines.append("Memory:")
        total = sys_info.get('total_memory_gb', 0)
        used = sys_info.get('used_memory_gb', 0)
        available = sys_info.get('available_memory_gb', 0)
        percent = sys_info.get('memory_percent', 0)

        lines.append(f"  Total:      {total:.2f} GB")
        lines.append(f"  Used:       {used:.2f} GB ({percent:.1f}%)")
        lines.append(f"  Available:  {available:.2f} GB")
        lines.append("")

        # Python
        lines.append("Python:")
        lines.append(f"  Version:    {sys_info.get('python_version', 'Unknown')}")
        lines.append("")

        # Error handling
        if 'error' in sys_info:
            lines.append(f"Note: {sys_info['error']}")

        return "\n".join(lines)

    def _format_memory_tab(self) -> str:
        """Format memory tab content"""
        mem_info = get_memory_info()

        lines = []
        lines.append("=" * 60)
        lines.append("  MEMORY INFORMATION")
        lines.append("=" * 60)
        lines.append("")

        # RAM
        lines.append("Physical Memory (RAM):")
        lines.append(f"  Total:      {mem_info.get('total_gb', 0):.2f} GB")
        lines.append(f"  Used:       {mem_info.get('used_gb', 0):.2f} GB "
                    f"({mem_info.get('percent_used', 0):.1f}%)")
        lines.append(f"  Available:  {mem_info.get('available_gb', 0):.2f} GB")
        lines.append(f"  Free:       {mem_info.get('free_gb', 0):.2f} GB")
        lines.append("")

        # Memory bar visualization
        percent = mem_info.get('percent_used', 0)
        bar_width = 40
        filled = int((percent / 100) * bar_width)
        bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
        lines.append(f"  Usage: {bar} {percent:.1f}%")
        lines.append("")

        # Swap
        lines.append("Swap Memory:")
        swap_total = mem_info.get('swap_total_gb', 0)

        if swap_total > 0:
            lines.append(f"  Total:      {swap_total:.2f} GB")
            lines.append(f"  Used:       {mem_info.get('swap_used_gb', 0):.2f} GB "
                        f"({mem_info.get('swap_percent_used', 0):.1f}%)")
            lines.append(f"  Free:       {mem_info.get('swap_free_gb', 0):.2f} GB")
            lines.append("")

            # Swap bar visualization
            swap_percent = mem_info.get('swap_percent_used', 0)
            swap_filled = int((swap_percent / 100) * bar_width)
            swap_bar = "[" + "#" * swap_filled + "-" * (bar_width - swap_filled) + "]"
            lines.append(f"  Usage: {swap_bar} {swap_percent:.1f}%")
        else:
            lines.append("  No swap configured")
        lines.append("")

        # Error handling
        if 'error' in mem_info:
            lines.append(f"Note: {mem_info['error']}")

        return "\n".join(lines)

    def _format_disk_tab(self) -> str:
        """Format disk tab content"""
        disks = get_all_disk_info()

        lines = []
        lines.append("=" * 60)
        lines.append("  DISK INFORMATION")
        lines.append("=" * 60)
        lines.append("")

        if not disks:
            lines.append("No disk information available")
            return "\n".join(lines)

        for i, disk in enumerate(disks):
            if 'error' in disk and 'path' not in disk:
                lines.append(f"Error: {disk['error']}")
                continue

            # Disk header
            path = disk.get('path', 'Unknown')
            device = disk.get('device', 'Unknown')
            filesystem = disk.get('filesystem', 'Unknown')

            lines.append(f"Disk {i+1}: {path}")
            lines.append(f"  Device:     {device}")
            lines.append(f"  Filesystem: {filesystem}")
            lines.append("")

            # Space information
            total = disk.get('total_gb', 0)
            used = disk.get('used_gb', 0)
            free = disk.get('free_gb', 0)
            percent = disk.get('percent_used', 0)

            lines.append(f"  Total:      {total:.2f} GB")
            lines.append(f"  Used:       {used:.2f} GB ({percent:.1f}%)")
            lines.append(f"  Free:       {free:.2f} GB")
            lines.append("")

            # Usage bar visualization
            bar_width = 40
            filled = int((percent / 100) * bar_width)
            bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
            lines.append(f"  Usage: {bar} {percent:.1f}%")
            lines.append("")

            if 'error' in disk:
                lines.append(f"  Note: {disk['error']}")
                lines.append("")

            lines.append("-" * 60)
            lines.append("")

        return "\n".join(lines)

    def _format_environment_tab(self) -> str:
        """Format environment tab content"""
        env_info = get_environment_info()
        sys_info = get_system_info()

        lines = []
        lines.append("=" * 60)
        lines.append("  ENVIRONMENT INFORMATION")
        lines.append("=" * 60)
        lines.append("")

        # System Identity
        lines.append("System Identity:")
        lines.append(f"  Hostname:   {env_info.get('hostname', 'Unknown')}")
        lines.append(f"  Username:   {env_info.get('username', 'Unknown')}")
        lines.append("")

        # Uptime
        lines.append("System Uptime:")
        uptime_hours = env_info.get('uptime_hours', 0)
        days = int(uptime_hours // 24)
        hours = int(uptime_hours % 24)
        lines.append(f"  Boot time:  {env_info.get('boot_time', 'Unknown')}")
        lines.append(f"  Uptime:     {days} days, {hours} hours")
        lines.append("")

        # Platform Details
        lines.append("Platform Details:")
        lines.append(f"  OS:         {sys_info.get('os_name', 'Unknown')}")
        lines.append(f"  Version:    {sys_info.get('os_version', 'Unknown')}")
        lines.append(f"  Platform:   {sys_info.get('platform', 'Unknown')}")
        lines.append("")

        # Runtime
        lines.append("Runtime Environment:")
        lines.append(f"  Python:     {sys_info.get('python_version', 'Unknown')}")
        lines.append("")

        # Error handling
        if 'error' in env_info:
            lines.append(f"Note: {env_info['error']}")

        return "\n".join(lines)

    def get_tab_header(self) -> str:
        """
        Get formatted tab header for display.

        Returns:
            Tab navigation header string
        """
        header_parts = []

        for i, tab in enumerate(self.TABS):
            if i == self.current_tab:
                # Current tab - highlighted
                header_parts.append(f"[{tab}]")
            else:
                # Other tabs
                header_parts.append(f" {tab} ")

        return "  ".join(header_parts)

    def get_help_text(self) -> str:
        """
        Get help text for system info screen.

        Returns:
            Help text string
        """
        return (
            "Navigation: TAB/Shift+TAB - Switch tabs | "
            "1-4 - Direct tab selection | "
            "Q/ESC - Close | "
            "R - Refresh"
        )


def create_system_info_screen() -> SystemInfoScreen:
    """
    Factory function to create SystemInfoScreen instance.

    Returns:
        Configured SystemInfoScreen instance
    """
    return SystemInfoScreen()
