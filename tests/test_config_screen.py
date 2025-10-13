"""Test script for configuration screen.

Quick test to verify the configuration screen works correctly.
"""

from textual.app import App, ComposeResult
from textual.widgets import Static

from features.config_manager import ConfigManager
from features.theme_manager import ThemeManager
from components.config_screen import ConfigScreen


class TestConfigApp(App):
    """Test application for configuration screen."""

    def __init__(self) -> None:
        """Initialize test application."""
        super().__init__()
        self.config_manager = ConfigManager()
        self.theme_manager = ThemeManager()

    def compose(self) -> ComposeResult:
        """Compose test layout."""
        yield Static("Press F9 to open configuration screen", id="info")

    def on_mount(self) -> None:
        """Mount handler."""
        # Ensure default themes exist
        self.theme_manager.create_default_themes()

        # Show config screen immediately
        self.show_config()

    def show_config(self) -> None:
        """Show configuration screen."""
        from features.config_manager import Config

        def handle_config_saved(config: Config) -> None:
            """Handle configuration save."""
            self.notify("Configuration saved successfully!", severity="information")

        config_screen = ConfigScreen(
            config_manager=self.config_manager,
            theme_manager=self.theme_manager,
            on_save=handle_config_saved
        )

        self.push_screen(config_screen)


def main() -> None:
    """Run test application."""
    app = TestConfigApp()
    app.run()


if __name__ == "__main__":
    main()
