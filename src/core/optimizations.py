"""
Performance Optimization System

Provides:
- Incremental directory loading
- Predictive caching
- Memory optimization
- Background refresh
- Lazy loading
"""

import asyncio
from pathlib import Path
from typing import List, AsyncGenerator, Optional, Set, Callable
from dataclasses import dataclass
from datetime import datetime
import logging
from weakref import WeakValueDictionary


logger = logging.getLogger(__name__)


@dataclass
class LoadingProgress:
    """Progress information for incremental loading."""
    items_loaded: int
    total_estimated: int
    batch_number: int
    is_complete: bool


class IncrementalDirectoryLoader:
    """Load large directories incrementally for immediate UI response."""

    def __init__(self, batch_size: int = 1000):
        """Initialize incremental loader.

        Args:
            batch_size: Number of items per batch
        """
        self.batch_size = batch_size

    async def load_directory_incremental(
        self,
        path: Path,
        progress_callback: Optional[Callable[[LoadingProgress], None]] = None
    ) -> AsyncGenerator[List, None]:
        """Load directory in batches for immediate display.

        Args:
            path: Directory to load
            progress_callback: Optional progress callback

        Yields:
            Batches of file items
        """
        if not path.exists() or not path.is_dir():
            return

        items = []
        batch_number = 0
        total_items = 0

        try:
            # Estimate total items (quick scan)
            try:
                estimated_total = sum(1 for _ in path.iterdir())
            except Exception:
                estimated_total = 0

            # Load items in batches
            for entry in path.iterdir():
                try:
                    # Create file item (import here to avoid circular dependency)
                    from models.file_item import FileItem

                    stat = entry.stat()
                    item = FileItem(
                        name=entry.name,
                        path=entry,
                        size=stat.st_size if entry.is_file() else 0,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        is_dir=entry.is_dir()
                    )
                    items.append(item)
                    total_items += 1

                    # Yield batch when full
                    if len(items) >= self.batch_size:
                        batch_number += 1

                        if progress_callback:
                            progress_callback(LoadingProgress(
                                items_loaded=total_items,
                                total_estimated=estimated_total,
                                batch_number=batch_number,
                                is_complete=False
                            ))

                        yield items
                        items = []

                        # Allow UI updates
                        await asyncio.sleep(0)

                except (PermissionError, OSError) as e:
                    logger.debug(f"Skipping {entry}: {e}")
                    continue

            # Yield final batch
            if items:
                batch_number += 1

                if progress_callback:
                    progress_callback(LoadingProgress(
                        items_loaded=total_items,
                        total_estimated=estimated_total,
                        batch_number=batch_number,
                        is_complete=True
                    ))

                yield items

        except Exception as e:
            logger.error(f"Error loading directory {path}: {e}")


class PredictiveCache:
    """Preload sibling directories for faster navigation."""

    def __init__(self, max_preload: int = 3):
        """Initialize predictive cache.

        Args:
            max_preload: Maximum directories to preload
        """
        self.max_preload = max_preload
        self._preload_tasks: Set[asyncio.Task] = set()
        self._cache_loader: Optional[Callable] = None

    def set_cache_loader(self, loader: Callable) -> None:
        """Set cache loading function.

        Args:
            loader: Async function to load directory into cache
        """
        self._cache_loader = loader

    async def preload_siblings(self, current_path: Path) -> int:
        """Preload sibling directories in background.

        Args:
            current_path: Current directory path

        Returns:
            Number of directories queued for preload
        """
        if not self._cache_loader:
            return 0

        parent = current_path.parent
        if not parent.exists():
            return 0

        # Get sibling directories
        try:
            siblings = [
                p for p in parent.iterdir()
                if p.is_dir() and p != current_path
            ]
        except Exception as e:
            logger.debug(f"Failed to get siblings: {e}")
            return 0

        # Preload up to max_preload siblings
        preloaded = 0
        for sibling in siblings[:self.max_preload]:
            task = asyncio.create_task(self._preload_directory(sibling))
            self._preload_tasks.add(task)
            task.add_done_callback(self._preload_tasks.discard)
            preloaded += 1

        logger.debug(f"Preloading {preloaded} sibling directories")
        return preloaded

    async def _preload_directory(self, path: Path) -> None:
        """Preload directory into cache.

        Args:
            path: Directory to preload
        """
        try:
            if self._cache_loader:
                await self._cache_loader(path)
                logger.debug(f"Preloaded: {path}")
        except Exception as e:
            logger.debug(f"Preload failed for {path}: {e}")

    def cancel_preloads(self) -> None:
        """Cancel all pending preload tasks."""
        for task in self._preload_tasks:
            if not task.done():
                task.cancel()
        self._preload_tasks.clear()


