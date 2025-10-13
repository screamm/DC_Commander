"""
DC Commander - Search Result Caching System

High-performance caching for search results with TTL, LRU eviction,
and memory-efficient storage.

Features:
- TTL-based expiration
- LRU eviction policy
- Memory usage limits
- Thread-safe operations
"""

import time
import hashlib
from pathlib import Path
from typing import List, Optional, Any, Dict, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
from threading import RLock
from datetime import datetime, timedelta


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    ttl: float  # Time to live in seconds
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return (time.time() - self.created_at) > self.ttl

    def touch(self) -> None:
        """Update access metadata"""
        self.access_count += 1
        self.last_access = time.time()


class SearchResultCache:
    """
    LRU cache with TTL for search results

    Features:
    - Time-to-live expiration
    - LRU eviction when memory limit reached
    - Thread-safe operations
    - Statistics tracking
    """

    def __init__(
        self,
        max_entries: int = 1000,
        default_ttl: float = 300.0,  # 5 minutes
        max_memory_mb: float = 50.0
    ):
        """
        Initialize search result cache

        Args:
            max_entries: Maximum number of cached entries
            default_ttl: Default time-to-live in seconds
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._current_memory = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired():
                self._remove_entry(key)
                self._misses += 1
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            entry.touch()
            self._hits += 1

            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None
    ) -> None:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self._lock:
            # Estimate size (rough approximation)
            size_bytes = self._estimate_size(value)

            # Check if we need to evict
            while (
                (len(self._cache) >= self.max_entries or
                 self._current_memory + size_bytes > self.max_memory_bytes)
                and self._cache
            ):
                self._evict_lru()

            # Remove old entry if exists
            if key in self._cache:
                self._remove_entry(key)

            # Add new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl or self.default_ttl,
                size_bytes=size_bytes
            )

            self._cache[key] = entry
            self._current_memory += size_bytes

    def invalidate(self, key: str) -> bool:
        """
        Invalidate cache entry

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was removed
        """
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all entries matching pattern

        Args:
            pattern: Key pattern to match (simple substring match)

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = [
                k for k in self._cache.keys()
                if pattern in k
            ]

            for key in keys_to_remove:
                self._remove_entry(key)

            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
            self._evictions = 0

    def cleanup_expired(self) -> int:
        """
        Remove expired entries

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if v.is_expired()
            ]

            for key in expired_keys:
                self._remove_entry(key)

            return len(expired_keys)

    def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if not self._cache:
            return

        # Remove first item (least recently used)
        key = next(iter(self._cache))
        self._remove_entry(key)
        self._evictions += 1

    def _remove_entry(self, key: str) -> None:
        """Remove entry and update memory tracking"""
        if key in self._cache:
            entry = self._cache[key]
            self._current_memory -= entry.size_bytes
            del self._cache[key]

    @staticmethod
    def _estimate_size(value: Any) -> int:
        """Estimate memory size of value (rough approximation)"""
        if isinstance(value, (list, tuple)):
            # Estimate based on length
            return len(value) * 100  # ~100 bytes per item
        elif isinstance(value, dict):
            return len(value) * 200  # ~200 bytes per dict entry
        elif isinstance(value, str):
            return len(value)
        else:
            return 1000  # Default estimate

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0

            return {
                'entries': len(self._cache),
                'max_entries': self.max_entries,
                'memory_bytes': self._current_memory,
                'memory_mb': self._current_memory / (1024 * 1024),
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'evictions': self._evictions,
                'avg_ttl': sum(e.ttl for e in self._cache.values()) / len(self._cache)
                if self._cache else 0
            }


