"""File repository for Modern Commander.

Provides data access layer for file system operations.
"""

from pathlib import Path
from typing import List, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
from models.file_item import FileItem


class FileRepository:
    """Repository for file system data access."""

    def __init__(self, show_hidden: bool = False):
        """Initialize file repository.

        Args:
            show_hidden: Whether to show hidden files
        """
        self.show_hidden = show_hidden

    def get_directory_contents(
        self,
        path: Path,
        filter_func: Optional[Callable[[Path], bool]] = None
    ) -> List[FileItem]:
        """Get contents of a directory.

        Args:
            path: Directory path
            filter_func: Optional filter function

        Returns:
            List of file items

        Raises:
            PermissionError: If directory cannot be accessed
            FileNotFoundError: If directory doesn't exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        items: List[FileItem] = []

        # Add parent directory entry
        if path.parent != path:
            items.append(FileItem(
                name="..",
                path=path.parent,
                size=0,
                modified=datetime.now(),
                is_dir=True,
                is_parent=True,
            ))

        # Add directory contents
        try:
            for entry in path.iterdir():
                # Skip hidden files if configured
                if not self.show_hidden and entry.name.startswith('.'):
                    continue

                # Apply custom filter if provided
                if filter_func and not filter_func(entry):
                    continue

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
                    # Skip inaccessible entries
                    continue

        except PermissionError as e:
            raise PermissionError(f"Permission denied: {path}") from e

        return items

    def find_files(
        self,
        root_path: Path,
        pattern: str,
        recursive: bool = True,
        max_depth: Optional[int] = None
    ) -> List[Path]:
        """Find files matching pattern.

        Args:
            root_path: Root directory to search
            pattern: Search pattern (glob or name)
            recursive: Whether to search recursively
            max_depth: Maximum recursion depth

        Returns:
            List of matching file paths
        """
        matches = []

        if recursive:
            if max_depth is not None:
                # Limited depth recursion
                matches = list(root_path.glob(f"**/{pattern}"))[:max_depth]
            else:
                matches = list(root_path.rglob(pattern))
        else:
            matches = list(root_path.glob(pattern))

        return matches

    def get_file_stats(self, path: Path) -> Optional[dict]:
        """Get file statistics.

        Args:
            path: File path

        Returns:
            Dictionary with file stats or None
        """
        try:
            stat = path.stat()
            return {
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "created": datetime.fromtimestamp(stat.st_ctime),
                "accessed": datetime.fromtimestamp(stat.st_atime),
                "mode": stat.st_mode,
                "is_dir": path.is_dir(),
                "is_file": path.is_file(),
                "is_symlink": path.is_symlink(),
            }
        except Exception:
            return None

    def get_directory_tree(
        self,
        root_path: Path,
        max_depth: int = 3
    ) -> List[Tuple[int, Path]]:
        """Get directory tree structure.

        Args:
            root_path: Root directory
            max_depth: Maximum depth to traverse

        Returns:
            List of (depth, path) tuples
        """
        tree = []

        def _walk_tree(path: Path, depth: int) -> None:
            if depth > max_depth:
                return

            tree.append((depth, path))

            if path.is_dir():
                try:
                    for entry in sorted(path.iterdir()):
                        if entry.is_dir():
                            _walk_tree(entry, depth + 1)
                except PermissionError:
                    pass

        _walk_tree(root_path, 0)
        return tree

    def get_drive_info(self, path: Path) -> Optional[dict]:
        """Get drive/volume information.

        Args:
            path: Path on the drive

        Returns:
            Dictionary with drive info or None
        """
        try:
            import shutil
            stat = shutil.disk_usage(path)

            return {
                "total": stat.total,
                "used": stat.used,
                "free": stat.free,
                "percent_used": (stat.used / stat.total) * 100 if stat.total > 0 else 0,
            }
        except Exception:
            return None
