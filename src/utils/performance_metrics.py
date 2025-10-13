"""
Performance Metrics and Monitoring System

Tracks and logs:
- Operation timing
- Memory usage
- Slow operation warnings
- Performance regression detection
- Resource utilization
"""

import time
import logging
import psutil
from functools import wraps
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from collections import deque, defaultdict
from datetime import datetime
import asyncio


logger = logging.getLogger(__name__)
perf_logger = logging.getLogger('dc_commander.performance')


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_start: int = 0
    memory_end: int = 0
    memory_delta: int = 0
    success: bool = True
    error: Optional[str] = None


@dataclass
class PerformanceStats:
    """Aggregate statistics for an operation type."""
    operation_name: str
    call_count: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    avg_duration: float = 0.0
    error_count: int = 0
    slow_count: int = 0  # Number of slow operations


class PerformanceMonitor:
    """Monitor and track performance metrics."""

    def __init__(
        self,
        slow_threshold: float = 5.0,
        history_size: int = 1000,
        enable_memory_tracking: bool = True
    ):
        """Initialize performance monitor.

        Args:
            slow_threshold: Duration threshold for slow operations (seconds)
            history_size: Number of operations to keep in history
            enable_memory_tracking: Whether to track memory usage
        """
        self.slow_threshold = slow_threshold
        self.history_size = history_size
        self.enable_memory_tracking = enable_memory_tracking

        self.operation_history: deque[OperationMetrics] = deque(maxlen=history_size)
        self.stats: Dict[str, PerformanceStats] = {}
        self.process = psutil.Process()

        # For regression detection
        self.baseline_durations: Dict[str, float] = {}

    def track_operation(self, operation_name: str, category: str = "general"):
        """Decorator to track operation performance.

        Args:
            operation_name: Name of operation
            category: Category for grouping

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    return await self._track_async_operation(
                        func, operation_name, category, *args, **kwargs
                    )
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    return self._track_sync_operation(
                        func, operation_name, category, *args, **kwargs
                    )
                return sync_wrapper
        return decorator

    def _track_sync_operation(
        self,
        func: Callable,
        operation_name: str,
        category: str,
        *args,
        **kwargs
    ) -> Any:
        """Track synchronous operation.

        Args:
            func: Function to track
            operation_name: Operation name
            category: Category
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        start_time = time.time()
        memory_start = self._get_memory_usage() if self.enable_memory_tracking else 0

        metrics = OperationMetrics(
            operation_name=operation_name,
            start_time=start_time,
            memory_start=memory_start
        )

        try:
            result = func(*args, **kwargs)
            metrics.success = True
            return result

        except Exception as e:
            metrics.success = False
            metrics.error = str(e)
            raise

        finally:
            end_time = time.time()
            metrics.end_time = end_time
            metrics.duration = end_time - start_time

            if self.enable_memory_tracking:
                metrics.memory_end = self._get_memory_usage()
                metrics.memory_delta = metrics.memory_end - metrics.memory_start

            self._record_metrics(metrics, category)

    async def _track_async_operation(
        self,
        func: Callable,
        operation_name: str,
        category: str,
        *args,
        **kwargs
    ) -> Any:
        """Track asynchronous operation.

        Args:
            func: Async function to track
            operation_name: Operation name
            category: Category
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        start_time = time.time()
        memory_start = self._get_memory_usage() if self.enable_memory_tracking else 0

        metrics = OperationMetrics(
            operation_name=operation_name,
            start_time=start_time,
            memory_start=memory_start
        )

        try:
            result = await func(*args, **kwargs)
            metrics.success = True
            return result

        except Exception as e:
            metrics.success = False
            metrics.error = str(e)
            raise

        finally:
            end_time = time.time()
            metrics.end_time = end_time
            metrics.duration = end_time - start_time

            if self.enable_memory_tracking:
                metrics.memory_end = self._get_memory_usage()
                metrics.memory_delta = metrics.memory_end - metrics.memory_start

            self._record_metrics(metrics, category)

    def _record_metrics(self, metrics: OperationMetrics, category: str) -> None:
        """Record metrics and update statistics.

        Args:
            metrics: Operation metrics
            category: Operation category
        """
        # Add to history
        self.operation_history.append(metrics)

        # Update statistics
        key = metrics.operation_name
        if key not in self.stats:
            self.stats[key] = PerformanceStats(operation_name=key)

        stats = self.stats[key]
        stats.call_count += 1
        stats.total_duration += metrics.duration

        if metrics.duration < stats.min_duration:
            stats.min_duration = metrics.duration
        if metrics.duration > stats.max_duration:
            stats.max_duration = metrics.duration

        stats.avg_duration = stats.total_duration / stats.call_count

        if not metrics.success:
            stats.error_count += 1

        if metrics.duration > self.slow_threshold:
            stats.slow_count += 1

        # Log metrics
        status = "SUCCESS" if metrics.success else "FAILED"
        perf_logger.info(
            f"{category.upper()}: {metrics.operation_name} - "
            f"Duration: {metrics.duration:.3f}s - "
            f"Memory: {self._format_bytes(metrics.memory_delta)} - "
            f"Status: {status}"
        )

        # Warn about slow operations
        if metrics.duration > self.slow_threshold:
            logger.warning(
                f"Slow operation detected: {metrics.operation_name} "
                f"took {metrics.duration:.1f}s (threshold: {self.slow_threshold}s)"
            )

        # Check for regression
        self._check_regression(metrics)

    def _check_regression(self, metrics: OperationMetrics) -> None:
        """Check if operation shows performance regression.

        Args:
            metrics: Operation metrics
        """
        key = metrics.operation_name

        # Need baseline for comparison
        if key not in self.baseline_durations:
            # First few calls establish baseline
            if key in self.stats and self.stats[key].call_count >= 5:
                self.baseline_durations[key] = self.stats[key].avg_duration
            return

        baseline = self.baseline_durations[key]

        # Check if current duration is significantly worse than baseline
        # Consider it a regression if >50% slower
        if metrics.duration > baseline * 1.5:
            logger.warning(
                f"Performance regression detected: {metrics.operation_name} - "
                f"Current: {metrics.duration:.3f}s vs Baseline: {baseline:.3f}s "
                f"({((metrics.duration / baseline - 1) * 100):.1f}% slower)"
            )

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes.

        Returns:
            Memory usage in bytes
        """
        try:
            return self.process.memory_info().rss
        except Exception:
            return 0

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes as human-readable string.

        Args:
            bytes_count: Number of bytes

        Returns:
            Formatted string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if abs(bytes_count) < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"

    def get_statistics(self, operation_name: Optional[str] = None) -> Dict:
        """Get performance statistics.

        Args:
            operation_name: Optional specific operation name

        Returns:
            Statistics dictionary
        """
        if operation_name:
            if operation_name in self.stats:
                stats = self.stats[operation_name]
                return {
                    'operation': stats.operation_name,
                    'calls': stats.call_count,
                    'total_duration': stats.total_duration,
                    'avg_duration': stats.avg_duration,
                    'min_duration': stats.min_duration,
                    'max_duration': stats.max_duration,
                    'errors': stats.error_count,
                    'slow_operations': stats.slow_count
                }
            return {}

        # Return all statistics
        return {
            op_name: {
                'calls': stats.call_count,
                'avg_duration': stats.avg_duration,
                'errors': stats.error_count,
                'slow_operations': stats.slow_count
            }
            for op_name, stats in self.stats.items()
        }

    def get_recent_operations(self, count: int = 10) -> List[Dict]:
        """Get recent operations.

        Args:
            count: Number of operations to return

        Returns:
            List of operation dictionaries
        """
        recent = list(self.operation_history)[-count:]
        return [
            {
                'operation': op.operation_name,
                'duration': op.duration,
                'memory_delta': op.memory_delta,
                'success': op.success,
                'timestamp': op.start_time
            }
            for op in recent
        ]

    def get_system_metrics(self) -> Dict:
        """Get current system metrics.

        Returns:
            System metrics dictionary
        """
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent(interval=0.1)

            return {
                'memory_rss': memory_info.rss,
                'memory_vms': memory_info.vms,
                'memory_percent': self.process.memory_percent(),
                'cpu_percent': cpu_percent,
                'num_threads': self.process.num_threads(),
                'num_fds': self.process.num_fds() if hasattr(self.process, 'num_fds') else 0
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}

    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self.operation_history.clear()
        self.stats.clear()
        self.baseline_durations.clear()
        logger.info("Performance statistics reset")

    def export_metrics(self) -> Dict:
        """Export all metrics for analysis.

        Returns:
            Complete metrics dictionary
        """
        return {
            'statistics': self.get_statistics(),
            'recent_operations': self.get_recent_operations(100),
            'system_metrics': self.get_system_metrics(),
            'slow_threshold': self.slow_threshold,
            'timestamp': datetime.now().isoformat()
        }


# Global performance monitor
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor.

    Returns:
        Global performance monitor
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def track_performance(operation_name: str, category: str = "general"):
    """Convenience decorator for tracking performance.

    Args:
        operation_name: Name of operation
        category: Category for grouping

    Returns:
        Decorator function
    """
    monitor = get_performance_monitor()
    return monitor.track_operation(operation_name, category)
