"""
DC Commander - Advanced Search Engine with Indexing and Fuzzy Matching

Combines indexing, caching, and fuzzy matching for high-performance search.

Performance Features:
- Indexed search: <100ms for 100,000+ files
- Result caching with TTL
- Fuzzy matching with trigrams
- Regex pattern support
- Content search for text files
- Search history with autocomplete
"""

import re
import fnmatch
from pathlib import Path
from typing import List, Optional, Generator, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

from features.search_engine import (
    SearchOptions, SearchResult, FileFilter, FilterCriteria,
    LogicalOperator, FilterOperator
)
from features.search_indexer import FileIndexer, SearchIndex, IndexEntry
from features.search_cache import QueryCache, SearchHistoryCache


@dataclass
class AdvancedSearchOptions(SearchOptions):
    """Extended search options with advanced features"""
    use_index: bool = True  # Use index for faster search
    use_cache: bool = True  # Use result caching
    fuzzy_threshold: float = 0.6  # Minimum similarity for fuzzy match
    max_fuzzy_results: int = 100  # Max fuzzy match results


class AdvancedFileSearch:
    """
    Advanced search engine with indexing, caching, and fuzzy matching

    Performance targets:
    - Index build: <1s for 10,000 files
    - Indexed search: <100ms
    - Fuzzy search: <200ms
    - Cache hit: <10ms
    """

    def __init__(
        self,
        cache_ttl: float = 300.0,  # 5 minutes
        max_cache_entries: int = 1000
    ):
        """
        Initialize advanced search engine

        Args:
            cache_ttl: Cache time-to-live in seconds
            max_cache_entries: Maximum cached queries
        """
        self.indexer = FileIndexer()
        self.query_cache = QueryCache(
            max_entries=max_cache_entries,
            default_ttl=cache_ttl
        )
        self.history = SearchHistoryCache()

    def search_files(
        self,
        root_path: Path,
        pattern: str,
        options: Optional[AdvancedSearchOptions] = None
    ) -> List[SearchResult]:
        """
        Search for files with advanced features

        Args:
            root_path: Root directory to search
            pattern: Search pattern (supports wildcards, regex, fuzzy)
            options: Advanced search options

        Returns:
            List of search results
        """
        if options is None:
            options = AdvancedSearchOptions()

        root_path = Path(root_path).resolve()

        # Check cache first
        if options.use_cache:
            cached = self._get_cached_results(root_path, pattern, 'filename', options)
            if cached is not None:
                return cached

        # Add to history
        self.history.add_search(pattern)

        # Perform search
        if options.use_index:
            results = self._indexed_search(root_path, pattern, options)
        else:
            results = self._traditional_search(root_path, pattern, options)

        # Apply additional filters if specified
        if hasattr(options, 'criteria') and options.criteria:
            results = self._apply_filters(results, options.criteria)

        # Limit results
        if options.max_results:
            results = results[:options.max_results]

        # Cache results
        if options.use_cache:
            self._cache_results(root_path, pattern, 'filename', results, options)

        return results

    def search_fuzzy(
        self,
        root_path: Path,
        pattern: str,
        options: Optional[AdvancedSearchOptions] = None
    ) -> List[Tuple[SearchResult, float]]:
        """
        Fuzzy search for files (typo-tolerant)

        Args:
            root_path: Root directory to search
            pattern: Search pattern
            options: Search options

        Returns:
            List of (SearchResult, similarity_score) tuples
        """
        if options is None:
            options = AdvancedSearchOptions()

        root_path = Path(root_path).resolve()

        # Check cache
        if options.use_cache:
            cached = self._get_cached_results(root_path, pattern, 'fuzzy', options)
            if cached is not None:
                return cached

        # Build/get index
        index = self.indexer.build_index(
            root_path,
            exclude_dirs=options.exclude_directories,
            max_depth=options.max_depth
        )

        # Fuzzy search
        fuzzy_results = index.search_fuzzy(
            pattern,
            max_results=options.max_fuzzy_results
        )

        # Filter by threshold
        filtered = [
            (entry, score)
            for entry, score in fuzzy_results
            if score >= options.fuzzy_threshold
        ]

        # Convert to SearchResult
        results = [
            (SearchResult(path=entry.path), score)
            for entry, score in filtered
        ]

        # Cache results
        if options.use_cache:
            self._cache_results(root_path, pattern, 'fuzzy', results, options)

        return results

    def search_regex(
        self,
        root_path: Path,
        regex_pattern: str,
        options: Optional[AdvancedSearchOptions] = None
    ) -> List[SearchResult]:
        """
        Search using regex pattern

        Args:
            root_path: Root directory to search
            regex_pattern: Regular expression pattern
            options: Search options

        Returns:
            List of search results
        """
        if options is None:
            options = AdvancedSearchOptions()

        options.use_regex = True
        return self.search_files(root_path, regex_pattern, options)

    def search_by_criteria(
        self,
        root_path: Path,
        criteria: FilterCriteria,
        options: Optional[AdvancedSearchOptions] = None
    ) -> List[Path]:
        """
        Search using filter criteria

        Args:
            root_path: Root directory to search
            criteria: Filter criteria
            options: Search options

        Returns:
            List of matching file paths
        """
        if options is None:
            options = AdvancedSearchOptions()

        root_path = Path(root_path).resolve()

        # Get all files from index or walk
        if options.use_index:
            index = self.indexer.build_index(
                root_path,
                exclude_dirs=options.exclude_directories,
                max_depth=options.max_depth
            )
            files = [entry.path for entry in index.entries if entry]
        else:
            from features.search_engine import FileSearch
            searcher = FileSearch()
            files = list(searcher._walk_directory(root_path, options))

        # Apply criteria
        results = []
        for file_path in files:
            try:
                stat = file_path.stat()
                if criteria.matches(file_path, stat):
                    results.append(file_path)
                    if options.max_results and len(results) >= options.max_results:
                        break
            except (OSError, PermissionError):
                continue

        return results

    def get_completions(self, prefix: str, limit: int = 10) -> List[str]:
        """
        Get search autocomplete suggestions

        Args:
            prefix: Query prefix
            limit: Maximum suggestions

        Returns:
            List of completion suggestions
        """
        return self.history.get_completions(prefix, limit)

    def get_recent_searches(self, limit: int = 10) -> List[Tuple[str, datetime]]:
        """
        Get recent search queries

        Args:
            limit: Maximum results

        Returns:
            List of (query, timestamp) tuples
        """
        return self.history.get_recent(limit)

    def rebuild_index(self, root_path: Path) -> SearchIndex:
        """
        Force rebuild index for directory

        Args:
            root_path: Root path to reindex

        Returns:
            New search index
        """
        root_path = Path(root_path).resolve()

        # Clear cache for this path
        self.query_cache.invalidate_path(root_path)

        # Rebuild index
        return self.indexer.build_index(root_path, force_rebuild=True)

    def update_file(self, root_path: Path, file_path: Path) -> bool:
        """
        Update single file in index (incremental update)

        Args:
            root_path: Root path of index
            file_path: File that changed

        Returns:
            True if updated successfully
        """
        success = self.indexer.update_file(root_path, file_path)

        if success:
            # Invalidate cache for this path
            self.query_cache.invalidate_path(root_path)

        return success

    def get_stats(self) -> dict:
        """Get search engine statistics"""
        cache_stats = self.query_cache.get_stats()

        index_stats = {}
        for root_path, index in self.indexer._indices.items():
            index_stats[str(root_path)] = index.get_statistics()

        return {
            'cache': cache_stats,
            'indices': index_stats,
            'total_indexed_files': sum(
                idx.file_count
                for idx in self.indexer._indices.values()
            )
        }

    def _indexed_search(
        self,
        root_path: Path,
        pattern: str,
        options: AdvancedSearchOptions
    ) -> List[SearchResult]:
        """Search using index"""
        # Build/get index
        index = self.indexer.build_index(
            root_path,
            exclude_dirs=options.exclude_directories,
            max_depth=options.max_depth
        )

        # Determine search type
        if options.use_regex:
            return self._indexed_regex_search(index, pattern, options)
        elif '*' in pattern or '?' in pattern:
            return self._indexed_wildcard_search(index, pattern, options)
        else:
            return self._indexed_exact_search(index, pattern, options)

    def _indexed_exact_search(
        self,
        index: SearchIndex,
        pattern: str,
        options: AdvancedSearchOptions
    ) -> List[SearchResult]:
        """Exact filename search using index"""
        entries = index.search_exact(pattern, options.case_sensitive)

        # Apply extension filter if specified
        if options.file_extensions:
            entries = [
                e for e in entries
                if e.extension in [ext.lower() for ext in options.file_extensions]
            ]

        return [SearchResult(path=entry.path) for entry in entries]

    def _indexed_wildcard_search(
        self,
        index: SearchIndex,
        pattern: str,
        options: AdvancedSearchOptions
    ) -> List[SearchResult]:
        """Wildcard search using index"""
        results = []

        # Check if pattern is just a prefix (e.g., "test*")
        if pattern.endswith('*') and '*' not in pattern[:-1] and '?' not in pattern:
            prefix = pattern[:-1]
            entries = index.search_prefix(prefix, options.case_sensitive)
        else:
            # Full wildcard matching - iterate entries
            if options.case_sensitive:
                match_func = lambda name: fnmatch.fnmatch(name, pattern)
            else:
                pattern_lower = pattern.lower()
                match_func = lambda name: fnmatch.fnmatch(name.lower(), pattern_lower)

            entries = [
                entry for entry in index.entries
                if entry and match_func(entry.name)
            ]

        # Apply extension filter
        if options.file_extensions:
            extensions = [ext.lower() for ext in options.file_extensions]
            entries = [e for e in entries if e.extension in extensions]

        return [SearchResult(path=entry.path) for entry in entries]

    def _indexed_regex_search(
        self,
        index: SearchIndex,
        pattern: str,
        options: AdvancedSearchOptions
    ) -> List[SearchResult]:
        """Regex search using index"""
        try:
            regex = re.compile(
                pattern,
                0 if options.case_sensitive else re.IGNORECASE
            )
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        # Search all entries
        matching_entries = [
            entry for entry in index.entries
            if entry and regex.search(entry.name)
        ]

        # Apply extension filter
        if options.file_extensions:
            extensions = [ext.lower() for ext in options.file_extensions]
            matching_entries = [
                e for e in matching_entries
                if e.extension in extensions
            ]

        return [SearchResult(path=entry.path) for entry in matching_entries]

    def _traditional_search(
        self,
        root_path: Path,
        pattern: str,
        options: AdvancedSearchOptions
    ) -> List[SearchResult]:
        """Fall back to traditional search when index not used"""
        from features.search_engine import FileSearch

        searcher = FileSearch()
        return list(searcher.search_files(root_path, pattern, options))

    def _apply_filters(
        self,
        results: List[SearchResult],
        criteria: FilterCriteria
    ) -> List[SearchResult]:
        """Apply filter criteria to results"""
        filtered = []
        for result in results:
            try:
                stat = result.path.stat()
                if criteria.matches(result.path, stat):
                    filtered.append(result)
            except (OSError, PermissionError):
                continue
        return filtered

    def _get_cached_results(
        self,
        root_path: Path,
        pattern: str,
        search_type: str,
        options: AdvancedSearchOptions
    ) -> Optional[List]:
        """Get cached results if available"""
        opts_dict = {
            'case_sensitive': options.case_sensitive,
            'use_regex': options.use_regex,
            'file_extensions': tuple(options.file_extensions) if options.file_extensions else None
        }

        return self.query_cache.get_results(
            root_path, pattern, search_type, **opts_dict
        )

    def _cache_results(
        self,
        root_path: Path,
        pattern: str,
        search_type: str,
        results: List,
        options: AdvancedSearchOptions
    ) -> None:
        """Cache search results"""
        opts_dict = {
            'case_sensitive': options.case_sensitive,
            'use_regex': options.use_regex,
            'file_extensions': tuple(options.file_extensions) if options.file_extensions else None
        }

        self.query_cache.cache_results(
            root_path, pattern, search_type, results, **opts_dict
        )


# Convenience functions
def advanced_search(
    path: Path,
    pattern: str,
    fuzzy: bool = False,
    use_index: bool = True,
    use_cache: bool = True
) -> List[SearchResult]:
    """
    Convenience function for advanced search

    Args:
        path: Root directory to search
        pattern: Search pattern
        fuzzy: Use fuzzy matching
        use_index: Use indexing for faster search
        use_cache: Use result caching

    Returns:
        List of search results
    """
    searcher = AdvancedFileSearch()
    options = AdvancedSearchOptions(use_index=use_index, use_cache=use_cache)

    if fuzzy:
        results_with_scores = searcher.search_fuzzy(path, pattern, options)
        return [result for result, _ in results_with_scores]
    else:
        return searcher.search_files(path, pattern, options)