class LazyFileItemCache:
    """Lazy-loading cache using weak references for memory efficiency."""

    def __init__(self):
        """Initialize lazy cache."""
        self._cache: WeakValueDictionary = WeakValueDictionary()
        self._string_cache: dict[str, str] = {}  # Intern common strings

    def get_or_create(self, path: Path, factory: Callable):
        """Get cached item or create new one.

        Args:
            path: File path
            factory: Function to create item if not cached

        Returns:
            File item
        """
        path_str = str(path)

        # Check cache
        if path_str in self._cache:
            return self._cache[path_str]

        # Create new item
        item = factory()
        self._cache[path_str] = item

        return item

    def intern_string(self, s: str) -> str:
        """Intern common strings to save memory.

        Args:
            s: String to intern

        Returns:
            Interned string
        """
        if s in self._string_cache:
            return self._string_cache[s]

        self._string_cache[s] = s
        return s

    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()
        self._string_cache.clear()


class BackgroundRefresher:
    """Background directory refresh to keep cache current."""

    def __init__(self, refresh_interval: int = 60):
        """Initialize background refresher.

        Args:
            refresh_interval: Refresh interval in seconds
        """
        self.refresh_interval = refresh_interval
        self._refresh_task: Optional[asyncio.Task] = None
        self._watched_dirs: Set[Path] = set()
        self._refresh_callback: Optional[Callable] = None

    def set_refresh_callback(self, callback: Callable) -> None:
        """Set callback for refresh notifications.

        Args:
            callback: Async function to call when directory changes
        """
        self._refresh_callback = callback

    def watch_directory(self, path: Path) -> None:
        """Add directory to watch list.

        Args:
            path: Directory to watch
        """
        self._watched_dirs.add(path)

    def unwatch_directory(self, path: Path) -> None:
        """Remove directory from watch list.

        Args:
            path: Directory to unwatch
        """
        self._watched_dirs.discard(path)

    async def start(self) -> None:
        """Start background refresh task."""
        if self._refresh_task and not self._refresh_task.done():
            return

        self._refresh_task = asyncio.create_task(self._refresh_loop())
        logger.info(f"Background refresh started (interval: {self.refresh_interval}s)")

    async def stop(self) -> None:
        """Stop background refresh task."""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        logger.info("Background refresh stopped")

    async def _refresh_loop(self) -> None:
        """Background refresh loop."""
        while True:
            try:
                await asyncio.sleep(self.refresh_interval)

                for directory in list(self._watched_dirs):
                    if not directory.exists():
                        self._watched_dirs.discard(directory)
                        continue

                    # Check if directory was modified
                    try:
                        current_mtime = directory.stat().st_mtime

                        # Notify callback if directory changed
                        if self._refresh_callback:
                            await self._refresh_callback(directory)

                    except Exception as e:
                        logger.debug(f"Refresh check failed for {directory}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in refresh loop: {e}")


class MemoryOptimizer:
    """Optimize memory usage through various strategies."""

    @staticmethod
    def optimize_file_items(items: List) -> List:
        """Optimize memory usage of file items.

        Args:
            items: List of file items

        Returns:
            Optimized list
        """
        # Intern common strings
        string_cache = {}

        def intern(s: str) -> str:
            if s in string_cache:
                return string_cache[s]
            string_cache[s] = s
            return s

        # Optimize each item
        for item in items:
            # Intern common extensions
            if hasattr(item, 'name'):
                parts = item.name.rsplit('.', 1)
                if len(parts) == 2:
                    item.name = f"{parts[0]}.{intern(parts[1])}"

        return items

    @staticmethod
    def estimate_memory_usage(items: List) -> int:
        """Estimate memory usage of item list.

        Args:
            items: List of file items

        Returns:
            Estimated bytes
        """
        import sys

        if not items:
            return 0

        # Sample first item
        sample = items[0]
        sample_size = sys.getsizeof(sample)

        # Add overhead for strings
        if hasattr(sample, 'name'):
            sample_size += sys.getsizeof(sample.name)
        if hasattr(sample, 'path'):
            sample_size += sys.getsizeof(str(sample.path))

        # Estimate total
        return sample_size * len(items)


# Global optimization instances
_predictive_cache: Optional[PredictiveCache] = None
_background_refresher: Optional[BackgroundRefresher] = None


def get_predictive_cache() -> PredictiveCache:
    """Get global predictive cache.

    Returns:
        Predictive cache instance
    """
    global _predictive_cache
    if _predictive_cache is None:
        _predictive_cache = PredictiveCache()
    return _predictive_cache


def get_background_refresher() -> BackgroundRefresher:
    """Get global background refresher.

    Returns:
        Background refresher instance
    """
    global _background_refresher
    if _background_refresher is None:
        _background_refresher = BackgroundRefresher()
    return _background_refresher
