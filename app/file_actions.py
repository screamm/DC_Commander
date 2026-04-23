"""File-operation action handlers for ModernCommanderApp.

This module extracts copy, move, delete, and create-directory logic from
the ``modern_commander`` monolith into :class:`FileActionsController`.
``ModernCommanderApp`` holds a single instance and delegates its
``action_copy_files``, ``action_move_files``, ``action_delete_files``,
and ``action_create_directory`` F-key handlers to the corresponding
methods on this controller.

Behaviour is preserved verbatim: each public method mirrors the previous
monolith method one-for-one. The controller reaches into the owning app
for panels, services, progress dialog state, and refresh/notify
utilities rather than duplicating that state.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Callable, List, Optional

from textual.worker import Worker  # noqa: F401  (kept for parity of imports)

from src.utils.logging_config import get_logger

from components.dialogs import (
    ConfirmDialog,
    ErrorDialog,
    InputDialog,
    ProgressDialog,
)
from models.file_item import FileItem
from services.file_service_async import AsyncOperationProgress
from src.core.error_messages import format_user_error
from src.core.ui_security import UIValidationError, validate_user_filename

if TYPE_CHECKING:
    from modern_commander import ModernCommanderApp


logger = get_logger(__name__)


class FileActionsController:
    """File-operation action handlers extracted from ModernCommanderApp.

    Owns the F5 (copy), F6 (move), F7 (create directory), and F8
    (delete) action entry points plus their sync / async / worker
    machinery. The controller never holds its own state; it reads and
    writes to the owning ``ModernCommanderApp`` so the refactor is
    purely organisational.

    Args:
        app: The owning ``ModernCommanderApp`` instance. Held as a
            back-reference so the controller can reach shared panels,
            services, and error boundary without re-implementing them.
    """

    def __init__(self, app: "ModernCommanderApp") -> None:
        self.app = app
        # Share the app-wide error boundary reference. This mirrors how
        # the monolith recorded errors — no new boundary is created.
        self._error_boundary = app._error_boundary

    # ------------------------------------------------------------------
    # Error dialog helper (shared across all file actions)
    # ------------------------------------------------------------------
    def show_error_dialog(
        self,
        exc: BaseException,
        *,
        operation_label: str,
        retry_callable: Optional[Callable[[], None]] = None,
    ) -> None:
        """Surface a file-operation exception through :class:`ErrorDialog`.

        This is the central failure-surfacing entrypoint for F-key
        handlers. It:

        1. Logs the exception with full traceback via
           ``logger.exception``.
        2. Maps the exception to a friendly user message plus technical
           details via :func:`format_user_error`.
        3. Pushes an :class:`ErrorDialog` with Retry (if a retry
           callable was provided) and Cancel buttons.
        4. On Retry, invokes ``retry_callable`` exactly once. A second
           failure surfaces the dialog again WITHOUT a Retry button to
           avoid infinite loops.

        Args:
            exc: The exception that was caught.
            operation_label: Short human label such as ``"Copy"`` used
                in the dialog title.
            retry_callable: Zero-argument callable that re-executes the
                failed operation. ``None`` disables the Retry button.
        """
        logger.exception(
            "%s operation failed: %s",
            operation_label,
            type(exc).__name__,
        )

        user_msg, details = format_user_error(exc)
        title = f"{operation_label} failed"
        allow_retry = retry_callable is not None

        def on_close(action: Optional[str]) -> None:
            if action == "retry" and retry_callable is not None:
                # Single retry. If it fails again, show the dialog
                # once more but WITHOUT retry to prevent an infinite
                # loop.
                try:
                    retry_callable()
                except (KeyboardInterrupt, asyncio.CancelledError):
                    raise
                except BaseException as retry_exc:  # noqa: BLE001
                    logger.exception(
                        "%s retry failed: %s",
                        operation_label,
                        type(retry_exc).__name__,
                    )
                    self.show_error_dialog(
                        retry_exc,
                        operation_label=operation_label,
                        retry_callable=None,  # no more retries
                    )

        dialog = ErrorDialog(
            message=user_msg,
            title=title,
            details=details,
            allow_retry=allow_retry,
            allow_cancel=True,
            on_close=on_close,
        )
        self.app.push_screen(dialog)

    # ------------------------------------------------------------------
    # F5 — Copy
    # ------------------------------------------------------------------
    def copy_files(self) -> None:
        """F5 - Copy selected files to other panel."""
        app = self.app
        active_panel = app._get_active_panel()
        inactive_panel = app._get_inactive_panel()

        # Get selected items or current item
        selected_items = active_panel.get_selected_items()
        if not selected_items:
            current_item = active_panel.get_current_item()
            if current_item and not current_item.is_parent:
                selected_items = [current_item]

        if not selected_items:
            app.notify("No files selected", severity="warning")
            return

        # Confirm copy
        count = len(selected_items)
        dest_path = inactive_panel.current_path

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                self._perform_copy(selected_items, dest_path)

        dialog = ConfirmDialog(
            title="Copy Files",
            message=f"Copy {count} file(s) to:\n{dest_path}",
            on_confirm=lambda: handle_confirm(True),
            on_cancel=lambda: handle_confirm(False),
        )

        app.push_screen(dialog, callback=handle_confirm)

    def _perform_copy(self, items: list[FileItem], dest_path: Path) -> None:
        """Perform copy operation with async support for large files.

        Args:
            items: List of items to copy
            dest_path: Destination directory
        """
        try:
            # Convert FileItem list to Path list
            item_paths = [item.path for item in items]

            # Check if async is needed
            if self.app.async_file_service.should_use_async(item_paths):
                # Use async operation with progress dialog
                self._perform_copy_async(items, dest_path)
            else:
                # Use sync operation for small files
                self._perform_copy_sync(items, dest_path)
        except (KeyboardInterrupt, asyncio.CancelledError):
            raise
        except BaseException as exc:  # noqa: BLE001
            self.show_error_dialog(
                exc,
                operation_label="Copy",
                retry_callable=lambda: self._perform_copy(items, dest_path),
            )

    def _perform_copy_sync(
        self, items: list[FileItem], dest_path: Path
    ) -> None:
        """Synchronous copy operation for small files.

        Args:
            items: List of items to copy
            dest_path: Destination directory
        """
        import shutil

        app = self.app
        success_count = 0
        error_count = 0

        for item in items:
            try:
                dest_file = dest_path / item.name

                if item.is_dir:
                    shutil.copytree(item.path, dest_file, dirs_exist_ok=False)
                else:
                    shutil.copy2(item.path, dest_file)

                success_count += 1

            except Exception as e:
                error_count += 1
                app.notify(
                    f"Failed to copy {item.name}: {e}", severity="error"
                )

        # Refresh panels
        app.action_refresh_panels()

        # Show result
        if error_count == 0:
            app.notify(
                f"Successfully copied {success_count} file(s)",
                severity="information",
            )
        else:
            app.notify(
                f"Copied {success_count} file(s) with {error_count} error(s)",
                severity="warning",
            )

    def _perform_copy_async(
        self, items: list[FileItem], dest_path: Path
    ) -> None:
        """Asynchronous copy operation for large files with progress dialog.

        Args:
            items: List of items to copy
            dest_path: Destination directory
        """
        app = self.app
        # Convert FileItem list to Path list
        item_paths = [item.path for item in items]

        # Show progress dialog
        def handle_cancel() -> None:
            app.async_file_service.cancel()

        app.progress_dialog = ProgressDialog(
            title="Copying Files",
            total=100,
            show_cancel=True,
            on_cancel=handle_cancel,
        )

        def on_dialog_close(result: bool) -> None:
            app.progress_dialog = None
            if not result:
                app.notify("Copy operation cancelled", severity="warning")

        app.push_screen(app.progress_dialog, callback=on_dialog_close)

        # Run async operation in worker
        app.run_worker(
            self._copy_worker(item_paths, dest_path),
            name="copy_operation",
            group="file_operations",
            description="Copying files",
        )

    async def _copy_worker(
        self, items: List[Path], dest_path: Path
    ) -> None:
        """Async worker for copy operation.

        Args:
            items: List of paths to copy
            dest_path: Destination directory
        """
        app = self.app

        def progress_callback(progress: AsyncOperationProgress) -> None:
            """Update progress dialog from async operation."""
            app._update_progress_safely(
                progress.percentage,
                f"Copying {progress.current_file} "
                f"({progress.files_completed}/{progress.total_files})",
            )

        try:
            # Perform async copy
            result = await app.async_file_service.copy_files_async(
                items,
                dest_path,
                overwrite=False,
                progress_callback=progress_callback,
            )

            # Close progress dialog (thread-safe atomic check-and-dismiss)
            with app._progress_dialog_lock:
                if app._progress_dialog is not None:
                    app.app.call_from_thread(
                        app._progress_dialog.dismiss, True
                    )

            # Refresh panels on main thread
            app.app.call_from_thread(app.action_refresh_panels)

            # Show result notification
            if result.error_count == 0:
                app.app.call_from_thread(
                    app.notify,
                    f"Successfully copied {result.success_count} file(s)",
                    severity="information",
                )
            else:
                app.app.call_from_thread(
                    app.notify,
                    f"Copied {result.success_count} file(s) with "
                    f"{result.error_count} error(s)",
                    severity="warning",
                )

                # Show detailed errors
                for filename, error_msg in result.errors:
                    app.app.call_from_thread(
                        app.notify,
                        f"Failed to copy {filename}: {error_msg}",
                        severity="error",
                        timeout=5,
                    )

        except Exception as e:
            # Close progress dialog (thread-safe atomic check-and-dismiss)
            with app._progress_dialog_lock:
                if app._progress_dialog is not None:
                    app.app.call_from_thread(
                        app._progress_dialog.dismiss, False
                    )

            # Show error
            app.app.call_from_thread(
                app.notify,
                f"Copy operation failed: {e}",
                severity="error",
            )

    # ------------------------------------------------------------------
    # F6 — Move
    # ------------------------------------------------------------------
    def move_files(self) -> None:
        """F6 - Move selected files to other panel."""
        app = self.app
        active_panel = app._get_active_panel()
        inactive_panel = app._get_inactive_panel()

        # Get selected items or current item
        selected_items = active_panel.get_selected_items()
        if not selected_items:
            current_item = active_panel.get_current_item()
            if current_item and not current_item.is_parent:
                selected_items = [current_item]

        if not selected_items:
            app.notify("No files selected", severity="warning")
            return

        # Confirm move
        count = len(selected_items)
        dest_path = inactive_panel.current_path

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                self._perform_move(selected_items, dest_path)

        dialog = ConfirmDialog(
            title="Move Files",
            message=f"Move {count} file(s) to:\n{dest_path}",
            on_confirm=lambda: handle_confirm(True),
            on_cancel=lambda: handle_confirm(False),
            danger=True,
        )

        app.push_screen(dialog, callback=handle_confirm)

    def _perform_move(self, items: list[FileItem], dest_path: Path) -> None:
        """Perform move operation with async support for large files.

        Args:
            items: List of items to move
            dest_path: Destination directory
        """
        try:
            # Convert FileItem list to Path list
            item_paths = [item.path for item in items]

            # Check if async is needed
            if self.app.async_file_service.should_use_async(item_paths):
                # Use async operation with progress dialog
                self._perform_move_async(items, dest_path)
            else:
                # Use sync operation for small files
                self._perform_move_sync(items, dest_path)
        except (KeyboardInterrupt, asyncio.CancelledError):
            raise
        except BaseException as exc:  # noqa: BLE001
            self.show_error_dialog(
                exc,
                operation_label="Move",
                retry_callable=lambda: self._perform_move(items, dest_path),
            )

    def _perform_move_sync(
        self, items: list[FileItem], dest_path: Path
    ) -> None:
        """Synchronous move operation for small files.

        Args:
            items: List of items to move
            dest_path: Destination directory
        """
        import shutil

        app = self.app
        success_count = 0
        error_count = 0

        for item in items:
            try:
                dest_file = dest_path / item.name
                shutil.move(str(item.path), str(dest_file))
                success_count += 1

            except Exception as e:
                error_count += 1
                app.notify(
                    f"Failed to move {item.name}: {e}", severity="error"
                )

        # Refresh panels
        app.action_refresh_panels()

        # Show result
        if error_count == 0:
            app.notify(
                f"Successfully moved {success_count} file(s)",
                severity="information",
            )
        else:
            app.notify(
                f"Moved {success_count} file(s) with {error_count} error(s)",
                severity="warning",
            )

    def _perform_move_async(
        self, items: list[FileItem], dest_path: Path
    ) -> None:
        """Asynchronous move operation for large files with progress dialog.

        Args:
            items: List of items to move
            dest_path: Destination directory
        """
        app = self.app
        # Convert FileItem list to Path list
        item_paths = [item.path for item in items]

        # Show progress dialog
        def handle_cancel() -> None:
            app.async_file_service.cancel()

        app.progress_dialog = ProgressDialog(
            title="Moving Files",
            total=100,
            show_cancel=True,
            on_cancel=handle_cancel,
        )

        def on_dialog_close(result: bool) -> None:
            app.progress_dialog = None
            if not result:
                app.notify("Move operation cancelled", severity="warning")

        app.push_screen(app.progress_dialog, callback=on_dialog_close)

        # Run async operation in worker
        app.run_worker(
            self._move_worker(item_paths, dest_path),
            name="move_operation",
            group="file_operations",
            description="Moving files",
        )

    async def _move_worker(
        self, items: List[Path], dest_path: Path
    ) -> None:
        """Async worker for move operation.

        Args:
            items: List of paths to move
            dest_path: Destination directory
        """
        app = self.app

        def progress_callback(progress: AsyncOperationProgress) -> None:
            """Update progress dialog from async operation."""
            app._update_progress_safely(
                progress.percentage,
                f"Moving {progress.current_file} "
                f"({progress.files_completed}/{progress.total_files})",
            )

        try:
            # Perform async move
            result = await app.async_file_service.move_files_async(
                items,
                dest_path,
                overwrite=False,
                progress_callback=progress_callback,
            )

            # Close progress dialog (thread-safe atomic check-and-dismiss)
            with app._progress_dialog_lock:
                if app._progress_dialog is not None:
                    app.app.call_from_thread(
                        app._progress_dialog.dismiss, True
                    )

            # Refresh panels
            app.app.call_from_thread(app.action_refresh_panels)

            # Show result notification
            if result.error_count == 0:
                app.app.call_from_thread(
                    app.notify,
                    f"Successfully moved {result.success_count} file(s)",
                    severity="information",
                )
            else:
                app.app.call_from_thread(
                    app.notify,
                    f"Moved {result.success_count} file(s) with "
                    f"{result.error_count} error(s)",
                    severity="warning",
                )

                # Show detailed errors
                for filename, error_msg in result.errors:
                    app.app.call_from_thread(
                        app.notify,
                        f"Failed to move {filename}: {error_msg}",
                        severity="error",
                        timeout=5,
                    )

        except Exception as e:
            # Close progress dialog (thread-safe atomic check-and-dismiss)
            with app._progress_dialog_lock:
                if app._progress_dialog is not None:
                    app.app.call_from_thread(
                        app._progress_dialog.dismiss, False
                    )

            # Show error
            app.app.call_from_thread(
                app.notify,
                f"Move operation failed: {e}",
                severity="error",
            )

    # ------------------------------------------------------------------
    # F7 — Create directory
    # ------------------------------------------------------------------
    def create_directory(self) -> None:
        """F7 - Create new directory.

        User input is validated via :func:`validate_user_filename`
        before any filesystem call. Invalid input surfaces an
        :class:`ErrorDialog` with Retry; on Retry the
        :class:`InputDialog` is reopened with the last attempted value
        preserved so the user can correct their entry.
        """
        app = self.app
        active_panel = app._get_active_panel()
        parent_path = active_panel.current_path

        def prompt(default: str = "") -> None:
            """Open the create-directory InputDialog (retry-reusable)."""

            def handle_input(dir_name: Optional[str]) -> None:
                if dir_name is None:
                    # User cancelled — nothing to do.
                    return
                try:
                    safe_name = validate_user_filename(dir_name)
                except UIValidationError as exc:
                    # Validator already emitted logger.warning. Re-prompt
                    # through an ErrorDialog(retry=True) that, on retry,
                    # reopens the InputDialog with the bad input so the
                    # user can edit it instead of retyping from scratch.
                    def on_close(action: Optional[str]) -> None:
                        if action == "retry":
                            prompt(default=dir_name)

                    app.push_screen(
                        ErrorDialog(
                            message=exc.user_message,
                            title="Invalid input",
                            details=exc.technical_details,
                            allow_retry=True,
                            allow_cancel=True,
                            on_close=on_close,
                        )
                    )
                    return

                self._perform_create_directory(parent_path, safe_name)

            dialog = InputDialog(
                title="Create Directory",
                message="Enter directory name:",
                placeholder="New Folder",
                default=default,
                on_submit=handle_input,
            )
            app.push_screen(dialog)

        prompt()

    def _perform_create_directory(
        self, parent_path: Path, dir_name: str
    ) -> None:
        """Create new directory.

        Args:
            parent_path: Parent directory
            dir_name: Name of new directory
        """
        app = self.app
        try:
            new_dir = parent_path / dir_name
            new_dir.mkdir(parents=False, exist_ok=False)

            # Refresh panels
            app.action_refresh_panels()

            app.notify(
                f"Created directory: {dir_name}", severity="information"
            )

        except (KeyboardInterrupt, asyncio.CancelledError):
            raise
        except BaseException as exc:  # noqa: BLE001
            self.show_error_dialog(
                exc,
                operation_label="Create directory",
                retry_callable=lambda: self._perform_create_directory(
                    parent_path, dir_name
                ),
            )

    # ------------------------------------------------------------------
    # F8 — Delete
    # ------------------------------------------------------------------
    def delete_files(self) -> None:
        """F8 - Delete selected files."""
        app = self.app
        active_panel = app._get_active_panel()

        # Get selected items or current item
        selected_items = active_panel.get_selected_items()
        if not selected_items:
            current_item = active_panel.get_current_item()
            if current_item and not current_item.is_parent:
                selected_items = [current_item]

        if not selected_items:
            app.notify("No files selected", severity="warning")
            return

        # Confirm deletion
        count = len(selected_items)

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                self._perform_delete(selected_items)

        dialog = ConfirmDialog(
            title="Delete Files",
            message=f"Permanently delete {count} file(s)?",
            on_confirm=lambda: handle_confirm(True),
            on_cancel=lambda: handle_confirm(False),
            danger=True,
        )

        app.push_screen(dialog, callback=handle_confirm)

    def _perform_delete(self, items: list[FileItem]) -> None:
        """Delete files/directories with async support for large operations.

        Args:
            items: List of items to delete
        """
        try:
            # Convert FileItem list to Path list
            item_paths = [item.path for item in items]

            # Check if async is needed
            if self.app.async_file_service.should_use_async(item_paths):
                # Use async operation with progress dialog
                self._perform_delete_async(items)
            else:
                # Use sync operation for small files
                self._perform_delete_sync(items)
        except (KeyboardInterrupt, asyncio.CancelledError):
            raise
        except BaseException as exc:  # noqa: BLE001
            self.show_error_dialog(
                exc,
                operation_label="Delete",
                retry_callable=lambda: self._perform_delete(items),
            )

    def _perform_delete_sync(self, items: list[FileItem]) -> None:
        """Synchronous delete operation for small files.

        Args:
            items: List of items to delete
        """
        import shutil

        app = self.app
        success_count = 0
        error_count = 0

        for item in items:
            try:
                # CRITICAL FIX: Create fresh Path object from string to
                # avoid stale references. Path objects from iterdir()
                # can become invalid in async/reactive systems.
                delete_path = Path(str(item.path))

                # Re-validate path existence at delete time (TOCTOU protection)
                if not delete_path.exists():
                    error_count += 1
                    app.notify(
                        f"{item.name} no longer exists", severity="error"
                    )
                    continue

                # Use fresh Path object with re-checked type
                # Don't rely on stale item.is_dir flag
                if delete_path.is_dir():
                    # Use str() for maximum Windows compatibility
                    shutil.rmtree(str(delete_path))
                else:
                    delete_path.unlink()

                success_count += 1

            except Exception as e:
                error_count += 1
                app.notify(
                    f"Failed to delete {item.name}: {e}", severity="error"
                )

        # Refresh panels
        app.action_refresh_panels()

        # Show result
        if error_count == 0:
            app.notify(
                f"Successfully deleted {success_count} file(s)",
                severity="information",
            )
        else:
            app.notify(
                f"Deleted {success_count} file(s) with {error_count} error(s)",
                severity="warning",
            )

    def _perform_delete_async(self, items: list[FileItem]) -> None:
        """Asynchronous delete operation for large files with progress dialog.

        Args:
            items: List of items to delete
        """
        app = self.app
        # Convert FileItem list to Path list
        item_paths = [item.path for item in items]

        # Show progress dialog
        def handle_cancel() -> None:
            app.async_file_service.cancel()

        app.progress_dialog = ProgressDialog(
            title="Deleting Files",
            total=100,
            show_cancel=True,
            on_cancel=handle_cancel,
        )

        def on_dialog_close(result: bool) -> None:
            app.progress_dialog = None
            if not result:
                app.notify("Delete operation cancelled", severity="warning")

        app.push_screen(app.progress_dialog, callback=on_dialog_close)

        # Run async operation in worker
        app.run_worker(
            self._delete_worker(item_paths),
            name="delete_operation",
            group="file_operations",
            description="Deleting files",
        )

    async def _delete_worker(self, items: List[Path]) -> None:
        """Async worker for delete operation.

        Args:
            items: List of paths to delete
        """
        app = self.app

        def progress_callback(progress: AsyncOperationProgress) -> None:
            """Update progress dialog from async operation."""
            app._update_progress_safely(
                progress.percentage,
                f"Deleting {progress.current_file} "
                f"({progress.files_completed}/{progress.total_files})",
            )

        try:
            # Perform async delete
            result = await app.async_file_service.delete_files_async(
                items,
                progress_callback=progress_callback,
            )

            # Close progress dialog (thread-safe atomic check-and-dismiss)
            with app._progress_dialog_lock:
                if app._progress_dialog is not None:
                    app.app.call_from_thread(
                        app._progress_dialog.dismiss, True
                    )

            # Refresh panels
            app.app.call_from_thread(app.action_refresh_panels)

            # Show result notification
            if result.error_count == 0:
                app.app.call_from_thread(
                    app.notify,
                    f"Successfully deleted {result.success_count} file(s)",
                    severity="information",
                )
            else:
                app.app.call_from_thread(
                    app.notify,
                    f"Deleted {result.success_count} file(s) with "
                    f"{result.error_count} error(s)",
                    severity="warning",
                )

                # Show detailed errors
                for filename, error_msg in result.errors:
                    app.app.call_from_thread(
                        app.notify,
                        f"Failed to delete {filename}: {error_msg}",
                        severity="error",
                        timeout=5,
                    )

        except Exception as e:
            # Close progress dialog (thread-safe atomic check-and-dismiss)
            with app._progress_dialog_lock:
                if app._progress_dialog is not None:
                    app.app.call_from_thread(
                        app._progress_dialog.dismiss, False
                    )

            # Show error
            app.app.call_from_thread(
                app.notify,
                f"Delete operation failed: {e}",
                severity="error",
            )
