"""
Enhanced Progress Tracking System

Provides accurate progress reporting with:
- Bytes and file counts
- Transfer rate calculation
- ETA estimation
- Time remaining
- Adaptive rate smoothing
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Deque
from collections import deque
import logging


logger = logging.getLogger(__name__)


@dataclass
class ProgressSnapshot:
    """Snapshot of progress at a point in time."""
    timestamp: float
    bytes_completed: int
    files_completed: int


@dataclass
class EnhancedProgressInfo:
    """Enhanced progress information with ETA and transfer rate."""
    # Current state
    current_file: str
    current_bytes: int
    total_bytes: int
    files_completed: int
    total_files: int

    # Calculated metrics
    percentage: float
    bytes_per_second: float
    eta_seconds: float
    elapsed_seconds: float

    # Operation info
    operation_type: str  # "copy", "move", "delete"
    operation_id: Optional[str] = None

    def format_status(self) -> str:
        """Format progress as human-readable status string.

        Returns:
            Formatted status string
        """
        percentage_str = f"{self.percentage:.1f}%"
        files_str = f"{self.files_completed}/{self.total_files}"
        rate_str = format_bytes(self.bytes_per_second) + "/s"
        eta_str = format_duration(self.eta_seconds)

        return (
            f"{self.current_file}: {percentage_str} "
            f"({files_str}) {rate_str} ETA: {eta_str}"
        )

    def format_compact(self) -> str:
        """Format progress as compact string.

        Returns:
            Compact status string
        """
        return (
            f"{self.percentage:.0f}% | "
            f"{format_bytes(self.current_bytes)}/{format_bytes(self.total_bytes)} | "
            f"{format_bytes(self.bytes_per_second)}/s"
        )


class ProgressTracker:
    """Tracks operation progress with accurate ETA calculation."""

    def __init__(
        self,
        total_bytes: int,
        total_files: int,
        operation_type: str,
        operation_id: Optional[str] = None,
        smoothing_window: int = 5
    ):
        """Initialize progress tracker.

        Args:
            total_bytes: Total bytes to process
            total_files: Total files to process
            operation_type: Type of operation
            operation_id: Optional operation identifier
            smoothing_window: Number of samples for rate smoothing
        """
        self.total_bytes = total_bytes
        self.total_files = total_files
        self.operation_type = operation_type
        self.operation_id = operation_id

        self.current_bytes = 0
        self.files_completed = 0
        self.current_file = ""

        self.start_time = time.time()
        self.last_update_time = self.start_time

        # For rate smoothing
        self.smoothing_window = smoothing_window
        self.recent_snapshots: Deque[ProgressSnapshot] = deque(maxlen=smoothing_window)
        self.recent_snapshots.append(ProgressSnapshot(
            timestamp=self.start_time,
            bytes_completed=0,
            files_completed=0
        ))

    def update(
        self,
        bytes_completed: Optional[int] = None,
        files_completed: Optional[int] = None,
        current_file: Optional[str] = None
    ) -> EnhancedProgressInfo:
        """Update progress and get current info.

        Args:
            bytes_completed: Total bytes completed
            files_completed: Total files completed
            current_file: Name of current file being processed

        Returns:
            Enhanced progress information
        """
        now = time.time()

        # Update state
        if bytes_completed is not None:
            self.current_bytes = bytes_completed
        if files_completed is not None:
            self.files_completed = files_completed
        if current_file is not None:
            self.current_file = current_file

        # Add snapshot for rate calculation
        self.recent_snapshots.append(ProgressSnapshot(
            timestamp=now,
            bytes_completed=self.current_bytes,
            files_completed=self.files_completed
        ))

        # Calculate metrics
        percentage = self._calculate_percentage()
        bytes_per_second = self._calculate_rate()
        elapsed = now - self.start_time
        eta = self._calculate_eta(bytes_per_second)

        self.last_update_time = now

        return EnhancedProgressInfo(
            current_file=self.current_file,
            current_bytes=self.current_bytes,
            total_bytes=self.total_bytes,
            files_completed=self.files_completed,
            total_files=self.total_files,
            percentage=percentage,
            bytes_per_second=bytes_per_second,
            eta_seconds=eta,
            elapsed_seconds=elapsed,
            operation_type=self.operation_type,
            operation_id=self.operation_id
        )

    def add_bytes(self, byte_count: int, current_file: Optional[str] = None) -> EnhancedProgressInfo:
        """Add to bytes completed.

        Args:
            byte_count: Number of bytes to add
            current_file: Optional current file name

        Returns:
            Enhanced progress information
        """
        self.current_bytes += byte_count
        return self.update(current_file=current_file)

    def complete_file(self, filename: str) -> EnhancedProgressInfo:
        """Mark a file as completed.

        Args:
            filename: Name of completed file

        Returns:
            Enhanced progress information
        """
        self.files_completed += 1
        return self.update(current_file=filename)

    def _calculate_percentage(self) -> float:
        """Calculate completion percentage.

        Returns:
            Percentage complete (0-100)
        """
        if self.total_bytes == 0:
            return 100.0 if self.files_completed >= self.total_files else 0.0

        return min(100.0, (self.current_bytes / self.total_bytes) * 100.0)

    def _calculate_rate(self) -> float:
        """Calculate current transfer rate with smoothing.

        Returns:
            Bytes per second
        """
        if len(self.recent_snapshots) < 2:
            return 0.0

        # Use oldest and newest snapshots
        oldest = self.recent_snapshots[0]
        newest = self.recent_snapshots[-1]

        time_delta = newest.timestamp - oldest.timestamp
        if time_delta <= 0:
            return 0.0

        bytes_delta = newest.bytes_completed - oldest.bytes_completed
        rate = bytes_delta / time_delta

        return max(0.0, rate)

    def _calculate_eta(self, bytes_per_second: float) -> float:
        """Calculate estimated time to completion.

        Args:
            bytes_per_second: Current transfer rate

        Returns:
            Estimated seconds remaining
        """
        if bytes_per_second <= 0:
            return float('inf')

        remaining_bytes = self.total_bytes - self.current_bytes
        if remaining_bytes <= 0:
            return 0.0

        eta = remaining_bytes / bytes_per_second
        return eta

    def is_complete(self) -> bool:
        """Check if operation is complete.

        Returns:
            True if all files processed
        """
        return (self.files_completed >= self.total_files and
                self.current_bytes >= self.total_bytes)

    def get_summary(self) -> dict:
        """Get summary of progress.

        Returns:
            Dictionary with progress summary
        """
        elapsed = time.time() - self.start_time
        rate = self._calculate_rate()

        return {
            'operation_type': self.operation_type,
            'operation_id': self.operation_id,
            'total_bytes': self.total_bytes,
            'bytes_completed': self.current_bytes,
            'total_files': self.total_files,
            'files_completed': self.files_completed,
            'percentage': self._calculate_percentage(),
            'elapsed_seconds': elapsed,
            'bytes_per_second': rate,
            'eta_seconds': self._calculate_eta(rate),
            'is_complete': self.is_complete()
        }


def format_bytes(byte_count: float) -> str:
    """Format byte count as human-readable string.

    Args:
        byte_count: Number of bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(byte_count) < 1024.0:
            return f"{byte_count:.1f} {unit}"
        byte_count /= 1024.0
    return f"{byte_count:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2h 15m")
    """
    if seconds == float('inf'):
        return "Unknown"

    if seconds < 0:
        return "0s"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def format_rate(bytes_per_second: float) -> str:
    """Format transfer rate as human-readable string.

    Args:
        bytes_per_second: Transfer rate

    Returns:
        Formatted string (e.g., "1.5 MB/s")
    """
    return f"{format_bytes(bytes_per_second)}/s"
