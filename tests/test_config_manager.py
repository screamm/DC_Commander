"""
Unit tests for config_manager module.

Tests configuration loading, saving, and validation.
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.config_manager import (
    ConfigManager,
    Config,
    PanelConfig,
    ColorScheme,
    EditorSettings,
    ViewSettings,
    KeyboardShortcuts
)


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager"""

    def setUp(self):
        """Create temporary config file for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.config_mgr = ConfigManager(self.config_path)

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_config_manager(self):
        """Test ConfigManager creation"""
        self.assertIsInstance(self.config_mgr, ConfigManager)
        self.assertEqual(str(self.config_mgr.config_path), self.config_path)

    def test_load_default_config(self):
        """Test loading default configuration"""
        config = self.config_mgr.load_config()
        self.assertIsInstance(config, Config)
        self.assertIsInstance(config.left_panel, PanelConfig)
        self.assertIsInstance(config.right_panel, PanelConfig)
        self.assertIsInstance(config.color_scheme, ColorScheme)
        self.assertIsInstance(config.editor, EditorSettings)
        self.assertIsInstance(config.view, ViewSettings)
        self.assertIsInstance(config.shortcuts, KeyboardShortcuts)

    def test_save_and_load_config(self):
        """Test saving and loading configuration"""
        # Load default config
        config = self.config_mgr.load_config()

        # Modify config
        config.left_panel.start_path = "/test/path"
        config.color_scheme.name = "dark"
        config.editor.tab_size = 8

        # Save config
        result = self.config_mgr.save_config()
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.config_path))

        # Load config in new manager
        new_mgr = ConfigManager(self.config_path)
        loaded_config = new_mgr.load_config()

        # Verify loaded values
        self.assertEqual(loaded_config.left_panel.start_path, "/test/path")
        self.assertEqual(loaded_config.color_scheme.name, "dark")
        self.assertEqual(loaded_config.editor.tab_size, 8)

    def test_config_file_format(self):
        """Test that config file is valid JSON"""
        config = self.config_mgr.load_config()
        self.config_mgr.save_config()

        # Read and parse JSON
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIsInstance(data, dict)
        self.assertIn('left_panel', data)
        self.assertIn('right_panel', data)
        self.assertIn('color_scheme', data)
        self.assertIn('editor', data)
        self.assertIn('view', data)
        self.assertIn('shortcuts', data)

    def test_update_panel_paths(self):
        """Test updating panel paths"""
        config = self.config_mgr.get_config()

        self.config_mgr.update_left_panel_path("/left/path")
        self.assertEqual(config.left_panel.start_path, "/left/path")

        self.config_mgr.update_right_panel_path("/right/path")
        self.assertEqual(config.right_panel.start_path, "/right/path")

    def test_update_color_scheme(self):
        """Test updating color scheme"""
        config = self.config_mgr.get_config()

        # Test all built-in schemes
        for scheme_name in ["default", "dark", "light", "classic"]:
            self.config_mgr.update_color_scheme(scheme_name)
            self.assertEqual(config.color_scheme.name, scheme_name)

        # Test invalid scheme (should not change)
        self.config_mgr.update_color_scheme("nonexistent")
        # Should still be "classic" from last valid update
        self.assertEqual(config.color_scheme.name, "classic")

    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults"""
        config = self.config_mgr.get_config()

        # Modify config
        config.left_panel.start_path = "/custom/path"
        config.editor.tab_size = 12
        config.view.show_hidden_files = True

        # Reset to defaults
        self.config_mgr.reset_to_defaults()
        config = self.config_mgr.get_config()

        # Verify defaults
        self.assertEqual(config.editor.tab_size, 4)
        self.assertEqual(config.view.show_hidden_files, False)

    def test_validate_config_valid(self):
        """Test validating a valid configuration"""
        config = self.config_mgr.load_config()

        # Set valid paths
        import tempfile
        temp_dir = tempfile.gettempdir()
        config.left_panel.start_path = temp_dir
        config.right_panel.start_path = temp_dir

        issues = self.config_mgr.validate_config()
        self.assertEqual(len(issues), 0)

    def test_validate_config_invalid_paths(self):
        """Test validating configuration with invalid paths"""
        config = self.config_mgr.get_config()

        # Set invalid paths
        config.left_panel.start_path = "/nonexistent/path"
        config.right_panel.start_path = "/another/invalid/path"

        issues = self.config_mgr.validate_config()
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("Left panel path" in issue for issue in issues))
        self.assertTrue(any("Right panel path" in issue for issue in issues))

    def test_validate_config_invalid_tab_size(self):
        """Test validating configuration with invalid tab size"""
        config = self.config_mgr.get_config()

        # Set invalid tab sizes
        config.editor.tab_size = 0
        issues = self.config_mgr.validate_config()
        self.assertTrue(any("tab size" in issue.lower() for issue in issues))

        config.editor.tab_size = 20
        issues = self.config_mgr.validate_config()
        self.assertTrue(any("tab size" in issue.lower() for issue in issues))

    def test_validate_config_invalid_file_size_format(self):
        """Test validating configuration with invalid file size format"""
        config = self.config_mgr.get_config()

        config.view.file_size_format = "invalid"
        issues = self.config_mgr.validate_config()
        self.assertTrue(any("file size format" in issue.lower() for issue in issues))

    def test_get_config_caching(self):
        """Test that get_config returns cached instance"""
        config1 = self.config_mgr.get_config()
        config2 = self.config_mgr.get_config()
        self.assertIs(config1, config2)

    def test_load_invalid_json(self):
        """Test loading invalid JSON file"""
        # Create invalid JSON file
        with open(self.config_path, 'w') as f:
            f.write("{ invalid json }")

        # Should load default config instead
        config = self.config_mgr.load_config()
        self.assertIsInstance(config, Config)

    def test_save_creates_directory(self):
        """Test that save creates parent directory if needed"""
        # Create path with non-existent directory
        nested_path = os.path.join(self.temp_dir, "nested", "dir", "config.json")
        mgr = ConfigManager(nested_path)

        config = mgr.load_config()
        result = mgr.save_config()

        self.assertTrue(result)
        self.assertTrue(os.path.exists(nested_path))


