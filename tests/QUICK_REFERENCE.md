# Testing Quick Reference Card

## Quick Commands

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=src --cov=components --cov-report=html
```

### Fast Parallel Execution
```bash
pytest -n auto
```

### Specific Test Categories
```bash
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m "not slow"        # Skip slow tests
pytest -m ui                # UI component tests only
```

### Specific Test Files
```bash
pytest tests/test_file_operations.py
pytest tests/test_file_scanner.py
pytest tests/test_archive_handler.py
pytest tests/test_ui_components.py
pytest tests/test_integration.py
```

### Specific Test Classes/Functions
```bash
pytest tests/test_file_operations.py::TestCopyFile
pytest tests/test_file_operations.py::TestCopyFile::test_copy_file_success
```

### Verbose Output
```bash
pytest -v                   # Verbose
pytest -vv                  # Extra verbose
pytest -s                   # Show print statements
```

### Coverage Reports
```bash
pytest --cov=src --cov-report=term-missing     # Terminal with missing lines
pytest --cov=src --cov-report=html             # HTML report (htmlcov/index.html)
pytest --cov=src --cov-report=xml              # XML report (coverage.xml)
```

### Failed Tests
```bash
pytest --lf                 # Run last failed tests
pytest --ff                 # Run failed first, then others
pytest -x                   # Stop on first failure
pytest --maxfail=2          # Stop after N failures
```

### Test Selection
```bash
pytest -k "copy"            # Run tests matching "copy"
pytest -k "not integration" # Exclude integration tests
pytest tests/ -v --collect-only  # List all tests without running
```

## Common Workflows

### Development Cycle
```bash
# 1. Run affected tests quickly
pytest tests/test_file_operations.py -v

# 2. Full test suite with coverage
pytest --cov=src --cov-report=term-missing

# 3. Generate HTML report for review
pytest --cov=src --cov-report=html
# Open htmlcov/index.html
```

### Pre-commit Check
```bash
# Run all tests with coverage threshold
pytest --cov=src --cov-fail-under=90 -n auto
```

### Debug Failing Test
```bash
# Run with detailed output and stop on failure
pytest tests/test_file_operations.py::TestCopyFile::test_copy_file_success -vv -s -x
```

### Performance Testing
```bash
# Run performance tests only
pytest -m performance -v

# Run all tests except slow ones
pytest -m "not slow" -n auto
```

## Fixtures Available

### File System Fixtures
- `temp_workspace` - Clean temporary directory
- `sample_files` - Collection of test files
- `sample_directory_structure` - Nested directory tree
- `large_file` - 10MB test file
- `hidden_files` - Hidden files/directories

### Mock Fixtures
- `mock_file_panel` - Mock FilePanel component
- `mock_command_bar` - Mock CommandBar component

### Utility Fixtures
- `fs_helper` - FileSystemHelper utilities
- `mock_data` - Test data generators
- `performance_timer` - Performance measurement
- `assertions` - Custom assertions

## Coverage Targets

| Module | Target |
|--------|--------|
| file_operations.py | 95% |
| file_scanner.py | 95% |
| archive_handler.py | 95% |
| file_panel.py | 85% |
| command_bar.py | 85% |
| **Overall** | **90%** |

## Test Markers

```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.slow          # Slow/performance test
@pytest.mark.ui            # UI component test
```

## Troubleshooting

### Import Errors
```bash
# Ensure in project root
cd "C:\Users\david\Documents\FSU23D\Egna Projekt\DC Commander"

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-xdist pytest-asyncio
```

### Permission Errors
```bash
# Clean up temp files
pytest --cache-clear
```

### Coverage Not Found
```bash
# Install coverage tools
pip install coverage pytest-cov
```

### Slow Tests
```bash
# Use parallel execution
pytest -n auto

# Skip slow tests
pytest -m "not slow"
```

## Quick Test Writing Template

```python
import pytest
from pathlib import Path

class TestFeature:
    """Test feature description."""

    def test_basic_case(self, temp_workspace):
        """Test basic functionality."""
        # Arrange
        test_file = temp_workspace / "test.txt"
        test_file.write_text("content")

        # Act
        result = your_function(test_file)

        # Assert
        assert result is True
        assert test_file.exists()

    def test_error_case(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            your_function(None)

    @pytest.mark.parametrize("input,expected", [
        (0, "0 B"),
        (1024, "1.0 KB"),
    ])
    def test_multiple_cases(self, input, expected):
        """Test with multiple inputs."""
        assert format_size(input) == expected
```

## File Locations

```
tests/
├── __init__.py                  # Package initialization
├── conftest.py                  # Shared fixtures
├── test_file_operations.py      # File operation tests
├── test_file_scanner.py         # Scanner tests
├── test_archive_handler.py      # Archive tests
├── test_ui_components.py        # UI tests
├── test_integration.py          # Integration tests
├── README.md                    # Full documentation
└── QUICK_REFERENCE.md           # This file

Configuration:
├── pytest.ini                   # Pytest config
└── .coveragerc                  # Coverage config

Reports:
├── htmlcov/                     # HTML coverage reports
├── coverage.xml                 # XML coverage
└── .coverage                    # Coverage database
```

## CI/CD Integration

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    pip install pytest pytest-cov pytest-xdist
    pytest --cov=src --cov-report=xml --cov-fail-under=90 -n auto
```

## Performance Benchmarks

- Total tests: 196+
- Execution time: ~30s (parallel)
- Coverage generation: +5s
- Target: All tests < 60s total

---

**Last Updated**: 2025-10-05
**Version**: 1.0.0
