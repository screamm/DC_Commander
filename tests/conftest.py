"""
Shared test fixtures and configuration for Modern Commander tests.

This module provides:
- Common test fixtures
- Shared mock objects
- Test utilities
- Pytest configuration hooks
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict
from unittest.mock import Mock, MagicMock


# Pytest Hooks
def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers",
        "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests for complete workflows"
    )
    config.addinivalue_line(
        "markers",
        "slow: Tests that take significant time to run"
    )
    config.addinivalue_line(
        "markers",
        "ui: UI component tests using Textual"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Auto-mark UI tests
        if "ui_components" in str(item.fspath):
            item.add_marker(pytest.mark.ui)

        # Auto-mark slow tests
        if "performance" in item.name.lower() or "large" in item.name.lower():
            item.add_marker(pytest.mark.slow)


# Common Fixtures
@pytest.fixture
def temp_workspace(tmp_path):
    """
    Provide clean temporary workspace for tests.

    Yields:
        Path: Temporary directory path that's cleaned up after test
    """
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    yield workspace
    # Cleanup handled by tmp_path


@pytest.fixture
def sample_files(temp_workspace):
    """
    Create sample files for testing.

    Returns:
        Dict[str, Path]: Dictionary mapping file types to paths
    """
    files = {}

    # Text files
    files['text'] = temp_workspace / "sample.txt"
    files['text'].write_text("Sample text content", encoding="utf-8")

    files['python'] = temp_workspace / "script.py"
    files['python'].write_text("# Python script\nprint('Hello')", encoding="utf-8")

    files['json'] = temp_workspace / "data.json"
    files['json'].write_text('{"key": "value", "number": 42}', encoding="utf-8")

    files['markdown'] = temp_workspace / "readme.md"
    files['markdown'].write_text("# README\n\nProject documentation", encoding="utf-8")

    # Binary file
    files['binary'] = temp_workspace / "data.bin"
    files['binary'].write_bytes(b'\x00\x01\x02\x03\x04\x05')

    # Empty file
    files['empty'] = temp_workspace / "empty.txt"
    files['empty'].touch()

    return files


@pytest.fixture
def sample_directory_structure(temp_workspace):
    """
    Create complex directory structure for testing.

    Returns:
        Path: Root of directory structure
    """
    root = temp_workspace / "structure"
    root.mkdir()

    # Create subdirectories
    (root / "level1").mkdir()
    (root / "level1" / "level2").mkdir()
    (root / "level1" / "level2" / "level3").mkdir()

    (root / "documents").mkdir()
    (root / "code").mkdir()
    (root / "data").mkdir()

    # Create files in structure
    (root / "root_file.txt").write_text("Root level")
    (root / "level1" / "file1.txt").write_text("Level 1 file")
    (root / "level1" / "level2" / "file2.txt").write_text("Level 2 file")
    (root / "level1" / "level2" / "level3" / "deep.txt").write_text("Deep file")

    (root / "documents" / "doc1.txt").write_text("Document 1")
    (root / "documents" / "doc2.md").write_text("# Document 2")

    (root / "code" / "main.py").write_text("# Main script")
    (root / "code" / "utils.py").write_text("# Utilities")

    (root / "data" / "data.json").write_text('{"test": "data"}')
    (root / "data" / "data.csv").write_text("col1,col2\nval1,val2")

    return root


@pytest.fixture
def large_file(temp_workspace):
    """
    Create large file for testing.

    Returns:
        Path: Path to large file (10MB)
    """
    large = temp_workspace / "large.bin"

    # Create 10MB file
    chunk_size = 1024 * 1024  # 1MB
    with open(large, 'wb') as f:
        for _ in range(10):
            f.write(b'0' * chunk_size)

    return large


@pytest.fixture
def hidden_files(temp_workspace):
    """
    Create hidden files for testing.

    Returns:
        List[Path]: List of hidden file paths
    """
    hidden = []

    # Hidden files (starting with .)
    h1 = temp_workspace / ".hidden"
    h1.write_text("Hidden content")
    hidden.append(h1)

    h2 = temp_workspace / ".config"
    h2.write_text("Config data")
    hidden.append(h2)

    # Hidden directory
    h_dir = temp_workspace / ".hidden_dir"
    h_dir.mkdir()
    (h_dir / "file.txt").write_text("File in hidden dir")
    hidden.append(h_dir)

    return hidden


@pytest.fixture
def mock_file_panel():
    """
    Provide mock FilePanel for testing.

    Returns:
        Mock: Configured FilePanel mock
    """
    panel = Mock()
    panel.current_path = Path.cwd()
    panel.selected_files = set()
    panel._file_items = []

    # Mock methods
    panel.navigate_to = Mock()
    panel.navigate_up = Mock()
    panel.refresh_directory = Mock()
    panel.toggle_selection = Mock()
    panel.clear_selection = Mock()

    return panel


@pytest.fixture
def mock_command_bar():
    """
    Provide mock CommandBar for testing.

    Returns:
        Mock: Configured CommandBar mock
    """
    from components.command_bar import Command

    bar = Mock()
    bar.commands = {
        'f1': Command('F1', 'Help', 'show_help'),
        'f5': Command('F5', 'Copy', 'copy_files'),
        'f8': Command('F8', 'Delete', 'delete_files'),
    }

    # Mock methods
    bar.update_command = Mock()
    bar.set_context = Mock()
    bar.enable_command = Mock()
    bar.disable_command = Mock()

    return bar


# Test Utilities
class FileSystemHelper:
    """Helper class for file system test operations."""

    @staticmethod
    def create_test_files(directory: Path, count: int, prefix: str = "test") -> List[Path]:
        """
        Create multiple test files.

        Args:
            directory: Directory to create files in
            count: Number of files to create
            prefix: Filename prefix

        Returns:
            List of created file paths
        """
        files = []
        for i in range(count):
            file_path = directory / f"{prefix}_{i}.txt"
            file_path.write_text(f"Test file {i}")
            files.append(file_path)
        return files

    @staticmethod
    def create_nested_structure(root: Path, depth: int, files_per_level: int = 2) -> Path:
        """
        Create nested directory structure.

        Args:
            root: Root directory
            depth: Depth of nesting
            files_per_level: Number of files per directory

        Returns:
            Root path
        """
        current = root
        for level in range(depth):
            # Create directory
            current = current / f"level{level}"
            current.mkdir(parents=True, exist_ok=True)

            # Create files
            for i in range(files_per_level):
                (current / f"file{i}.txt").write_text(f"Level {level}, File {i}")

        return root

    @staticmethod
    def get_file_count(directory: Path, recursive: bool = False) -> int:
        """
        Count files in directory.

        Args:
            directory: Directory to count files in
            recursive: Count recursively

        Returns:
            Number of files
        """
        if recursive:
            return sum(1 for _ in directory.rglob('*') if _.is_file())
        else:
            return sum(1 for _ in directory.iterdir() if _.is_file())

    @staticmethod
    def create_files_with_extensions(
        directory: Path,
        extensions: List[str],
        count_per_ext: int = 2
    ) -> Dict[str, List[Path]]:
        """
        Create files with specific extensions.

        Args:
            directory: Directory to create files in
            extensions: List of extensions (e.g., ['.txt', '.py'])
            count_per_ext: Files to create per extension

        Returns:
            Dictionary mapping extension to file paths
        """
        files_by_ext = {}

        for ext in extensions:
            files = []
            for i in range(count_per_ext):
                file_path = directory / f"file{i}{ext}"
                file_path.write_text(f"Content for {ext} file {i}")
                files.append(file_path)
            files_by_ext[ext] = files

        return files_by_ext


@pytest.fixture
def fs_helper():
    """Provide FileSystemHelper instance."""
    return FileSystemHelper()


# Mock Data Generators
class MockDataGenerator:
    """Generate mock data for testing."""

    @staticmethod
    def generate_file_entries(count: int, base_path: Path) -> List:
        """
        Generate mock FileEntry objects.

        Args:
            count: Number of entries to generate
            base_path: Base directory path

        Returns:
            List of mock FileEntry objects
        """
        from src.core.file_scanner import FileEntry

        entries = []
        for i in range(count):
            path = base_path / f"file{i}.txt"
            path.touch()
            entries.append(FileEntry(path))

        return entries

    @staticmethod
    def generate_archive_entries(count: int) -> List:
        """
        Generate mock ArchiveEntry objects.

        Args:
            count: Number of entries to generate

        Returns:
            List of mock ArchiveEntry objects
        """
        from src.core.archive_handler import ArchiveEntry

        entries = []
        for i in range(count):
            entry = ArchiveEntry(
                name=f"file{i}.txt",
                size=1000 + i * 100,
                compressed_size=500 + i * 50,
                is_directory=False,
                modified=datetime.now()
            )
            entries.append(entry)

        return entries


@pytest.fixture
def mock_data():
    """Provide MockDataGenerator instance."""
    return MockDataGenerator()


# Performance Testing Utilities
@pytest.fixture
def performance_timer():
    """
    Provide simple performance timer.

    Usage:
        with performance_timer() as timer:
            # code to time
        assert timer.elapsed < 1.0  # Assert under 1 second
    """
    import time
    from contextlib import contextmanager

    @contextmanager
    def timer():
        class Timer:
            def __init__(self):
                self.start = time.time()
                self.elapsed = 0

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.elapsed = time.time() - self.start

        t = Timer()
        yield t

    return timer


# Cleanup Utilities
@pytest.fixture(autouse=True)
def cleanup_temp_files(request):
    """Auto-cleanup temporary files after each test."""
    temp_files = []

    def register_temp(path: Path):
        """Register path for cleanup."""
        temp_files.append(path)

    request.node.register_temp = register_temp

    yield

    # Cleanup
    for path in temp_files:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


# Test Assertions
class CustomAssertions:
    """Custom assertion helpers for tests."""

    @staticmethod
    def assert_file_contents_equal(file1: Path, file2: Path):
        """Assert two files have identical contents."""
        assert file1.exists(), f"File does not exist: {file1}"
        assert file2.exists(), f"File does not exist: {file2}"

        content1 = file1.read_bytes()
        content2 = file2.read_bytes()

        assert content1 == content2, f"File contents differ: {file1} != {file2}"

    @staticmethod
    def assert_directory_structure_equal(dir1: Path, dir2: Path):
        """Assert two directories have identical structure."""
        files1 = sorted([p.relative_to(dir1) for p in dir1.rglob('*')])
        files2 = sorted([p.relative_to(dir2) for p in dir2.rglob('*')])

        assert files1 == files2, f"Directory structures differ: {dir1} != {dir2}"


@pytest.fixture
def assertions():
    """Provide CustomAssertions instance."""
    return CustomAssertions()
