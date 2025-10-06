"""
File scanning and filtering module for Modern Commander.

Provides efficient directory scanning with filtering, sorting, and search capabilities.
"""

from pathlib import Path
from typing import List, Optional, Callable, Dict
from datetime import datetime
from enum import Enum
import fnmatch


class SortOrder(Enum):
    """File sorting order options."""
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    SIZE_ASC = "size_asc"
    SIZE_DESC = "size_desc"
    DATE_ASC = "date_asc"
    DATE_DESC = "date_desc"
    EXT_ASC = "ext_asc"
    EXT_DESC = "ext_desc"


class FileEntry:
    """Represents a file or directory entry with metadata."""

    def __init__(self, path: Path):
        """
        Initialize file entry.

        Args:
            path: Path to file or directory
        """
        self.path = path
        self.name = path.name
        self.is_directory = path.is_dir()
        self.is_file = path.is_file()
        self.is_symlink = path.is_symlink()

        try:
            stat = path.stat()
            self.size = stat.st_size if self.is_file else 0
            self.modified = datetime.fromtimestamp(stat.st_mtime)
            self.created = datetime.fromtimestamp(stat.st_ctime)
            self.extension = path.suffix.lower() if self.is_file else ""
            self.accessible = True
        except (OSError, PermissionError):
            self.size = 0
            self.modified = datetime.min
            self.created = datetime.min
            self.extension = ""
            self.accessible = False

    def __repr__(self) -> str:
        """String representation of file entry."""
        type_str = "DIR" if self.is_directory else "FILE"
        return f"<FileEntry {type_str}: {self.name}>"

    def matches_pattern(self, pattern: str) -> bool:
        """
        Check if filename matches wildcard pattern.

        Args:
            pattern: Wildcard pattern (e.g., "*.txt")

        Returns:
            True if filename matches pattern
        """
        return fnmatch.fnmatch(self.name.lower(), pattern.lower())


def scan_directory(
    path: Path,
    show_hidden: bool = False,
    recursive: bool = False
) -> List[FileEntry]:
    """
    Scan directory and return file entries.

    Args:
        path: Directory path to scan
        show_hidden: If True, include hidden files
        recursive: If True, scan subdirectories recursively

    Returns:
        List of FileEntry objects

    Raises:
        ValueError: Path is not a directory
        PermissionError: Insufficient permissions to read directory
    """
    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    entries = []

    try:
        iterator = path.rglob('*') if recursive else path.iterdir()

        for item in iterator:
            if not show_hidden and item.name.startswith('.'):
                continue

            try:
                entry = FileEntry(item)
                entries.append(entry)
            except (OSError, PermissionError):
                continue

    except PermissionError as e:
        raise PermissionError(f"Permission denied: {path}") from e

    return entries


def get_file_list(
    path: Path,
    pattern: Optional[str] = None,
    show_hidden: bool = False,
    files_only: bool = False,
    directories_only: bool = False,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    modified_after: Optional[datetime] = None,
    modified_before: Optional[datetime] = None,
    extensions: Optional[List[str]] = None
) -> List[FileEntry]:
    """
    Get filtered file list from directory.

    Args:
        path: Directory path to scan
        pattern: Wildcard pattern for filename matching (e.g., "*.txt")
        show_hidden: Include hidden files
        files_only: Only return files, exclude directories
        directories_only: Only return directories, exclude files
        min_size: Minimum file size in bytes
        max_size: Maximum file size in bytes
        modified_after: Only files modified after this datetime
        modified_before: Only files modified before this datetime
        extensions: List of file extensions to include (e.g., ['.txt', '.py'])

    Returns:
        Filtered list of FileEntry objects
    """
    entries = scan_directory(path, show_hidden=show_hidden)
    filtered = []

    for entry in entries:
        if files_only and entry.is_directory:
            continue

        if directories_only and entry.is_file:
            continue

        if pattern and not entry.matches_pattern(pattern):
            continue

        if min_size is not None and entry.size < min_size:
            continue

        if max_size is not None and entry.size > max_size:
            continue

        if modified_after and entry.modified < modified_after:
            continue

        if modified_before and entry.modified > modified_before:
            continue

        if extensions:
            if entry.extension not in [ext.lower() for ext in extensions]:
                continue

        filtered.append(entry)

    return filtered


