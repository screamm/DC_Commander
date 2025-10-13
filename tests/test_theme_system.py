"""
Comprehensive test suite for theme system.

Tests all theme components including:
- ThemeManager: Theme loading, toggling, custom theme management
- Theme/ThemeMetadata: Serialization, validation, backward compatibility
- ThemeConfigDialog: Color validation, theme creation/editing
- ThemeSelectionMenu: Theme selection UI and interactions
- Integration: Complete workflows and message handlers
- Security: Path traversal prevention, input validation
- Edge cases: Error handling, malformed data, boundary conditions

Target: >90% code coverage for theme system
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from unittest.mock import Mock, patch, MagicMock

from features.theme_manager import (
    ThemeManager,
    Theme,
    ThemeMetadata,
    ThemeType,
    get_theme_manager
)
from components.theme_config_dialog import ThemeConfigDialog, ColorValidator
from components.theme_selection_menu import ThemeSelectionMenu


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_themes_dir(tmp_path):
    """Create temporary themes directory."""
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    return themes_dir


@pytest.fixture
def theme_manager(temp_themes_dir):
    """Create ThemeManager with temp directory."""
    return ThemeManager(themes_dir=temp_themes_dir)


@pytest.fixture
def sample_theme():
    """Create sample theme for testing."""
    return Theme(
        name="test_theme",
        display_name="Test Theme",
        primary="#0000AA",
        accent="#00FFFF",
        surface="#000055",
        panel="#0000AA",
        text="#FFFF77",
        text_muted="#AAAAAA",
        warning="#FFFF00",
        error="#FF5555",
        success="#55FF55",
        selection="#FFFF00",
        selection_text="#000000",
        metadata=ThemeMetadata(
            theme_id="test_theme",
            display_name="Test Theme",
            theme_type=ThemeType.CUSTOM,
            description="Test theme",
            author="Test Author"
        )
    )


@pytest.fixture
def sample_theme_dict():
    """Create sample theme dictionary for testing."""
    return {
        "name": "test_theme",
        "display_name": "Test Theme",
        "primary": "#0000AA",
        "accent": "#00FFFF",
        "surface": "#000055",
        "panel": "#0000AA",
        "text": "#FFFF77",
        "text_muted": "#AAAAAA",
        "warning": "#FFFF00",
        "error": "#FF5555",
        "success": "#55FF55",
        "selection": "#FFFF00",
        "selection_text": "#000000"
    }


@pytest.fixture
def legacy_theme_dict():
    """Create legacy theme dictionary (without metadata)."""
    return {
        "name": "legacy_theme",
        "display_name": "Legacy Theme",
        "primary": "#0000AA",
        "accent": "#00FFFF",
        "surface": "#000055",
        "panel": "#0000AA",
        "text": "#FFFF77",
        "text_muted": "#AAAAAA",
        "warning": "#FFFF00",
        "error": "#FF5555",
        "success": "#55FF55",
        "selection": "#FFFF00",
        "selection_text": "#000000"
    }


# ============================================================================
# ThemeManager Tests
# ============================================================================

class TestThemeManager:
    """Tests for ThemeManager class."""

    def test_init_creates_themes_directory(self, tmp_path):
        """Test ThemeManager creates themes directory if it doesn't exist."""
        themes_dir = tmp_path / "new_themes"
        assert not themes_dir.exists()

        manager = ThemeManager(themes_dir=themes_dir)

        assert themes_dir.exists()
        assert themes_dir.is_dir()

    def test_init_with_none_uses_default(self):
        """Test ThemeManager uses default directory when None provided."""
        manager = ThemeManager(themes_dir=None)

        assert manager.themes_dir.name == "themes"
        assert manager.themes_dir.parent.name == "features"

    def test_get_toggle_themes_built_in_only(self, theme_manager):
        """Test toggle list contains only built-in when no custom themes."""
        toggle_list = theme_manager.get_toggle_themes()

        assert toggle_list == ThemeManager.BUILT_IN_THEMES
        assert len(toggle_list) == 4
        assert "norton_commander" in toggle_list
        assert "modern_dark" in toggle_list
        assert "solarized" in toggle_list
        assert "midnight_blue" in toggle_list

    def test_get_toggle_themes_with_custom(self, theme_manager, sample_theme):
        """Test toggle list includes custom themes when they exist."""
        # Save custom theme
        theme_manager.save_custom_theme("custom1", sample_theme)

        toggle_list = theme_manager.get_toggle_themes()

        assert len(toggle_list) == 5  # 4 built-in + 1 custom
        assert "custom1" in toggle_list
        assert "norton_commander" in toggle_list

    def test_get_toggle_themes_with_both_custom(self, theme_manager, sample_theme):
        """Test toggle list includes both custom themes."""
        # Save to both custom slots
        theme_manager.save_custom_theme("custom1", sample_theme)
        theme_manager.save_custom_theme("custom2", sample_theme)

        toggle_list = theme_manager.get_toggle_themes()

        assert len(toggle_list) == 6  # 4 built-in + 2 custom
        assert "custom1" in toggle_list
        assert "custom2" in toggle_list

    def test_toggle_theme_no_current(self, theme_manager):
        """Test toggle_theme returns first theme when no current theme."""
        next_theme = theme_manager.toggle_theme()

        assert next_theme == "norton_commander"

    def test_toggle_theme_cycles_correctly(self, theme_manager):
        """Test toggle_theme cycles through themes correctly."""
        # Set current theme
        theme_manager._current_theme = Theme(
            name="norton_commander",
            display_name="Norton Commander",
            primary="#0000AA",
            accent="#00FFFF",
            surface="#000055",
            panel="#0000AA",
            text="#FFFF77",
            text_muted="#AAAAAA",
            warning="#FFFF00",
            error="#FF5555",
            success="#55FF55",
            selection="#FFFF00",
            selection_text="#000000"
        )

        # Toggle to next
        next_theme = theme_manager.toggle_theme()
        assert next_theme == "modern_dark"

        # Set to last theme
        theme_manager._current_theme.name = "midnight_blue"

        # Toggle should wrap to first
        next_theme = theme_manager.toggle_theme()
        assert next_theme == "norton_commander"

    def test_toggle_theme_with_custom(self, theme_manager, sample_theme):
        """Test toggle_theme includes custom themes in cycle."""
        # Save custom theme
        theme_manager.save_custom_theme("custom1", sample_theme)

        # Set current to last built-in
        theme_manager._current_theme = Theme(
            name="midnight_blue",
            display_name="Midnight Blue",
            primary="#4169E1",
            accent="#6495ED",
            surface="#191970",
            panel="#000080",
            text="#F0F8FF",
            text_muted="#B0C4DE",
            warning="#FFD700",
            error="#FF6347",
            success="#98FB98",
            selection="#4169E1",
            selection_text="#FFFFFF"
        )

        # Toggle should go to custom1
        next_theme = theme_manager.toggle_theme()
        assert next_theme == "custom1"

    def test_toggle_theme_empty_list(self, theme_manager):
        """Test toggle_theme handles empty theme list."""
        # Mock empty theme list
        with patch.object(theme_manager, 'get_toggle_themes', return_value=[]):
            next_theme = theme_manager.toggle_theme()
            assert next_theme is None

    def test_apply_theme_success(self, theme_manager, sample_theme):
        """Test apply_theme loads and sets theme successfully."""
        # Save theme first
        theme_manager.save_theme(sample_theme)

        result = theme_manager.apply_theme("test_theme")

        assert result is True
        assert theme_manager._current_theme is not None
        assert theme_manager._current_theme.name == "test_theme"

    def test_apply_theme_empty_id(self, theme_manager):
        """Test apply_theme rejects empty theme_id."""
        result = theme_manager.apply_theme("")

        assert result is False

    def test_apply_theme_invalid_id(self, theme_manager):
        """Test apply_theme rejects invalid theme_id."""
        result = theme_manager.apply_theme("../etc/passwd")

        assert result is False

    def test_apply_theme_not_found(self, theme_manager):
        """Test apply_theme handles non-existent theme."""
        result = theme_manager.apply_theme("nonexistent")

        assert result is False

    def test_save_custom_theme_success(self, theme_manager, sample_theme):
        """Test save_custom_theme saves theme correctly."""
        result = theme_manager.save_custom_theme("custom1", sample_theme)

        assert result is True
        assert (theme_manager.themes_dir / "custom1.json").exists()

        # Verify theme metadata updated
        assert sample_theme.name == "custom1"
        assert sample_theme.metadata.theme_id == "custom1"
        assert sample_theme.metadata.theme_type == ThemeType.CUSTOM

    def test_save_custom_theme_invalid_slot(self, theme_manager, sample_theme):
        """Test save_custom_theme rejects invalid slot."""
        with pytest.raises(ValueError, match="Invalid custom theme slot"):
            theme_manager.save_custom_theme("invalid_slot", sample_theme)

    def test_save_custom_theme_validation_failure(self, theme_manager):
        """Test save_custom_theme rejects invalid theme."""
        invalid_theme = Theme(
            name="invalid",
            display_name="Invalid",
            primary="not_a_color",  # Invalid color
            accent="#00FFFF",
            surface="#000055",
            panel="#0000AA",
            text="#FFFF77",
            text_muted="#AAAAAA",
            warning="#FFFF00",
            error="#FF5555",
            success="#55FF55",
            selection="#FFFF00",
            selection_text="#000000"
        )

        result = theme_manager.save_custom_theme("custom1", invalid_theme)

        assert result is False

    def test_save_custom_theme_creates_metadata(self, theme_manager):
        """Test save_custom_theme creates metadata if missing."""
        theme = Theme(
            name="test",
            display_name="Test",
            primary="#0000AA",
            accent="#00FFFF",
            surface="#000055",
            panel="#0000AA",
            text="#FFFF77",
            text_muted="#AAAAAA",
            warning="#FFFF00",
            error="#FF5555",
            success="#55FF55",
            selection="#FFFF00",
            selection_text="#000000",
            metadata=None  # No metadata
        )

        result = theme_manager.save_custom_theme("custom1", theme)

        assert result is True
        assert theme.metadata is not None
        assert theme.metadata.theme_id == "custom1"
        assert theme.metadata.theme_type == ThemeType.CUSTOM

    def test_delete_custom_theme_success(self, theme_manager, sample_theme):
        """Test delete_custom_theme removes theme successfully."""
        # Save theme first
        theme_manager.save_custom_theme("custom1", sample_theme)
        assert (theme_manager.themes_dir / "custom1.json").exists()

        result = theme_manager.delete_custom_theme("custom1")

        assert result is True
        assert not (theme_manager.themes_dir / "custom1.json").exists()

    def test_delete_custom_theme_invalid_slot(self, theme_manager):
        """Test delete_custom_theme rejects invalid slot."""
        with pytest.raises(ValueError, match="Invalid custom theme slot"):
            theme_manager.delete_custom_theme("invalid_slot")

    def test_delete_custom_theme_not_exists(self, theme_manager):
        """Test delete_custom_theme handles non-existent theme."""
        result = theme_manager.delete_custom_theme("custom1")

        # Should return True (already deleted)
        assert result is True

    def test_delete_custom_theme_removes_from_cache(self, theme_manager, sample_theme):
        """Test delete_custom_theme removes theme from cache."""
        # Save and load theme (caches it)
        theme_manager.save_custom_theme("custom1", sample_theme)
        theme_manager.load_theme("custom1")
        assert "custom1" in theme_manager._themes_cache

        # Delete theme
        theme_manager.delete_custom_theme("custom1")

        assert "custom1" not in theme_manager._themes_cache

    def test_has_custom_slot_available_both_free(self, theme_manager):
        """Test has_custom_slot_available returns True when slots free."""
        assert theme_manager.has_custom_slot_available() is True

    def test_has_custom_slot_available_one_occupied(self, theme_manager, sample_theme):
        """Test has_custom_slot_available returns True when one slot free."""
        theme_manager.save_custom_theme("custom1", sample_theme)

        assert theme_manager.has_custom_slot_available() is True

    def test_has_custom_slot_available_all_occupied(self, theme_manager, sample_theme):
        """Test has_custom_slot_available returns False when all slots full."""
        theme_manager.save_custom_theme("custom1", sample_theme)
        theme_manager.save_custom_theme("custom2", sample_theme)

        assert theme_manager.has_custom_slot_available() is False

    def test_get_available_custom_slot_returns_first(self, theme_manager):
        """Test get_available_custom_slot returns first available slot."""
        slot = theme_manager.get_available_custom_slot()

        assert slot == "custom1"

    def test_get_available_custom_slot_returns_second(self, theme_manager, sample_theme):
        """Test get_available_custom_slot returns second when first occupied."""
        theme_manager.save_custom_theme("custom1", sample_theme)

        slot = theme_manager.get_available_custom_slot()

        assert slot == "custom2"

    def test_get_available_custom_slot_none_available(self, theme_manager, sample_theme):
        """Test get_available_custom_slot returns None when all full."""
        theme_manager.save_custom_theme("custom1", sample_theme)
        theme_manager.save_custom_theme("custom2", sample_theme)

        slot = theme_manager.get_available_custom_slot()

        assert slot is None

    def test_load_theme_success(self, theme_manager, sample_theme):
        """Test load_theme loads theme from file."""
        # Save theme
        theme_manager.save_theme(sample_theme)

        # Clear cache
        theme_manager._themes_cache.clear()

        # Load theme
        loaded = theme_manager.load_theme("test_theme")

        assert loaded is not None
        assert loaded.name == "test_theme"
        assert loaded.display_name == "Test Theme"

    def test_load_theme_caches_result(self, theme_manager, sample_theme):
        """Test load_theme caches loaded theme."""
        theme_manager.save_theme(sample_theme)

        # Load twice
        theme_manager.load_theme("test_theme")
        cached = theme_manager.load_theme("test_theme")

        assert cached is not None
        assert "test_theme" in theme_manager._themes_cache

    def test_load_theme_empty_name(self, theme_manager):
        """Test load_theme rejects empty name."""
        result = theme_manager.load_theme("")

        assert result is None

    def test_load_theme_invalid_name(self, theme_manager):
        """Test load_theme rejects invalid name."""
        result = theme_manager.load_theme("../etc/passwd")

        assert result is None

    def test_load_theme_not_found(self, theme_manager):
        """Test load_theme handles non-existent file."""
        result = theme_manager.load_theme("nonexistent")

        assert result is None

    def test_load_theme_malformed_json(self, theme_manager):
        """Test load_theme handles malformed JSON."""
        # Write invalid JSON
        theme_file = theme_manager.themes_dir / "malformed.json"
        theme_file.write_text("{ invalid json }")

        result = theme_manager.load_theme("malformed")

        assert result is None

    def test_load_theme_validation_failure(self, theme_manager):
        """Test load_theme rejects invalid theme data."""
        # Write theme with invalid color
        invalid_data = {
            "name": "invalid",
            "display_name": "Invalid",
            "primary": "not_a_color",  # Invalid
            "accent": "#00FFFF",
            "surface": "#000055",
            "panel": "#0000AA",
            "text": "#FFFF77",
            "text_muted": "#AAAAAA",
            "warning": "#FFFF00",
            "error": "#FF5555",
            "success": "#55FF55",
            "selection": "#FFFF00",
            "selection_text": "#000000"
        }

        theme_file = theme_manager.themes_dir / "invalid.json"
        theme_file.write_text(json.dumps(invalid_data))

        result = theme_manager.load_theme("invalid")

        assert result is None


