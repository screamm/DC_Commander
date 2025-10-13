"""Async file service layer for Modern Commander.

Provides non-blocking file operations integrated with AsyncFileOperations.
Used for large file operations to prevent UI freezing.
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Callable, Tuple
from dataclasses import dataclass

from src.utils.async_file_ops import AsyncFileOperations, CopyProgress
from services.file_service import OperationResult, OperationSummary

# Import security validation
from src.core.security import (
    validate_path,
    sanitize_filename,
    is_safe_filename,
    SecurityError,
    UnsafePathError
)


# File size threshold for using async operations (1MB)
ASYNC_THRESHOLD_BYTES = 1 * 1024 * 1024


@dataclass
class AsyncOperationProgress:
    """Progress information for async operations."""
    current_file: str
    current_bytes: int
    total_bytes: int
    files_completed: int
    total_files: int
    percentage: float
    operation_type: str  # "copy", "move", "delete"


class AsyncFileService:
    """Async service layer for file operations."""

    def __init__(self, chunk_size: int = 64 * 1024):
        """Initialize async file service.

        Args:
            chunk_size: Bytes to read/write per chunk (default 64KB)
        """
        self.async_ops = AsyncFileOperations(chunk_size=chunk_size)
        self._cancelled = False

    def cancel(self) -> None:
        """Cancel current operation."""
        self._cancelled = True
        self.async_ops.cancel()

    def should_use_async(self, items: List[Path]) -> bool:
        """Determine if async operations should be used.

        Args:
            items: List of file/directory paths

        Returns:
            True if any file exceeds async threshold
        """
        for item in items:
            if item.is_file():
                if item.stat().st_size >= ASYNC_THRESHOLD_BYTES:
                    return True
            elif item.is_dir():
                # For directories, check if total size exceeds threshold
                try:
                    total_size = sum(
                        f.stat().st_size
                        for f in item.rglob("*")
                        if f.is_file()
                    )
                    if total_size >= ASYNC_THRESHOLD_BYTES:
                        return True
                except:
                    pass  # Assume large if can't calculate
        return False

    async def copy_files_async(
        self,
        items: List[Path],
        dest_path: Path,
        overwrite: bool = False,
        progress_callback: Optional[Callable[[AsyncOperationProgress], None]] = None
    ) -> OperationSummary:
        """Copy files asynchronously.

        Args:
            items: List of file/directory paths to copy
            dest_path: Destination directory
            overwrite: Whether to overwrite existing files
            progress_callback: Optional callback for progress updates

        Returns:
            Operation summary
        """
        self._cancelled = False
        success_count = 0
        error_count = 0
        errors = []

        # Calculate totals for progress
        total_files = 0
        total_bytes = 0
        for item in items:
            if item.is_file():
                total_files += 1
                total_bytes += item.stat().st_size
            elif item.is_dir():
                dir_files = [f for f in item.rglob("*") if f.is_file()]
                total_files += len(dir_files)
                total_bytes += sum(f.stat().st_size for f in dir_files)

        files_completed = 0
        bytes_copied = 0

        for item in items:
            if self._cancelled:
                break

            try:
                # SECURITY: Validate source path
                is_valid, error_msg = validate_path(item, item.parent)
                if not is_valid:
                    errors.append((item.name, f"Security: {error_msg}"))
                    error_count += 1
                    continue

                # SECURITY: Sanitize destination filename
                safe_name = sanitize_filename(item.name)
                dest_file = dest_path / safe_name

                # SECURITY: Validate destination path
                is_valid, error_msg = validate_path(dest_file, dest_path)
                if not is_valid:
                    errors.append((item.name, f"Security: {error_msg}"))
                    error_count += 1
                    continue

                # Check if destination exists
                if dest_file.exists() and not overwrite:
                    errors.append((item.name, "File already exists"))
                    error_count += 1
                    continue

                if item.is_dir():
                    # Copy directory with progress
                    async for file_path, success, error in self.async_ops.copy_directory_async(
                        item,
                        dest_file,
                        progress_callback=lambda p: self._update_progress(
                            p, bytes_copied, total_bytes, files_completed, total_files,
                            "copy", progress_callback
                        )
                    ):
                        if not success:
                            errors.append((file_path.name, error or "Unknown error"))
                            error_count += 1
                        else:
                            files_completed += 1
                            if file_path.is_file():
                                bytes_copied += file_path.stat().st_size
                else:
                    # Copy single file with progress
                    file_size = item.stat().st_size

                    def file_progress(bytes_done: int):
                        if progress_callback:
                            progress = AsyncOperationProgress(
                                current_file=item.name,
                                current_bytes=bytes_done,
                                total_bytes=total_bytes,
                                files_completed=files_completed,
                                total_files=total_files,
                                percentage=(bytes_copied + bytes_done) / total_bytes * 100,
                                operation_type="copy"
                            )
                            progress_callback(progress)

                    await self.async_ops.copy_file_async(
                        item,
                        dest_file,
                        progress_callback=file_progress
                    )

                    files_completed += 1
                    bytes_copied += file_size

                    # Send final progress update for this file
                    if progress_callback:
                        progress = AsyncOperationProgress(
                            current_file=item.name,
                            current_bytes=bytes_copied,
                            total_bytes=total_bytes,
                            files_completed=files_completed,
                            total_files=total_files,
                            percentage=(bytes_copied / total_bytes * 100) if total_bytes > 0 else 100.0,
                            operation_type="copy"
                        )
                        progress_callback(progress)

                success_count += 1

            except asyncio.CancelledError:
                errors.append((item.name, "Operation cancelled"))
                error_count += 1
                break
            except PermissionError as e:
                errors.append((item.name, f"Permission denied: {e}"))
                error_count += 1
            except Exception as e:
                errors.append((item.name, str(e)))
                error_count += 1

        # Determine result status
        if self._cancelled:
            result = OperationResult.PARTIAL if success_count > 0 else OperationResult.FAILURE
        elif error_count == 0:
            result = OperationResult.SUCCESS
        elif success_count == 0:
            result = OperationResult.FAILURE
        else:
            result = OperationResult.PARTIAL

        return OperationSummary(result, success_count, error_count, errors)

    async def move_files_async(
        self,
        items: List[Path],
        dest_path: Path,
        overwrite: bool = False,
        progress_callback: Optional[Callable[[AsyncOperationProgress], None]] = None
    ) -> OperationSummary:
        """Move files asynchronously.

        Args:
            items: List of file/directory paths to move
            dest_path: Destination directory
            overwrite: Whether to overwrite existing files
            progress_callback: Optional callback for progress updates

        Returns:
            Operation summary
        """
        self._cancelled = False
        success_count = 0
        error_count = 0
        errors = []

        # Calculate totals
        total_files = len(items)
        files_completed = 0

        for item in items:
            if self._cancelled:
                break

            try:
                # SECURITY: Validate and sanitize
                safe_name = sanitize_filename(item.name)
                dest_file = dest_path / safe_name

                is_valid, error_msg = validate_path(dest_file, dest_path)
                if not is_valid:
                    errors.append((item.name, f"Security: {error_msg}"))
                    error_count += 1
                    continue

                # Check if destination exists
                if dest_file.exists() and not overwrite:
                    errors.append((item.name, "File already exists"))
                    error_count += 1
                    continue

                # Move file/directory
                await self.async_ops.move_file_async(item, dest_file)

                success_count += 1
                files_completed += 1

                # Update progress
                if progress_callback:
                    progress = AsyncOperationProgress(
                        current_file=item.name,
                        current_bytes=0,
                        total_bytes=0,
                        files_completed=files_completed,
                        total_files=total_files,
                        percentage=files_completed / total_files * 100,
                        operation_type="move"
                    )
                    progress_callback(progress)

            except asyncio.CancelledError:
                errors.append((item.name, "Operation cancelled"))
                error_count += 1
                break
            except PermissionError as e:
                errors.append((item.name, f"Permission denied: {e}"))
                error_count += 1
            except Exception as e:
                errors.append((item.name, str(e)))
                error_count += 1

        # Determine result status
        if self._cancelled:
            result = OperationResult.PARTIAL if success_count > 0 else OperationResult.FAILURE
        elif error_count == 0:
            result = OperationResult.SUCCESS
        elif success_count == 0:
            result = OperationResult.FAILURE
        else:
            result = OperationResult.PARTIAL

        return OperationSummary(result, success_count, error_count, errors)

    async def delete_files_async(
        self,
        items: List[Path],
        progress_callback: Optional[Callable[[AsyncOperationProgress], None]] = None
    ) -> OperationSummary:
        """Delete files asynchronously.

        Args:
            items: List of file/directory paths to delete
            progress_callback: Optional callback for progress updates

        Returns:
            Operation summary
        """
        self._cancelled = False
        success_count = 0
        error_count = 0
        errors = []

        # Calculate totals
        total_files = len(items)
        files_completed = 0

        for item in items:
            if self._cancelled:
                break

            try:
                await self.async_ops.delete_file_async(item)

                success_count += 1
                files_completed += 1

                # Update progress
                if progress_callback:
                    progress = AsyncOperationProgress(
                        current_file=item.name,
                        current_bytes=0,
                        total_bytes=0,
                        files_completed=files_completed,
                        total_files=total_files,
                        percentage=files_completed / total_files * 100,
                        operation_type="delete"
                    )
                    progress_callback(progress)

            except asyncio.CancelledError:
                errors.append((item.name, "Operation cancelled"))
                error_count += 1
                break
            except PermissionError as e:
                errors.append((item.name, f"Permission denied: {e}"))
                error_count += 1
            except Exception as e:
                errors.append((item.name, str(e)))
                error_count += 1

        # Determine result status
        if self._cancelled:
            result = OperationResult.PARTIAL if success_count > 0 else OperationResult.FAILURE
        elif error_count == 0:
            result = OperationResult.SUCCESS
        elif success_count == 0:
            result = OperationResult.FAILURE
        else:
            result = OperationResult.PARTIAL

        return OperationSummary(result, success_count, error_count, errors)

    def _update_progress(
        self,
        copy_progress: CopyProgress,
        base_bytes: int,
        total_bytes: int,
        base_files: int,
        total_files: int,
        operation_type: str,
        callback: Optional[Callable[[AsyncOperationProgress], None]]
    ) -> None:
        """Internal helper to update progress during directory copy.

        Args:
            copy_progress: Progress from async operation
            base_bytes: Previously completed bytes
            total_bytes: Total bytes for entire operation
            base_files: Previously completed files
            total_files: Total files for entire operation
            operation_type: Type of operation
            callback: Progress callback
        """
        if callback:
            progress = AsyncOperationProgress(
                current_file=copy_progress.current_file,
                current_bytes=base_bytes + copy_progress.bytes_copied,
                total_bytes=total_bytes,
                files_completed=base_files + copy_progress.files_completed,
                total_files=total_files,
                percentage=(base_bytes + copy_progress.bytes_copied) / total_bytes * 100,
                operation_type=operation_type
            )
            callback(progress)
