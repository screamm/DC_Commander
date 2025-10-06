"""
Unit tests for system_info module.

Tests system information gathering with mock data and error handling.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.system_info import (
    get_system_info,
    get_cpu_info,
    get_memory_info,
    get_disk_info,
    get_all_disk_info,
    get_environment_info,
    clear_cache
)


class TestSystemInfo(unittest.TestCase):
    """Test cases for system information functions"""

    def setUp(self):
        """Clear cache before each test"""
        clear_cache()

    def test_get_system_info_returns_dict(self):
        """Test that get_system_info returns a dictionary"""
        info = get_system_info()
        self.assertIsInstance(info, dict)

    def test_get_system_info_required_keys(self):
        """Test that system info contains required keys"""
        info = get_system_info()
        required_keys = [
            'os_name', 'os_version', 'platform', 'processor',
            'python_version', 'cpu_count', 'total_memory_gb'
        ]
        for key in required_keys:
            self.assertIn(key, info)

    def test_get_system_info_memory_values(self):
        """Test that memory values are positive numbers"""
        info = get_system_info()
        self.assertGreaterEqual(info['total_memory_gb'], 0)
        self.assertGreaterEqual(info['used_memory_gb'], 0)
        self.assertGreaterEqual(info['available_memory_gb'], 0)
        self.assertGreaterEqual(info['memory_percent'], 0)
        self.assertLessEqual(info['memory_percent'], 100)

    def test_get_cpu_info_returns_dict(self):
        """Test that get_cpu_info returns a dictionary"""
        info = get_cpu_info()
        self.assertIsInstance(info, dict)

    def test_get_cpu_info_required_keys(self):
        """Test that CPU info contains required keys"""
        info = get_cpu_info()
        required_keys = [
            'logical_cores', 'physical_cores', 'processor_model',
            'architecture', 'cpu_percent'
        ]
        for key in required_keys:
            self.assertIn(key, info)

    def test_get_cpu_info_core_counts(self):
        """Test that CPU core counts are valid"""
        info = get_cpu_info()
        self.assertGreater(info['logical_cores'], 0)
        # Physical cores might be None on some systems
        if info['physical_cores'] is not None:
            self.assertGreater(info['physical_cores'], 0)
            self.assertGreaterEqual(info['logical_cores'], info['physical_cores'])

    def test_get_memory_info_returns_dict(self):
        """Test that get_memory_info returns a dictionary"""
        info = get_memory_info()
        self.assertIsInstance(info, dict)

    def test_get_memory_info_required_keys(self):
        """Test that memory info contains required keys"""
        info = get_memory_info()
        required_keys = [
            'total_gb', 'available_gb', 'used_gb', 'free_gb',
            'percent_used', 'swap_total_gb'
        ]
        for key in required_keys:
            self.assertIn(key, info)

    def test_get_memory_info_values_valid(self):
        """Test that memory values are within valid ranges"""
        info = get_memory_info()
        self.assertGreater(info['total_gb'], 0)
        self.assertGreaterEqual(info['percent_used'], 0)
        self.assertLessEqual(info['percent_used'], 100)
        # Used + Available should roughly equal Total
        self.assertAlmostEqual(
            info['used_gb'] + info['available_gb'],
            info['total_gb'],
            delta=1.0  # Allow 1GB difference
        )

    def test_get_disk_info_root_returns_dict(self):
        """Test that get_disk_info for root returns a dictionary"""
        # Use current directory as it's guaranteed to exist
        import os
        info = get_disk_info(os.getcwd())
        self.assertIsInstance(info, dict)

    def test_get_disk_info_required_keys(self):
        """Test that disk info contains required keys"""
        import os
        info = get_disk_info(os.getcwd())
        required_keys = ['path', 'total_gb', 'used_gb', 'free_gb', 'percent_used']
        for key in required_keys:
            self.assertIn(key, info)

    def test_get_disk_info_values_valid(self):
        """Test that disk values are within valid ranges"""
        import os
        info = get_disk_info(os.getcwd())
        if 'error' not in info:
            self.assertGreater(info['total_gb'], 0)
            self.assertGreaterEqual(info['percent_used'], 0)
            self.assertLessEqual(info['percent_used'], 100)
            # Used + Free should roughly equal Total
            self.assertAlmostEqual(
                info['used_gb'] + info['free_gb'],
                info['total_gb'],
                delta=1.0
            )

    def test_get_disk_info_invalid_path(self):
        """Test that get_disk_info handles invalid paths gracefully"""
        info = get_disk_info("/nonexistent/path/that/does/not/exist")
        self.assertIn('error', info)

    def test_get_all_disk_info_returns_list(self):
        """Test that get_all_disk_info returns a list"""
        disks = get_all_disk_info()
        self.assertIsInstance(disks, list)
        if disks:
            self.assertIsInstance(disks[0], dict)

    def test_get_environment_info_returns_dict(self):
        """Test that get_environment_info returns a dictionary"""
        info = get_environment_info()
        self.assertIsInstance(info, dict)

    def test_get_environment_info_required_keys(self):
        """Test that environment info contains required keys"""
        info = get_environment_info()
        required_keys = ['hostname', 'username', 'boot_time', 'uptime_hours']
        for key in required_keys:
            self.assertIn(key, info)

    def test_get_environment_info_uptime_valid(self):
        """Test that uptime is a positive number"""
        info = get_environment_info()
        if 'error' not in info:
            self.assertGreaterEqual(info['uptime_hours'], 0)

    def test_caching_behavior(self):
        """Test that caching works correctly"""
        # First call
        info1 = get_system_info()
        # Second call (should be cached)
        info2 = get_system_info()
        # Should return same object due to caching
        self.assertEqual(info1, info2)

        # Clear cache
        clear_cache()

        # Third call (cache cleared)
        info3 = get_system_info()
        # Should still have same values but might be different object
        self.assertEqual(info1['os_name'], info3['os_name'])


class TestSystemInfoErrorHandling(unittest.TestCase):
    """Test error handling in system info functions"""

    def setUp(self):
        """Clear cache before each test"""
        clear_cache()

    @patch('features.system_info.psutil.virtual_memory')
    def test_get_system_info_handles_exception(self, mock_mem):
        """Test that get_system_info handles exceptions gracefully"""
        mock_mem.side_effect = Exception("Test error")
        info = get_system_info()
        # Should still return a dictionary with error info
        self.assertIsInstance(info, dict)
        self.assertIn('error', info)

    @patch('features.system_info.psutil.cpu_freq')
    def test_get_cpu_info_handles_missing_frequency(self, mock_freq):
        """Test CPU info when frequency is not available"""
        mock_freq.return_value = None
        info = get_cpu_info()
        self.assertEqual(info['current_frequency_mhz'], 0.0)

    @patch('features.system_info.psutil.disk_usage')
    def test_get_disk_info_handles_permission_error(self, mock_usage):
        """Test disk info handles permission errors"""
        mock_usage.side_effect = PermissionError("Access denied")
        info = get_disk_info("/test")
        self.assertIn('error', info)
        self.assertIn('Access denied', info['error'])


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()