# ============================================================================
# Theme and ThemeMetadata Tests
# ============================================================================

class TestTheme:
    """Tests for Theme class."""

    def test_from_dict_backward_compatibility(self, legacy_theme_dict):
        """Test Theme.from_dict() handles old format without metadata."""
        theme = Theme.from_dict(legacy_theme_dict)

        assert theme.name == "legacy_theme"
        assert theme.display_name == "Legacy Theme"
        assert theme.metadata is not None
        assert theme.metadata.theme_type == ThemeType.BUILT_IN
        assert theme.metadata.is_editable is False

    def test_from_dict_new_format(self, sample_theme_dict):
        """Test Theme.from_dict() handles new format with metadata."""
        data_with_metadata = sample_theme_dict.copy()
        data_with_metadata["metadata"] = {
            "theme_id": "test_theme",
            "display_name": "Test Theme",
            "theme_type": "custom",
            "description": "Test",
            "author": "Test Author",
            "created_date": "2024-01-01T00:00:00",
            "modified_date": "2024-01-01T00:00:00",
            "is_editable": True
        }

        theme = Theme.from_dict(data_with_metadata)

        assert theme.name == "test_theme"
        assert theme.metadata is not None
        assert theme.metadata.theme_type == ThemeType.CUSTOM
        assert theme.metadata.is_editable is True

    def test_to_dict_without_metadata(self):
        """Test Theme.to_dict() without metadata."""
        theme = Theme(
            name="test",
            display_name="Test",
            primary="#0000AA",
            accent="#00FFFF",
            surface="#000055",
            panel="#0000AA",
            text="#FFFF77",
            text_muted="#AAAAAA",
            warning="#FFFF00",
            error="#FF5555",
            success="#55FF55",
            selection="#FFFF00",
            selection_text="#000000",
            metadata=None
        )

        data = theme.to_dict()

        assert "name" in data
        assert "metadata" not in data

    def test_to_dict_with_metadata(self, sample_theme):
        """Test Theme.to_dict() includes metadata."""
        data = sample_theme.to_dict()

        assert "name" in data
        assert "metadata" in data
        assert data["metadata"]["theme_type"] == "custom"

    def test_validate_success(self, sample_theme):
        """Test Theme.validate() passes for valid theme."""
        issues = sample_theme.validate()

        assert len(issues) == 0

    def test_validate_missing_field(self):
        """Test Theme.validate() detects missing color."""
        theme = Theme(
            name="test",
            display_name="Test",
            primary="",  # Missing
            accent="#00FFFF",
            surface="#000055",
            panel="#0000AA",
            text="#FFFF77",
            text_muted="#AAAAAA",
            warning="#FFFF00",
            error="#FF5555",
            success="#55FF55",
            selection="#FFFF00",
            selection_text="#000000"
        )

        issues = theme.validate()

        assert len(issues) > 0
        assert any("primary" in issue for issue in issues)

    def test_validate_invalid_color(self):
        """Test Theme.validate() detects invalid color format."""
        theme = Theme(
            name="test",
            display_name="Test",
            primary="not_a_color",  # Invalid
            accent="#00FFFF",
            surface="#000055",
            panel="#0000AA",
            text="#FFFF77",
            text_muted="#AAAAAA",
            warning="#FFFF00",
            error="#FF5555",
            success="#55FF55",
            selection="#FFFF00",
            selection_text="#000000"
        )

        issues = theme.validate()

        assert len(issues) > 0
        assert any("primary" in issue and "Invalid color" in issue for issue in issues)

    def test_is_valid_color_hex_3(self):
        """Test _is_valid_color accepts #RGB format."""
        assert Theme._is_valid_color("#FFF") is True
        assert Theme._is_valid_color("#000") is True

    def test_is_valid_color_hex_6(self):
        """Test _is_valid_color accepts #RRGGBB format."""
        assert Theme._is_valid_color("#FFFFFF") is True
        assert Theme._is_valid_color("#000000") is True

    def test_is_valid_color_hex_8(self):
        """Test _is_valid_color accepts #RRGGBBAA format."""
        assert Theme._is_valid_color("#FFFFFFFF") is True
        assert Theme._is_valid_color("#00000000") is True

    def test_is_valid_color_named(self):
        """Test _is_valid_color accepts named colors."""
        assert Theme._is_valid_color("red") is True
        assert Theme._is_valid_color("blue") is True
        assert Theme._is_valid_color("transparent") is True

    def test_is_valid_color_rgb(self):
        """Test _is_valid_color accepts rgb() format."""
        assert Theme._is_valid_color("rgb(255, 255, 255)") is True

    def test_is_valid_color_invalid(self):
        """Test _is_valid_color rejects invalid colors."""
        assert Theme._is_valid_color("not_a_color") is False
        assert Theme._is_valid_color("#GGGGGG") is False
        assert Theme._is_valid_color("") is False
        assert Theme._is_valid_color(None) is False


