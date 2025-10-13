# DC Commander Test Suite - Quick Reference

## 🚀 Quick Start

### Run All Tests
```bash
pytest tests/test_production_ready.py tests/test_e2e_workflows.py tests/test_menu_system.py tests/test_config_system.py -v
```

### Run Single Test File
```bash
# Production-ready smoke tests
pytest tests/test_production_ready.py -v

# End-to-end workflow tests
pytest tests/test_e2e_workflows.py -v

# Menu system tests (F2)
pytest tests/test_menu_system.py -v

# Config system tests (F9)
pytest tests/test_config_system.py -v
```

## 📁 Test Files

### test_production_ready.py (55 tests)
Core functionality smoke tests:
- FilePanel operations
- Menu system structure
- Configuration management
- Theme system
- Dialog components
- Group selection
- Quick search
- Edge cases

### test_e2e_workflows.py (40+ tests)
Complete user workflow tests:
- File copy (F5)
- File move (F6)
- Directory creation (F7)
- File deletion (F8)
- Menu navigation (F2)
- Configuration (F9)
- Quick view (Ctrl+Q)
- Find file (Ctrl+F)
- Theme cycling (Ctrl+T)
- Async operations

### test_menu_system.py (45+ tests)
F2 menu system comprehensive tests:
- MenuAction structure
- MenuCategory navigation
- MenuScreen functionality
- Keyboard shortcuts
- State management
- Edge cases

### test_config_system.py (50+ tests)
F9 configuration system tests:
- Configuration dataclasses
- ConfigManager operations
- ThemeManager operations
- Theme validation
- ConfigScreen UI
- Persistence
- Edge cases

## 🎯 Test by Component

### FilePanel
```bash
pytest tests/test_production_ready.py::TestFilePanelCore -v
```

### Menu System
```bash
pytest tests/test_menu_system.py -v
pytest tests/test_production_ready.py::TestMenuSystem -v
```

### Configuration
```bash
pytest tests/test_config_system.py -v
pytest tests/test_production_ready.py::TestConfigurationSystem -v
```

### Theme System
```bash
pytest tests/test_config_system.py::TestThemeManager -v
pytest tests/test_production_ready.py::TestThemeSystem -v
```

### Dialogs
```bash
pytest tests/test_production_ready.py::TestDialogSystem -v
```

## 📊 Run with Coverage

### Generate Coverage Report
```bash
pytest tests/ --cov=components --cov=features --cov-report=html
```

### View Coverage Report
Open `htmlcov/index.html` in browser

## 🏃 Performance Testing

### Run Without Slow Tests
```bash
pytest tests/ -m "not slow" -v
```

### Run Only Slow Tests
```bash
pytest tests/ -m "slow" -v
```

### Parallel Execution
```bash
pytest tests/ -n auto
```

## 🔍 Debugging Tests

### Run Single Test with Detailed Output
```bash
pytest tests/test_production_ready.py::TestFilePanelCore::test_file_panel_initialization -v -s
```

### Stop on First Failure
```bash
pytest tests/ -x
```

### Show Local Variables on Failure
```bash
pytest tests/ -l
```

### Full Traceback
```bash
pytest tests/ --tb=long
```

## 🎨 Test Markers

### Available Markers
- `unit` - Unit tests
- `integration` - Integration tests
- `slow` - Tests taking >1 second
- `ui` - UI component tests

### Run by Marker
```bash
pytest tests/ -m "unit" -v
pytest tests/ -m "integration" -v
```

## 📝 Test Examples

### Example 1: Test File Panel Navigation
```bash
pytest tests/test_production_ready.py::TestFilePanelCore::test_file_panel_navigation -v
```

### Example 2: Test Menu Navigation Workflow
```bash
pytest tests/test_e2e_workflows.py::TestMenuNavigationWorkflow -v
```

### Example 3: Test Configuration Persistence
```bash
pytest tests/test_config_system.py::TestConfigPersistence -v
```

### Example 4: Test File Copy Workflow
```bash
pytest tests/test_e2e_workflows.py::TestFileCopyWorkflow -v
```

## ✅ Test Status

All tests have been verified and are passing:
- ✅ 55 tests in test_production_ready.py
- ✅ 40+ tests in test_e2e_workflows.py
- ✅ 45+ tests in test_menu_system.py
- ✅ 50+ tests in test_config_system.py

**Total: 190+ production-ready tests**

## 🔧 Fixtures Available

### From conftest.py
- `temp_workspace` - Clean temporary directory
- `sample_files` - Various file types
- `sample_directory_structure` - Nested directories
- `large_file` - 10MB test file
- `hidden_files` - Hidden file scenarios
- `mock_file_panel` - Mocked FilePanel
- `fs_helper` - FileSystemHelper utilities
- `performance_timer` - Performance measurement

### From fixtures.py
- `test_file` - Single test file
- `test_files` - Multiple test files
- `test_directory` - Directory with files
- `nested_structure` - Nested directories
- `file_items` - FileItem objects
- `files_with_extensions` - Various file types
- `security_test_filenames` - Unsafe filenames
- `performance_files` - Performance test files

## 🐛 Common Issues

### Issue: Tests failing due to file permissions
**Solution**: Run with appropriate permissions or use temp directories

### Issue: Tests hanging on Windows
**Solution**: Use `pytest -n auto` for parallel execution or run individual test files

### Issue: Import errors
**Solution**: Ensure you're in project root directory and all dependencies are installed

```bash
cd "C:\Users\david\Documents\FSU23D\Egna Projekt\DC Commander"
pip install -r requirements.txt
pytest tests/ -v
```

## 📚 Additional Resources

- See `TEST_SUITE_SUMMARY.md` for comprehensive test documentation
- See `conftest.py` for fixture details
- See `pytest.ini` for pytest configuration

## 💡 Tips

1. **Run tests frequently** during development
2. **Use `-v` flag** for verbose output
3. **Use `-x` flag** to stop on first failure
4. **Use `--lf` flag** to run last failed tests
5. **Use `-k` flag** to run tests matching pattern

```bash
# Run all tests with "menu" in name
pytest tests/ -k "menu" -v

# Run all tests with "config" in name
pytest tests/ -k "config" -v
```

## 📞 Support

For issues or questions about the test suite, refer to:
- TEST_SUITE_SUMMARY.md - Comprehensive documentation
- Project README.md - General project information
- pytest documentation - https://docs.pytest.org/
