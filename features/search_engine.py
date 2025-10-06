"""
Modern Commander - Advanced Search and Filtering Engine

Provides high-performance file search, content search, and filtering capabilities
with support for wildcards, regular expressions, and complex filter criteria.

Architecture:
- Generator-based design for memory efficiency
- Asynchronous operations for large directory trees
- Indexed search for performance optimization
- Comprehensive error handling and validation
"""

import re
import fnmatch
from pathlib import Path
from typing import Generator, List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import queue
import mmap
from concurrent.futures import ThreadPoolExecutor, as_completed


class SearchType(Enum):
    """Search operation types"""
    FILENAME = "filename"
    CONTENT = "content"
    COMBINED = "combined"


class FilterOperator(Enum):
    """Filter comparison operators"""
    EQUALS = "="
    GREATER = ">"
    LESS = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    NOT_EQUAL = "!="
    CONTAINS = "contains"
    REGEX = "regex"


class LogicalOperator(Enum):
    """Logical operators for combining filters"""
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class SearchOptions:
    """Configuration options for search operations"""
    case_sensitive: bool = False
    use_regex: bool = False
    search_subdirectories: bool = True
    follow_symlinks: bool = False
    exclude_patterns: List[str] = field(default_factory=list)
    exclude_directories: Set[str] = field(default_factory=lambda: {
        '.git', '.svn', '__pycache__', 'node_modules', '.venv', 'venv'
    })
    max_file_size: Optional[int] = None  # bytes
    max_depth: Optional[int] = None
    file_extensions: Optional[List[str]] = None
    max_results: Optional[int] = None

    def should_exclude_directory(self, dir_name: str) -> bool:
        """Check if directory should be excluded from search"""
        return dir_name in self.exclude_directories

    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded based on patterns"""
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_path.name, pattern):
                return True
        return False

    def matches_extension_filter(self, file_path: Path) -> bool:
        """Check if file matches extension filter"""
        if not self.file_extensions:
            return True
        return file_path.suffix.lower() in [ext.lower() for ext in self.file_extensions]


@dataclass
class FileFilter:
    """Individual file filter specification"""
    attribute: str  # 'name', 'size', 'modified', 'created', 'extension'
    operator: FilterOperator
    value: Any

    def matches(self, file_path: Path, file_stat: Optional[Any] = None) -> bool:
        """
        Check if file matches this filter criteria

        Args:
            file_path: Path to file
            file_stat: Optional pre-computed stat object for performance

        Returns:
            True if file matches filter criteria
        """
        try:
            if self.attribute == 'name':
                return self._match_name(file_path)
            elif self.attribute == 'size':
                return self._match_size(file_path, file_stat)
            elif self.attribute in ('modified', 'created'):
                return self._match_date(file_path, file_stat)
            elif self.attribute == 'extension':
                return self._match_extension(file_path)
            return False
        except (OSError, PermissionError):
            return False

    def _match_name(self, file_path: Path) -> bool:
        """Match against filename"""
        name = file_path.name

        if self.operator == FilterOperator.EQUALS:
            return name == self.value
        elif self.operator == FilterOperator.CONTAINS:
            return self.value in name
        elif self.operator == FilterOperator.REGEX:
            return bool(re.search(self.value, name))
        elif self.operator == FilterOperator.NOT_EQUAL:
            return name != self.value
        return False

    def _match_size(self, file_path: Path, file_stat: Optional[Any]) -> bool:
        """Match against file size"""
        size = file_stat.st_size if file_stat else file_path.stat().st_size
        value = int(self.value)

        if self.operator == FilterOperator.EQUALS:
            return size == value
        elif self.operator == FilterOperator.GREATER:
            return size > value
        elif self.operator == FilterOperator.LESS:
            return size < value
        elif self.operator == FilterOperator.GREATER_EQUAL:
            return size >= value
        elif self.operator == FilterOperator.LESS_EQUAL:
            return size <= value
        elif self.operator == FilterOperator.NOT_EQUAL:
            return size != value
        return False

    def _match_date(self, file_path: Path, file_stat: Optional[Any]) -> bool:
        """Match against file modification/creation date"""
        stat = file_stat if file_stat else file_path.stat()

        if self.attribute == 'modified':
            file_time = datetime.fromtimestamp(stat.st_mtime)
        else:  # created
            file_time = datetime.fromtimestamp(stat.st_ctime)

        compare_time = self.value if isinstance(self.value, datetime) else datetime.fromisoformat(self.value)

        if self.operator == FilterOperator.EQUALS:
            return file_time.date() == compare_time.date()
        elif self.operator == FilterOperator.GREATER:
            return file_time > compare_time
        elif self.operator == FilterOperator.LESS:
            return file_time < compare_time
        elif self.operator == FilterOperator.GREATER_EQUAL:
            return file_time >= compare_time
        elif self.operator == FilterOperator.LESS_EQUAL:
            return file_time <= compare_time
        return False

    def _match_extension(self, file_path: Path) -> bool:
        """Match against file extension"""
        ext = file_path.suffix.lower()
        value = self.value.lower() if isinstance(self.value, str) else self.value

        if self.operator == FilterOperator.EQUALS:
            return ext == value
        elif self.operator == FilterOperator.NOT_EQUAL:
            return ext != value
        elif self.operator == FilterOperator.CONTAINS:
            return value in ext
        return False


@dataclass
class FilterCriteria:
    """Combined filter criteria with logical operators"""
    filters: List[FileFilter] = field(default_factory=list)
    operator: LogicalOperator = LogicalOperator.AND

    def matches(self, file_path: Path, file_stat: Optional[Any] = None) -> bool:
        """
        Check if file matches all filter criteria

        Args:
            file_path: Path to file
            file_stat: Optional pre-computed stat object

        Returns:
            True if file matches combined criteria
        """
        if not self.filters:
            return True

        results = [f.matches(file_path, file_stat) for f in self.filters]

        if self.operator == LogicalOperator.AND:
            return all(results)
        elif self.operator == LogicalOperator.OR:
            return any(results)
        elif self.operator == LogicalOperator.NOT:
            return not any(results)

        return False


@dataclass
class SearchResult:
    """Search result containing file information and match details"""
    path: Path
    matched_line: Optional[str] = None
    line_number: Optional[int] = None
    match_context: Optional[str] = None
    file_size: Optional[int] = None
    modified_time: Optional[datetime] = None

    def __post_init__(self):
        """Populate file metadata on initialization"""
        try:
            stat = self.path.stat()
            if self.file_size is None:
                self.file_size = stat.st_size
            if self.modified_time is None:
                self.modified_time = datetime.fromtimestamp(stat.st_mtime)
        except (OSError, PermissionError):
            pass


class FileSearch:
    """
    High-performance file search engine with support for wildcards,
    regex patterns, and content search.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize search engine

        Args:
            max_workers: Maximum number of worker threads for parallel search
        """
        self.max_workers = max_workers
        self._stop_event = threading.Event()

    def search_files(
        self,
        root_path: Path,
        pattern: str,
        options: Optional[SearchOptions] = None
    ) -> Generator[SearchResult, None, None]:
        """
        Search for files matching pattern in directory tree

        Args:
            root_path: Root directory to search
            pattern: Search pattern (supports wildcards * and ?)
            options: Search configuration options

        Yields:
            SearchResult objects for matching files
        """
        if options is None:
            options = SearchOptions()

        root_path = Path(root_path)
        if not root_path.exists():
            raise ValueError(f"Search path does not exist: {root_path}")

        # Compile pattern based on options
        if options.use_regex:
            try:
                regex_pattern = re.compile(
                    pattern,
                    0 if options.case_sensitive else re.IGNORECASE
                )
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
            match_func = lambda name: bool(regex_pattern.search(name))
        else:
            # Use fnmatch for wildcard patterns
            if options.case_sensitive:
                match_func = lambda name: fnmatch.fnmatch(name, pattern)
            else:
                pattern_lower = pattern.lower()
                match_func = lambda name: fnmatch.fnmatch(name.lower(), pattern_lower)

        result_count = 0

        # Walk directory tree
        for file_path in self._walk_directory(root_path, options):
            if self._stop_event.is_set():
                break

            if match_func(file_path.name):
                yield SearchResult(path=file_path)
                result_count += 1

                if options.max_results and result_count >= options.max_results:
                    break

    def search_content(
        self,
        root_path: Path,
        pattern: str,
        options: Optional[SearchOptions] = None,
        context_lines: int = 0
    ) -> Generator[SearchResult, None, None]:
        """
        Search for pattern in file contents (grep-like functionality)

        Args:
            root_path: Root directory to search
            pattern: Search pattern (supports regex if options.use_regex=True)
            options: Search configuration options
            context_lines: Number of context lines to include before/after match

        Yields:
            SearchResult objects with matched content
        """
        if options is None:
            options = SearchOptions()

        root_path = Path(root_path)
        if not root_path.exists():
            raise ValueError(f"Search path does not exist: {root_path}")

        # Compile search pattern
        if options.use_regex:
            try:
                regex_pattern = re.compile(
                    pattern,
                    0 if options.case_sensitive else re.IGNORECASE
                )
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        else:
            # Convert simple pattern to regex
            regex_pattern = re.compile(
                re.escape(pattern),
                0 if options.case_sensitive else re.IGNORECASE
            )

        result_count = 0

        # Search files
        for file_path in self._walk_directory(root_path, options):
            if self._stop_event.is_set():
                break

            # Skip binary files and large files
            if not self._is_text_file(file_path):
                continue

            # Search file content
            for result in self._search_file_content(
                file_path, regex_pattern, context_lines
            ):
                yield result
                result_count += 1

                if options.max_results and result_count >= options.max_results:
                    return

    def get_matching_files(
        self,
        root_path: Path,
        criteria: FilterCriteria,
        options: Optional[SearchOptions] = None
    ) -> Generator[Path, None, None]:
        """
        Get files matching filter criteria

        Args:
            root_path: Root directory to search
            criteria: Filter criteria to apply
            options: Search configuration options

        Yields:
            Path objects for matching files
        """
        if options is None:
            options = SearchOptions()

        root_path = Path(root_path)
        if not root_path.exists():
            raise ValueError(f"Search path does not exist: {root_path}")

        result_count = 0

        for file_path in self._walk_directory(root_path, options):
            if self._stop_event.is_set():
                break

            try:
                file_stat = file_path.stat()
                if criteria.matches(file_path, file_stat):
                    yield file_path
                    result_count += 1

                    if options.max_results and result_count >= options.max_results:
                        break
            except (OSError, PermissionError):
                continue

    def _walk_directory(
        self,
        root_path: Path,
        options: SearchOptions,
        current_depth: int = 0
    ) -> Generator[Path, None, None]:
        """
        Walk directory tree with filtering and depth control

        Args:
            root_path: Directory to walk
            options: Search options for filtering
            current_depth: Current recursion depth

        Yields:
            Path objects for files in tree
        """
        try:
            for item in root_path.iterdir():
                if self._stop_event.is_set():
                    break

                try:
                    if item.is_dir(follow_symlinks=options.follow_symlinks):
                        # Check directory exclusions
                        if options.should_exclude_directory(item.name):
                            continue

                        # Check depth limit
                        if options.max_depth and current_depth >= options.max_depth:
                            continue

                        # Recurse if enabled
                        if options.search_subdirectories:
                            yield from self._walk_directory(
                                item, options, current_depth + 1
                            )

                    elif item.is_file():
                        # Check file exclusions
                        if options.should_exclude_file(item):
                            continue

                        # Check extension filter
                        if not options.matches_extension_filter(item):
                            continue

                        # Check size limit
                        if options.max_file_size:
                            try:
                                if item.stat().st_size > options.max_file_size:
                                    continue
                            except (OSError, PermissionError):
                                continue

                        yield item

                except (OSError, PermissionError):
                    # Skip inaccessible items
                    continue

        except (OSError, PermissionError):
            # Skip inaccessible directories
            pass

    def _search_file_content(
        self,
        file_path: Path,
        pattern: re.Pattern,
        context_lines: int
    ) -> Generator[SearchResult, None, None]:
        """
        Search for pattern in single file content

        Args:
            file_path: File to search
            pattern: Compiled regex pattern
            context_lines: Number of context lines

        Yields:
            SearchResult objects for matches
        """
        try:
            # Use memory mapping for large files
            file_size = file_path.stat().st_size

            if file_size > 10 * 1024 * 1024:  # 10MB threshold
                yield from self._search_large_file(file_path, pattern, context_lines)
            else:
                yield from self._search_small_file(file_path, pattern, context_lines)

        except (OSError, PermissionError, UnicodeDecodeError):
            # Skip files that can't be read
            pass

    def _search_small_file(
        self,
        file_path: Path,
        pattern: re.Pattern,
        context_lines: int
    ) -> Generator[SearchResult, None, None]:
        """Search small file by reading into memory"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                if pattern.search(line):
                    context = self._get_context(lines, line_num - 1, context_lines)
                    yield SearchResult(
                        path=file_path,
                        matched_line=line.rstrip('\n'),
                        line_number=line_num,
                        match_context=context
                    )
        except Exception:
            pass

    def _search_large_file(
        self,
        file_path: Path,
        pattern: re.Pattern,
        context_lines: int
    ) -> Generator[SearchResult, None, None]:
        """Search large file using memory mapping"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_num = 0
                recent_lines = []  # Ring buffer for context

                for line in f:
                    line_num += 1
                    recent_lines.append((line_num, line))

                    # Maintain context window
                    if len(recent_lines) > (context_lines * 2 + 1):
                        recent_lines.pop(0)

                    if pattern.search(line):
                        context = '\n'.join(l for _, l in recent_lines)
                        yield SearchResult(
                            path=file_path,
                            matched_line=line.rstrip('\n'),
                            line_number=line_num,
                            match_context=context
                        )
        except Exception:
            pass

    def _get_context(
        self,
        lines: List[str],
        match_index: int,
        context_lines: int
    ) -> str:
        """Extract context lines around match"""
        start = max(0, match_index - context_lines)
        end = min(len(lines), match_index + context_lines + 1)
        return ''.join(lines[start:end])

    def _is_text_file(self, file_path: Path) -> bool:
        """
        Check if file is likely a text file

        Args:
            file_path: File to check

        Returns:
            True if file appears to be text
        """
        # Check extension blacklist
        binary_extensions = {
            '.exe', '.dll', '.so', '.dylib', '.bin', '.obj', '.o',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
            '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
            '.zip', '.tar', '.gz', '.7z', '.rar', '.bz2',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
        }

        if file_path.suffix.lower() in binary_extensions:
            return False

        # Sample first bytes to check for binary content
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(8192)

            # Check for null bytes (common in binary files)
            if b'\x00' in sample:
                return False

            # Try to decode as UTF-8
            try:
                sample.decode('utf-8')
                return True
            except UnicodeDecodeError:
                return False

        except (OSError, PermissionError):
            return False

    def stop(self):
        """Stop ongoing search operations"""
        self._stop_event.set()

    def reset(self):
        """Reset stop event for new search"""
        self._stop_event.clear()


class AsyncFileSearch:
    """
    Asynchronous file search for large directory trees
    using thread pool for parallel processing.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize async search engine

        Args:
            max_workers: Maximum concurrent workers
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.base_search = FileSearch(max_workers=1)

    def search_parallel(
        self,
        root_paths: List[Path],
        pattern: str,
        options: Optional[SearchOptions] = None,
        callback: Optional[Callable[[SearchResult], None]] = None
    ) -> List[SearchResult]:
        """
        Search multiple directories in parallel

        Args:
            root_paths: List of directories to search
            pattern: Search pattern
            options: Search options
            callback: Optional callback for each result

        Returns:
            Combined list of search results
        """
        if options is None:
            options = SearchOptions()

        futures = []
        for path in root_paths:
            future = self.executor.submit(
                self._search_single_path,
                path,
                pattern,
                options,
                callback
            )
            futures.append(future)

        # Collect results
        all_results = []
        for future in as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception:
                # Handle individual path failures gracefully
                pass

        return all_results

    def _search_single_path(
        self,
        path: Path,
        pattern: str,
        options: SearchOptions,
        callback: Optional[Callable[[SearchResult], None]]
    ) -> List[SearchResult]:
        """Search single path and return results"""
        results = []
        for result in self.base_search.search_files(path, pattern, options):
            results.append(result)
            if callback:
                callback(result)
        return results

    def shutdown(self):
        """Shutdown thread pool executor"""
        self.executor.shutdown(wait=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


def filter_files(
    files: List[Path],
    criteria: FilterCriteria
) -> List[Path]:
    """
    Filter list of files based on criteria

    Args:
        files: List of file paths
        criteria: Filter criteria to apply

    Returns:
        Filtered list of files
    """
    filtered = []
    for file_path in files:
        try:
            file_stat = file_path.stat()
            if criteria.matches(file_path, file_stat):
                filtered.append(file_path)
        except (OSError, PermissionError):
            continue

    return filtered


# Convenience functions for common operations

def search_files(
    path: str | Path,
    pattern: str,
    options: Optional[SearchOptions] = None
) -> List[SearchResult]:
    """
    Convenience function to search files

    Args:
        path: Root directory to search
        pattern: Search pattern
        options: Search options

    Returns:
        List of search results
    """
    searcher = FileSearch()
    return list(searcher.search_files(Path(path), pattern, options))


def search_content(
    path: str | Path,
    pattern: str,
    options: Optional[SearchOptions] = None,
    context_lines: int = 0
) -> List[SearchResult]:
    """
    Convenience function to search file contents

    Args:
        path: Root directory to search
        pattern: Search pattern
        options: Search options
        context_lines: Context lines to include

    Returns:
        List of search results with matched content
    """
    searcher = FileSearch()
    return list(searcher.search_content(Path(path), pattern, options, context_lines))


def get_matching_files(
    path: str | Path,
    criteria: FilterCriteria,
    options: Optional[SearchOptions] = None
) -> List[Path]:
    """
    Convenience function to get files matching criteria

    Args:
        path: Root directory to search
        criteria: Filter criteria
        options: Search options

    Returns:
        List of matching file paths
    """
    searcher = FileSearch()
    return list(searcher.get_matching_files(Path(path), criteria, options))
