"""
Debug Overlay Component

Provides real-time debug information:
- Memory usage statistics
- Cache performance
- Active operations
- Performance metrics
- System resources
"""

import psutil
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, DataTable
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.reactive import reactive
import logging


logger = logging.getLogger(__name__)


class DebugOverlay(Screen):
    """Debug information overlay screen."""

    DEFAULT_CSS = """
    DebugOverlay {
        align: center middle;
        background: $background 80%;
    }

    DebugOverlay Container {
        width: 90;
        height: 35;
        border: thick $primary;
        background: $surface;
    }

    DebugOverlay .debug-header {
        width: 100%;
        background: $primary;
        color: $text;
        text-align: center;
        padding: 1;
        text-style: bold;
    }

    DebugOverlay .debug-section {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin: 1 0;
    }

    DebugOverlay .section-title {
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }

    DebugOverlay .stat-line {
        padding: 0 2;
    }

    DebugOverlay .stat-label {
        color: $text-muted;
        width: 25;
    }

    DebugOverlay .stat-value {
        color: $success;
        text-style: bold;
    }

    DebugOverlay Button {
        margin: 1 2;
    }

    DebugOverlay DataTable {
        height: 10;
        margin: 1 0;
    }
    """

    # Reactive properties
    refresh_interval: reactive[float] = reactive(1.0)

    def compose(self) -> ComposeResult:
        """Compose debug overlay widgets."""
        with Container():
            yield Static("🐛 Debug Information", classes="debug-header")

            with Vertical(classes="debug-section"):
                yield Static("System Resources", classes="section-title")
                yield Static("", id="memory-stats", classes="stat-line")
                yield Static("", id="cpu-stats", classes="stat-line")
                yield Static("", id="thread-stats", classes="stat-line")

            with Vertical(classes="debug-section"):
                yield Static("Cache Statistics", classes="section-title")
                yield Static("", id="cache-stats", classes="stat-line")
                yield Static("", id="cache-hit-rate", classes="stat-line")

            with Vertical(classes="debug-section"):
                yield Static("Performance Metrics", classes="section-title")
                yield Static("", id="perf-stats", classes="stat-line")

            with Vertical(classes="debug-section"):
                yield Static("Recent Operations", classes="section-title")
                table = DataTable(zebra_stripes=True)
                table.add_columns("Operation", "Duration", "Status")
                yield table

            with Horizontal():
                yield Button("Refresh Now", id="refresh-button", variant="primary")
                yield Button("Reset Stats", id="reset-button")
                yield Button("Close (Esc)", id="close-button", variant="error")

    def on_mount(self) -> None:
        """Initialize debug overlay on mount."""
        self.update_all_stats()
        self.set_interval(self.refresh_interval, self.update_all_stats)

    def update_all_stats(self) -> None:
        """Update all debug statistics."""
        self.update_system_stats()
        self.update_cache_stats()
        self.update_performance_stats()
        self.update_recent_operations()

    def update_system_stats(self) -> None:
        """Update system resource statistics."""
        try:
            process = psutil.Process()

            # Memory stats
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            memory_stat = self.query_one("#memory-stats", Static)
            memory_stat.update(
                f"Memory: {self._format_bytes(memory_info.rss)} "
                f"({memory_percent:.1f}%) "
                f"[Peak: {self._format_bytes(memory_info.vms)}]"
            )

            # CPU stats
            cpu_percent = process.cpu_percent(interval=0.1)
            cpu_stat = self.query_one("#cpu-stats", Static)
            cpu_stat.update(f"CPU: {cpu_percent:.1f}%")

            # Thread stats
            num_threads = process.num_threads()
            thread_stat = self.query_one("#thread-stats", Static)
            thread_stat.update(f"Threads: {num_threads}")

        except Exception as e:
            logger.error(f"Failed to update system stats: {e}")

    def update_cache_stats(self) -> None:
        """Update cache statistics."""
        try:
            from components.file_panel import FilePanel

            cache_stats = FilePanel.get_cache_stats()
            if cache_stats:
                cache_stat = self.query_one("#cache-stats", Static)
                cache_stat.update(
                    f"Cache: {cache_stats['size']}/{cache_stats['maxsize']} entries "
                    f"(Memory: ~{self._format_bytes(cache_stats.get('memory_usage', 0))})"
                )

                hit_rate_stat = self.query_one("#cache-hit-rate", Static)
                hit_rate_stat.update(
                    f"Hit Rate: {cache_stats['hit_rate']:.1f}% "
                    f"({cache_stats['hits']}/{cache_stats['hits'] + cache_stats['misses']} requests)"
                )
            else:
                cache_stat = self.query_one("#cache-stats", Static)
                cache_stat.update("Cache: Disabled")

                hit_rate_stat = self.query_one("#cache-hit-rate", Static)
                hit_rate_stat.update("")

        except Exception as e:
            logger.error(f"Failed to update cache stats: {e}")

    def update_performance_stats(self) -> None:
        """Update performance metrics."""
        try:
            from src.utils.performance_metrics import get_performance_monitor

            monitor = get_performance_monitor()
            stats = monitor.get_statistics()

            if stats:
                total_ops = sum(s['calls'] for s in stats.values())
                avg_duration = sum(s['avg_duration'] * s['calls'] for s in stats.values()) / total_ops if total_ops > 0 else 0
                total_errors = sum(s['errors'] for s in stats.values())

                perf_stat = self.query_one("#perf-stats", Static)
                perf_stat.update(
                    f"Operations: {total_ops} total | "
                    f"Avg: {avg_duration:.3f}s | "
                    f"Errors: {total_errors}"
                )
            else:
                perf_stat = self.query_one("#perf-stats", Static)
                perf_stat.update("No performance data available")

        except Exception as e:
            logger.error(f"Failed to update performance stats: {e}")

    def update_recent_operations(self) -> None:
        """Update recent operations table."""
        try:
            from src.utils.performance_metrics import get_performance_monitor

            monitor = get_performance_monitor()
            recent = monitor.get_recent_operations(10)

            table = self.query_one(DataTable)
            table.clear()

            for op in reversed(recent):  # Show newest first
                status = "✓" if op['success'] else "✗"
                table.add_row(
                    op['operation'][:30],  # Truncate long names
                    f"{op['duration']:.3f}s",
                    status
                )

        except Exception as e:
            logger.error(f"Failed to update recent operations: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button press event
        """
        button_id = event.button.id

        if button_id == "close-button":
            self.app.pop_screen()

        elif button_id == "refresh-button":
            self.update_all_stats()
            self.notify("Debug stats refreshed")

        elif button_id == "reset-button":
            try:
                from src.utils.performance_metrics import get_performance_monitor

                monitor = get_performance_monitor()
                monitor.reset_statistics()

                self.update_all_stats()
                self.notify("Performance statistics reset")

            except Exception as e:
                self.notify(f"Failed to reset stats: {e}", severity="error")

    def on_key(self, event) -> None:
        """Handle key events.

        Args:
            event: Key event
        """
        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "r":
            self.update_all_stats()

    def _format_bytes(self, byte_count: int) -> str:
        """Format bytes as human-readable string.

        Args:
            byte_count: Number of bytes

        Returns:
            Formatted string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(byte_count) < 1024.0:
                return f"{byte_count:.1f} {unit}"
            byte_count /= 1024.0
        return f"{byte_count:.1f} PB"


class CompactDebugInfo(Static):
    """Compact debug info for status bar."""

    DEFAULT_CSS = """
    CompactDebugInfo {
        width: auto;
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text-muted;
    }
    """

    def on_mount(self) -> None:
        """Initialize compact debug info."""
        self.set_interval(2.0, self.update_compact_info)
        self.update_compact_info()

    def update_compact_info(self) -> None:
        """Update compact debug information."""
        try:
            process = psutil.Process()

            # Get quick stats
            memory_mb = process.memory_info().rss / (1024 * 1024)
            cpu_percent = process.cpu_percent(interval=0.1)

            # Get cache stats if available
            cache_str = ""
            try:
                from components.file_panel import FilePanel
                cache_stats = FilePanel.get_cache_stats()
                if cache_stats:
                    cache_str = f" | Cache: {cache_stats['hit_rate']:.0f}%"
            except Exception:
                pass

            # Update display
            self.update(
                f"🐛 Mem: {memory_mb:.0f}MB | CPU: {cpu_percent:.0f}%{cache_str}"
            )

        except Exception as e:
            self.update(f"🐛 Debug: Error ({str(e)[:20]})")
