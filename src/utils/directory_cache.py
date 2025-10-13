"""
Directory caching system for DC Commander.

Provides LRU cache with TTL for directory listings to improve performance.
Reduces filesystem access for frequently visited directories.

Usage:
    from src.utils.directory_cache import DirectoryCache

    cache = DirectoryCache(maxsize=100, ttl_seconds=60)

    # Get cached entries or load fresh
    entries = cache.get_or_load(path, loader_func)

    # Invalidate specific path
    cache.invalidate(path)

    # Clear entire cache
    cache.clear()
"""

from pathlib import Path
from typing import Optional, List, Callable, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass
from threading import Lock


T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with timestamp."""
    data: T
    timestamp: datetime
    path: Path

    def is_expired(self, ttl: timedelta) -> bool:
        """Check if entry is expired."""
        return datetime.now() - self.timestamp > ttl


class DirectoryCache(Generic[T]):
    """
    LRU cache with TTL for directory listings.

    Thread-safe implementation using Lock.
    """

    def __init__(self, maxsize: int = 100, ttl_seconds: int = 60):
        """
        Initialize directory cache.

        Args:
            maxsize: Maximum number of cached directories
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.maxsize = maxsize
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: dict[Path, CacheEntry[T]] = {}
        self._access_order: list[Path] = []  # LRU tracking
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, path: Path) -> Optional[T]:
        """
        Get cached directory listing.

        Args:
            path: Directory path

        Returns:
            Cached data if exists and not expired, None otherwise
        """
        with self._lock:
            if path not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[path]

            # Check if expired
            if entry.is_expired(self.ttl):
                self._remove(path)
                self._misses += 1
                return None

            # Update access order (move to end = most recently used)
            self._access_order.remove(path)
            self._access_order.append(path)

            self._hits += 1
            return entry.data

    def put(self, path: Path, data: T) -> None:
        """
        Store directory listing in cache.

        Args:
            path: Directory path
            data: Directory listing data
        """
        with self._lock:
            # If already exists, update
            if path in self._cache:
                self._access_order.remove(path)

            # Evict least recently used if at capacity
            if len(self._cache) >= self.maxsize:
                lru_path = self._access_order.pop(0)
                del self._cache[lru_path]

            # Add new entry
            entry = CacheEntry(
                data=data,
                timestamp=datetime.now(),
                path=path
            )
            self._cache[path] = entry
            self._access_order.append(path)

    def get_or_load(
        self,
        path: Path,
        loader: Callable[[Path], T]
    ) -> T:
        """
        Get from cache or load fresh data.

        Args:
            path: Directory path
            loader: Function to load data if not cached

        Returns:
            Cached or freshly loaded data
        """
        cached = self.get(path)
        if cached is not None:
            return cached

        # Load fresh data
        data = loader(path)
        self.put(path, data)
        return data

    def invalidate(self, path: Path) -> bool:
        """
        Invalidate specific cache entry.

        Args:
            path: Directory path to invalidate

        Returns:
            True if entry was found and removed
        """
        with self._lock:
            if path in self._cache:
                self._remove(path)
                return True
            return False

    def invalidate_tree(self, base_path: Path) -> int:
        """
        Invalidate all cached entries under base path.

        Args:
            base_path: Base directory path

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            to_remove = [
                p for p in self._cache.keys()
                if p == base_path or base_path in p.parents
            ]

            for path in to_remove:
                self._remove(path)

            return len(to_remove)

    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._hits = 0
            self._misses = 0

    def _remove(self, path: Path) -> None:
        """Remove entry (must be called with lock held)."""
        if path in self._cache:
            del self._cache[path]
            self._access_order.remove(path)

    @property
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            Hit rate as percentage (0-100)
        """
        with self._lock:
            total = self._hits + self._misses
            if total == 0:
                return 0.0
            return (self._hits / total) * 100.0

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        with self._lock:
            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self.hit_rate,
                "ttl_seconds": self.ttl.total_seconds()
            }


# Example usage in FilePanel:
"""
from src.utils.directory_cache import DirectoryCache
from models.file_item import FileItem

class FilePanel(Container):
    # Class-level cache shared across all panels
    _dir_cache = DirectoryCache[List[FileItem]](maxsize=100, ttl_seconds=60)

    def _load_directory(self) -> List[FileItem]:
        # Try cache first
        def loader(path: Path) -> List[FileItem]:
            items = []
            for entry in path.iterdir():
                try:
                    stat = entry.stat()
                    items.append(FileItem(
                        name=entry.name,
                        path=entry,
                        size=stat.st_size if entry.is_file() else 0,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        is_dir=entry.is_dir(),
                    ))
                except (PermissionError, OSError):
                    continue
            return items

        return self._dir_cache.get_or_load(self.current_path, loader)

    def refresh_directory(self, force: bool = False):
        # Force refresh bypasses cache
        if force:
            self._dir_cache.invalidate(self.current_path)

        self._file_items = self._load_directory()
        self._sort_and_display()
"""
