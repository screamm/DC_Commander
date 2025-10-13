"""
Theme Configuration Dialog

Provides UI for creating and editing custom themes with:
- Color input fields with validation
- Live preview panel
- Save to Custom 1 or Custom 2 slots
- Support for both create and edit modes
"""

from typing import Optional, Callable
from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Input, Button, Static
from textual.validation import ValidationResult, Validator
from textual.message import Message

from features.theme_manager import Theme, ThemeMetadata, ThemeType


class ColorValidator(Validator):
    """
    Validator for hex color codes.

    Validates color strings in formats:
    - #RGB (3 hex digits)
    - #RRGGBB (6 hex digits)
    - #RRGGBBAA (8 hex digits with alpha)

    Requirements:
    - Must start with #
    - Only hex characters (0-9, A-F, case insensitive)
    - Valid length (3, 6, or 8 hex digits)
    """

    def validate(self, value: str) -> ValidationResult:
        """
        Validate color string format.

        Args:
            value: Color string to validate

        Returns:
            ValidationResult with success status and optional failure description
        """
        if not value:
            return self.failure("Color code cannot be empty")

        if not value.startswith('#'):
            return self.failure("Color must start with #")

        hex_part = value[1:]

        if len(hex_part) not in (3, 6, 8):
            return self.failure(f"Invalid length: expected #RGB, #RRGGBB, or #RRGGBBAA")

        try:
            int(hex_part, 16)
            return self.success()
        except ValueError:
            return self.failure("Invalid hex characters (use 0-9, A-F only)")