def sort_files(
    entries: List[FileEntry],
    sort_by: SortOrder = SortOrder.NAME_ASC,
    directories_first: bool = True
) -> List[FileEntry]:
    """
    Sort file entries.

    Args:
        entries: List of FileEntry objects to sort
        sort_by: Sort order option
        directories_first: If True, directories appear before files

    Returns:
        Sorted list of FileEntry objects
    """
    sort_functions: Dict[SortOrder, Callable[[FileEntry], any]] = {
        SortOrder.NAME_ASC: lambda e: e.name.lower(),
        SortOrder.NAME_DESC: lambda e: e.name.lower(),
        SortOrder.SIZE_ASC: lambda e: e.size,
        SortOrder.SIZE_DESC: lambda e: e.size,
        SortOrder.DATE_ASC: lambda e: e.modified,
        SortOrder.DATE_DESC: lambda e: e.modified,
        SortOrder.EXT_ASC: lambda e: (e.extension, e.name.lower()),
        SortOrder.EXT_DESC: lambda e: (e.extension, e.name.lower())
    }

    reverse_sorts = {
        SortOrder.NAME_DESC,
        SortOrder.SIZE_DESC,
        SortOrder.DATE_DESC,
        SortOrder.EXT_DESC
    }

    if directories_first:
        entries.sort(
            key=lambda e: (
                not e.is_directory,
                sort_functions[sort_by](e)
            ),
            reverse=sort_by in reverse_sorts
        )
    else:
        entries.sort(
            key=sort_functions[sort_by],
            reverse=sort_by in reverse_sorts
        )

    return entries


def search_files(
    path: Path,
    search_term: str,
    case_sensitive: bool = False,
    search_content: bool = False,
    max_depth: Optional[int] = None
) -> List[FileEntry]:
    """
    Search for files by name or content.

    Args:
        path: Directory path to search in
        search_term: Term to search for
        case_sensitive: Enable case-sensitive search
        search_content: Search file contents (text files only)
        max_depth: Maximum directory depth to search (None = unlimited)

    Returns:
        List of matching FileEntry objects
    """
    results = []
    search_lower = search_term if case_sensitive else search_term.lower()

    def should_process(item_path: Path, current_depth: int) -> bool:
        """Check if path should be processed based on depth."""
        if max_depth is None:
            return True
        relative = item_path.relative_to(path)
        return len(relative.parts) <= max_depth

    try:
        for item in path.rglob('*'):
            if not should_process(item, 0):
                continue

            try:
                entry = FileEntry(item)

                name_to_check = entry.name if case_sensitive else entry.name.lower()
                if search_lower in name_to_check:
                    results.append(entry)
                    continue

                if search_content and entry.is_file and entry.accessible:
                    if _search_file_content(item, search_term, case_sensitive):
                        results.append(entry)

            except (OSError, PermissionError):
                continue

    except PermissionError:
        pass

    return results


def _search_file_content(
    path: Path,
    search_term: str,
    case_sensitive: bool
) -> bool:
    """
    Search for term in text file content.

    Args:
        path: File path
        search_term: Term to search for
        case_sensitive: Enable case-sensitive search

    Returns:
        True if term found in file
    """
    text_extensions = {'.txt', '.py', '.js', '.html', '.css', '.json', '.xml',
                      '.md', '.rst', '.log', '.cfg', '.ini', '.yaml', '.yml'}

    if path.suffix.lower() not in text_extensions:
        return False

    try:
        content = path.read_text(encoding='utf-8', errors='ignore')
        if not case_sensitive:
            content = content.lower()
            search_term = search_term.lower()

        return search_term in content

    except (OSError, UnicodeDecodeError):
        return False


def get_directory_stats(path: Path) -> Dict[str, any]:
    """
    Calculate directory statistics.

    Args:
        path: Directory path

    Returns:
        Dictionary with statistics (file_count, dir_count, total_size, etc.)
    """
    stats = {
        'file_count': 0,
        'directory_count': 0,
        'total_size': 0,
        'largest_file': None,
        'largest_file_size': 0,
        'extensions': {},
        'hidden_count': 0
    }

    try:
        for item in path.rglob('*'):
            try:
                if item.is_file():
                    stats['file_count'] += 1
                    size = item.stat().st_size
                    stats['total_size'] += size

                    if size > stats['largest_file_size']:
                        stats['largest_file_size'] = size
                        stats['largest_file'] = str(item)

                    ext = item.suffix.lower()
                    if ext:
                        stats['extensions'][ext] = stats['extensions'].get(ext, 0) + 1

                elif item.is_dir():
                    stats['directory_count'] += 1

                if item.name.startswith('.'):
                    stats['hidden_count'] += 1

            except (OSError, PermissionError):
                continue

    except PermissionError:
        pass

    return stats
