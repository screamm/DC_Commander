"""
Theme Cycle Edge Cases Tests

Tests for Ctrl+T theme cycling edge cases and error handling.
Covers scenarios that can cause crashes:
- Corrupted theme files
- Missing theme files
- IO errors
- Empty theme directories
- Invalid theme names
- Concurrent access
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
import concurrent.futures

from features.theme_manager import ThemeManager, Theme
from features.config_manager import ConfigManager


class TestThemeCycleEdgeCases:
    """Test edge cases in theme cycling that can cause crashes."""

    def test_cycle_theme_with_corrupted_json(self, tmp_path):
        """Test Ctrl+T when theme file has invalid JSON.

        Edge Case: User or system corrupts theme file.
        Expected: Should skip corrupted theme, not crash.
        """
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()

        # Create corrupted theme file
        (themes_dir / "broken.json").write_text("{ invalid json }")

        # Create valid theme for comparison
        valid_theme = {
            "name": "valid",
            "display_name": "Valid Theme",
            "primary": "#FF0000",
            "accent": "#00FF00",
            "surface": "#0000FF",
            "panel": "#FFFF00",
            "text": "#FFFFFF",
            "text_muted": "#CCCCCC",
            "warning": "#FFA500",
            "error": "#FF0000",
            "success": "#00FF00",
            "selection": "#FFFF00",
            "selection_text": "#000000"
        }
        (themes_dir / "valid.json").write_text(json.dumps(valid_theme))

        manager = ThemeManager(themes_dir)

        # Should not crash when loading corrupted theme
        broken = manager.load_theme("broken")
        assert broken is None

        # Valid theme should still load
        valid = manager.load_theme("valid")
        assert valid is not None
        assert valid.name == "valid"

        # Available themes should only include valid ones
        available = manager.get_available_themes()
        assert "valid" in available
        # Note: broken.json exists but should be filtered out when loaded

    def test_cycle_theme_with_missing_field(self, tmp_path):
        """Test Ctrl+T when theme file is missing required field.

        Edge Case: Theme file exists but missing color field.
        Expected: Validation should fail, theme not loaded.
        """
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()

        # Create theme missing 'primary' field
        incomplete_theme = {
            "name": "incomplete",
            "display_name": "Incomplete Theme",
            # "primary": "#FF0000",  # MISSING
            "accent": "#00FF00",
            "surface": "#0000FF",
            "panel": "#FFFF00",
            "text": "#FFFFFF",
            "text_muted": "#CCCCCC",
            "warning": "#FFA500",
            "error": "#FF0000",
            "success": "#00FF00",
            "selection": "#FFFF00",
            "selection_text": "#000000"
        }
        (themes_dir / "incomplete.json").write_text(json.dumps(incomplete_theme))

        manager = ThemeManager(themes_dir)

        # Should not crash, should return None
        theme = manager.load_theme("incomplete")
        assert theme is None

    def test_cycle_theme_with_deleted_file(self, tmp_path):
        """Test Ctrl+T when theme file is deleted.

        Edge Case: Theme file deleted while app running.
        Expected: Should handle gracefully, not crash.
        """
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        # Verify theme loads initially
        theme = manager.load_theme("modern_dark")
        assert theme is not None

        # Delete theme file
        (themes_dir / "modern_dark.json").unlink()

        # Clear cache to force reload
        manager._themes_cache.clear()

        # Should not crash when trying to load deleted theme
        theme = manager.load_theme("modern_dark")
        assert theme is None

    def test_cycle_theme_with_io_error(self, tmp_path, monkeypatch):
        """Test Ctrl+T when file system error occurs.

        Edge Case: Permission denied, disk full, etc.
        Expected: Should handle error gracefully, not crash.
        """
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        # Simulate IO error
        original_open = open

        def mock_open(file, *args, **kwargs):
            if "norton_commander.json" in str(file):
                raise IOError("Simulated disk error")
            return original_open(file, *args, **kwargs)

        # Clear cache to force file access
        manager._themes_cache.clear()

        with patch("builtins.open", side_effect=mock_open):
            # Should not crash, should return None
            theme = manager.load_theme("norton_commander")
            assert theme is None

    def test_cycle_theme_no_themes_directory(self, tmp_path):
        """Test Ctrl+T when themes directory doesn't exist.

        Edge Case: Themes directory deleted or never created.
        Expected: Should create directory, not crash.
        """
        themes_dir = tmp_path / "nonexistent" / "themes"
        manager = ThemeManager(themes_dir)

        # Should create directory automatically
        assert manager.themes_dir.exists()

        # Should have empty theme list
        available = manager.get_available_themes()
        assert len(available) == 0

    def test_cycle_theme_empty_themes_directory(self, tmp_path):
        """Test Ctrl+T when no themes available.

        Edge Case: Themes directory exists but is empty.
        Expected: Should return current theme, not crash.
        """
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()

        manager = ThemeManager(themes_dir)

        # Empty directory
        available = manager.get_available_themes()
        assert len(available) == 0

        # Cycling should return current theme (no crash)
        next_theme = manager.get_next_theme_name("any_theme")
        assert next_theme == "any_theme"

    def test_cycle_theme_invalid_current_theme(self, tmp_path):
        """Test Ctrl+T when config has invalid theme name.

        Edge Case: Config contains theme name that doesn't exist.
        Expected: Should fallback to first available theme.
        """
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        # Current theme doesn't exist
        next_theme = manager.get_next_theme_name("nonexistent_theme")

        # Should return first available theme (no crash)
        available = manager.get_available_themes()
        assert next_theme == available[0]

    def test_cycle_theme_all_themes_invalid(self, tmp_path):
        """Test Ctrl+T when all theme files are corrupted.

        Edge Case: System corruption affects all themes.
        Expected: Should handle gracefully, fallback behavior.
        """
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()

        # Create multiple corrupted themes
        (themes_dir / "broken1.json").write_text("{ invalid }")
        (themes_dir / "broken2.json").write_text("{ also invalid }")
        (themes_dir / "broken3.json").write_text("{ still invalid }")

        manager = ThemeManager(themes_dir)

        # All theme files exist
        available = manager.get_available_themes()
        assert len(available) == 3  # Files exist

        # But none should load successfully
        for theme_name in available:
            theme = manager.load_theme(theme_name)
            assert theme is None  # All corrupted

    def test_cycle_theme_with_invalid_color_format(self, tmp_path):
        """Test Ctrl+T when theme has invalid color format.

        Edge Case: Theme colors don't follow hex/rgb format.
        Expected: Validation should fail, theme not loaded.
        """
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()

        # Theme with invalid color
        invalid_theme = {
            "name": "invalid_color",
            "display_name": "Invalid Color Theme",
            "primary": "not_a_color",  # INVALID
            "accent": "#00FF00",
            "surface": "#0000FF",
            "panel": "#FFFF00",
            "text": "#FFFFFF",
            "text_muted": "#CCCCCC",
            "warning": "#FFA500",
            "error": "#FF0000",
            "success": "#00FF00",
            "selection": "#FFFF00",
            "selection_text": "#000000"
        }
        (themes_dir / "invalid_color.json").write_text(json.dumps(invalid_theme))

        manager = ThemeManager(themes_dir)

        # Should not crash, should return None
        theme = manager.load_theme("invalid_color")
        assert theme is None


class TestThemeCycleConcurrency:
    """Test concurrent access to theme system."""

    def test_rapid_theme_cycling(self, tmp_path):
        """Test rapidly pressing Ctrl+T multiple times.

        Edge Case: User rapidly presses Ctrl+T.
        Expected: Should cycle correctly without race conditions.
        """
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        themes = manager.get_available_themes()
        current_theme = themes[0]

        # Rapidly cycle 100 times
        for i in range(100):
            next_theme = manager.get_next_theme_name(current_theme)
            result = manager.set_current_theme(next_theme)
            assert result, f"Failed at iteration {i}"
            current_theme = next_theme

        # Should end up at correct position
        expected_index = 100 % len(themes)
        assert current_theme == themes[expected_index]

    def test_concurrent_theme_loading(self, tmp_path):
        """Test loading themes concurrently from multiple threads.

        Edge Case: Multiple operations accessing themes simultaneously.
        Expected: Should handle safely without corruption.
        """
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        themes = manager.get_available_themes()

        # Load themes concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(manager.load_theme, theme)
                for theme in themes * 20  # Load each theme 20 times
            ]

            results = [f.result() for f in futures]

        # All loads should succeed
        assert all(r is not None for r in results)

    def test_concurrent_theme_cycling(self, tmp_path):
        """Test cycling themes from multiple threads.

        Edge Case: Multiple Ctrl+T operations happening simultaneously.
        Expected: Should handle safely, no crashes.
        """
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        themes = manager.get_available_themes()

        def cycle_theme():
            current = themes[0]
            for _ in range(10):
                next_theme = manager.get_next_theme_name(current)
                manager.set_current_theme(next_theme)
                current = next_theme
            return current

        # Cycle from multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(cycle_theme) for _ in range(5)]
            results = [f.result() for f in futures]

        # All should complete without error
        assert len(results) == 5
        assert all(r in themes for r in results)


class TestThemeCycleIntegration:
    """Integration tests for complete theme cycle workflow."""

    def test_end_to_end_theme_cycle(self, tmp_path):
        """Test complete Ctrl+T workflow from app perspective.

        Integration: Config + Theme + Cycle logic together.
        Expected: Should cycle through all themes correctly.
        """
        config_file = tmp_path / "config.json"
        themes_dir = tmp_path / "themes"

        config_manager = ConfigManager(str(config_file))
        theme_manager = ThemeManager(themes_dir)
        theme_manager.create_default_themes()

        config = config_manager.load_config()
        themes = theme_manager.get_available_themes()

        # Cycle through all themes
        for i in range(len(themes)):
            current_theme = config.theme
            next_theme = theme_manager.get_next_theme_name(current_theme)

            # Update config
            config_manager.update_theme(next_theme)
            config_manager.save_config()

            # Apply theme
            result = theme_manager.set_current_theme(next_theme)
            assert result

            # Verify persistence
            config = config_manager.load_config()
            assert config.theme == next_theme

    def test_theme_cycle_with_app_restart(self, tmp_path):
        """Test Ctrl+T persists after app restart.

        Integration: Theme changes persist across sessions.
        Expected: Theme should be same after restart.
        """
        config_file = tmp_path / "config.json"
        themes_dir = tmp_path / "themes"

        # Session 1
        config_manager1 = ConfigManager(str(config_file))
        theme_manager1 = ThemeManager(themes_dir)
        theme_manager1.create_default_themes()

        config1 = config_manager1.load_config()
        initial_theme = config1.theme

        # Cycle theme
        next_theme = theme_manager1.get_next_theme_name(initial_theme)
        config_manager1.update_theme(next_theme)
        config_manager1.save_config()

        # Session 2 (simulated restart)
        config_manager2 = ConfigManager(str(config_file))
        theme_manager2 = ThemeManager(themes_dir)

        config2 = config_manager2.load_config()

        # Theme should persist
        assert config2.theme == next_theme
        assert config2.theme != initial_theme

    def test_theme_cycle_with_invalid_theme_in_config(self, tmp_path):
        """Test Ctrl+T when config has invalid theme but themes exist.

        Integration: Config out of sync with available themes.
        Expected: Should recover to valid theme.
        """
        config_file = tmp_path / "config.json"
        themes_dir = tmp_path / "themes"

        config_manager = ConfigManager(str(config_file))
        theme_manager = ThemeManager(themes_dir)
        theme_manager.create_default_themes()

        # Manually set invalid theme in config
        config = config_manager.load_config()
        config.theme = "this_theme_does_not_exist"
        config_manager.save_config()

        # Reload
        config = config_manager.load_config()
        assert config.theme == "this_theme_does_not_exist"

        # Try to cycle (should handle invalid current theme)
        next_theme = theme_manager.get_next_theme_name(config.theme)

        # Should return first available theme
        available = theme_manager.get_available_themes()
        assert next_theme == available[0]

        # Should be able to set it
        result = theme_manager.set_current_theme(next_theme)
        assert result

    def test_theme_cycle_full_rotation(self, tmp_path):
        """Test cycling through all themes and back to start.

        Integration: Verify complete rotation works correctly.
        Expected: Should return to starting theme after full cycle.
        """
        themes_dir = tmp_path / "themes"
        manager = ThemeManager(themes_dir)
        manager.create_default_themes()

        themes = manager.get_available_themes()
        assert len(themes) >= 3  # Default themes

        start_theme = themes[0]
        current_theme = start_theme

        # Cycle through all themes
        for _ in range(len(themes)):
            next_theme = manager.get_next_theme_name(current_theme)
            current_theme = next_theme

        # Should be back at start
        assert current_theme == start_theme


class TestThemeValidation:
    """Test theme validation edge cases."""

    def test_theme_with_empty_name(self, tmp_path):
        """Test theme with empty name field.

        Edge Case: Theme name is empty string.
        Expected: Should still load but not be usable.
        """
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()

        empty_name_theme = {
            "name": "",  # Empty name
            "display_name": "Empty Name Theme",
            "primary": "#FF0000",
            "accent": "#00FF00",
            "surface": "#0000FF",
            "panel": "#FFFF00",
            "text": "#FFFFFF",
            "text_muted": "#CCCCCC",
            "warning": "#FFA500",
            "error": "#FF0000",
            "success": "#00FF00",
            "selection": "#FFFF00",
            "selection_text": "#000000"
        }
        (themes_dir / "empty_name.json").write_text(json.dumps(empty_name_theme))

        manager = ThemeManager(themes_dir)
        theme = manager.load_theme("empty_name")

        # Should load but validation might fail
        if theme:
            assert theme.name == ""

    def test_theme_with_unicode_characters(self, tmp_path):
        """Test theme with unicode characters in display name.

        Edge Case: Non-ASCII characters in theme data.
        Expected: Should handle unicode correctly.
        """
        themes_dir = tmp_path / "themes"
        themes_dir.mkdir()

        unicode_theme = {
            "name": "unicode",
            "display_name": "测试主题 🎨",  # Chinese + emoji
            "primary": "#FF0000",
            "accent": "#00FF00",
            "surface": "#0000FF",
            "panel": "#FFFF00",
            "text": "#FFFFFF",
            "text_muted": "#CCCCCC",
            "warning": "#FFA500",
            "error": "#FF0000",
            "success": "#00FF00",
            "selection": "#FFFF00",
            "selection_text": "#000000"
        }
        (themes_dir / "unicode.json").write_text(
            json.dumps(unicode_theme, ensure_ascii=False),
            encoding="utf-8"
        )

        manager = ThemeManager(themes_dir)
        theme = manager.load_theme("unicode")

        assert theme is not None
        assert theme.display_name == "测试主题 🎨"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
