"""Dialog coordination for ModernCommander.

Manages dialog creation, display, and lifecycle across the application.
Provides centralized dialog management and notification services.
"""

from typing import Callable, Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from textual.app import App
    from components.dialogs import ProgressDialog


class DialogCoordinator:
    """Manages dialog creation and lifecycle.

    Responsibilities:
    - Create and display dialogs
    - Manage dialog callbacks
    - Coordinate notifications
    - Track active dialogs
    """

    def __init__(self, app: "App"):
        """Initialize dialog coordinator.

        Args:
            app: Application instance for screen management
        """
        self.app = app
        self._active_dialogs = []

    def show_input_dialog(
        self,
        title: str,
        message: str,
        placeholder: str = "",
        callback: Optional[Callable[[Optional[str]], None]] = None
    ) -> None:
        """Show input dialog for text entry.

        Args:
            title: Dialog title
            message: Prompt message
            placeholder: Placeholder text
            callback: Callback function receiving input value
        """
        from components.dialogs import InputDialog

        dialog = InputDialog(
            title=title,
            message=message,
            placeholder=placeholder,
            on_submit=callback
        )

        self._active_dialogs.append(dialog)
        self.app.push_screen(dialog, callback=lambda result: self._handle_dialog_close(dialog, callback, result))

    def show_confirm_dialog(
        self,
        title: str,
        message: str,
        on_confirm: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        danger: bool = False
    ) -> None:
        """Show confirmation dialog.

        Args:
            title: Dialog title
            message: Confirmation message
            on_confirm: Callback for confirmation
            on_cancel: Callback for cancellation
            danger: Whether this is a dangerous operation
        """
        from components.dialogs import ConfirmDialog

        def handle_result(confirmed: bool) -> None:
            if confirmed and on_confirm:
                on_confirm()
            elif not confirmed and on_cancel:
                on_cancel()

        dialog = ConfirmDialog(
            title=title,
            message=message,
            on_confirm=lambda: handle_result(True),
            on_cancel=lambda: handle_result(False),
            danger=danger
        )

        self._active_dialogs.append(dialog)
        self.app.push_screen(dialog, callback=lambda result: self._handle_dialog_close(dialog, handle_result, result))

    def show_progress_dialog(
        self,
        title: str,
        show_cancel: bool = True,
        on_cancel: Optional[Callable[[], None]] = None
    ) -> "ProgressDialog":
        """Show progress dialog for long-running operations.

        Args:
            title: Dialog title
            show_cancel: Whether to show cancel button
            on_cancel: Callback for cancellation

        Returns:
            ProgressDialog instance for progress updates
        """
        from components.dialogs import ProgressDialog

        dialog = ProgressDialog(
            title=title,
            total=100,
            show_cancel=show_cancel,
            on_cancel=on_cancel
        )

        self._active_dialogs.append(dialog)

        def on_dialog_close(result: bool) -> None:
            self._handle_dialog_close(dialog, None, result)
            if not result and on_cancel:
                on_cancel()

        self.app.push_screen(dialog, callback=on_dialog_close)
        return dialog

    def show_message(
        self,
        title: str,
        message: str,
        message_type: str = "info"
    ) -> None:
        """Show informational message dialog.

        Args:
            title: Dialog title
            message: Message content
            message_type: Type of message ("info", "warning", "error")
        """
        from components.dialogs import MessageDialog

        dialog = MessageDialog(
            title=title,
            message=message,
            message_type=message_type
        )

        self._active_dialogs.append(dialog)
        self.app.push_screen(dialog, callback=lambda _: self._handle_dialog_close(dialog, None, None))

    def show_error_dialog(
        self,
        title: str,
        error_message: str,
        details: Optional[str] = None
    ) -> None:
        """Show error dialog with optional details.

        Args:
            title: Dialog title
            error_message: Error message
            details: Optional detailed error information
        """
        from components.dialogs import ErrorDialog

        dialog = ErrorDialog(
            title=title,
            error_message=error_message,
            details=details
        )

        self._active_dialogs.append(dialog)
        self.app.push_screen(dialog, callback=lambda _: self._handle_dialog_close(dialog, None, None))

    def notify(
        self,
        message: str,
        severity: str = "information",
        timeout: int = 3
    ) -> None:
        """Show notification message.

        Args:
            message: Notification message
            severity: Severity level ("information", "warning", "error")
            timeout: Display timeout in seconds
        """
        self.app.notify(message, severity=severity, timeout=timeout)

    def close_all_dialogs(self) -> None:
        """Close all active dialogs."""
        for dialog in self._active_dialogs:
            try:
                dialog.dismiss()
            except:
                pass
        self._active_dialogs.clear()

    def _handle_dialog_close(
        self,
        dialog: Any,
        callback: Optional[Callable],
        result: Any
    ) -> None:
        """Handle dialog close event.

        Args:
            dialog: Dialog instance
            callback: Optional callback to invoke
            result: Dialog result
        """
        if dialog in self._active_dialogs:
            self._active_dialogs.remove(dialog)

        if callback:
            callback(result)
