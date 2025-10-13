"""Dialog system for Modern Commander.

Provides various dialog types for user interaction.
"""

from typing import Optional, Callable, List
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Input, ProgressBar, Label
from textual.screen import ModalScreen
from textual.reactive import reactive


class BaseDialog(ModalScreen):
    """Base dialog class with common styling."""

    DEFAULT_CSS = """
    BaseDialog {
        align: center middle;
    }

    BaseDialog > Container {
        width: auto;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }

    BaseDialog .dialog-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        background: $surface-darken-1;
        padding: 0 1;
        margin-bottom: 1;
    }

    BaseDialog .dialog-content {
        margin-bottom: 1;
        min-width: 40;
    }

    BaseDialog .dialog-buttons {
        align: center middle;
        height: auto;
    }

    BaseDialog Button {
        margin: 0 1;
        min-width: 10;
    }

    BaseDialog .primary-button {
        background: $primary;
        color: $text;
    }

    BaseDialog .danger-button {
        background: $error;
        color: $text;
    }
    """

    def __init__(
        self,
        title: str,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """Initialize base dialog.

        Args:
            title: Dialog title
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self.dialog_title = title


class ConfirmDialog(BaseDialog):
    """Confirmation dialog with Yes/No options."""

    def __init__(
        self,
        title: str,
        message: str,
        on_confirm: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        danger: bool = False,
        name: Optional[str] = None,
    ) -> None:
        """Initialize confirmation dialog.

        Args:
            title: Dialog title
            message: Confirmation message
            on_confirm: Callback for confirmation
            on_cancel: Callback for cancellation
            danger: Use danger styling
            name: Widget name
        """
        super().__init__(title, name=name)
        self.message = message
        self.on_confirm_callback = on_confirm
        self.on_cancel_callback = on_cancel
        self.danger = danger

    def compose(self) -> ComposeResult:
        """Compose dialog widgets."""
        with Container():
            yield Static(self.dialog_title, classes="dialog-title")
            yield Static(self.message, classes="dialog-content")

            with Horizontal(classes="dialog-buttons"):
                button_class = "danger-button" if self.danger else "primary-button"
                yield Button("Yes", variant="primary", id="yes", classes=button_class)
                yield Button("No", variant="default", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press.

        Args:
            event: Button pressed event
        """
        if event.button.id == "yes":
            if self.on_confirm_callback:
                self.on_confirm_callback()
            self.dismiss(True)
        else:
            if self.on_cancel_callback:
                self.on_cancel_callback()
            self.dismiss(False)

    def on_key(self, event) -> None:
        """Handle keyboard input.

        Args:
            event: Key event
        """
        if event.key == "y":
            self.query_one("#yes", Button).press()
        elif event.key == "n" or event.key == "escape":
            self.query_one("#no", Button).press()


class InputDialog(BaseDialog):
    """Text input dialog."""

    def __init__(
        self,
        title: str,
        message: str,
        default: str = "",
        placeholder: str = "",
        on_submit: Optional[Callable[[str], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        password: bool = False,
        name: Optional[str] = None,
    ) -> None:
        """Initialize input dialog.

        Args:
            title: Dialog title
            message: Input prompt message
            default: Default input value
            placeholder: Input placeholder text
            on_submit: Callback for submission
            on_cancel: Callback for cancellation
            password: Use password input
            name: Widget name
        """
        super().__init__(title, name=name)
        self.message = message
        self.default = default
        self.placeholder = placeholder
        self.on_submit_callback = on_submit
        self.on_cancel_callback = on_cancel
        self.password = password

    def compose(self) -> ComposeResult:
        """Compose dialog widgets."""
        with Container():
            yield Static(self.dialog_title, classes="dialog-title")
            yield Static(self.message, classes="dialog-content")

            yield Input(
                value=self.default,
                placeholder=self.placeholder,
                password=self.password,
                id="input_field",
            )

            with Horizontal(classes="dialog-buttons"):
                yield Button("OK", variant="primary", id="ok", classes="primary-button")
                yield Button("Cancel", variant="default", id="cancel")

    def on_mount(self) -> None:
        """Focus input on mount."""
        self.query_one("#input_field", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press.

        Args:
            event: Button pressed event
        """
        if event.button.id == "ok":
            value = self.query_one("#input_field", Input).value
            if self.on_submit_callback:
                self.on_submit_callback(value)
            self.dismiss(value)
        else:
            if self.on_cancel_callback:
                self.on_cancel_callback()
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission.

        Args:
            event: Input submitted event
        """
        self.query_one("#ok", Button).press()


class MessageDialog(BaseDialog):
    """Simple message dialog."""

    def __init__(
        self,
        title: str,
        message: str,
        message_type: str = "info",
        on_close: Optional[Callable[[], None]] = None,
        name: Optional[str] = None,
    ) -> None:
        """Initialize message dialog.

        Args:
            title: Dialog title
            message: Message to display
            message_type: Message type (info, warning, error, success)
            on_close: Callback for close
            name: Widget name
        """
        super().__init__(title, name=name)
        self.message = message
        self.message_type = message_type
        self.on_close_callback = on_close

    def compose(self) -> ComposeResult:
        """Compose dialog widgets."""
        with Container():
            title_class = f"dialog-title {self.message_type}"
            yield Static(self.dialog_title, classes=title_class)
            yield Static(self.message, classes="dialog-content")

            with Horizontal(classes="dialog-buttons"):
                yield Button("OK", variant="primary", id="ok", classes="primary-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press.

        Args:
            event: Button pressed event
        """
        if self.on_close_callback:
            self.on_close_callback()
        self.dismiss(True)

    def on_key(self, event) -> None:
        """Handle keyboard input.

        Args:
            event: Key event
        """
        if event.key == "enter" or event.key == "escape":
            self.query_one("#ok", Button).press()


class ErrorDialog(MessageDialog):
    """Error message dialog with danger styling."""

    DEFAULT_CSS = """
    ErrorDialog .dialog-title {
        background: $error;
        color: $text;
    }
    """

    def __init__(
        self,
        message: str,
        title: str = "Error",
        on_close: Optional[Callable[[], None]] = None,
        name: Optional[str] = None,
    ) -> None:
        """Initialize error dialog.

        Args:
            message: Error message
            title: Dialog title
            on_close: Callback for close
            name: Widget name
        """
        super().__init__(
            title=title,
            message=message,
            message_type="error",
            on_close=on_close,
            name=name,
        )


class ProgressDialog(BaseDialog):
    """Progress dialog with progress bar."""

    DEFAULT_CSS = """
    ProgressDialog .progress-label {
        text-align: center;
        margin-bottom: 1;
    }

    ProgressDialog ProgressBar {
        margin-bottom: 1;
    }
    """

    progress: reactive[float] = reactive(0.0)
    status_text: reactive[str] = reactive("")

    def __init__(
        self,
        title: str,
        total: int = 100,
        show_cancel: bool = False,
        on_cancel: Optional[Callable[[], None]] = None,
        name: Optional[str] = None,
    ) -> None:
        """Initialize progress dialog.

        Args:
            title: Dialog title
            total: Total progress value
            show_cancel: Show cancel button
            on_cancel: Callback for cancellation
            name: Widget name
        """
        super().__init__(title, name=name)
        self.total = total
        self.show_cancel = show_cancel
        self.on_cancel_callback = on_cancel
        self._cancelled = False

    def compose(self) -> ComposeResult:
        """Compose dialog widgets."""
        with Container():
            yield Static(self.dialog_title, classes="dialog-title")
            yield Label("", id="progress_label", classes="progress-label")
            yield ProgressBar(total=self.total, show_eta=True, id="progress_bar")

            if self.show_cancel:
                with Horizontal(classes="dialog-buttons"):
                    yield Button("Cancel", variant="default", id="cancel")

    def watch_progress(self, progress: float) -> None:
        """React to progress changes.

        Args:
            progress: New progress value
        """
        # Only update widgets if mounted
        if self.is_mounted:
            try:
                progress_bar = self.query_one("#progress_bar", ProgressBar)
                progress_bar.update(progress=progress)
            except:
                pass  # Widget not ready yet

    def watch_status_text(self, text: str) -> None:
        """React to status text changes.

        Args:
            text: New status text
        """
        # Only update widgets if mounted
        if self.is_mounted:
            try:
                label = self.query_one("#progress_label", Label)
                label.update(text)
            except:
                pass  # Widget not ready yet

    def update_progress(self, progress: float, status: Optional[str] = None) -> None:
        """Update progress and status.

        Args:
            progress: New progress value
            status: New status text
        """
        self.progress = progress
        if status:
            self.status_text = status

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press.

        Args:
            event: Button pressed event
        """
        if event.button.id == "cancel":
            self._cancelled = True
            if self.on_cancel_callback:
                self.on_cancel_callback()
            self.dismiss(False)

    @property
    def is_cancelled(self) -> bool:
        """Check if dialog was cancelled.

        Returns:
            True if cancelled
        """
        return self._cancelled


class ListDialog(BaseDialog):
    """Dialog for selecting from a list of items."""

    DEFAULT_CSS = """
    ListDialog .list-container {
        height: 15;
        border: solid $accent;
        margin-bottom: 1;
    }

    ListDialog .list-item {
        padding: 0 1;
    }

    ListDialog .list-item:hover {
        background: $primary 50%;
    }

    ListDialog .list-item.selected {
        background: $primary;
        color: $text;
    }
    """

    selected_index: reactive[int] = reactive(0)

    def __init__(
        self,
        title: str,
        items: List[str],
        on_select: Optional[Callable[[int, str], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        name: Optional[str] = None,
    ) -> None:
        """Initialize list dialog.

        Args:
            title: Dialog title
            items: List of items to display
            on_select: Callback for selection
            on_cancel: Callback for cancellation
            name: Widget name
        """
        super().__init__(title, name=name)
        self.items = items
        self.on_select_callback = on_select
        self.on_cancel_callback = on_cancel

    def compose(self) -> ComposeResult:
        """Compose dialog widgets."""
        with Container():
            yield Static(self.dialog_title, classes="dialog-title")

            with Vertical(classes="list-container"):
                for idx, item in enumerate(self.items):
                    classes = "list-item selected" if idx == 0 else "list-item"
                    yield Static(item, id=f"item_{idx}", classes=classes)

            with Horizontal(classes="dialog-buttons"):
                yield Button("Select", variant="primary", id="select", classes="primary-button")
                yield Button("Cancel", variant="default", id="cancel")

    def watch_selected_index(self, index: int) -> None:
        """React to selection changes.

        Args:
            index: New selected index
        """
        for idx in range(len(self.items)):
            item = self.query_one(f"#item_{idx}", Static)
            if idx == index:
                item.add_class("selected")
            else:
                item.remove_class("selected")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press.

        Args:
            event: Button pressed event
        """
        if event.button.id == "select":
            selected_item = self.items[self.selected_index]
            if self.on_select_callback:
                self.on_select_callback(self.selected_index, selected_item)
            self.dismiss((self.selected_index, selected_item))
        else:
            if self.on_cancel_callback:
                self.on_cancel_callback()
            self.dismiss(None)

    def on_key(self, event) -> None:
        """Handle keyboard input.

        Args:
            event: Key event
        """
        if event.key == "up":
            self.selected_index = max(0, self.selected_index - 1)
        elif event.key == "down":
            self.selected_index = min(len(self.items) - 1, self.selected_index + 1)
        elif event.key == "enter":
            self.query_one("#select", Button).press()
        elif event.key == "escape":
            self.query_one("#cancel", Button).press()
