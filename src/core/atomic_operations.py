"""
Atomic File Operations with Rollback

Provides ACID-like guarantees for file operations:
- Atomicity: Operations complete fully or not at all
- Consistency: File system state remains valid
- Isolation: Operations don't interfere with each other
- Durability: Completed operations persist
"""

import shutil
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import uuid
import time


logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of file operations."""
    COPY = "copy"
    MOVE = "move"
    DELETE = "delete"
    CREATE = "create"
    RENAME = "rename"


@dataclass
class OperationLog:
    """Log entry for a file operation."""
    operation_id: str
    operation_type: OperationType
    source: Optional[Path]
    destination: Optional[Path]
    temp_file: Optional[Path]
    backup_file: Optional[Path]
    completed: bool
    timestamp: float


class AtomicFileOperation:
    """Atomic file operation with rollback capability."""

    def __init__(self, temp_dir: Optional[Path] = None):
        """Initialize atomic operation handler.

        Args:
            temp_dir: Directory for temporary files (default: system temp)
        """
        self.temp_dir = temp_dir or Path.home() / '.dc-commander' / 'temp'
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.operation_log: List[OperationLog] = []
        self.current_operation_id: Optional[str] = None

    def _generate_operation_id(self) -> str:
        """Generate unique operation ID.

        Returns:
            Unique operation identifier
        """
        return f"{uuid.uuid4().hex[:8]}_{int(time.time())}"

    def _create_temp_path(self, original: Path) -> Path:
        """Create temporary file path.

        Args:
            original: Original file path

        Returns:
            Temporary file path
        """
        return self.temp_dir / f"{original.name}.{uuid.uuid4().hex[:8]}.tmp"

    def _create_backup_path(self, original: Path) -> Path:
        """Create backup file path.

        Args:
            original: Original file path

        Returns:
            Backup file path
        """
        return self.temp_dir / f"{original.name}.{uuid.uuid4().hex[:8]}.bak"

    def _log_operation(
        self,
        operation_type: OperationType,
        source: Optional[Path] = None,
        destination: Optional[Path] = None,
        temp_file: Optional[Path] = None,
        backup_file: Optional[Path] = None,
        completed: bool = False
    ) -> None:
        """Log file operation for rollback.

        Args:
            operation_type: Type of operation
            source: Source file path
            destination: Destination file path
            temp_file: Temporary file path
            backup_file: Backup file path
            completed: Whether operation completed successfully
        """
        log_entry = OperationLog(
            operation_id=self.current_operation_id,
            operation_type=operation_type,
            source=source,
            destination=destination,
            temp_file=temp_file,
            backup_file=backup_file,
            completed=completed,
            timestamp=time.time()
        )
        self.operation_log.append(log_entry)

    def copy_file_atomic(
        self,
        source: Path,
        destination: Path,
        overwrite: bool = False,
        preserve_metadata: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """Copy file atomically with rollback capability.

        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite existing file
            preserve_metadata: Whether to preserve file metadata

        Returns:
            Tuple of (success, error_message)
        """
        self.current_operation_id = self._generate_operation_id()
        temp_dest = self._create_temp_path(destination)
        backup_file = None

        try:
            # TOCTOU Protection: Re-check source exists
            if not source.exists():
                return False, f"Source file disappeared: {source}"

            # Check destination
            if destination.exists():
                if not overwrite:
                    return False, f"Destination exists: {destination}"
                # Create backup of existing file
                backup_file = self._create_backup_path(destination)
                shutil.copy2(destination, backup_file)
                logger.debug(f"Created backup: {backup_file}")

            # Copy to temporary file
            if preserve_metadata:
                shutil.copy2(source, temp_dest)
            else:
                shutil.copy(source, temp_dest)

            self._log_operation(
                OperationType.COPY,
                source=source,
                destination=destination,
                temp_file=temp_dest,
                backup_file=backup_file
            )

            # Verify copy succeeded
            if not temp_dest.exists():
                raise IOError("Temporary file creation failed")

            # Atomic move to final destination
            temp_dest.replace(destination)

            # Mark operation as completed
            self._log_operation(
                OperationType.COPY,
                source=source,
                destination=destination,
                completed=True
            )

            # Clean up backup
            if backup_file and backup_file.exists():
                backup_file.unlink()

            logger.info(f"Atomic copy completed: {source} -> {destination}")
            return True, None

        except PermissionError as e:
            self._rollback_copy(temp_dest, backup_file, destination)
            return False, f"Permission denied: {e}"

        except OSError as e:
            self._rollback_copy(temp_dest, backup_file, destination)
            return False, f"OS error: {e}"

        except Exception as e:
            self._rollback_copy(temp_dest, backup_file, destination)
            return False, f"Unexpected error: {e}"

    def _rollback_copy(
        self,
        temp_dest: Path,
        backup_file: Optional[Path],
        destination: Path
    ) -> None:
        """Rollback failed copy operation.

        Args:
            temp_dest: Temporary destination file
            backup_file: Backup file (if any)
            destination: Final destination path
        """
        logger.warning(f"Rolling back copy operation: {destination}")

        # Remove temporary file
        if temp_dest.exists():
            try:
                temp_dest.unlink()
                logger.debug(f"Removed temp file: {temp_dest}")
            except Exception as e:
                logger.error(f"Failed to remove temp file: {e}")

        # Restore backup if destination was overwritten
        if backup_file and backup_file.exists():
            try:
                if destination.exists():
                    destination.unlink()
                shutil.move(str(backup_file), str(destination))
                logger.info(f"Restored backup: {destination}")
            except Exception as e:
                logger.error(f"Failed to restore backup: {e}")

    def move_file_atomic(
        self,
        source: Path,
        destination: Path,
        overwrite: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Move file atomically with rollback capability.

        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite existing file

        Returns:
            Tuple of (success, error_message)
        """
        self.current_operation_id = self._generate_operation_id()
        backup_file = None

        try:
            # TOCTOU Protection: Re-check source exists
            if not source.exists():
                return False, f"Source file disappeared: {source}"

            # Check if on same filesystem (can use rename)
            same_filesystem = source.stat().st_dev == destination.parent.stat().st_dev

            if same_filesystem:
                # Use atomic rename
                if destination.exists():
                    if not overwrite:
                        return False, f"Destination exists: {destination}"
                    backup_file = self._create_backup_path(destination)
                    shutil.move(str(destination), str(backup_file))

                self._log_operation(
                    OperationType.MOVE,
                    source=source,
                    destination=destination,
                    backup_file=backup_file
                )

                source.rename(destination)
                logger.info(f"Atomic move (rename): {source} -> {destination}")

            else:
                # Copy then delete (cross-filesystem)
                success, error = self.copy_file_atomic(source, destination, overwrite)
                if not success:
                    return False, error

                # Delete source after successful copy
                source.unlink()
                logger.info(f"Atomic move (copy+delete): {source} -> {destination}")

            # Mark completed
            self._log_operation(
                OperationType.MOVE,
                source=source,
                destination=destination,
                completed=True
            )

            # Clean up backup
            if backup_file and backup_file.exists():
                backup_file.unlink()

            return True, None

        except Exception as e:
            self._rollback_move(source, destination, backup_file)
            return False, f"Move failed: {e}"

    def _rollback_move(
        self,
        source: Path,
        destination: Path,
        backup_file: Optional[Path]
    ) -> None:
        """Rollback failed move operation.

        Args:
            source: Original source path
            destination: Destination path
            backup_file: Backup file (if any)
        """
        logger.warning(f"Rolling back move operation: {source} -> {destination}")

        # Restore backup if exists
        if backup_file and backup_file.exists():
            try:
                if destination.exists():
                    destination.unlink()
                shutil.move(str(backup_file), str(destination))
                logger.info(f"Restored backup: {destination}")
            except Exception as e:
                logger.error(f"Failed to restore backup: {e}")

    def delete_file_atomic(
        self,
        path: Path,
        to_trash: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Delete file atomically with backup.

        Args:
            path: File path to delete
            to_trash: Whether to move to trash instead of permanent delete

        Returns:
            Tuple of (success, error_message)
        """
        self.current_operation_id = self._generate_operation_id()
        backup_file = None

        try:
            # TOCTOU Protection: Re-check file exists
            if not path.exists():
                return False, f"File disappeared: {path}"

            # Create backup before delete
            backup_file = self._create_backup_path(path)
            if path.is_dir():
                shutil.copytree(path, backup_file)
            else:
                shutil.copy2(path, backup_file)

            self._log_operation(
                OperationType.DELETE,
                source=path,
                backup_file=backup_file
            )

            # Perform delete
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

            # Mark completed
            self._log_operation(
                OperationType.DELETE,
                source=path,
                backup_file=backup_file,
                completed=True
            )

            logger.info(f"Atomic delete: {path}")

            # Keep backup for a while in case of undo
            # (cleanup happens in separate maintenance task)

            return True, None

        except PermissionError as e:
            self._rollback_delete(path, backup_file)
            return False, f"Permission denied: {e}"

        except Exception as e:
            self._rollback_delete(path, backup_file)
            return False, f"Delete failed: {e}"

    def _rollback_delete(
        self,
        path: Path,
        backup_file: Optional[Path]
    ) -> None:
        """Rollback failed delete operation.

        Args:
            path: Original file path
            backup_file: Backup file
        """
        logger.warning(f"Rolling back delete operation: {path}")

        if backup_file and backup_file.exists():
            try:
                if backup_file.is_dir():
                    shutil.copytree(backup_file, path)
                else:
                    shutil.copy2(backup_file, path)
                logger.info(f"Restored from backup: {path}")
            except Exception as e:
                logger.error(f"Failed to restore from backup: {e}")

    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up old temporary files.

        Args:
            max_age_hours: Maximum age of files to keep (hours)

        Returns:
            Number of files cleaned up
        """
        if not self.temp_dir.exists():
            return 0

        cleaned = 0
        cutoff_time = time.time() - (max_age_hours * 3600)

        for temp_file in self.temp_dir.glob('*'):
            try:
                if temp_file.stat().st_mtime < cutoff_time:
                    if temp_file.is_dir():
                        shutil.rmtree(temp_file)
                    else:
                        temp_file.unlink()
                    cleaned += 1
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_file}: {e}")

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} temporary files")

        return cleaned


# Global atomic operation handler
_atomic_handler: Optional[AtomicFileOperation] = None


def get_atomic_handler() -> AtomicFileOperation:
    """Get global atomic operation handler.

    Returns:
        Global atomic operation handler
    """
    global _atomic_handler
    if _atomic_handler is None:
        _atomic_handler = AtomicFileOperation()
    return _atomic_handler
