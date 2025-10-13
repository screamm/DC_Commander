"""Configuration Screen for Modern Commander.

Interactive configuration editor allowing users to modify all settings.
Provides theme selection, cache configuration, sort preferences, and view modes.
"""

from typing import Optional, Callable
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Input, Select, Switch, Label
from textual.screen import ModalScreen
from textual.reactive import reactive

from features.config_manager import ConfigManager, Config
from features.theme_manager import ThemeManager


class ConfigScreen(ModalScreen):
    """Interactive configuration screen with all settings."""

    DEFAULT_CSS = """
    ConfigScreen {
        align: center middle;
    }

    ConfigScreen > Container {
        width: 80;
        height: auto;
        max-height: 90%;
        border: heavy $primary;
        background: $surface;
        padding: 1 2;
    }

    ConfigScreen .config-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        background: $surface-darken-1;
        padding: 0 1;
        margin-bottom: 1;
    }

    ConfigScreen .config-section {
        margin-bottom: 1;
        padding: 1;
        border: solid $accent;
        background: $panel;
    }

    ConfigScreen .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    ConfigScreen .config-row {
        height: auto;
        margin-bottom: 1;
    }

    ConfigScreen .config-label {
        width: 30;
        content-align: left middle;
        color: $text;
    }

    ConfigScreen .config-input {
        width: 1fr;
    }

    ConfigScreen Input {
        width: 100%;
    }

    ConfigScreen Select {
        width: 100%;
    }

    ConfigScreen Switch {
        width: auto;
    }

    ConfigScreen .config-buttons {
        align: center middle;
        height: auto;
        margin-top: 1;
    }

    ConfigScreen Button {
        margin: 0 1;
        min-width: 12;
    }

    ConfigScreen .primary-button {
        background: $primary;
        color: $text;
    }

    ConfigScreen .danger-button {
        background: $error;
        color: $text;
    }
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        theme_manager: ThemeManager,
        on_save: Optional[Callable[[Config], None]] = None,
        name: Optional[str] = None,
    ) -> None:
        """Initialize configuration screen.

        Args:
            config_manager: Configuration manager instance
            theme_manager: Theme manager instance
            on_save: Callback for save action
            name: Widget name
        """
        super().__init__(name=name)
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        self.on_save_callback = on_save

        # Load current config
        self.config = config_manager.get_config()

        # Track modified state
        self.modified = False

    def compose(self) -> ComposeResult:
        """Compose configuration screen widgets."""
        with Container():
            yield Static("Configuration", classes="config-title")

            # Theme Section
            with Vertical(classes="config-section"):
                yield Static("Theme Settings", classes="section-title")

                with Horizontal(classes="config-row"):
                    yield Label("Theme:", classes="config-label")
                    themes = self.theme_manager.get_available_themes()
                    theme_options = [(theme, theme) for theme in themes]
                    yield Select(
                        theme_options,
                        value=self.config.theme,
                        id="theme_select",
                        classes="config-input",
                        allow_blank=False
                    )

            # Cache Section
            with Vertical(classes="config-section"):
                yield Static("Cache Settings", classes="section-title")

                with Horizontal(classes="config-row"):
                    yield Label("Enable Cache:", classes="config-label")
                    yield Switch(
                        value=self.config.cache.enabled,
                        id="cache_enabled",
                        classes="config-input"
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Max Cache Size:", classes="config-label")
                    yield Input(
                        value=str(self.config.cache.maxsize),
                        placeholder="100",
                        id="cache_maxsize",
                        classes="config-input",
                        type="integer"
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Cache TTL (seconds):", classes="config-label")
                    yield Input(
                        value=str(self.config.cache.ttl_seconds),
                        placeholder="60",
                        id="cache_ttl",
                        classes="config-input",
                        type="integer"
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Show Cache Stats:", classes="config-label")
                    yield Switch(
                        value=self.config.cache.show_stats,
                        id="cache_stats",
                        classes="config-input"
                    )

            # Left Panel Section
            with Vertical(classes="config-section"):
                yield Static("Left Panel Settings", classes="section-title")

                with Horizontal(classes="config-row"):
                    yield Label("Sort By:", classes="config-label")
                    sort_options = [
                        ("name", "Name"),
                        ("size", "Size"),
                        ("date", "Date"),
                        ("extension", "Extension")
                    ]
                    yield Select(
                        sort_options,
                        value=self.config.left_panel.sort_by,
                        id="left_sort_by",
                        classes="config-input",
                        allow_blank=False
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Sort Ascending:", classes="config-label")
                    yield Switch(
                        value=self.config.left_panel.sort_ascending,
                        id="left_sort_asc",
                        classes="config-input"
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Show Hidden Files:", classes="config-label")
                    yield Switch(
                        value=self.config.left_panel.show_hidden_files,
                        id="left_hidden",
                        classes="config-input"
                    )

            # Right Panel Section
            with Vertical(classes="config-section"):
                yield Static("Right Panel Settings", classes="section-title")

                with Horizontal(classes="config-row"):
                    yield Label("Sort By:", classes="config-label")
                    sort_options = [
                        ("name", "Name"),
                        ("size", "Size"),
                        ("date", "Date"),
                        ("extension", "Extension")
                    ]
                    yield Select(
                        sort_options,
                        value=self.config.right_panel.sort_by,
                        id="right_sort_by",
                        classes="config-input",
                        allow_blank=False
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Sort Ascending:", classes="config-label")
                    yield Switch(
                        value=self.config.right_panel.sort_ascending,
                        id="right_sort_asc",
                        classes="config-input"
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Show Hidden Files:", classes="config-label")
                    yield Switch(
                        value=self.config.right_panel.show_hidden_files,
                        id="right_hidden",
                        classes="config-input"
                    )

            # View Settings Section
            with Vertical(classes="config-section"):
                yield Static("View Settings", classes="section-title")

                with Horizontal(classes="config-row"):
                    yield Label("File Size Format:", classes="config-label")
                    size_options = [
                        ("auto", "Auto"),
                        ("bytes", "Bytes"),
                        ("kb", "KB"),
                        ("mb", "MB"),
                        ("gb", "GB")
                    ]
                    yield Select(
                        size_options,
                        value=self.config.view.file_size_format,
                        id="size_format",
                        classes="config-input",
                        allow_blank=False
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Show File Size:", classes="config-label")
                    yield Switch(
                        value=self.config.view.show_file_size,
                        id="show_size",
                        classes="config-input"
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Show File Date:", classes="config-label")
                    yield Switch(
                        value=self.config.view.show_file_date,
                        id="show_date",
                        classes="config-input"
                    )

            # Editor Settings Section
            with Vertical(classes="config-section"):
                yield Static("Editor Settings", classes="section-title")

                with Horizontal(classes="config-row"):
                    yield Label("Tab Size:", classes="config-label")
                    yield Input(
                        value=str(self.config.editor.tab_size),
                        placeholder="4",
                        id="tab_size",
                        classes="config-input",
                        type="integer"
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Use Spaces:", classes="config-label")
                    yield Switch(
                        value=self.config.editor.use_spaces,
                        id="use_spaces",
                        classes="config-input"
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Word Wrap:", classes="config-label")
                    yield Switch(
                        value=self.config.editor.word_wrap,
                        id="word_wrap",
                        classes="config-input"
                    )

                with Horizontal(classes="config-row"):
                    yield Label("Show Line Numbers:", classes="config-label")
                    yield Switch(
                        value=self.config.editor.show_line_numbers,
                        id="line_numbers",
                        classes="config-input"
                    )

            # Buttons
            with Horizontal(classes="config-buttons"):
                yield Button("Save", variant="primary", id="save", classes="primary-button")
                yield Button("Reset to Defaults", variant="default", id="reset", classes="danger-button")
                yield Button("Cancel", variant="default", id="cancel")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget changes.

        Args:
            event: Select changed event
        """
        self.modified = True

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch widget changes.

        Args:
            event: Switch changed event
        """
        self.modified = True

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input widget changes.

        Args:
            event: Input changed event
        """
        self.modified = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button pressed event
        """
        if event.button.id == "save":
            self._save_config()
        elif event.button.id == "reset":
            self._reset_config()
        elif event.button.id == "cancel":
            self.dismiss(False)

    def on_key(self, event) -> None:
        """Handle keyboard input.

        Args:
            event: Key event
        """
        if event.key == "escape":
            self.dismiss(False)

    def _save_config(self) -> None:
        """Save configuration changes."""
        try:
            # Update theme
            theme_select = self.query_one("#theme_select", Select)
            self.config.theme = str(theme_select.value)

            # Update cache settings
            cache_enabled = self.query_one("#cache_enabled", Switch)
            self.config.cache.enabled = cache_enabled.value

            cache_maxsize = self.query_one("#cache_maxsize", Input)
            try:
                self.config.cache.maxsize = int(cache_maxsize.value)
            except ValueError:
                self.config.cache.maxsize = 100

            cache_ttl = self.query_one("#cache_ttl", Input)
            try:
                self.config.cache.ttl_seconds = int(cache_ttl.value)
            except ValueError:
                self.config.cache.ttl_seconds = 60

            cache_stats = self.query_one("#cache_stats", Switch)
            self.config.cache.show_stats = cache_stats.value

            # Update left panel settings
            left_sort_by = self.query_one("#left_sort_by", Select)
            self.config.left_panel.sort_by = str(left_sort_by.value)

            left_sort_asc = self.query_one("#left_sort_asc", Switch)
            self.config.left_panel.sort_ascending = left_sort_asc.value

            left_hidden = self.query_one("#left_hidden", Switch)
            self.config.left_panel.show_hidden_files = left_hidden.value

            # Update right panel settings
            right_sort_by = self.query_one("#right_sort_by", Select)
            self.config.right_panel.sort_by = str(right_sort_by.value)

            right_sort_asc = self.query_one("#right_sort_asc", Switch)
            self.config.right_panel.sort_ascending = right_sort_asc.value

            right_hidden = self.query_one("#right_hidden", Switch)
            self.config.right_panel.show_hidden_files = right_hidden.value

            # Update view settings
            size_format = self.query_one("#size_format", Select)
            self.config.view.file_size_format = str(size_format.value)

            show_size = self.query_one("#show_size", Switch)
            self.config.view.show_file_size = show_size.value

            show_date = self.query_one("#show_date", Switch)
            self.config.view.show_file_date = show_date.value

            # Update editor settings
            tab_size = self.query_one("#tab_size", Input)
            try:
                self.config.editor.tab_size = int(tab_size.value)
            except ValueError:
                self.config.editor.tab_size = 4

            use_spaces = self.query_one("#use_spaces", Switch)
            self.config.editor.use_spaces = use_spaces.value

            word_wrap = self.query_one("#word_wrap", Switch)
            self.config.editor.word_wrap = word_wrap.value

            line_numbers = self.query_one("#line_numbers", Switch)
            self.config.editor.show_line_numbers = line_numbers.value

            # Validate configuration
            issues = self.config_manager.validate_config()
            if issues:
                error_msg = "Configuration validation failed:\n" + "\n".join(issues)
                self.app.notify(error_msg, severity="error", timeout=5)
                return

            # Save to file
            if self.config_manager.save_config():
                if self.on_save_callback:
                    self.on_save_callback(self.config)
                self.dismiss(True)
            else:
                self.app.notify("Failed to save configuration", severity="error")

        except Exception as e:
            self.app.notify(f"Error saving configuration: {e}", severity="error")

    def _reset_config(self) -> None:
        """Reset configuration to defaults."""
        # Reset config manager
        self.config_manager.reset_to_defaults()
        self.config = self.config_manager.get_config()

        # Update all widgets with default values
        try:
            # Theme
            theme_select = self.query_one("#theme_select", Select)
            theme_select.value = self.config.theme

            # Cache
            cache_enabled = self.query_one("#cache_enabled", Switch)
            cache_enabled.value = self.config.cache.enabled

            cache_maxsize = self.query_one("#cache_maxsize", Input)
            cache_maxsize.value = str(self.config.cache.maxsize)

            cache_ttl = self.query_one("#cache_ttl", Input)
            cache_ttl.value = str(self.config.cache.ttl_seconds)

            cache_stats = self.query_one("#cache_stats", Switch)
            cache_stats.value = self.config.cache.show_stats

            # Left panel
            left_sort_by = self.query_one("#left_sort_by", Select)
            left_sort_by.value = self.config.left_panel.sort_by

            left_sort_asc = self.query_one("#left_sort_asc", Switch)
            left_sort_asc.value = self.config.left_panel.sort_ascending

            left_hidden = self.query_one("#left_hidden", Switch)
            left_hidden.value = self.config.left_panel.show_hidden_files

            # Right panel
            right_sort_by = self.query_one("#right_sort_by", Select)
            right_sort_by.value = self.config.right_panel.sort_by

            right_sort_asc = self.query_one("#right_sort_asc", Switch)
            right_sort_asc.value = self.config.right_panel.sort_ascending

            right_hidden = self.query_one("#right_hidden", Switch)
            right_hidden.value = self.config.right_panel.show_hidden_files

            # View settings
            size_format = self.query_one("#size_format", Select)
            size_format.value = self.config.view.file_size_format

            show_size = self.query_one("#show_size", Switch)
            show_size.value = self.config.view.show_file_size

            show_date = self.query_one("#show_date", Switch)
            show_date.value = self.config.view.show_file_date

            # Editor settings
            tab_size = self.query_one("#tab_size", Input)
            tab_size.value = str(self.config.editor.tab_size)

            use_spaces = self.query_one("#use_spaces", Switch)
            use_spaces.value = self.config.editor.use_spaces

            word_wrap = self.query_one("#word_wrap", Switch)
            word_wrap.value = self.config.editor.word_wrap

            line_numbers = self.query_one("#line_numbers", Switch)
            line_numbers.value = self.config.editor.show_line_numbers

            self.modified = False
            self.app.notify("Configuration reset to defaults", severity="information")

        except Exception as e:
            self.app.notify(f"Error resetting configuration: {e}", severity="error")
