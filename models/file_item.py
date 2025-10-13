"""File item data model for Modern Commander."""

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime


@dataclass
class FileItem:
    """Represents a file or directory entry."""
    name: str
    path: Path
    size: int
    modified: datetime
    is_dir: bool
    is_parent: bool = False
