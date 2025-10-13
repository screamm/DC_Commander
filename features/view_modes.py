"""View modes for file panel display.

Provides different ways to display file information similar to Norton Commander.
"""

from enum import Enum
from typing import List, Tuple, Any
from pathlib import Path


class ViewMode(Enum):
    """File panel view modes."""
    FULL = "full"          # Full details: Name, Size, Date, Time
    BRIEF = "brief"        # Brief: Name only, multiple columns
    INFO = "info"          # Info: Full details + permissions, owner
    QUICK_VIEW = "quick"   # Quick: Preview of selected file


class ViewModeConfig:
    """Configuration for different view modes."""

    @staticmethod
    def get_columns(mode: ViewMode) -> List[str]:
        """Get column definitions for view mode.

        Args:
            mode: View mode

        Returns:
            List of column names
        """
        if mode == ViewMode.FULL:
            return ["Name", "Size", "Date", "Time"]
        elif mode == ViewMode.BRIEF:
            return ["Name"]
        elif mode == ViewMode.INFO:
            return ["Name", "Size", "Date", "Time", "Permissions", "Owner"]
        elif mode == ViewMode.QUICK_VIEW:
            return ["Name"]  # Single column for file list
        else:
            return ["Name", "Size", "Date", "Time"]

    @staticmethod
    def get_column_widths(mode: ViewMode) -> List[int]:
        """Get column width hints for view mode.

        Args:
            mode: View mode

        Returns:
            List of column widths (0 = auto)
        """
        if mode == ViewMode.FULL:
            return [0, 12, 10, 6]  # Name auto, others fixed
        elif mode == ViewMode.BRIEF:
            return [0]  # Name auto-width
        elif mode == ViewMode.INFO:
            return [0, 12, 10, 6, 12, 12]
        elif mode == ViewMode.QUICK_VIEW:
            return [0]
        else:
            return [0, 12, 10, 6]

    @staticmethod
    def format_row(item: Any, mode: ViewMode) -> List[str]:
        """Format file item for display in specified view mode.

        Args:
            item: FileItem to format
            mode: View mode

        Returns:
            List of formatted cell values
        """
        if mode == ViewMode.FULL:
            return ViewModeConfig._format_full_row(item)
        elif mode == ViewMode.BRIEF:
            return ViewModeConfig._format_brief_row(item)
        elif mode == ViewMode.INFO:
            return ViewModeConfig._format_info_row(item)
        elif mode == ViewMode.QUICK_VIEW:
            return ViewModeConfig._format_brief_row(item)
        else:
            return ViewModeConfig._format_full_row(item)

    @staticmethod
    def _format_full_row(item: Any) -> List[str]:
        """Format row for Full view mode.

        Args:
            item: FileItem

        Returns:
            List of cell values
        """
        # Format name
        if item.is_dir:
            name_display = f"[bold cyan][{item.name.upper()}][/bold cyan]"
        else:
            name_display = item.name

        # Format size
        size_display = ViewModeConfig._format_size(item.size) if not item.is_dir else "<DIR>"

        # Format date and time
        date_display = item.modified.strftime("%y-%m-%d")
        time_display = item.modified.strftime("%H:%M")

        return [name_display, size_display, date_display, time_display]

    @staticmethod
    def _format_brief_row(item: Any) -> List[str]:
        """Format row for Brief view mode.

        Args:
            item: FileItem

        Returns:
            List of cell values
        """
        if item.is_dir:
            name_display = f"[bold cyan][{item.name.upper()}][/bold cyan]"
        else:
            name_display = item.name

        return [name_display]

    @staticmethod
    def _format_info_row(item: Any) -> List[str]:
        """Format row for Info view mode.

        Args:
            item: FileItem

        Returns:
            List of cell values
        """
        import stat
        import pwd
        import grp

        # Start with full row data
        row_data = ViewModeConfig._format_full_row(item)

        # Add permissions
        try:
            st = item.path.stat()
            mode = st.st_mode
            perms = stat.filemode(mode)
            row_data.append(perms)
        except Exception:
            row_data.append("?????????")

        # Add owner (Unix only)
        try:
            st = item.path.stat()
            owner_name = pwd.getpwuid(st.st_uid).pw_name
            group_name = grp.getgrgid(st.st_gid).gr_name
            row_data.append(f"{owner_name}:{group_name}")
        except Exception:
            row_data.append("Unknown")

        return row_data

    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size for display.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        if size < 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:3.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
