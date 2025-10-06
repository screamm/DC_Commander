# Modern Commander Test Suite

Comprehensive testing framework for Modern Commander with >90% code coverage target.

## Test Organization

### Test Files

- **test_file_operations.py**: File operation tests (copy, move, delete, create directories, size formatting)
- **test_file_scanner.py**: Directory scanning, filtering, sorting, and search functionality
- **test_archive_handler.py**: Archive operations (ZIP, TAR, TAR.GZ, extraction, creation)
- **test_ui_components.py**: UI component tests (FilePanel, CommandBar, StatusBar, Dialogs)
- **test_integration.py**: End-to-end integration tests and complete user workflows

### Configuration Files

- **pytest.ini**: Pytest configuration with coverage targets and test discovery
- **conftest.py**: Shared fixtures and test utilities
- **.coveragerc**: Coverage reporting configuration

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_file_operations.py

# Run specific test class
pytest tests/test_file_operations.py::TestCopyFile

# Run specific test
pytest tests/test_file_operations.py::TestCopyFile::test_copy_file_success
```

### Coverage Reporting

```bash
# Run tests with coverage
pytest --cov=src --cov=components --cov=features

# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser

# Coverage with missing lines
pytest --cov=src --cov-report=term-missing
```

### Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only UI tests
pytest -m ui

# Skip slow tests
pytest -m "not slow"
```

### Parallel Execution

```bash
# Run tests in parallel (auto-detect CPU cores)
pytest -n auto

# Run tests with specific worker count
pytest -n 4
```

## Test Coverage

### Current Coverage Targets

- **Overall**: >90%
- **Core modules**: >95%
- **UI components**: >85%
- **Integration**: >80%

### Coverage by Module

| Module | Target | Description |
|--------|--------|-------------|
| src/core/file_operations.py | 95% | File and directory operations |
| src/core/file_scanner.py | 95% | Directory scanning and filtering |
| src/core/archive_handler.py | 95% | Archive operations |
| components/file_panel.py | 85% | File panel UI component |
| components/command_bar.py | 85% | Command bar UI component |

## Test Fixtures

### Common Fixtures (conftest.py)

- **temp_workspace**: Clean temporary directory for tests
- **sample_files**: Collection of sample files (text, binary, JSON, etc.)
- **sample_directory_structure**: Complex nested directory structure
- **large_file**: 10MB test file for performance testing
- **hidden_files**: Hidden files and directories
- **mock_file_panel**: Mock FilePanel for testing
- **mock_command_bar**: Mock CommandBar for testing
- **fs_helper**: FileSystemHelper utility class
- **mock_data**: MockDataGenerator for test data
- **performance_timer**: Simple performance measurement
- **assertions**: Custom assertion helpers

## Writing Tests

### Test Structure

```python
import pytest
from pathlib import Path

class TestFeature:
    """Test feature description."""

    def test_basic_functionality(self, temp_workspace):
        """Test basic feature works."""
        # Arrange
        test_file = temp_workspace / "test.txt"
        test_file.write_text("content")

        # Act
        result = process_file(test_file)

        # Assert
        assert result is True
        assert test_file.exists()

    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(FileNotFoundError):
            process_nonexistent_file()
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input_value,expected", [
    (0, "0 B"),
    (1024, "1.0 KB"),
    (1048576, "1.0 MB"),
])
def test_format_size(input_value, expected):
    """Test size formatting with various values."""
    result = format_size(input_value)
    assert result == expected
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation(self):
    """Test asynchronous operation."""
    result = await async_function()
    assert result is not None
```

## Best Practices

### Test Naming

- Use descriptive test names: `test_copy_file_with_overwrite`
- Follow pattern: `test_<feature>_<scenario>`
- Use docstrings to explain complex tests

### Test Organization

- Group related tests in classes
- Use fixtures for common setup
- Keep tests independent and isolated
- Clean up resources after tests

### Edge Cases

Always test:
- Empty inputs
- Null/None values
- Boundary conditions (0, max values)
- Permission errors
- Non-existent paths
- Invalid inputs
- Large datasets

### Assertions

- Use specific assertions: `assert x == y` not `assert x`
- Test one thing per test
- Use pytest's assertion introspection
- Add meaningful assertion messages

## Performance Testing

### Performance Markers

```python
@pytest.mark.slow
def test_large_directory_scan(self):
    """Test scanning directory with 1000+ files."""
    # Create large directory
    # Run scan
    # Assert performance
```

### Performance Fixtures

```python
def test_with_timer(performance_timer):
    """Test with performance measurement."""
    with performance_timer() as timer:
        # Code to measure
        process_large_data()

    assert timer.elapsed < 1.0  # Under 1 second
```

## Continuous Integration

### CI Configuration

Tests run automatically on:
- Every commit
- Pull requests
- Pre-merge validation

### CI Requirements

- All tests must pass
- Coverage must be >90%
- No failing quality gates
- No new warnings

## Troubleshooting

### Common Issues

**Tests fail with "Permission denied"**
- Check file permissions in temp directories
- Ensure cleanup happens after tests

**Coverage not reaching target**
- Review uncovered lines in report
- Add tests for edge cases
- Check if code is reachable

**Slow test execution**
- Use `pytest -n auto` for parallel execution
- Mark slow tests with `@pytest.mark.slow`
- Optimize fixture creation

**Import errors**
- Ensure PYTHONPATH includes project root
- Check virtual environment activation
- Verify dependencies installed

## Test Maintenance

### Regular Tasks

- Review and update test coverage
- Remove obsolete tests
- Update fixtures for new features
- Refactor duplicated test code
- Update documentation

### Quality Metrics

Track:
- Test count trend
- Coverage percentage
- Test execution time
- Flaky test occurrences
- New test additions

## Resources

### Pytest Documentation
- [Pytest Official Docs](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Parametrize](https://docs.pytest.org/en/stable/parametrize.html)

### Coverage Documentation
- [Coverage.py](https://coverage.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

### Best Practices
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [Test-Driven Development](https://testdriven.io/)