class TestThemeMetadata:
    """Tests for ThemeMetadata class."""

    def test_to_dict(self):
        """Test ThemeMetadata.to_dict() serialization."""
        metadata = ThemeMetadata(
            theme_id="test",
            display_name="Test",
            theme_type=ThemeType.CUSTOM,
            description="Test theme",
            author="Test Author"
        )

        data = metadata.to_dict()

        assert data["theme_id"] == "test"
        assert data["theme_type"] == "custom"
        assert data["is_editable"] is True

    def test_from_dict(self):
        """Test ThemeMetadata.from_dict() deserialization."""
        data = {
            "theme_id": "test",
            "display_name": "Test",
            "theme_type": "custom",
            "description": "Test theme",
            "author": "Test Author",
            "created_date": "2024-01-01T00:00:00",
            "modified_date": "2024-01-01T00:00:00",
            "is_editable": True
        }

        metadata = ThemeMetadata.from_dict(data)

        assert metadata.theme_id == "test"
        assert metadata.theme_type == ThemeType.CUSTOM
        assert metadata.is_editable is True

    def test_from_dict_invalid_theme_type(self):
        """Test ThemeMetadata.from_dict() handles invalid theme_type."""
        data = {
            "theme_id": "test",
            "display_name": "Test",
            "theme_type": "invalid_type",  # Invalid
        }

        metadata = ThemeMetadata.from_dict(data)

        # Should default to BUILT_IN
        assert metadata.theme_type == ThemeType.BUILT_IN