class ThemeConfigDialog(ModalScreen):
    """
    Modal dialog for creating and editing custom themes.

    Features:
    - 13 color input fields with validation
    - Live preview panel showing theme colors
    - Theme name input
    - Save to Custom 1 or Custom 2 buttons
    - Cancel button with Escape key binding
    - Support for both create (theme=None) and edit (theme=Theme) modes

    Messages:
        ThemeSaved: Emitted when theme is saved successfully
    """

    CSS = """
    ThemeConfigDialog {
        align: center middle;
    }

    #dialog-container {
        width: 90;
        height: auto;
        max-height: 95%;
        background: $panel;
        border: heavy $primary;
        padding: 1 2;
    }

    #dialog-title {
        text-align: center;
        text-style: bold;
        color: $text;
        background: $primary;
        width: 100%;
        height: 1;
        padding: 0 1;
        margin-bottom: 1;
    }

    #theme-name-container {
        height: auto;
        margin-bottom: 1;
    }

    #theme-name-label {
        width: 15;
        text-align: right;
        margin-right: 1;
    }

    #theme-name-input {
        width: 1fr;
    }

    #colors-grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-rows: auto;
        height: auto;
        margin-bottom: 1;
        padding: 1;
        border: solid $accent;
    }

    .color-field-container {
        height: 3;
        padding: 0 1;
    }

    .color-label {
        width: 100%;
        text-align: left;
        color: $text_muted;
        height: 1;
    }

    .color-input {
        width: 100%;
        height: 1;
    }

    #preview-container {
        height: 12;
        margin-bottom: 1;
        padding: 1;
        border: solid $accent;
    }

    #preview-title {
        text-align: center;
        text-style: bold;
        color: $text;
        height: 1;
        margin-bottom: 1;
    }

    #preview-content {
        height: 1fr;
        padding: 1;
    }

    #preview-primary {
        height: 1;
        width: 100%;
        margin-bottom: 1;
    }

    #preview-text {
        height: 1;
        width: 100%;
        margin-bottom: 1;
    }

    #preview-selection {
        height: 1;
        width: 100%;
        margin-bottom: 1;
    }

    #preview-panel {
        height: 3;
        width: 100%;
        padding: 1;
        margin-bottom: 1;
    }

    #preview-status {
        height: 1;
        width: 100%;
    }

    #buttons-container {
        height: 3;
        align: center middle;
    }

    .dialog-button {
        min-width: 15;
        margin: 0 1;
    }

    .error-text {
        color: $error;
        text-style: bold;
    }

    #validation-error {
        height: auto;
        color: $error;
        text-align: center;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    class ThemeSaved(Message):
        """Message emitted when theme is saved.

        Attributes:
            theme: Saved Theme object
            slot: Custom theme slot identifier (custom1 or custom2)
        """

        def __init__(self, theme: Theme, slot: str) -> None:
            self.theme = theme
            self.slot = slot
            super().__init__()

    def __init__(
        self,
        theme: Optional[Theme] = None,
        slot: Optional[str] = None,
        on_save: Optional[Callable[[Theme, str], None]] = None
    ):
        """
        Initialize theme configuration dialog.

        Args:
            theme: Optional Theme to edit (None for create mode)
            slot: Optional custom slot identifier (custom1 or custom2)
            on_save: Optional callback when theme is saved
        """
        super().__init__()

        self.edit_mode = theme is not None
        self.theme = theme
        self.slot = slot
        self.on_save = on_save

        # Initialize color values from theme or defaults
        if theme:
            self.color_values = {
                'primary': theme.primary,
                'accent': theme.accent,
                'surface': theme.surface,
                'panel': theme.panel,
                'text': theme.text,
                'text_muted': theme.text_muted,
                'warning': theme.warning,
                'error': theme.error,
                'success': theme.success,
                'selection': theme.selection,
                'selection_text': theme.selection_text,
            }
            self.theme_name = theme.display_name
        else:
            # Default color values for new themes
            self.color_values = {
                'primary': '#0000AA',
                'accent': '#00FFFF',
                'surface': '#000055',
                'panel': '#0000AA',
                'text': '#FFFF77',
                'text_muted': '#AAAAAA',
                'warning': '#FFFF00',
                'error': '#FF5555',
                'success': '#55FF55',
                'selection': '#FFFF00',
                'selection_text': '#000000',
            }
            self.theme_name = "New Custom Theme"

        # Color field definitions with display labels
        self.color_fields = [
            ('primary', 'Primary Color'),
            ('accent', 'Accent Color'),
            ('surface', 'Surface Background'),
            ('panel', 'Panel Background'),
            ('text', 'Primary Text'),
            ('text_muted', 'Muted Text'),
            ('warning', 'Warning Color'),
            ('error', 'Error Color'),
            ('success', 'Success Color'),
            ('selection', 'Selection Background'),
            ('selection_text', 'Selection Text'),
        ]

    def compose(self) -> ComposeResult:
        """Compose dialog layout with color inputs and preview."""
        with Container(id="dialog-container"):
            # Title
            title = "Edit Theme" if self.edit_mode else "Create Custom Theme"
            yield Label(title, id="dialog-title")

            # Theme name input
            with Horizontal(id="theme-name-container"):
                yield Label("Theme Name:", id="theme-name-label")
                yield Input(
                    value=self.theme_name,
                    placeholder="Enter theme name",
                    id="theme-name-input"
                )

            # Color input fields in grid
            with Grid(id="colors-grid"):
                for field_id, field_label in self.color_fields:
                    with Vertical(classes="color-field-container"):
                        yield Label(field_label, classes="color-label")
                        yield Input(
                            value=self.color_values[field_id],
                            placeholder="#RRGGBB",
                            validators=[ColorValidator()],
                            id=f"color-{field_id}",
                            classes="color-input"
                        )

            # Live preview panel
            with Container(id="preview-container"):
                yield Label("Theme Preview", id="preview-title")
                with Container(id="preview-content"):
                    yield Static("Primary Border", id="preview-primary")
                    yield Static("Normal Text", id="preview-text")
                    yield Static("Selected Item", id="preview-selection")
                    yield Static("Panel Content", id="preview-panel")
                    yield Static("Success | Warning | Error", id="preview-status")

            # Validation error display
            yield Label("", id="validation-error")

            # Action buttons
            with Horizontal(id="buttons-container"):
                yield Button("Save to Custom 1", variant="primary", id="btn-save-custom1", classes="dialog-button")
                yield Button("Save to Custom 2", variant="primary", id="btn-save-custom2", classes="dialog-button")
                yield Button("Cancel", variant="default", id="btn-cancel", classes="dialog-button")

    def on_mount(self) -> None:
        """Initialize dialog on mount."""
        # Update preview with initial colors
        self._update_preview()

        # Focus theme name input
        name_input = self.query_one("#theme-name-input", Input)
        name_input.focus()

    @on(Input.Changed, "#theme-name-input")
    def on_name_changed(self, event: Input.Changed) -> None:
        """Handle theme name input changes.

        Args:
            event: Input changed event
        """
        self.theme_name = event.value

    @on(Input.Changed, ".color-input")
    def on_color_changed(self, event: Input.Changed) -> None:
        """Handle color input changes and update preview.

        Args:
            event: Input changed event
        """
        # Extract field ID from input ID (format: "color-{field_id}")
        input_id = event.input.id
        if input_id and input_id.startswith("color-"):
            field_id = input_id[6:]  # Remove "color-" prefix

            # Update color value if valid
            if event.validation_result and event.validation_result.is_valid:
                self.color_values[field_id] = event.value
                self._update_preview()
                self._clear_validation_error()

    def _update_preview(self) -> None:
        """Update live preview panel with current color values."""
        try:
            # Get preview elements
            preview_primary = self.query_one("#preview-primary", Static)
            preview_text = self.query_one("#preview-text", Static)
            preview_selection = self.query_one("#preview-selection", Static)
            preview_panel = self.query_one("#preview-panel", Static)
            preview_status = self.query_one("#preview-status", Static)

            # Apply color styles to preview elements
            primary_color = self.color_values.get('primary', '#0000AA')
            text_color = self.color_values.get('text', '#FFFF77')
            surface_color = self.color_values.get('surface', '#000055')
            panel_color = self.color_values.get('panel', '#0000AA')
            selection_color = self.color_values.get('selection', '#FFFF00')
            selection_text_color = self.color_values.get('selection_text', '#000000')
            success_color = self.color_values.get('success', '#55FF55')
            warning_color = self.color_values.get('warning', '#FFFF00')
            error_color = self.color_values.get('error', '#FF5555')

            # Primary border preview
            preview_primary.styles.background = surface_color
            preview_primary.styles.color = text_color
            preview_primary.styles.border = ("heavy", primary_color)

            # Normal text preview
            preview_text.styles.background = surface_color
            preview_text.styles.color = text_color

            # Selection preview
            preview_selection.styles.background = selection_color
            preview_selection.styles.color = selection_text_color

            # Panel preview
            preview_panel.styles.background = panel_color
            preview_panel.styles.color = text_color

            # Status colors preview
            preview_status.styles.background = surface_color
            preview_status.update(f"[{success_color}]Success[/] | [{warning_color}]Warning[/] | [{error_color}]Error[/]")

        except Exception:
            # Preview update failed, continue silently
            pass

    def _validate_all_inputs(self) -> tuple[bool, str]:
        """
        Validate all color inputs before saving.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate theme name
        if not self.theme_name or not self.theme_name.strip():
            return False, "Theme name cannot be empty"

        # Validate all color fields
        validator = ColorValidator()

        for field_id, field_label in self.color_fields:
            color_value = self.color_values.get(field_id, '')
            result = validator.validate(color_value)

            if not result.is_valid:
                failures = result.failures
                error_msg = failures[0] if failures else "Invalid color format"
                return False, f"{field_label}: {error_msg}"

        return True, ""

    def _show_validation_error(self, error: str) -> None:
        """
        Display validation error message.

        Args:
            error: Error message to display
        """
        error_label = self.query_one("#validation-error", Label)
        error_label.update(f"Validation Error: {error}")
        error_label.add_class("error-text")

    def _clear_validation_error(self) -> None:
        """Clear validation error message."""
        error_label = self.query_one("#validation-error", Label)
        error_label.update("")
        error_label.remove_class("error-text")

    def _save_theme(self, target_slot: str) -> None:
        """
        Save theme to specified custom slot.

        Args:
            target_slot: Custom slot identifier (custom1 or custom2)
        """
        # Validate all inputs
        is_valid, error_msg = self._validate_all_inputs()

        if not is_valid:
            self._show_validation_error(error_msg)
            return

        # Create Theme object
        theme = Theme(
            name=target_slot,  # Theme name matches slot
            display_name=self.theme_name.strip(),
            primary=self.color_values['primary'],
            accent=self.color_values['accent'],
            surface=self.color_values['surface'],
            panel=self.color_values['panel'],
            text=self.color_values['text'],
            text_muted=self.color_values['text_muted'],
            warning=self.color_values['warning'],
            error=self.color_values['error'],
            success=self.color_values['success'],
            selection=self.color_values['selection'],
            selection_text=self.color_values['selection_text'],
            metadata=ThemeMetadata(
                theme_id=target_slot,
                display_name=self.theme_name.strip(),
                theme_type=ThemeType.CUSTOM,
                description=f"Custom theme: {self.theme_name.strip()}",
                author="User",
                is_editable=True
            )
        )

        # Call callback if provided
        if self.on_save:
            self.on_save(theme, target_slot)

        # Post message
        self.post_message(self.ThemeSaved(theme, target_slot))

        # Dismiss dialog
        self.dismiss(True)

    @on(Button.Pressed, "#btn-save-custom1")
    def on_save_custom1(self, event: Button.Pressed) -> None:
        """Handle Save to Custom 1 button press."""
        self._save_theme("custom1")

    @on(Button.Pressed, "#btn-save-custom2")
    def on_save_custom2(self, event: Button.Pressed) -> None:
        """Handle Save to Custom 2 button press."""
        self._save_theme("custom2")

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self, event: Button.Pressed) -> None:
        """Handle Cancel button press."""
        self.dismiss(False)

    def action_cancel(self) -> None:
        """Handle Escape key press."""
        self.dismiss(False)
