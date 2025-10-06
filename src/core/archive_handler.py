"""
Archive handling module for Modern Commander.

Provides comprehensive archive operations for ZIP, TAR, and other formats
with security protections against path traversal and archive bombs.
"""

import zipfile
import tarfile
import os
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

from .security import (
    validate_archive_member,
    check_archive_bomb,
    sanitize_filename,
    ArchiveBombError,
    PathTraversalError,
    SecurityError
)


class ArchiveType(Enum):
    """Supported archive formats."""
    ZIP = "zip"
    TAR = "tar"
    TAR_GZ = "tar.gz"
    TAR_BZ2 = "tar.bz2"
    TAR_XZ = "tar.xz"
    UNKNOWN = "unknown"


class ArchiveError(Exception):
    """Base exception for archive operations."""
    pass


class UnsupportedArchiveError(ArchiveError):
    """Raised when archive format is not supported."""
    pass


class ArchiveEntry:
    """Represents an entry in an archive."""

    def __init__(
        self,
        name: str,
        size: int,
        compressed_size: int,
        is_directory: bool,
        modified: Optional[datetime] = None
    ):
        """
        Initialize archive entry.

        Args:
            name: Entry name/path
            size: Uncompressed size in bytes
            compressed_size: Compressed size in bytes
            is_directory: True if entry is a directory
            modified: Last modification datetime
        """
        self.name = name
        self.size = size
        self.compressed_size = compressed_size
        self.is_directory = is_directory
        self.modified = modified or datetime.min

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio (0-100%)."""
        if self.size == 0:
            return 0.0
        return (1 - self.compressed_size / self.size) * 100

    def __repr__(self) -> str:
        """String representation of archive entry."""
        type_str = "DIR" if self.is_directory else "FILE"
        return f"<ArchiveEntry {type_str}: {self.name}>"


def is_archive(path: Path) -> bool:
    """
    Check if file is a supported archive.

    Args:
        path: File path to check

    Returns:
        True if file is a supported archive
    """
    archive_type = get_archive_type(path)
    return archive_type != ArchiveType.UNKNOWN


def get_archive_type(path: Path) -> ArchiveType:
    """
    Determine archive type from file extension.

    Args:
        path: File path

    Returns:
        ArchiveType enum value
    """
    name_lower = path.name.lower()

    if name_lower.endswith('.tar.gz') or name_lower.endswith('.tgz'):
        return ArchiveType.TAR_GZ
    elif name_lower.endswith('.tar.bz2') or name_lower.endswith('.tbz2'):
        return ArchiveType.TAR_BZ2
    elif name_lower.endswith('.tar.xz'):
        return ArchiveType.TAR_XZ
    elif name_lower.endswith('.tar'):
        return ArchiveType.TAR
    elif name_lower.endswith('.zip'):
        return ArchiveType.ZIP

    return ArchiveType.UNKNOWN


def list_archive_contents(path: Path) -> List[ArchiveEntry]:
    """
    List contents of archive file.

    Args:
        path: Archive file path

    Returns:
        List of ArchiveEntry objects

    Raises:
        FileNotFoundError: Archive file does not exist
        UnsupportedArchiveError: Archive format not supported
        ArchiveError: Failed to read archive
    """
    if not path.exists():
        raise FileNotFoundError(f"Archive not found: {path}")

    archive_type = get_archive_type(path)

    if archive_type == ArchiveType.ZIP:
        return _list_zip_contents(path)
    elif archive_type in (ArchiveType.TAR, ArchiveType.TAR_GZ,
                          ArchiveType.TAR_BZ2, ArchiveType.TAR_XZ):
        return _list_tar_contents(path, archive_type)
    else:
        raise UnsupportedArchiveError(f"Unsupported archive format: {path.suffix}")


def _list_zip_contents(path: Path) -> List[ArchiveEntry]:
    """
    List ZIP archive contents.

    Args:
        path: ZIP file path

    Returns:
        List of ArchiveEntry objects
    """
    entries = []

    try:
        with zipfile.ZipFile(path, 'r') as zf:
            for info in zf.infolist():
                modified = datetime(*info.date_time) if info.date_time else None

                entry = ArchiveEntry(
                    name=info.filename,
                    size=info.file_size,
                    compressed_size=info.compress_size,
                    is_directory=info.is_dir(),
                    modified=modified
                )
                entries.append(entry)

    except zipfile.BadZipFile as e:
        raise ArchiveError(f"Invalid ZIP archive: {e}")
    except Exception as e:
        raise ArchiveError(f"Failed to read ZIP archive: {e}")

    return entries


def _list_tar_contents(path: Path, archive_type: ArchiveType) -> List[ArchiveEntry]:
    """
    List TAR archive contents.

    Args:
        path: TAR file path
        archive_type: TAR archive type

    Returns:
        List of ArchiveEntry objects
    """
    mode_map = {
        ArchiveType.TAR: 'r',
        ArchiveType.TAR_GZ: 'r:gz',
        ArchiveType.TAR_BZ2: 'r:bz2',
        ArchiveType.TAR_XZ: 'r:xz'
    }

    entries = []

    try:
        with tarfile.open(path, mode_map[archive_type]) as tf:
            for member in tf.getmembers():
                modified = datetime.fromtimestamp(member.mtime) if member.mtime else None

                entry = ArchiveEntry(
                    name=member.name,
                    size=member.size,
                    compressed_size=member.size,
                    is_directory=member.isdir(),
                    modified=modified
                )
                entries.append(entry)

    except tarfile.TarError as e:
        raise ArchiveError(f"Invalid TAR archive: {e}")
    except Exception as e:
        raise ArchiveError(f"Failed to read TAR archive: {e}")

    return entries


def _validate_archive_safety(
    source: Path,
    dest: Path,
    entries: List[ArchiveEntry]
) -> None:
    """
    Validate archive is safe to extract (no bombs, no path traversal).

    Args:
        source: Archive file path
        dest: Destination directory
        entries: Archive entries to validate

    Raises:
        ArchiveBombError: Archive bomb detected
        PathTraversalError: Path traversal attack detected
        SecurityError: Other security violation
    """
    # Calculate totals for bomb detection
    total_compressed = source.stat().st_size
    total_uncompressed = sum(e.size for e in entries if not e.is_directory)
    file_count = sum(1 for e in entries if not e.is_directory)

    # Check for archive bomb
    is_safe, error_msg = check_archive_bomb(
        total_compressed,
        total_uncompressed,
        file_count
    )

    if not is_safe:
        raise ArchiveBombError(f"Archive bomb detected: {error_msg}")

    # Validate each member path
    for entry in entries:
        is_valid, error_msg = validate_archive_member(entry.name, dest)
        if not is_valid:
            raise PathTraversalError(
                f"Unsafe archive member '{entry.name}': {error_msg}"
            )


def _sanitize_archive_member(member_name: str, dest: Path) -> Path:
    """
    Sanitize and validate archive member path for extraction.

    Args:
        member_name: Archive member path
        dest: Destination directory

    Returns:
        Safe extraction path

    Raises:
        PathTraversalError: Path traversal detected
        SecurityError: Path validation failed
    """
    # Normalize path separators
    member_name = member_name.replace('\\', '/')

    # Validate member is safe
    is_valid, error_msg = validate_archive_member(member_name, dest)
    if not is_valid:
        raise PathTraversalError(f"Unsafe archive member: {error_msg}")

    # Build safe destination path
    safe_path = dest / member_name

    # Final validation: ensure resolved path is within destination
    try:
        safe_path_resolved = safe_path.resolve()
        dest_resolved = dest.resolve()

        # Verify still within destination after resolution
        safe_path_resolved.relative_to(dest_resolved)

    except ValueError:
        raise PathTraversalError(
            f"Path traversal detected: '{member_name}' "
            f"resolves outside destination"
        )
    except (OSError, RuntimeError) as e:
        raise SecurityError(f"Path validation failed: {e}")

    return safe_path


def extract_archive(
    source: Path,
    dest: Path,
    members: Optional[List[str]] = None,
    overwrite: bool = False,
    validate_safety: bool = True
) -> bool:
    """
    Extract archive to destination directory with security validation.

    Security features:
    - Path traversal prevention
    - Archive bomb detection
    - Compression ratio validation
    - File count limits

    Args:
        source: Archive file path
        dest: Destination directory path
        members: Specific files to extract (None = all)
        overwrite: Overwrite existing files
        validate_safety: Perform security validation (recommended)

    Returns:
        True if extraction succeeded

    Raises:
        FileNotFoundError: Archive file does not exist
        UnsupportedArchiveError: Archive format not supported
        ArchiveBombError: Archive bomb detected
        PathTraversalError: Path traversal attack detected
        ArchiveError: Extraction failed
    """
    if not source.exists():
        raise FileNotFoundError(f"Archive not found: {source}")

    archive_type = get_archive_type(source)

    if not overwrite and dest.exists():
        raise ArchiveError(f"Destination already exists: {dest}")

    dest.mkdir(parents=True, exist_ok=True)

    # Security validation
    if validate_safety:
        entries = list_archive_contents(source)
        _validate_archive_safety(source, dest, entries)

    if archive_type == ArchiveType.ZIP:
        return _extract_zip(source, dest, members, validate_safety)
    elif archive_type in (ArchiveType.TAR, ArchiveType.TAR_GZ,
                          ArchiveType.TAR_BZ2, ArchiveType.TAR_XZ):
        return _extract_tar(source, dest, archive_type, members, validate_safety)
    else:
        raise UnsupportedArchiveError(f"Unsupported archive format: {source.suffix}")


def _extract_zip(
    source: Path,
    dest: Path,
    members: Optional[List[str]] = None,
    validate_safety: bool = True
) -> bool:
    """
    Extract ZIP archive with security validation.

    Args:
        source: ZIP file path
        dest: Destination directory
        members: Specific files to extract
        validate_safety: Perform path validation

    Returns:
        True if extraction succeeded
    """
    try:
        with zipfile.ZipFile(source, 'r') as zf:
            members_to_extract = members if members else zf.namelist()

            for member_name in members_to_extract:
                # Security validation for each member
                if validate_safety:
                    safe_path = _sanitize_archive_member(member_name, dest)

                    # Extract to validated path
                    info = zf.getinfo(member_name)
                    if not info.is_dir():
                        safe_path.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member_name) as source_file:
                            with open(safe_path, 'wb') as dest_file:
                                dest_file.write(source_file.read())
                    else:
                        safe_path.mkdir(parents=True, exist_ok=True)
                else:
                    # Direct extraction (less secure)
                    zf.extract(member_name, dest)

        return True

    except (PathTraversalError, ArchiveBombError, SecurityError):
        raise
    except zipfile.BadZipFile as e:
        raise ArchiveError(f"Invalid ZIP archive: {e}")
    except Exception as e:
        raise ArchiveError(f"Extraction failed: {e}")


def _extract_tar(
    source: Path,
    dest: Path,
    archive_type: ArchiveType,
    members: Optional[List[str]] = None,
    validate_safety: bool = True
) -> bool:
    """
    Extract TAR archive with security validation.

    Args:
        source: TAR file path
        dest: Destination directory
        archive_type: TAR archive type
        members: Specific files to extract
        validate_safety: Perform path validation

    Returns:
        True if extraction succeeded
    """
    mode_map = {
        ArchiveType.TAR: 'r',
        ArchiveType.TAR_GZ: 'r:gz',
        ArchiveType.TAR_BZ2: 'r:bz2',
        ArchiveType.TAR_XZ: 'r:xz'
    }

    try:
        with tarfile.open(source, mode_map[archive_type]) as tf:
            if validate_safety:
                # Secure extraction with path validation
                members_to_extract = tf.getmembers()
                if members:
                    members_to_extract = [
                        m for m in members_to_extract if m.name in members
                    ]

                for member in members_to_extract:
                    # Validate and sanitize path
                    safe_path = _sanitize_archive_member(member.name, dest)

                    # Check for symlinks pointing outside destination
                    if member.issym() or member.islnk():
                        # Validate symlink target
                        link_target = Path(member.linkname)
                        if link_target.is_absolute():
                            raise PathTraversalError(
                                f"Absolute symlink not allowed: {member.name} -> "
                                f"{member.linkname}"
                            )

                        # Resolve target relative to member's directory
                        member_dir = safe_path.parent
                        target_path = (member_dir / link_target).resolve()

                        try:
                            target_path.relative_to(dest.resolve())
                        except ValueError:
                            raise PathTraversalError(
                                f"Symlink points outside destination: "
                                f"{member.name} -> {member.linkname}"
                            )

                    # Extract member
                    if member.isfile():
                        safe_path.parent.mkdir(parents=True, exist_ok=True)
                        with tf.extractfile(member) as source_file:
                            with open(safe_path, 'wb') as dest_file:
                                dest_file.write(source_file.read())
                    elif member.isdir():
                        safe_path.mkdir(parents=True, exist_ok=True)
                    elif member.issym():
                        safe_path.parent.mkdir(parents=True, exist_ok=True)
                        if safe_path.exists() or safe_path.is_symlink():
                            safe_path.unlink()
                        os.symlink(member.linkname, safe_path)

            else:
                # Direct extraction (less secure)
                if members:
                    member_objs = [m for m in tf.getmembers() if m.name in members]
                    tf.extractall(dest, members=member_objs)
                else:
                    tf.extractall(dest)

        return True

    except (PathTraversalError, ArchiveBombError, SecurityError):
        raise
    except tarfile.TarError as e:
        raise ArchiveError(f"Invalid TAR archive: {e}")
    except Exception as e:
        raise ArchiveError(f"Extraction failed: {e}")


def create_archive(
    files: List[Path],
    dest: Path,
    archive_type: ArchiveType = ArchiveType.ZIP,
    compression_level: int = 6,
    base_dir: Optional[Path] = None
) -> bool:
    """
    Create archive from files.

    Args:
        files: List of file/directory paths to archive
        dest: Destination archive path
        archive_type: Type of archive to create
        compression_level: Compression level (0-9, higher = better compression)
        base_dir: Base directory for relative paths

    Returns:
        True if creation succeeded

    Raises:
        UnsupportedArchiveError: Archive format not supported
        ArchiveError: Archive creation failed
    """
    if not files:
        raise ArchiveError("No files specified for archive")

    if compression_level < 0 or compression_level > 9:
        compression_level = 6

    dest.parent.mkdir(parents=True, exist_ok=True)

    if archive_type == ArchiveType.ZIP:
        return _create_zip(files, dest, compression_level, base_dir)
    elif archive_type in (ArchiveType.TAR, ArchiveType.TAR_GZ,
                          ArchiveType.TAR_BZ2, ArchiveType.TAR_XZ):
        return _create_tar(files, dest, archive_type, base_dir)
    else:
        raise UnsupportedArchiveError(f"Unsupported archive format: {archive_type}")


def _create_zip(
    files: List[Path],
    dest: Path,
    compression_level: int,
    base_dir: Optional[Path]
) -> bool:
    """
    Create ZIP archive.

    Args:
        files: Files to archive
        dest: Destination path
        compression_level: Compression level
        base_dir: Base directory for relative paths

    Returns:
        True if creation succeeded
    """
    try:
        with zipfile.ZipFile(
            dest,
            'w',
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=compression_level
        ) as zf:
            for file_path in files:
                if not file_path.exists():
                    continue

                arcname = _get_archive_name(file_path, base_dir)

                if file_path.is_file():
                    zf.write(file_path, arcname)
                elif file_path.is_dir():
                    for item in file_path.rglob('*'):
                        if item.is_file():
                            item_arcname = _get_archive_name(item, base_dir)
                            zf.write(item, item_arcname)

        return True

    except Exception as e:
        raise ArchiveError(f"Failed to create ZIP archive: {e}")


def _create_tar(
    files: List[Path],
    dest: Path,
    archive_type: ArchiveType,
    base_dir: Optional[Path]
) -> bool:
    """
    Create TAR archive.

    Args:
        files: Files to archive
        dest: Destination path
        archive_type: TAR archive type
        base_dir: Base directory for relative paths

    Returns:
        True if creation succeeded
    """
    mode_map = {
        ArchiveType.TAR: 'w',
        ArchiveType.TAR_GZ: 'w:gz',
        ArchiveType.TAR_BZ2: 'w:bz2',
        ArchiveType.TAR_XZ: 'w:xz'
    }

    try:
        with tarfile.open(dest, mode_map[archive_type]) as tf:
            for file_path in files:
                if not file_path.exists():
                    continue

                arcname = _get_archive_name(file_path, base_dir)
                tf.add(file_path, arcname=arcname)

        return True

    except Exception as e:
        raise ArchiveError(f"Failed to create TAR archive: {e}")


def _get_archive_name(path: Path, base_dir: Optional[Path]) -> str:
    """
    Get archive name for file.

    Args:
        path: File path
        base_dir: Base directory for relative paths

    Returns:
        Archive name string
    """
    if base_dir:
        try:
            return str(path.relative_to(base_dir))
        except ValueError:
            pass

    return path.name


def get_archive_info(path: Path) -> Dict[str, any]:
    """
    Get comprehensive archive information.

    Args:
        path: Archive file path

    Returns:
        Dictionary with archive statistics
    """
    entries = list_archive_contents(path)

    info = {
        'type': get_archive_type(path).value,
        'file_count': sum(1 for e in entries if not e.is_directory),
        'directory_count': sum(1 for e in entries if e.is_directory),
        'total_size': sum(e.size for e in entries),
        'compressed_size': sum(e.compressed_size for e in entries),
        'compression_ratio': 0.0,
        'entry_count': len(entries)
    }

    if info['total_size'] > 0:
        info['compression_ratio'] = (
            1 - info['compressed_size'] / info['total_size']
        ) * 100

    return info