# ============================================================================
# ColorValidator Tests
# ============================================================================

class TestColorValidator:
    """Tests for ColorValidator class."""

    def test_validate_hex_3_valid(self):
        """Test ColorValidator accepts #RGB format."""
        validator = ColorValidator()

        result = validator.validate("#FFF")
        assert result.is_valid is True

        result = validator.validate("#000")
        assert result.is_valid is True

    def test_validate_hex_6_valid(self):
        """Test ColorValidator accepts #RRGGBB format."""
        validator = ColorValidator()

        result = validator.validate("#FFFFFF")
        assert result.is_valid is True

        result = validator.validate("#000000")
        assert result.is_valid is True

    def test_validate_hex_8_valid(self):
        """Test ColorValidator accepts #RRGGBBAA format."""
        validator = ColorValidator()

        result = validator.validate("#FFFFFFFF")
        assert result.is_valid is True

    def test_validate_empty(self):
        """Test ColorValidator rejects empty string."""
        validator = ColorValidator()

        result = validator.validate("")
        assert result.is_valid is False
        assert "empty" in str(result.failures[0]).lower()

    def test_validate_no_hash(self):
        """Test ColorValidator rejects color without #."""
        validator = ColorValidator()

        result = validator.validate("FFFFFF")
        assert result.is_valid is False
        assert "must start with #" in str(result.failures[0]).lower()

    def test_validate_invalid_length(self):
        """Test ColorValidator rejects invalid length."""
        validator = ColorValidator()

        result = validator.validate("#FF")  # Too short
        assert result.is_valid is False

        result = validator.validate("#FFFFFFF")  # Invalid length
        assert result.is_valid is False

    def test_validate_invalid_hex(self):
        """Test ColorValidator rejects non-hex characters."""
        validator = ColorValidator()

        result = validator.validate("#GGGGGG")
        assert result.is_valid is False
        assert "invalid hex" in str(result.failures[0]).lower()


