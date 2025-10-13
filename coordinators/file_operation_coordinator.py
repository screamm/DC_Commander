"""File operation coordination for ModernCommander.

Coordinates file operations (copy, move, delete) with progress tracking
and async support for large files. Integrates FileService and AsyncFileService.
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Callable, TYPE_CHECKING
from threading import Lock

from models.file_item import FileItem
from services.file_service import FileService, OperationSummary
from services.file_service_async import AsyncFileService, AsyncOperationProgress

if TYPE_CHECKING:
    from textual.app import App


class FileOperationCoordinator:
    """Coordinates file operations with progress tracking.

    Responsibilities:
    - Execute file operations (copy, move, delete, create directory)
    - Determine sync vs async execution strategy
    - Track operation progress
    - Handle cancellation
    """

    def __init__(self, app: "App"):
        """Initialize file operation coordinator.

        Args:
            app: Application instance for worker management
        """
        self.app = app
        self.file_service = FileService()
        self.async_file_service = AsyncFileService()
        self._progress_dialog = None
        self._progress_dialog_lock = Lock()

    @property
    def progress_dialog(self):
        """Thread-safe progress dialog accessor."""
        with self._progress_dialog_lock:
            return self._progress_dialog

    @progress_dialog.setter
    def progress_dialog(self, value):
        """Thread-safe progress dialog setter."""
        with self._progress_dialog_lock:
            self._progress_dialog = value

    def _update_progress_safely(self, percentage: int, message: str) -> None:
        """Thread-safe progress update helper.

        Args:
            percentage: Progress percentage (0-100)
            message: Progress message to display
        """
        with self._progress_dialog_lock:
            if self._progress_dialog is not None:
                self._progress_dialog.update_progress(percentage, message)

    def copy_files(
        self,
        items: List[FileItem],
        dest_path: Path,
        progress_callback: Optional[Callable] = None
    ) -> Optional[OperationSummary]:
        """Copy files to destination with automatic sync/async selection.

        Args:
            items: List of items to copy
            dest_path: Destination directory
            progress_callback: Optional progress callback for sync operations

        Returns:
            OperationSummary for sync operations, None for async
        """
        item_paths = [item.path for item in items]

        if self.async_file_service.should_use_async(item_paths):
            # Async operation - caller must handle worker setup
            return None
        else:
            # Sync operation
            result = self.file_service.copy_files(item_paths, dest_path)
            return result

    def move_files(
        self,
        items: List[FileItem],
        dest_path: Path,
        progress_callback: Optional[Callable] = None
    ) -> Optional[OperationSummary]:
        """Move files to destination with automatic sync/async selection.

        Args:
            items: List of items to move
            dest_path: Destination directory
            progress_callback: Optional progress callback for sync operations

        Returns:
            OperationSummary for sync operations, None for async
        """
        item_paths = [item.path for item in items]

        if self.async_file_service.should_use_async(item_paths):
            # Async operation - caller must handle worker setup
            return None
        else:
            # Sync operation
            result = self.file_service.move_files(item_paths, dest_path)
            return result

    def delete_files(
        self,
        items: List[FileItem],
        progress_callback: Optional[Callable] = None
    ) -> Optional[OperationSummary]:
        """Delete files with automatic sync/async selection.

        Args:
            items: List of items to delete
            progress_callback: Optional progress callback for sync operations

        Returns:
            OperationSummary for sync operations, None for async
        """
        item_paths = [item.path for item in items]

        if self.async_file_service.should_use_async(item_paths):
            # Async operation - caller must handle worker setup
            return None
        else:
            # Sync operation
            result = self.file_service.delete_files(item_paths)
            return result

    def create_directory(self, parent_path: Path, dir_name: str) -> tuple[bool, Optional[str]]:
        """Create new directory.

        Args:
            parent_path: Parent directory
            dir_name: Name of new directory

        Returns:
            Tuple of (success, error_message)
        """
        return self.file_service.create_directory(parent_path, dir_name)

    async def copy_files_async(
        self,
        items: List[FileItem],
        dest_path: Path,
        progress_callback: Optional[Callable[[AsyncOperationProgress], None]] = None
    ) -> OperationSummary:
        """Execute async copy operation.

        Args:
            items: List of items to copy
            dest_path: Destination directory
            progress_callback: Progress callback

        Returns:
            Operation summary
        """
        item_paths = [item.path for item in items]
        return await self.async_file_service.copy_files_async(
            item_paths,
            dest_path,
            overwrite=False,
            progress_callback=progress_callback
        )

    async def move_files_async(
        self,
        items: List[FileItem],
        dest_path: Path,
        progress_callback: Optional[Callable[[AsyncOperationProgress], None]] = None
    ) -> OperationSummary:
        """Execute async move operation.

        Args:
            items: List of items to move
            dest_path: Destination directory
            progress_callback: Progress callback

        Returns:
            Operation summary
        """
        item_paths = [item.path for item in items]
        return await self.async_file_service.move_files_async(
            item_paths,
            dest_path,
            overwrite=False,
            progress_callback=progress_callback
        )

    async def delete_files_async(
        self,
        items: List[FileItem],
        progress_callback: Optional[Callable[[AsyncOperationProgress], None]] = None
    ) -> OperationSummary:
        """Execute async delete operation.

        Args:
            items: List of items to delete
            progress_callback: Progress callback

        Returns:
            Operation summary
        """
        item_paths = [item.path for item in items]
        return await self.async_file_service.delete_files_async(
            item_paths,
            progress_callback=progress_callback
        )

    def cancel_operation(self) -> None:
        """Cancel current async operation."""
        self.async_file_service.cancel()

    def should_use_async(self, items: List[FileItem]) -> bool:
        """Check if async operations should be used.

        Args:
            items: List of items to process

        Returns:
            True if async operations should be used
        """
        item_paths = [item.path for item in items]
        return self.async_file_service.should_use_async(item_paths)
