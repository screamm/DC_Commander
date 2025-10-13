"""Formatting utilities for DC Commander."""

from datetime import datetime


def format_file_size(size: int) -> str:
    """Format file size for display."""
    if size < 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:3.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def format_date(dt: datetime) -> str:
    """Format date in Norton Commander style (YY-MM-DD)."""
    return dt.strftime("%y-%m-%d")


def format_time(dt: datetime) -> str:
    """Format time in Norton Commander style (HH:MM)."""
    return dt.strftime("%H:%M")