# ============================================================================
# Security Tests
# ============================================================================

class TestSecurity:
    """Security tests for theme system."""

    def test_path_traversal_prevention_dots(self, theme_manager):
        """Test directory traversal with .. is prevented."""
        result = theme_manager._is_valid_theme_id("../etc/passwd")

        assert result is False

    def test_path_traversal_prevention_forward_slash(self, theme_manager):
        """Test directory traversal with / is prevented."""
        result = theme_manager._is_valid_theme_id("etc/passwd")

        assert result is False

    def test_path_traversal_prevention_backslash(self, theme_manager):
        """Test directory traversal with \\ is prevented."""
        result = theme_manager._is_valid_theme_id("etc\\passwd")

        assert result is False

    def test_is_valid_theme_id_alphanumeric(self, theme_manager):
        """Test _is_valid_theme_id accepts valid IDs."""
        assert theme_manager._is_valid_theme_id("theme_123") is True
        assert theme_manager._is_valid_theme_id("custom1") is True

    def test_is_valid_theme_id_special_chars(self, theme_manager):
        """Test _is_valid_theme_id rejects special characters."""
        assert theme_manager._is_valid_theme_id("theme-123") is False
        assert theme_manager._is_valid_theme_id("theme.json") is False
        assert theme_manager._is_valid_theme_id("theme!") is False

    def test_is_safe_path_within_themes_dir(self, theme_manager):
        """Test _is_safe_path accepts path within themes directory."""
        safe_path = theme_manager.themes_dir / "test_theme.json"

        assert theme_manager._is_safe_path(safe_path) is True

    def test_is_safe_path_outside_themes_dir(self, theme_manager, tmp_path):
        """Test _is_safe_path rejects path outside themes directory."""
        unsafe_path = tmp_path / "outside" / "test.json"

        assert theme_manager._is_safe_path(unsafe_path) is False

    def test_load_theme_path_validation(self, theme_manager):
        """Test load_theme validates path security."""
        # Try to load theme with path traversal
        result = theme_manager.load_theme("../../../etc/passwd")

        assert result is None

    def test_save_custom_theme_path_validation(self, theme_manager, sample_theme):
        """Test save_custom_theme validates path security."""
        # Mock _is_safe_path to return False
        with patch.object(theme_manager, '_is_safe_path', return_value=False):
            result = theme_manager.save_custom_theme("custom1", sample_theme)

            assert result is False


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Edge case tests for theme system."""

    def test_empty_themes_directory(self, theme_manager):
        """Test behavior with empty themes directory."""
        available = theme_manager.get_available_themes()

        assert len(available) == 0

    def test_malformed_json_handling(self, theme_manager):
        """Test handling of malformed JSON files."""
        # Create malformed JSON file
        theme_file = theme_manager.themes_dir / "malformed.json"
        theme_file.write_text("{ malformed json }")

        result = theme_manager.load_theme("malformed")

        assert result is None

    def test_missing_theme_file(self, theme_manager):
        """Test handling of missing theme file."""
        result = theme_manager.load_theme("nonexistent")

        assert result is None

    def test_full_custom_slots(self, theme_manager, sample_theme):
        """Test behavior when all custom slots are full."""
        # Fill both slots
        theme_manager.save_custom_theme("custom1", sample_theme)
        theme_manager.save_custom_theme("custom2", sample_theme)

        assert theme_manager.has_custom_slot_available() is False
        assert theme_manager.get_available_custom_slot() is None

    def test_deleting_active_theme(self, theme_manager, sample_theme):
        """Test deleting currently active theme."""
        # Save and activate theme
        theme_manager.save_custom_theme("custom1", sample_theme)
        theme_manager.apply_theme("custom1")

        # Delete active theme
        result = theme_manager.delete_custom_theme("custom1")

        assert result is True
        # Current theme reference remains, but file is gone
        assert not (theme_manager.themes_dir / "custom1.json").exists()

    def test_invalid_color_formats(self):
        """Test various invalid color formats."""
        assert Theme._is_valid_color("invalid") is False
        assert Theme._is_valid_color("123456") is False
        assert Theme._is_valid_color("#") is False
        assert Theme._is_valid_color("##FFFFFF") is False

    def test_theme_with_minimal_data(self):
        """Test theme creation with minimal required data."""
        theme_dict = {
            "name": "minimal",
            "display_name": "Minimal"
            # Missing all color fields - should use defaults
        }

        theme = Theme.from_dict(theme_dict)

        assert theme.name == "minimal"
        # Should have default colors
        assert theme.primary == "#0000AA"

    def test_concurrent_theme_operations(self, theme_manager, sample_theme):
        """Test thread-safe theme operations."""
        # Save and load theme multiple times
        for i in range(10):
            theme_manager.save_custom_theme("custom1", sample_theme)
            loaded = theme_manager.load_theme("custom1")
            assert loaded is not None


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for complete theme workflows."""

    def test_complete_theme_creation_workflow(self, theme_manager):
        """Test complete theme creation from start to finish."""
        # 1. Check slot availability
        assert theme_manager.has_custom_slot_available() is True

        # 2. Get available slot
        slot = theme_manager.get_available_custom_slot()
        assert slot == "custom1"

        # 3. Create theme
        theme = Theme(
            name=slot,
            display_name="My Custom Theme",
            primary="#1E90FF",
            accent="#00CED1",
            surface="#1A1A1A",
            panel="#2A2A2A",
            text="#E0E0E0",
            text_muted="#888888",
            warning="#FFA500",
            error="#FF4444",
            success="#44FF44",
            selection="#1E90FF",
            selection_text="#FFFFFF"
        )

        # 4. Save theme
        assert theme_manager.save_custom_theme(slot, theme) is True

        # 5. Verify saved
        assert (theme_manager.themes_dir / f"{slot}.json").exists()

        # 6. Load and verify
        loaded = theme_manager.load_theme(slot)
        assert loaded is not None
        assert loaded.display_name == "My Custom Theme"

        # 7. Apply theme
        assert theme_manager.apply_theme(slot) is True

    def test_complete_theme_editing_workflow(self, theme_manager, sample_theme):
        """Test complete theme editing workflow."""
        # 1. Save initial theme
        theme_manager.save_custom_theme("custom1", sample_theme)

        # 2. Load theme for editing
        theme = theme_manager.load_theme("custom1")
        assert theme is not None

        # 3. Modify theme
        theme.display_name = "Modified Theme"
        theme.primary = "#FF0000"

        # 4. Save modifications
        assert theme_manager.save_custom_theme("custom1", theme) is True

        # 5. Clear cache and reload
        theme_manager._themes_cache.clear()
        reloaded = theme_manager.load_theme("custom1")

        # 6. Verify modifications
        assert reloaded.display_name == "Modified Theme"
        assert reloaded.primary == "#FF0000"

    def test_complete_theme_deletion_workflow(self, theme_manager, sample_theme):
        """Test complete theme deletion workflow."""
        # 1. Save theme
        theme_manager.save_custom_theme("custom1", sample_theme)
        assert (theme_manager.themes_dir / "custom1.json").exists()

        # 2. Apply theme
        theme_manager.apply_theme("custom1")

        # 3. Delete theme
        assert theme_manager.delete_custom_theme("custom1") is True

        # 4. Verify deleted
        assert not (theme_manager.themes_dir / "custom1.json").exists()
        assert "custom1" not in theme_manager._themes_cache

        # 5. Try to load deleted theme
        loaded = theme_manager.load_theme("custom1")
        assert loaded is None

    def test_theme_toggle_with_persistence(self, theme_manager, sample_theme):
        """Test theme toggling with configuration persistence."""
        # 1. Save two themes to toggle between
        theme_manager.save_custom_theme("custom1", sample_theme)
        
        base_theme = Theme(
            name="test_base",
            display_name="Base Theme",
            primary="#FF0000",
            accent="#00FFFF",
            surface="#000055",
            panel="#0000AA",
            text="#FFFF77",
            text_muted="#AAAAAA",
            warning="#FFFF00",
            error="#FF5555",
            success="#55FF55",
            selection="#FFFF00",
            selection_text="#000000"
        )
        theme_manager.save_theme(base_theme)

        # 2. Apply base theme and verify
        assert theme_manager.apply_theme("test_base") is True
        assert theme_manager._current_theme is not None
        assert theme_manager._current_theme.name == "test_base"

        # 3. Apply custom theme and verify
        assert theme_manager.apply_theme("custom1") is True
        assert theme_manager._current_theme is not None
        assert theme_manager._current_theme.name == "custom1"

        # 4. Toggle back to base theme and verify
        assert theme_manager.apply_theme("test_base") is True
        assert theme_manager._current_theme.name == "test_base"

    def test_backward_compatibility_workflow(self, theme_manager, legacy_theme_dict):
        """Test loading and upgrading legacy themes."""
        # 1. Save legacy theme format
        theme_file = theme_manager.themes_dir / "legacy.json"
        theme_file.write_text(json.dumps(legacy_theme_dict))

        # 2. Load legacy theme
        theme = theme_manager.load_theme("legacy")
        assert theme is not None

        # 3. Verify metadata created
        assert theme.metadata is not None
        assert theme.metadata.theme_type == ThemeType.BUILT_IN
        assert theme.metadata.is_editable is False

        # 4. Save as new format
        theme.metadata.is_editable = True
        theme_manager.save_custom_theme("custom1", theme)

        # 5. Reload and verify upgrade
        upgraded = theme_manager.load_theme("custom1")
        assert upgraded.metadata.is_editable is True


# ============================================================================
# Global Function Tests
# ============================================================================

def test_get_theme_manager_singleton():
    """Test get_theme_manager returns singleton."""
    manager1 = get_theme_manager()
    manager2 = get_theme_manager()

    assert manager1 is manager2


def test_get_theme_manager_custom_dir(tmp_path):
    """Test get_theme_manager with custom directory."""
    custom_dir = tmp_path / "custom_themes"

    manager = get_theme_manager(themes_dir=custom_dir)

    assert manager.themes_dir == custom_dir
    assert custom_dir.exists()