class TestConfigDataClasses(unittest.TestCase):
    """Test configuration dataclasses"""

    def test_panel_config_defaults(self):
        """Test PanelConfig default values"""
        panel = PanelConfig()
        self.assertEqual(panel.start_path, "")
        self.assertEqual(panel.show_hidden_files, False)
        self.assertEqual(panel.sort_by, "name")
        self.assertEqual(panel.sort_ascending, True)

    def test_color_scheme_defaults(self):
        """Test ColorScheme default values"""
        scheme = ColorScheme()
        self.assertEqual(scheme.name, "default")
        self.assertEqual(scheme.background, "blue")
        self.assertEqual(scheme.text, "white")

    def test_editor_settings_defaults(self):
        """Test EditorSettings default values"""
        editor = EditorSettings()
        self.assertEqual(editor.default_editor, "")
        self.assertEqual(editor.tab_size, 4)
        self.assertEqual(editor.use_spaces, True)
        self.assertEqual(editor.word_wrap, False)

    def test_view_settings_defaults(self):
        """Test ViewSettings default values"""
        view = ViewSettings()
        self.assertEqual(view.show_hidden_files, False)
        self.assertEqual(view.show_file_size, True)
        self.assertEqual(view.file_size_format, "auto")

    def test_keyboard_shortcuts_defaults(self):
        """Test KeyboardShortcuts default values"""
        shortcuts = KeyboardShortcuts()
        self.assertEqual(shortcuts.quit, "q")
        self.assertEqual(shortcuts.copy, "F5")
        self.assertEqual(shortcuts.delete, "F8")
        self.assertEqual(shortcuts.help, "F1")

    def test_config_defaults(self):
        """Test Config default values"""
        config = Config()
        self.assertIsInstance(config.left_panel, PanelConfig)
        self.assertIsInstance(config.right_panel, PanelConfig)
        self.assertIsInstance(config.color_scheme, ColorScheme)
        self.assertIsInstance(config.editor, EditorSettings)
        self.assertIsInstance(config.view, ViewSettings)
        self.assertIsInstance(config.shortcuts, KeyboardShortcuts)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()