class QueryCache:
    """
    High-level cache for search queries

    Generates cache keys from query parameters and manages result caching
    """

    def __init__(
        self,
        max_entries: int = 1000,
        default_ttl: float = 300.0,
        max_memory_mb: float = 50.0
    ):
        """
        Initialize query cache

        Args:
            max_entries: Maximum cached queries
            default_ttl: Default TTL in seconds
            max_memory_mb: Maximum memory usage in MB
        """
        self.cache = SearchResultCache(max_entries, default_ttl, max_memory_mb)

    def make_key(
        self,
        root_path: Path,
        pattern: str,
        search_type: str,
        **options
    ) -> str:
        """
        Generate cache key from query parameters

        Args:
            root_path: Search root path
            pattern: Search pattern
            search_type: Type of search (filename, content, etc.)
            **options: Additional search options

        Returns:
            Cache key string
        """
        # Create deterministic key from parameters
        key_parts = [
            str(root_path),
            pattern,
            search_type,
            str(sorted(options.items()))
        ]

        key_str = '|'.join(key_parts)
        # Use hash for shorter keys
        key_hash = hashlib.md5(key_str.encode()).hexdigest()

        return f"{search_type}:{key_hash}"

    def get_results(
        self,
        root_path: Path,
        pattern: str,
        search_type: str,
        **options
    ) -> Optional[List[Any]]:
        """
        Get cached search results

        Args:
            root_path: Search root path
            pattern: Search pattern
            search_type: Type of search
            **options: Search options

        Returns:
            Cached results or None
        """
        key = self.make_key(root_path, pattern, search_type, **options)
        return self.cache.get(key)

    def cache_results(
        self,
        root_path: Path,
        pattern: str,
        search_type: str,
        results: List[Any],
        ttl: Optional[float] = None,
        **options
    ) -> None:
        """
        Cache search results

        Args:
            root_path: Search root path
            pattern: Search pattern
            search_type: Type of search
            results: Results to cache
            ttl: Time-to-live override
            **options: Search options
        """
        key = self.make_key(root_path, pattern, search_type, **options)
        self.cache.set(key, results, ttl)

    def invalidate_path(self, root_path: Path) -> int:
        """
        Invalidate all cache entries for a path

        Args:
            root_path: Path to invalidate

        Returns:
            Number of entries invalidated
        """
        return self.cache.invalidate_pattern(str(root_path))

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()


class SearchHistoryCache:
    """
    Cache for search history with autocomplete support

    Tracks recent searches and provides completion suggestions
    """

    def __init__(self, max_history: int = 100):
        """
        Initialize search history cache

        Args:
            max_history: Maximum history entries to keep
        """
        self.max_history = max_history
        self._history: List[Tuple[str, datetime]] = []
        self._frequency: Dict[str, int] = {}
        self._lock = RLock()

    def add_search(self, query: str) -> None:
        """
        Add search to history

        Args:
            query: Search query string
        """
        with self._lock:
            # Add to history
            self._history.append((query, datetime.now()))

            # Track frequency
            self._frequency[query] = self._frequency.get(query, 0) + 1

            # Trim history if needed
            if len(self._history) > self.max_history:
                # Remove oldest, excluding frequent queries
                self._history = self._history[-self.max_history:]

    def get_completions(
        self,
        prefix: str,
        max_results: int = 10
    ) -> List[str]:
        """
        Get autocomplete suggestions

        Args:
            prefix: Query prefix to match
            max_results: Maximum suggestions to return

        Returns:
            List of completion suggestions sorted by frequency
        """
        with self._lock:
            prefix_lower = prefix.lower()

            # Find matching queries
            matches = [
                (query, freq)
                for query, freq in self._frequency.items()
                if query.lower().startswith(prefix_lower)
            ]

            # Sort by frequency (descending) and recency
            matches.sort(key=lambda x: x[1], reverse=True)

            return [query for query, _ in matches[:max_results]]

    def get_recent(self, limit: int = 10) -> List[Tuple[str, datetime]]:
        """
        Get recent searches

        Args:
            limit: Maximum results to return

        Returns:
            List of (query, timestamp) tuples
        """
        with self._lock:
            return list(reversed(self._history[-limit:]))

    def clear(self) -> None:
        """Clear search history"""
        with self._lock:
            self._history.clear()
            self._frequency.clear()
