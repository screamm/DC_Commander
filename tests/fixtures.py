"""Additional test fixtures for DC Commander test suite.

Provides specialized fixtures for different test scenarios:
- File and directory structures
- Security testing scenarios
- Mock objects and data generators
"""

import pytest
from pathlib import Path
from datetime import datetime
from models.file_item import FileItem


@pytest.fixture
def test_file(tmp_path):
    """Create a single test file."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Test file content")
    return file_path


@pytest.fixture
def test_files(tmp_path):
    """Create multiple test files."""
    files = []
    for i in range(3):
        file_path = tmp_path / f"file{i}.txt"
        file_path.write_text(f"Content of file {i}")
        files.append(file_path)
    return files


@pytest.fixture
def test_directory(tmp_path):
    """Create a test directory with files."""
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    (dir_path / "subfile1.txt").write_text("Subfile 1")
    (dir_path / "subfile2.txt").write_text("Subfile 2")
    return dir_path


@pytest.fixture
def nested_structure(tmp_path):
    """Create a nested directory structure."""
    root = tmp_path / "nested"
    root.mkdir()

    # Create levels
    level1 = root / "level1"
    level1.mkdir()
    (level1 / "file1.txt").write_text("Level 1 file")

    level2 = level1 / "level2"
    level2.mkdir()
    (level2 / "file2.txt").write_text("Level 2 file")

    level3 = level2 / "level3"
    level3.mkdir()
    (level3 / "file3.txt").write_text("Level 3 file")

    return root


@pytest.fixture
def temp_dir(tmp_path):
    """Alias for tmp_path for backwards compatibility."""
    return tmp_path


@pytest.fixture
def file_items(tmp_path):
    """Create FileItem objects for testing."""
    items = []

    # Create parent entry
    items.append(FileItem(
        name="..",
        path=tmp_path.parent,
        size=0,
        modified=datetime.now(),
        is_dir=True,
        is_parent=True
    ))

    # Create file entries
    for i in range(3):
        file_path = tmp_path / f"file{i}.txt"
        file_path.write_text(f"Content {i}")

        items.append(FileItem(
            name=f"file{i}.txt",
            path=file_path,
            size=len(f"Content {i}"),
            modified=datetime.fromtimestamp(file_path.stat().st_mtime),
            is_dir=False,
            is_parent=False
        ))

    # Create directory entry
    dir_path = tmp_path / "subdir"
    dir_path.mkdir()

    items.append(FileItem(
        name="subdir",
        path=dir_path,
        size=0,
        modified=datetime.fromtimestamp(dir_path.stat().st_mtime),
        is_dir=True,
        is_parent=False
    ))

    return items


@pytest.fixture
def binary_file(tmp_path):
    """Create a binary test file."""
    file_path = tmp_path / "binary.bin"
    file_path.write_bytes(bytes(range(256)))
    return file_path


@pytest.fixture
def large_text_file(tmp_path):
    """Create a large text file for testing."""
    file_path = tmp_path / "large.txt"
    content = "Line of text\n" * 10000  # ~120KB
    file_path.write_text(content)
    return file_path


@pytest.fixture
def files_with_extensions(tmp_path):
    """Create files with various extensions."""
    files = {}

    extensions = ['.txt', '.py', '.md', '.json', '.csv']
    for ext in extensions:
        file_path = tmp_path / f"file{ext}"
        file_path.write_text(f"Content for {ext} file")
        files[ext] = file_path

    return files


@pytest.fixture
def empty_directory(tmp_path):
    """Create an empty directory."""
    dir_path = tmp_path / "empty"
    dir_path.mkdir()
    return dir_path


@pytest.fixture
def readonly_file(tmp_path):
    """Create a read-only file."""
    file_path = tmp_path / "readonly.txt"
    file_path.write_text("Read-only content")

    # Make read-only
    import os
    import stat
    current_permissions = os.stat(file_path).st_mode
    os.chmod(file_path, current_permissions & ~stat.S_IWRITE)

    yield file_path

    # Restore permissions for cleanup
    try:
        os.chmod(file_path, current_permissions)
    except:
        pass


@pytest.fixture
def special_chars_files(tmp_path):
    """Create files with special characters in names."""
    files = []

    # Space in name
    f1 = tmp_path / "file with spaces.txt"
    f1.write_text("content")
    files.append(f1)

    # Dash and underscore
    f2 = tmp_path / "file-name_test.txt"
    f2.write_text("content")
    files.append(f2)

    # Numbers
    f3 = tmp_path / "file123.txt"
    f3.write_text("content")
    files.append(f3)

    return files


@pytest.fixture
def symlink_file(tmp_path):
    """Create a symbolic link."""
    target = tmp_path / "target.txt"
    target.write_text("Target content")

    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
        return {"target": target, "link": link}
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this system")


@pytest.fixture
def mock_file_items():
    """Create mock FileItem objects without filesystem."""
    items = []

    # Parent
    items.append(FileItem(
        name="..",
        path=Path("/parent"),
        size=0,
        modified=datetime(2024, 1, 1, 12, 0),
        is_dir=True,
        is_parent=True
    ))

    # Files
    for i in range(5):
        items.append(FileItem(
            name=f"file{i}.txt",
            path=Path(f"/test/file{i}.txt"),
            size=1000 * (i + 1),
            modified=datetime(2024, 1, i + 1, 12, 0),
            is_dir=False,
            is_parent=False
        ))

    # Directory
    items.append(FileItem(
        name="subdir",
        path=Path("/test/subdir"),
        size=0,
        modified=datetime(2024, 1, 10, 12, 0),
        is_dir=True,
        is_parent=False
    ))

    return items


@pytest.fixture
def security_test_filenames():
    """Provide dangerous/unsafe filenames for security testing."""
    return {
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "./../sensitive.txt",
        ],
        "null_bytes": [
            "file\x00.txt",
            "test\x00\x00file.txt",
        ],
        "dangerous_chars": [
            "file<>:.txt",
            "file|?*.txt",
            'file"name.txt',
        ],
        "windows_reserved": [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "LPT1",
        ],
        "control_chars": [
            "file\x01\x02.txt",
            "test\x1fname.txt",
        ],
    }


@pytest.fixture
def archive_bomb_scenarios():
    """Provide archive bomb test scenarios."""
    return [
        {
            "name": "high_compression_ratio",
            "compressed": 1000,
            "uncompressed": 500_000_000,  # 500,000:1
            "file_count": 10,
        },
        {
            "name": "excessive_size",
            "compressed": 1_000_000,
            "uncompressed": 2_000_000_000,  # 2GB
            "file_count": 10,
        },
        {
            "name": "excessive_files",
            "compressed": 1000,
            "uncompressed": 50_000,
            "file_count": 50_000,
        },
        {
            "name": "42zip_simulation",
            "compressed": 42_000,
            "uncompressed": 4_500_000_000_000_000,  # 4.5PB
            "file_count": 1,
        },
    ]


@pytest.fixture
def performance_files(tmp_path):
    """Create files for performance testing."""
    perf_dir = tmp_path / "performance"
    perf_dir.mkdir()

    # Create many small files
    for i in range(100):
        (perf_dir / f"small{i}.txt").write_text(f"Small file {i}")

    # Create few large files
    for i in range(5):
        (perf_dir / f"large{i}.bin").write_bytes(b'0' * 1024 * 1024)  # 1MB each

    return perf_dir


@pytest.fixture
def mixed_content_directory(tmp_path):
    """Create directory with mixed content types."""
    mixed_dir = tmp_path / "mixed"
    mixed_dir.mkdir()

    # Text files
    (mixed_dir / "readme.txt").write_text("Readme content")
    (mixed_dir / "notes.txt").write_text("Notes content")

    # Code files
    (mixed_dir / "script.py").write_text("# Python script\nprint('Hello')")
    (mixed_dir / "config.json").write_text('{"key": "value"}')

    # Binary files
    (mixed_dir / "data.bin").write_bytes(b'\x00\x01\x02\x03')
    (mixed_dir / "image.dat").write_bytes(b'\xFF\xD8\xFF\xE0')  # JPEG header

    # Subdirectories
    (mixed_dir / "subdir1").mkdir()
    (mixed_dir / "subdir2").mkdir()
    (mixed_dir / "subdir1" / "nested.txt").write_text("Nested file")

    # Hidden files
    (mixed_dir / ".hidden").write_text("Hidden content")

    # Empty file
    (mixed_dir / "empty.txt").touch()

    return mixed_dir
