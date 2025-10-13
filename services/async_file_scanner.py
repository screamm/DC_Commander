"""
Asynchronous file scanner for Modern Commander.

Provides high-performance async file searching with streaming results,
progress reporting, and cancellation support.
"""

import asyncio
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional, List
from dataclasses import dataclass
import fnmatch


@dataclass
class ScanProgress:
    """Progress information for file scanning operations."""

    files_scanned: int
    matches_found: int
    current_directory: str
    is_complete: bool = False


class AsyncFileScanner:
    """
    Async file scanner with progress reporting and cancellation.

    Provides non-blocking file search operations that stream results
    as they are found, allowing UI to remain responsive during large
    directory tree scans.
    """

    def __init__(self):
        """Initialize async file scanner."""
        self._cancelled = False

    def cancel(self) -> None:
        """Cancel ongoing search operation."""
        self._cancelled = True

    def reset(self) -> None:
        """Reset cancellation state for new search."""
        self._cancelled = False

    async def search_files(
        self,
        base_path: Path,
        pattern: str,
        case_sensitive: bool = False,
        recursive: bool = True,
        max_depth: Optional[int] = None,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None
    ) -> AsyncGenerator[Path, None]:
        """
        Search for files matching pattern with streaming results.

        Uses breadth-first search to find matches quickly and yield control
        to event loop frequently for responsive UI.

        Args:
            base_path: Root directory to search
            pattern: Search pattern (supports wildcards * and ?)
            case_sensitive: Enable case-sensitive matching
            recursive: Search subdirectories recursively
            max_depth: Maximum directory depth (None = unlimited)
            progress_callback: Called periodically with progress updates

        Yields:
            Matching file paths as they're found

        Example:
            async for file_path in scanner.search_files(Path("/data"), "*.py"):
                print(f"Found: {file_path}")
        """
        self._cancelled = False
        files_scanned = 0
        matches_found = 0

        # Normalize pattern for case-insensitive search
        pattern_lower = pattern.lower() if not case_sensitive else pattern

        async def _scan_directory(directory: Path) -> List[Path]:
            """Scan single directory (blocking I/O in thread pool)."""
            try:
                # Run blocking I/O in thread pool to avoid blocking event loop
                return await asyncio.to_thread(lambda: list(directory.iterdir()))
            except (PermissionError, OSError):
                return []

        # BFS queue for directory traversal
        queue: List[tuple[Path, int]] = [(base_path, 0)]

        while queue and not self._cancelled:
            current_dir, depth = queue.pop(0)

            # Report progress
            if progress_callback:
                progress = ScanProgress(
                    files_scanned=files_scanned,
                    matches_found=matches_found,
                    current_directory=str(current_dir),
                    is_complete=False
                )
                progress_callback(progress)

            # Scan directory entries
            entries = await _scan_directory(current_dir)

            for entry in entries:
                if self._cancelled:
                    break

                files_scanned += 1

                # Check if entry matches pattern
                name = entry.name if case_sensitive else entry.name.lower()
                if fnmatch.fnmatch(name, pattern_lower):
                    matches_found += 1
                    yield entry

                # Add subdirectories to queue
                if recursive and entry.is_dir():
                    # Check depth limit
                    if max_depth is None or depth < max_depth:
                        queue.append((entry, depth + 1))

                # Yield control to event loop every 10 files
                if files_scanned % 10 == 0:
                    await asyncio.sleep(0)

        # Final progress update
        if progress_callback:
            progress = ScanProgress(
                files_scanned=files_scanned,
                matches_found=matches_found,
                current_directory=str(current_dir) if 'current_dir' in locals() else "",
                is_complete=True
            )
            progress_callback(progress)

    async def find_files_batch(
        self,
        base_path: Path,
        pattern: str,
        case_sensitive: bool = False,
        recursive: bool = True,
        max_results: Optional[int] = None,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None
    ) -> List[Path]:
        """
        Search for files and return complete results list.

        Convenience method for when you need all results at once
        rather than streaming them.

        Args:
            base_path: Root directory to search
            pattern: Search pattern (supports wildcards)
            case_sensitive: Enable case-sensitive matching
            recursive: Search subdirectories recursively
            max_results: Maximum number of results to return
            progress_callback: Called periodically with progress updates

        Returns:
            List of matching file paths

        Example:
            results = await scanner.find_files_batch(Path("/data"), "*.txt")
        """
        results = []

        async for file_path in self.search_files(
            base_path,
            pattern,
            case_sensitive,
            recursive,
            progress_callback=progress_callback
        ):
            results.append(file_path)

            # Check result limit
            if max_results and len(results) >= max_results:
                break

        return results

    async def count_files(
        self,
        base_path: Path,
        pattern: str = "*",
        case_sensitive: bool = False,
        recursive: bool = True,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None
    ) -> int:
        """
        Count files matching pattern without collecting results.

        Memory-efficient way to count files without storing paths.

        Args:
            base_path: Root directory to search
            pattern: Search pattern (supports wildcards)
            case_sensitive: Enable case-sensitive matching
            recursive: Search subdirectories recursively
            progress_callback: Called periodically with progress updates

        Returns:
            Number of matching files
        """
        count = 0

        async for _ in self.search_files(
            base_path,
            pattern,
            case_sensitive,
            recursive,
            progress_callback=progress_callback
        ):
            count += 1

        return count


class FileSearchOptions:
    """Configuration options for file search operations."""

    def __init__(
        self,
        case_sensitive: bool = False,
        recursive: bool = True,
        max_depth: Optional[int] = None,
        max_results: Optional[int] = None,
        include_hidden: bool = False,
        exclude_patterns: Optional[List[str]] = None
    ):
        """
        Initialize search options.

        Args:
            case_sensitive: Enable case-sensitive pattern matching
            recursive: Search subdirectories recursively
            max_depth: Maximum directory depth to search
            max_results: Maximum number of results to return
            include_hidden: Include hidden files (starting with .)
            exclude_patterns: List of patterns to exclude (e.g., ['*.tmp', '__pycache__'])
        """
        self.case_sensitive = case_sensitive
        self.recursive = recursive
        self.max_depth = max_depth
        self.max_results = max_results
        self.include_hidden = include_hidden
        self.exclude_patterns = exclude_patterns or []

    def should_exclude(self, path: Path) -> bool:
        """
        Check if path should be excluded from search.

        Args:
            path: Path to check

        Returns:
            True if path should be excluded
        """
        # Check hidden files
        if not self.include_hidden and path.name.startswith('.'):
            return True

        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(path.name, pattern):
                return True

        return False


# Convenience function for quick searches
async def find_files(
    path: Path,
    pattern: str,
    **options
) -> List[Path]:
    """
    Convenience function for quick file searches.

    Args:
        path: Root directory to search
        pattern: Search pattern (supports wildcards)
        **options: Additional search options

    Returns:
        List of matching file paths

    Example:
        results = await find_files(Path("/data"), "*.py", recursive=True)
    """
    scanner = AsyncFileScanner()
    return await scanner.find_files_batch(path, pattern, **options)
