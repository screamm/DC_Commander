"""
Core module for Modern Commander.

Provides essential file operations, scanning, and archive handling functionality.
"""

from .file_operations import (
    copy_file,
    move_file,
    delete_file,
    create_directory,
    get_file_info,
    format_size,
    get_directory_size,
    validate_path,
    FileOperationError,
    PermissionError,
    PathNotFoundError,
    InvalidPathError
)

from .file_scanner import (
    scan_directory,
    get_file_list,
    sort_files,
    search_files,
    get_directory_stats,
    FileEntry,
    SortOrder
)

from .archive_handler import (
    is_archive,
    get_archive_type,
    list_archive_contents,
    extract_archive,
    create_archive,
    get_archive_info,
    ArchiveEntry,
    ArchiveType,
    ArchiveError,
    UnsupportedArchiveError
)

__all__ = [
    # File operations
    'copy_file',
    'move_file',
    'delete_file',
    'create_directory',
    'get_file_info',
    'format_size',
    'get_directory_size',
    'validate_path',
    'FileOperationError',
    'PermissionError',
    'PathNotFoundError',
    'InvalidPathError',

    # File scanner
    'scan_directory',
    'get_file_list',
    'sort_files',
    'search_files',
    'get_directory_stats',
    'FileEntry',
    'SortOrder',

    # Archive handler
    'is_archive',
    'get_archive_type',
    'list_archive_contents',
    'extract_archive',
    'create_archive',
    'get_archive_info',
    'ArchiveEntry',
    'ArchiveType',
    'ArchiveError',
    'UnsupportedArchiveError'
]
