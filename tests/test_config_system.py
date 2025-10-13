"""
Configuration System Tests for DC Commander (F9 Config)

Comprehensive testing of configuration management including:
- Configuration loading and saving
- Default configuration generation
- Panel settings (left/right)
- Cache configuration
- Theme selection
- Editor settings
- View settings
- Validation and error handling
- Configuration screen UI
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from features.config_manager import (
    ConfigManager,
    Config,
    PanelConfig,
    CacheConfig,
    ColorScheme,
    EditorSettings,
    ViewSettings,
    KeyboardShortcuts
)
from features.theme_manager import ThemeManager, Theme
from components.config_screen import ConfigScreen


class TestPanelConfig:
    """Test PanelConfig dataclass."""

    def test_panel_config_defaults(self):
        """Test PanelConfig default values."""
        config = PanelConfig()

        assert config.start_path == ""
        assert not config.show_hidden_files
        assert config.sort_by == "name"
        assert config.sort_ascending

    def test_panel_config_custom_values(self):
        """Test PanelConfig with custom values."""
        config = PanelConfig(
            start_path="/home/user",
            show_hidden_files=True,
            sort_by="size",
            sort_ascending=False
        )

        assert config.start_path == "/home/user"
        assert config.show_hidden_files
        assert config.sort_by == "size"
        assert not config.sort_ascending

    def test_panel_config_sort_options(self):
        """Test valid sort options."""
        valid_sorts = ["name", "size", "date", "extension"]

        for sort_option in valid_sorts:
            config = PanelConfig(sort_by=sort_option)
            assert config.sort_by == sort_option


class TestCacheConfig:
    """Test CacheConfig dataclass."""

    def test_cache_config_defaults(self):
        """Test CacheConfig default values."""
        config = CacheConfig()

        assert config.enabled
        assert config.maxsize == 100
        assert config.ttl_seconds == 60
        assert not config.show_stats

    def test_cache_config_custom_values(self):
        """Test CacheConfig with custom values."""
        config = CacheConfig(
            enabled=False,
            maxsize=200,
            ttl_seconds=120,
            show_stats=True
        )

        assert not config.enabled
        assert config.maxsize == 200
        assert config.ttl_seconds == 120
        assert config.show_stats

    def test_cache_config_boundary_values(self):
        """Test CacheConfig with boundary values."""
        # Minimum values
        config_min = CacheConfig(maxsize=1, ttl_seconds=1)
        assert config_min.maxsize == 1
        assert config_min.ttl_seconds == 1

        # Maximum reasonable values
        config_max = CacheConfig(maxsize=1000, ttl_seconds=3600)
        assert config_max.maxsize == 1000
        assert config_max.ttl_seconds == 3600


class TestEditorSettings:
    """Test EditorSettings dataclass."""

    def test_editor_settings_defaults(self):
        """Test EditorSettings default values."""
        settings = EditorSettings()

        assert settings.default_editor == ""
        assert settings.tab_size == 4
        assert settings.use_spaces
        assert not settings.word_wrap
        assert settings.show_line_numbers
        assert settings.syntax_highlighting

    def test_editor_settings_custom(self):
        """Test EditorSettings with custom values."""
        settings = EditorSettings(
            default_editor="vim",
            tab_size=2,
            use_spaces=False,
            word_wrap=True,
            show_line_numbers=False
        )

        assert settings.default_editor == "vim"
        assert settings.tab_size == 2
        assert not settings.use_spaces
        assert settings.word_wrap
        assert not settings.show_line_numbers


class TestViewSettings:
    """Test ViewSettings dataclass."""

    def test_view_settings_defaults(self):
        """Test ViewSettings default values."""
        settings = ViewSettings()

        assert not settings.show_hidden_files
        assert settings.show_file_size
        assert settings.show_file_date
        assert not settings.show_file_permissions
        assert settings.file_size_format == "auto"
        assert settings.date_format == "%Y-%m-%d %H:%M"
        assert settings.use_24_hour_time

    def test_view_settings_custom(self):
        """Test ViewSettings with custom values."""
        settings = ViewSettings(
            show_hidden_files=True,
            show_file_size=False,
            file_size_format="mb",
            use_24_hour_time=False
        )

        assert settings.show_hidden_files
        assert not settings.show_file_size
        assert settings.file_size_format == "mb"
        assert not settings.use_24_hour_time

    def test_view_settings_size_formats(self):
        """Test valid size format options."""
        valid_formats = ["auto", "bytes", "kb", "mb", "gb"]

        for fmt in valid_formats:
            settings = ViewSettings(file_size_format=fmt)
            assert settings.file_size_format == fmt


class TestConfig:
    """Test main Config dataclass."""

    def test_config_defaults(self):
        """Test Config with default values."""
        config = Config()

        assert isinstance(config.left_panel, PanelConfig)
        assert isinstance(config.right_panel, PanelConfig)
        assert isinstance(config.cache, CacheConfig)
        assert isinstance(config.color_scheme, ColorScheme)
        assert isinstance(config.editor, EditorSettings)
        assert isinstance(config.view, ViewSettings)
        assert isinstance(config.shortcuts, KeyboardShortcuts)
        assert config.theme == "norton_commander"

    def test_config_custom_values(self):
        """Test Config with custom nested values."""
        config = Config()

        config.left_panel.start_path = "/custom/left"
        config.right_panel.start_path = "/custom/right"
        config.cache.enabled = False
        config.theme = "modern_dark"

        assert config.left_panel.start_path == "/custom/left"
        assert config.right_panel.start_path == "/custom/right"
        assert not config.cache.enabled
        assert config.theme == "modern_dark"


class TestConfigManager:
    """Test ConfigManager functionality."""

    def test_config_manager_initialization(self, tmp_path):
        """Test ConfigManager initialization."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))

        assert manager.config_path == config_file
        assert manager._config is None  # Not loaded yet

    def test_config_manager_default_path(self):
        """Test default configuration path generation."""
        default_path = ConfigManager._get_default_config_path()

        assert isinstance(default_path, str)
        assert "config.json" in default_path

    def test_config_manager_load_default(self, tmp_path):
        """Test loading default configuration when file doesn't exist."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))

        config = manager.load_config()

        assert isinstance(config, Config)
        assert config_file.exists()  # Should be created

    def test_config_manager_save_and_load(self, tmp_path):
        """Test saving and loading configuration."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))

        # Load and modify config
        config = manager.load_config()
        config.theme = "test_theme"
        config.cache.maxsize = 150

        # Save
        assert manager.save_config()

        # Load with new manager
        manager2 = ConfigManager(str(config_file))
        config2 = manager2.load_config()

        assert config2.theme == "test_theme"
        assert config2.cache.maxsize == 150

    def test_config_manager_json_format(self, tmp_path):
        """Test configuration is saved in valid JSON format."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))

        config = manager.load_config()
        manager.save_config()

        # Load raw JSON
        with open(config_file, 'r') as f:
            data = json.load(f)

        assert "left_panel" in data
        assert "right_panel" in data
        assert "cache" in data
        assert "theme" in data

    def test_config_manager_invalid_json(self, tmp_path):
        """Test handling of invalid JSON file."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json }")

        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        # Should return default config
        assert isinstance(config, Config)

    def test_config_manager_update_methods(self, tmp_path):
        """Test configuration update methods."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        # Update panel paths
        manager.update_left_panel_path("/new/left")
        manager.update_right_panel_path("/new/right")

        assert config.left_panel.start_path == "/new/left"
        assert config.right_panel.start_path == "/new/right"

        # Update theme
        manager.update_theme("custom_theme")
        assert config.theme == "custom_theme"

        # Update cache
        manager.update_cache_settings(
            enabled=False,
            maxsize=200,
            ttl_seconds=90
        )

        assert not config.cache.enabled
        assert config.cache.maxsize == 200
        assert config.cache.ttl_seconds == 90

    def test_config_manager_reset_defaults(self, tmp_path):
        """Test resetting configuration to defaults."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))

        config = manager.load_config()
        config.theme = "custom"
        config.cache.maxsize = 999

        # Reset
        manager.reset_to_defaults()
        config = manager.get_config()

        assert config.theme == "norton_commander"
        assert config.cache.maxsize == 100

    def test_config_manager_validation(self, tmp_path):
        """Test configuration validation."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        # Valid configuration
        issues = manager.validate_config()
        assert isinstance(issues, list)

        # Invalid cache maxsize
        config.cache.maxsize = 5000  # Too large
        issues = manager.validate_config()
        assert len(issues) > 0
        assert any("maxsize" in issue.lower() for issue in issues)

        # Invalid cache TTL
        config.cache.maxsize = 100  # Fix
        config.cache.ttl_seconds = 10000  # Too large
        issues = manager.validate_config()
        assert any("ttl" in issue.lower() for issue in issues)

        # Invalid tab size
        config.cache.ttl_seconds = 60  # Fix
        config.editor.tab_size = 100  # Too large
        issues = manager.validate_config()
        assert any("tab size" in issue.lower() for issue in issues)

    def test_config_manager_color_scheme_update(self, tmp_path):
        """Test updating color scheme."""
        config_file = tmp_path / "config.json"
        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        # Update to different schemes
        manager.update_color_scheme("dark")
        assert config.color_scheme.name == "dark"

        manager.update_color_scheme("light")
        assert config.color_scheme.name == "light"

        manager.update_color_scheme("classic")
        assert config.color_scheme.name == "classic"


class TestThemeManager:
    """Test ThemeManager functionality."""

    def test_theme_manager_initialization(self, tmp_path):
        """Test ThemeManager initialization."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)

        assert manager.themes_dir == themes_dir
        assert themes_dir.exists()

    def test_theme_manager_create_defaults(self, tmp_path):
        """Test creating default themes."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)

        manager.create_default_themes()

        # Check files exist
        assert (themes_dir / "norton_commander.json").exists()
        assert (themes_dir / "modern_dark.json").exists()
        assert (themes_dir / "solarized.json").exists()

    def test_theme_manager_load_theme(self, tmp_path):
        """Test loading a theme."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        theme = manager.load_theme("norton_commander")

        assert theme is not None
        assert theme.name == "norton_commander"
        assert isinstance(theme, Theme)

    def test_theme_manager_load_nonexistent(self, tmp_path):
        """Test loading nonexistent theme."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)

        theme = manager.load_theme("nonexistent")

        assert theme is None

    def test_theme_manager_get_available(self, tmp_path):
        """Test getting available themes."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        themes = manager.get_available_themes()

        assert len(themes) >= 3
        assert "norton_commander" in themes
        assert "modern_dark" in themes
        assert "solarized" in themes

    def test_theme_manager_save_theme(self, tmp_path):
        """Test saving a custom theme."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)

        custom_theme = Theme(
            name="custom",
            display_name="Custom Theme",
            primary="#FF0000",
            accent="#00FF00",
            surface="#0000FF",
            panel="#FFFF00",
            text="#FFFFFF",
            text_muted="#CCCCCC",
            warning="#FFA500",
            error="#FF0000",
            success="#00FF00",
            selection="#FFFF00",
            selection_text="#000000"
        )

        result = manager.save_theme(custom_theme)

        assert result
        assert (themes_dir / "custom.json").exists()

    def test_theme_manager_current_theme(self, tmp_path):
        """Test setting and getting current theme."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        result = manager.set_current_theme("norton_commander")
        assert result

        current = manager.get_current_theme()
        assert current is not None
        assert current.name == "norton_commander"

    def test_theme_manager_cycle_themes(self, tmp_path):
        """Test cycling through themes."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        themes = manager.get_available_themes()

        # Get next theme for each
        for i, theme in enumerate(themes):
            next_theme = manager.get_next_theme_name(theme)
            expected_next = themes[(i + 1) % len(themes)]

            assert next_theme == expected_next

    def test_theme_manager_generate_css(self, tmp_path):
        """Test CSS generation from theme."""
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        manager.set_current_theme("norton_commander")
        css = manager.generate_css()

        assert css
        assert "$primary" in css
        assert "$accent" in css
        assert "$surface" in css


class TestTheme:
    """Test Theme dataclass."""

    def test_theme_creation(self):
        """Test Theme object creation."""
        theme = Theme(
            name="test",
            display_name="Test Theme",
            primary="#FF0000",
            accent="#00FF00",
            surface="#0000FF",
            panel="#FFFF00",
            text="#FFFFFF",
            text_muted="#CCCCCC",
            warning="#FFA500",
            error="#FF0000",
            success="#00FF00",
            selection="#FFFF00",
            selection_text="#000000"
        )

        assert theme.name == "test"
        assert theme.display_name == "Test Theme"

    def test_theme_validation_valid(self):
        """Test theme validation with valid colors."""
        theme = Theme(
            name="valid",
            display_name="Valid",
            primary="#FF0000",
            accent="#00FF00",
            surface="#0000FF",
            panel="#FFFF00",
            text="#FFFFFF",
            text_muted="#CCCCCC",
            warning="#FFA500",
            error="#FF0000",
            success="#00FF00",
            selection="#FFFF00",
            selection_text="#000000"
        )

        issues = theme.validate()
        assert len(issues) == 0

    def test_theme_validation_invalid(self):
        """Test theme validation with invalid colors."""
        theme = Theme(
            name="invalid",
            display_name="Invalid",
            primary="not_a_color",
            accent="#00FF00",
            surface="#0000FF",
            panel="#FFFF00",
            text="#FFFFFF",
            text_muted="#CCCCCC",
            warning="#FFA500",
            error="#FF0000",
            success="#00FF00",
            selection="#FFFF00",
            selection_text="#000000"
        )

        issues = theme.validate()
        assert len(issues) > 0

    def test_theme_css_generation(self):
        """Test generating CSS from theme."""
        theme = Theme(
            name="test",
            display_name="Test",
            primary="#FF0000",
            accent="#00FF00",
            surface="#0000FF",
            panel="#FFFF00",
            text="#FFFFFF",
            text_muted="#CCCCCC",
            warning="#FFA500",
            error="#FF0000",
            success="#00FF00",
            selection="#FFFF00",
            selection_text="#000000"
        )

        css = theme.to_css_variables()

        assert "$primary: #FF0000" in css
        assert "$accent: #00FF00" in css
        assert "$surface: #0000FF" in css


class TestConfigScreen:
    """Test ConfigScreen UI component."""

    def test_config_screen_initialization(self, tmp_path):
        """Test ConfigScreen initialization."""
        config_file = tmp_path / "config.json"
        config_manager = ConfigManager(str(config_file))

        themes_dir = tmp_path / "themes"
        theme_manager = ThemeManager(themes_dir)

        screen = ConfigScreen(
            config_manager=config_manager,
            theme_manager=theme_manager
        )

        assert screen.config_manager == config_manager
        assert screen.theme_manager == theme_manager
        assert not screen.modified

    def test_config_screen_with_callback(self, tmp_path):
        """Test ConfigScreen with save callback."""
        config_file = tmp_path / "config.json"
        config_manager = ConfigManager(str(config_file))
        theme_manager = ThemeManager()

        callback_called = False
        saved_config = None

        def on_save(config):
            nonlocal callback_called, saved_config
            callback_called = True
            saved_config = config

        screen = ConfigScreen(
            config_manager=config_manager,
            theme_manager=theme_manager,
            on_save=on_save
        )

        assert screen.on_save_callback == on_save


class TestConfigPersistence:
    """Test configuration persistence across sessions."""

    def test_config_persists_between_sessions(self, tmp_path):
        """Test configuration persists across manager instances."""
        config_file = tmp_path / "config.json"

        # Session 1
        manager1 = ConfigManager(str(config_file))
        config1 = manager1.load_config()
        config1.theme = "custom_theme"
        config1.cache.maxsize = 175
        manager1.save_config()

        # Session 2
        manager2 = ConfigManager(str(config_file))
        config2 = manager2.load_config()

        assert config2.theme == "custom_theme"
        assert config2.cache.maxsize == 175

    def test_config_handles_partial_updates(self, tmp_path):
        """Test updating only part of configuration."""
        config_file = tmp_path / "config.json"

        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        # Update only theme
        original_cache = config.cache.maxsize
        manager.update_theme("new_theme")
        manager.save_config()

        # Reload
        manager2 = ConfigManager(str(config_file))
        config2 = manager2.load_config()

        assert config2.theme == "new_theme"
        assert config2.cache.maxsize == original_cache  # Unchanged


class TestConfigEdgeCases:
    """Test configuration edge cases."""

    def test_config_with_missing_fields(self, tmp_path):
        """Test handling config with missing fields."""
        config_file = tmp_path / "config.json"

        # Write minimal config
        minimal_config = {
            "theme": "test"
        }

        with open(config_file, 'w') as f:
            json.dump(minimal_config, f)

        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        # Should fill in defaults for missing fields
        assert isinstance(config.left_panel, PanelConfig)
        assert isinstance(config.cache, CacheConfig)

    def test_config_with_extra_fields(self, tmp_path):
        """Test handling config with extra unknown fields."""
        config_file = tmp_path / "config.json"

        # Write config with extra fields
        config_data = {
            "theme": "test",
            "unknown_field": "value",
            "cache": {
                "enabled": True,
                "maxsize": 100,
                "ttl_seconds": 60,
                "show_stats": False,
                "extra_field": "ignored"
            }
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        manager = ConfigManager(str(config_file))
        config = manager.load_config()

        # Should load successfully, ignoring extra fields
        assert config.theme == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
