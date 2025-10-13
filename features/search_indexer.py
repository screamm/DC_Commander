"""
DC Commander - Advanced Search Indexing System

High-performance search indexing for fast file lookups with incremental updates,
memory-efficient storage, and concurrent access support.

Performance Targets:
- Index build: <1s for 10,000 files
- Search query: <100ms for indexed directories
- Memory: <100MB for 100,000 files
- Incremental updates: <10ms per file change
"""

import pickle
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from threading import RLock
import mmap


@dataclass
class IndexEntry:
    """Single file index entry with metadata"""
    path: Path
    name: str
    name_lower: str  # For case-insensitive search
    size: int
    modified: float
    extension: str
    # Trigram index for fuzzy matching
    trigrams: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Generate trigrams from filename for fuzzy matching"""
        if not self.trigrams:
            self.trigrams = self._generate_trigrams(self.name_lower)

    @staticmethod
    def _generate_trigrams(text: str) -> Set[str]:
        """Generate trigram set from text for fuzzy matching"""
        if len(text) < 3:
            return {text}
        return {text[i:i+3] for i in range(len(text) - 2)}

    @classmethod
    def from_path(cls, file_path: Path) -> 'IndexEntry':
        """Create index entry from file path"""
        try:
            stat = file_path.stat()
            return cls(
                path=file_path,
                name=file_path.name,
                name_lower=file_path.name.lower(),
                size=stat.st_size,
                modified=stat.st_mtime,
                extension=file_path.suffix.lower()
            )
        except (OSError, PermissionError) as e:
            raise ValueError(f"Cannot index file {file_path}: {e}")


@dataclass
class SearchIndex:
    """In-memory search index with fast lookup capabilities"""
    # Core indices
    entries: List[IndexEntry] = field(default_factory=list)
    path_map: Dict[Path, int] = field(default_factory=dict)  # path -> entry index

    # Fast lookup indices
    name_index: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    extension_index: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    trigram_index: Dict[str, Set[int]] = field(default_factory=lambda: defaultdict(set))

    # Metadata
    root_path: Optional[Path] = None
    indexed_at: Optional[datetime] = None
    file_count: int = 0

    # Thread safety
    _lock: RLock = field(default_factory=RLock)

    def add_entry(self, entry: IndexEntry) -> None:
        """Add or update entry in index"""
        with self._lock:
            # Update or add entry
            if entry.path in self.path_map:
                idx = self.path_map[entry.path]
                old_entry = self.entries[idx]
                # Remove old indices
                self._remove_indices(old_entry, idx)
                self.entries[idx] = entry
            else:
                idx = len(self.entries)
                self.entries.append(entry)
                self.path_map[entry.path] = idx
                self.file_count += 1

            # Add new indices
            self._add_indices(entry, idx)

    def remove_entry(self, file_path: Path) -> bool:
        """Remove entry from index"""
        with self._lock:
            if file_path not in self.path_map:
                return False

            idx = self.path_map[file_path]
            entry = self.entries[idx]

            # Remove from indices
            self._remove_indices(entry, idx)

            # Mark as deleted (don't remove to preserve indices)
            self.entries[idx] = None
            del self.path_map[file_path]
            self.file_count -= 1
            return True

    def _add_indices(self, entry: IndexEntry, idx: int) -> None:
        """Add entry to all indices"""
        # Name index (case-insensitive)
        self.name_index[entry.name_lower].append(idx)

        # Extension index
        if entry.extension:
            self.extension_index[entry.extension].append(idx)

        # Trigram index for fuzzy search
        for trigram in entry.trigrams:
            self.trigram_index[trigram].add(idx)

    def _remove_indices(self, entry: IndexEntry, idx: int) -> None:
        """Remove entry from all indices"""
        # Name index
        if entry.name_lower in self.name_index:
            try:
                self.name_index[entry.name_lower].remove(idx)
            except ValueError:
                pass

        # Extension index
        if entry.extension and entry.extension in self.extension_index:
            try:
                self.extension_index[entry.extension].remove(idx)
            except ValueError:
                pass

        # Trigram index
        for trigram in entry.trigrams:
            if trigram in self.trigram_index:
                self.trigram_index[trigram].discard(idx)

    def search_exact(self, filename: str, case_sensitive: bool = False) -> List[IndexEntry]:
        """Search for exact filename match"""
        with self._lock:
            search_name = filename if case_sensitive else filename.lower()

            if case_sensitive:
                # Linear search for case-sensitive
                return [e for e in self.entries if e and e.name == filename]
            else:
                # Use index for case-insensitive
                indices = self.name_index.get(search_name, [])
                return [self.entries[i] for i in indices if self.entries[i]]

    def search_prefix(self, prefix: str, case_sensitive: bool = False) -> List[IndexEntry]:
        """Search for filenames starting with prefix"""
        with self._lock:
            search_prefix = prefix if case_sensitive else prefix.lower()
            results = []

            for name, indices in self.name_index.items():
                if name.startswith(search_prefix):
                    results.extend([self.entries[i] for i in indices if self.entries[i]])

            return results

    def search_fuzzy(self, pattern: str, max_results: int = 100) -> List[Tuple[IndexEntry, float]]:
        """
        Fuzzy search using trigram matching

        Returns list of (entry, similarity_score) tuples sorted by score
        """
        with self._lock:
            pattern_lower = pattern.lower()
            pattern_trigrams = IndexEntry._generate_trigrams(pattern_lower)

            if not pattern_trigrams:
                return []

            # Count trigram matches for each file
            match_counts = defaultdict(int)
            for trigram in pattern_trigrams:
                if trigram in self.trigram_index:
                    for idx in self.trigram_index[trigram]:
                        if self.entries[idx]:
                            match_counts[idx] += 1

            # Calculate similarity scores (Jaccard similarity)
            results = []
            for idx, count in match_counts.items():
                entry = self.entries[idx]
                if not entry:
                    continue

                # Jaccard similarity: |intersection| / |union|
                union_size = len(pattern_trigrams) + len(entry.trigrams) - count
                similarity = count / union_size if union_size > 0 else 0

                # Boost exact matches and prefix matches
                if entry.name_lower == pattern_lower:
                    similarity = 1.0
                elif entry.name_lower.startswith(pattern_lower):
                    similarity = max(similarity, 0.9)

                results.append((entry, similarity))

            # Sort by similarity (descending) and limit results
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:max_results]

    def search_by_extension(self, extension: str) -> List[IndexEntry]:
        """Search for files by extension"""
        with self._lock:
            ext = extension.lower() if not extension.startswith('.') else extension[1:].lower()
            ext = f'.{ext}' if not ext.startswith('.') else ext

            indices = self.extension_index.get(ext, [])
            return [self.entries[i] for i in indices if self.entries[i]]

    def get_statistics(self) -> Dict[str, any]:
        """Get index statistics"""
        with self._lock:
            total_size = sum(e.size for e in self.entries if e)
            extensions = defaultdict(int)
            for e in self.entries:
                if e and e.extension:
                    extensions[e.extension] += 1

            return {
                'file_count': self.file_count,
                'total_size': total_size,
                'indexed_at': self.indexed_at,
                'root_path': str(self.root_path) if self.root_path else None,
                'extensions': dict(extensions),
                'memory_entries': len(self.entries),
                'index_sizes': {
                    'name_index': len(self.name_index),
                    'extension_index': len(self.extension_index),
                    'trigram_index': len(self.trigram_index)
                }
            }


class FileIndexer:
    """
    High-performance file indexer with incremental updates

    Features:
    - Fast initial indexing (<1s for 10,000 files)
    - Incremental updates on file changes
    - Memory-efficient storage
    - Persistent index caching
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize file indexer

        Args:
            cache_dir: Directory for index cache (default: system temp)
        """
        self.cache_dir = cache_dir or Path.home() / '.dc_commander' / 'index_cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._indices: Dict[Path, SearchIndex] = {}
        self._lock = RLock()

    def build_index(
        self,
        root_path: Path,
        exclude_dirs: Optional[Set[str]] = None,
        max_depth: Optional[int] = None,
        force_rebuild: bool = False
    ) -> SearchIndex:
        """
        Build search index for directory

        Args:
            root_path: Root directory to index
            exclude_dirs: Directory names to exclude
            max_depth: Maximum recursion depth
            force_rebuild: Force rebuild even if cache exists

        Returns:
            SearchIndex for the directory
        """
        root_path = Path(root_path).resolve()

        # Check cache first
        if not force_rebuild:
            cached_index = self._load_cached_index(root_path)
            if cached_index and self._is_index_valid(cached_index, root_path):
                with self._lock:
                    self._indices[root_path] = cached_index
                return cached_index

        # Build new index
        start_time = time.time()
        index = SearchIndex(root_path=root_path, indexed_at=datetime.now())

        exclude_dirs = exclude_dirs or {
            '.git', '.svn', '__pycache__', 'node_modules', '.venv', 'venv'
        }

        # Walk directory and build index
        self._walk_and_index(root_path, index, exclude_dirs, max_depth)

        build_time = time.time() - start_time

        # Cache the index
        self._save_index_cache(root_path, index)

        with self._lock:
            self._indices[root_path] = index

        print(f"Indexed {index.file_count} files in {build_time:.3f}s "
              f"({index.file_count/build_time:.0f} files/s)")

        return index

    def _walk_and_index(
        self,
        path: Path,
        index: SearchIndex,
        exclude_dirs: Set[str],
        max_depth: Optional[int],
        current_depth: int = 0
    ) -> None:
        """Recursively walk directory and add to index"""
        if max_depth is not None and current_depth > max_depth:
            return

        try:
            for item in path.iterdir():
                try:
                    if item.is_dir():
                        if item.name not in exclude_dirs:
                            self._walk_and_index(
                                item, index, exclude_dirs, max_depth, current_depth + 1
                            )
                    elif item.is_file():
                        entry = IndexEntry.from_path(item)
                        index.add_entry(entry)
                except (OSError, PermissionError, ValueError):
                    continue
        except (OSError, PermissionError):
            pass

    def update_file(self, root_path: Path, file_path: Path) -> bool:
        """
        Update single file in index (incremental update)

        Args:
            root_path: Root path of index
            file_path: File that changed

        Returns:
            True if updated successfully
        """
        with self._lock:
            if root_path not in self._indices:
                return False

            index = self._indices[root_path]

            try:
                if file_path.exists():
                    entry = IndexEntry.from_path(file_path)
                    index.add_entry(entry)
                else:
                    index.remove_entry(file_path)
                return True
            except (OSError, PermissionError, ValueError):
                return False

    def get_index(self, root_path: Path) -> Optional[SearchIndex]:
        """Get index for root path"""
        with self._lock:
            return self._indices.get(Path(root_path).resolve())

    def _get_cache_path(self, root_path: Path) -> Path:
        """Get cache file path for root directory"""
        # Use hash of path for cache filename
        path_hash = hashlib.md5(str(root_path).encode()).hexdigest()
        return self.cache_dir / f'index_{path_hash}.pkl'

    def _save_index_cache(self, root_path: Path, index: SearchIndex) -> None:
        """Save index to cache"""
        try:
            cache_path = self._get_cache_path(root_path)
            with open(cache_path, 'wb') as f:
                pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            print(f"Warning: Failed to cache index: {e}")

    def _load_cached_index(self, root_path: Path) -> Optional[SearchIndex]:
        """Load index from cache"""
        try:
            cache_path = self._get_cache_path(root_path)
            if not cache_path.exists():
                return None

            with open(cache_path, 'rb') as f:
                index = pickle.load(f)

            return index
        except Exception as e:
            print(f"Warning: Failed to load cached index: {e}")
            return None

    def _is_index_valid(self, index: SearchIndex, root_path: Path) -> bool:
        """
        Check if cached index is still valid

        Uses sampling approach: check a few files to detect changes
        """
        if not index.indexed_at or index.file_count == 0:
            return False

        # Sample 10% of files (max 100) to validate
        sample_size = min(100, max(10, index.file_count // 10))
        sample_indices = range(0, len(index.entries), len(index.entries) // sample_size)

        for idx in sample_indices:
            entry = index.entries[idx]
            if not entry:
                continue

            try:
                if not entry.path.exists():
                    return False

                stat = entry.path.stat()
                if abs(stat.st_mtime - entry.modified) > 0.1:  # 100ms tolerance
                    return False
            except (OSError, PermissionError):
                return False

        return True

    def clear_cache(self, root_path: Optional[Path] = None) -> None:
        """Clear index cache"""
        if root_path:
            cache_path = self._get_cache_path(Path(root_path).resolve())
            cache_path.unlink(missing_ok=True)
            with self._lock:
                self._indices.pop(Path(root_path).resolve(), None)
        else:
            # Clear all caches
            for cache_file in self.cache_dir.glob('index_*.pkl'):
                cache_file.unlink()
            with self._lock:
                self._indices.clear()
