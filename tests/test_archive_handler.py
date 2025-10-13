"""
Comprehensive unit tests for archive handler module.

Tests cover:
- Archive type detection (ZIP, TAR, TAR.GZ, etc.)
- Archive listing (contents, metadata)
- Archive extraction (full, partial, overwrite)
- Archive creation (various formats, compression)
- Archive information retrieval
"""

import pytest
from pathlib import Path
from datetime import datetime
import zipfile
import tarfile

from src.core.archive_handler import (
    is_archive,
    get_archive_type,
    list_archive_contents,
    extract_archive,
    create_archive,
    get_archive_info,
    ArchiveEntry,
    ArchiveType,
    ArchiveError,
    UnsupportedArchiveError,
)


# Test Fixtures
@pytest.fixture
def test_files(tmp_path):
    """Create test files for archiving."""
    base = tmp_path / "test_files"
    base.mkdir()

    (base / "file1.txt").write_text("Content of file 1")
    (base / "file2.txt").write_text("Content of file 2")
    (base / "data.json").write_text('{"key": "value"}')

    sub = base / "subdir"
    sub.mkdir()
    (sub / "nested.txt").write_text("Nested content")

    return base


@pytest.fixture
def zip_archive(tmp_path, test_files):
    """Create a ZIP archive for testing."""
    archive_path = tmp_path / "test.zip"

    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in test_files.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(test_files)
                zf.write(file, arcname)

    return archive_path


@pytest.fixture
def tar_archive(tmp_path, test_files):
    """Create a TAR archive for testing."""
    archive_path = tmp_path / "test.tar"

    with tarfile.open(archive_path, 'w') as tf:
        for file in test_files.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(test_files)
                tf.add(file, arcname=str(arcname))

    return archive_path


@pytest.fixture
def tar_gz_archive(tmp_path, test_files):
    """Create a TAR.GZ archive for testing."""
    archive_path = tmp_path / "test.tar.gz"

    with tarfile.open(archive_path, 'w:gz') as tf:
        for file in test_files.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(test_files)
                tf.add(file, arcname=str(arcname))

    return archive_path


# ArchiveEntry Tests
class TestArchiveEntry:
    """Test ArchiveEntry class."""

    def test_archive_entry_creation(self):
        """Test archive entry creation."""
        entry = ArchiveEntry(
            name="test.txt",
            size=1000,
            compressed_size=500,
            is_directory=False,
            modified=datetime.now()
        )

        assert entry.name == "test.txt"
        assert entry.size == 1000
        assert entry.compressed_size == 500
        assert entry.is_directory is False

    def test_archive_entry_compression_ratio(self):
        """Test compression ratio calculation."""
        entry = ArchiveEntry(
            name="test.txt",
            size=1000,
            compressed_size=500,
            is_directory=False
        )

        # 50% compression
        assert entry.compression_ratio == 50.0

    def test_archive_entry_compression_ratio_zero_size(self):
        """Test compression ratio with zero size."""
        entry = ArchiveEntry(
            name="empty.txt",
            size=0,
            compressed_size=0,
            is_directory=False
        )

        assert entry.compression_ratio == 0.0

    def test_archive_entry_repr(self):
        """Test string representation."""
        file_entry = ArchiveEntry("test.txt", 100, 50, False)
        dir_entry = ArchiveEntry("folder", 0, 0, True)

        assert "FILE" in repr(file_entry)
        assert "DIR" in repr(dir_entry)
        assert "test.txt" in repr(file_entry)


# Archive Type Detection Tests
class TestArchiveTypeDetection:
    """Test archive type detection."""

    @pytest.mark.parametrize("filename,expected_type", [
        ("archive.zip", ArchiveType.ZIP),
        ("archive.tar", ArchiveType.TAR),
        ("archive.tar.gz", ArchiveType.TAR_GZ),
        ("archive.tgz", ArchiveType.TAR_GZ),
        ("archive.tar.bz2", ArchiveType.TAR_BZ2),
        ("archive.tbz2", ArchiveType.TAR_BZ2),
        ("archive.tar.xz", ArchiveType.TAR_XZ),
        ("archive.txt", ArchiveType.UNKNOWN),
        ("archive.rar", ArchiveType.UNKNOWN),
    ])
    def test_get_archive_type(self, tmp_path, filename, expected_type):
        """Test archive type detection from filename."""
        path = tmp_path / filename
        archive_type = get_archive_type(path)

        assert archive_type == expected_type

    def test_get_archive_type_case_insensitive(self, tmp_path):
        """Test archive type detection is case-insensitive."""
        assert get_archive_type(tmp_path / "ARCHIVE.ZIP") == ArchiveType.ZIP
        assert get_archive_type(tmp_path / "Archive.Tar.Gz") == ArchiveType.TAR_GZ

    def test_is_archive_supported(self, zip_archive, tar_archive):
        """Test is_archive for supported formats."""
        assert is_archive(zip_archive) is True
        assert is_archive(tar_archive) is True

    def test_is_archive_unsupported(self, tmp_path):
        """Test is_archive for unsupported formats."""
        text_file = tmp_path / "file.txt"
        text_file.write_text("Not an archive")

        assert is_archive(text_file) is False


# List Archive Contents Tests
class TestListArchiveContents:
    """Test listing archive contents."""

    def test_list_zip_contents(self, zip_archive):
        """Test listing ZIP archive contents."""
        entries = list_archive_contents(zip_archive)

        assert len(entries) > 0
        names = [e.name for e in entries]
        assert any("file1.txt" in name for name in names)
        assert any("file2.txt" in name for name in names)

    def test_list_tar_contents(self, tar_archive):
        """Test listing TAR archive contents."""
        entries = list_archive_contents(tar_archive)

        assert len(entries) > 0
        names = [e.name for e in entries]
        assert any("file1.txt" in name for name in names)

    def test_list_tar_gz_contents(self, tar_gz_archive):
        """Test listing TAR.GZ archive contents."""
        entries = list_archive_contents(tar_gz_archive)

        assert len(entries) > 0
        names = [e.name for e in entries]
        assert any("file1.txt" in name for name in names)

    def test_list_archive_entry_metadata(self, zip_archive):
        """Test archive entries have correct metadata."""
        entries = list_archive_contents(zip_archive)

        for entry in entries:
            assert isinstance(entry, ArchiveEntry)
            assert entry.name
            assert entry.size >= 0
            assert entry.compressed_size >= 0

    def test_list_archive_nonexistent(self, tmp_path):
        """Test listing nonexistent archive."""
        path = tmp_path / "nonexistent.zip"

        with pytest.raises(FileNotFoundError, match="not found"):
            list_archive_contents(path)

    def test_list_archive_unsupported(self, tmp_path):
        """Test listing unsupported archive format."""
        path = tmp_path / "file.rar"
        path.write_text("Not a real archive")

        with pytest.raises(UnsupportedArchiveError, match="Unsupported"):
            list_archive_contents(path)

    def test_list_archive_corrupted_zip(self, tmp_path):
        """Test listing corrupted ZIP archive."""
        path = tmp_path / "corrupted.zip"
        path.write_text("This is not a valid ZIP file")

        with pytest.raises(ArchiveError, match="Invalid ZIP"):
            list_archive_contents(path)


# Extract Archive Tests
class TestExtractArchive:
    """Test archive extraction."""

    def test_extract_zip_all(self, zip_archive, tmp_path):
        """Test extracting all files from ZIP."""
        dest = tmp_path / "extract_zip"

        result = extract_archive(zip_archive, dest)

        assert result is True
        assert dest.exists()
        assert (dest / "file1.txt").exists()
        assert (dest / "file2.txt").exists()
        assert (dest / "subdir" / "nested.txt").exists()

    def test_extract_tar_all(self, tar_archive, tmp_path):
        """Test extracting all files from TAR."""
        dest = tmp_path / "extract_tar"

        result = extract_archive(tar_archive, dest)

        assert result is True
        assert dest.exists()
        assert (dest / "file1.txt").exists()

    def test_extract_tar_gz_all(self, tar_gz_archive, tmp_path):
        """Test extracting all files from TAR.GZ."""
        dest = tmp_path / "extract_tar_gz"

        result = extract_archive(tar_gz_archive, dest)

        assert result is True
        assert dest.exists()

    def test_extract_specific_members_zip(self, zip_archive, tmp_path):
        """Test extracting specific files from ZIP."""
        dest = tmp_path / "extract_specific"

        result = extract_archive(
            zip_archive,
            dest,
            members=["file1.txt"]
        )

        assert result is True
        assert (dest / "file1.txt").exists()
        # file2.txt should not be extracted
        assert not (dest / "file2.txt").exists()

    def test_extract_specific_members_tar(self, tar_archive, tmp_path):
        """Test extracting specific files from TAR."""
        dest = tmp_path / "extract_specific"

        result = extract_archive(
            tar_archive,
            dest,
            members=["file1.txt"]
        )

        assert result is True
        assert (dest / "file1.txt").exists()

    def test_extract_overwrite_disabled(self, zip_archive, tmp_path):
        """Test extraction fails when destination exists without overwrite."""
        dest = tmp_path / "extract_exists"
        dest.mkdir()

        with pytest.raises(ArchiveError, match="already exists"):
            extract_archive(zip_archive, dest, overwrite=False)

    def test_extract_overwrite_enabled(self, zip_archive, tmp_path):
        """Test extraction with overwrite."""
        dest = tmp_path / "extract_overwrite"
        dest.mkdir()
        (dest / "old_file.txt").write_text("Old content")

        result = extract_archive(zip_archive, dest, overwrite=True)

        assert result is True
        assert (dest / "file1.txt").exists()

    def test_extract_creates_parent_directories(self, zip_archive, tmp_path):
        """Test extraction creates parent directories."""
        dest = tmp_path / "nested" / "deep" / "extract"

        result = extract_archive(zip_archive, dest)

        assert result is True
        assert dest.exists()

    def test_extract_nonexistent_archive(self, tmp_path):
        """Test extraction fails for nonexistent archive."""
        source = tmp_path / "nonexistent.zip"
        dest = tmp_path / "extract"

        with pytest.raises(FileNotFoundError, match="not found"):
            extract_archive(source, dest)

    def test_extract_unsupported_format(self, tmp_path):
        """Test extraction fails for unsupported format."""
        source = tmp_path / "file.rar"
        source.write_text("Not a real archive")
        dest = tmp_path / "extract"

        with pytest.raises(UnsupportedArchiveError, match="Unsupported"):
            extract_archive(source, dest)


# Create Archive Tests
class TestCreateArchive:
    """Test archive creation."""

    def test_create_zip_archive(self, test_files, tmp_path):
        """Test creating ZIP archive."""
        dest = tmp_path / "created.zip"
        files = list(test_files.rglob('*.txt'))

        result = create_archive(files, dest, ArchiveType.ZIP)

        assert result is True
        assert dest.exists()

        # Verify archive contents
        entries = list_archive_contents(dest)
        assert len(entries) > 0

    def test_create_tar_archive(self, test_files, tmp_path):
        """Test creating TAR archive."""
        dest = tmp_path / "created.tar"
        files = list(test_files.rglob('*.txt'))

        result = create_archive(files, dest, ArchiveType.TAR)

        assert result is True
        assert dest.exists()

    def test_create_tar_gz_archive(self, test_files, tmp_path):
        """Test creating TAR.GZ archive."""
        dest = tmp_path / "created.tar.gz"
        files = list(test_files.rglob('*.txt'))

        result = create_archive(files, dest, ArchiveType.TAR_GZ)

        assert result is True
        assert dest.exists()

    def test_create_archive_with_directory(self, test_files, tmp_path):
        """Test creating archive with directories."""
        dest = tmp_path / "created.zip"
        files = [test_files / "subdir"]

        result = create_archive(files, dest, ArchiveType.ZIP)

        assert result is True

        # Verify directory contents are included
        entries = list_archive_contents(dest)
        names = [e.name for e in entries]
        assert any("nested.txt" in name for name in names)

    def test_create_archive_compression_level(self, test_files, tmp_path):
        """Test creating archive with different compression levels."""
        files = [test_files / "file1.txt"]

        # Low compression
        low_comp = tmp_path / "low.zip"
        create_archive(files, low_comp, ArchiveType.ZIP, compression_level=1)

        # High compression
        high_comp = tmp_path / "high.zip"
        create_archive(files, high_comp, ArchiveType.ZIP, compression_level=9)

        # Both should exist
        assert low_comp.exists()
        assert high_comp.exists()

    def test_create_archive_base_dir(self, test_files, tmp_path):
        """Test creating archive with base directory."""
        dest = tmp_path / "created.zip"
        files = list(test_files.rglob('*.txt'))

        result = create_archive(
            files,
            dest,
            ArchiveType.ZIP,
            base_dir=test_files
        )

        assert result is True

        # Entries should have relative paths
        entries = list_archive_contents(dest)
        names = [e.name for e in entries]
        # Should not contain full path
        assert all(not name.startswith(str(test_files)) for name in names)

    def test_create_archive_empty_files(self, tmp_path):
        """Test creating archive fails with no files."""
        dest = tmp_path / "empty.zip"

        with pytest.raises(ArchiveError, match="No files"):
            create_archive([], dest, ArchiveType.ZIP)

    def test_create_archive_unsupported_format(self, test_files, tmp_path):
        """Test creating archive with unsupported format."""
        dest = tmp_path / "archive.rar"
        files = [test_files / "file1.txt"]

        with pytest.raises(UnsupportedArchiveError, match="Unsupported"):
            create_archive(files, dest, ArchiveType.UNKNOWN)

    def test_create_archive_creates_parent_directories(self, test_files, tmp_path):
        """Test archive creation creates parent directories."""
        dest = tmp_path / "nested" / "deep" / "archive.zip"
        files = [test_files / "file1.txt"]

        result = create_archive(files, dest, ArchiveType.ZIP)

        assert result is True
        assert dest.exists()

    def test_create_archive_compression_level_clamping(self, test_files, tmp_path):
        """Test compression level is clamped to valid range."""
        dest = tmp_path / "archive.zip"
        files = [test_files / "file1.txt"]

        # Invalid levels should be clamped to 6 (default)
        result = create_archive(files, dest, ArchiveType.ZIP, compression_level=99)
        assert result is True

        result = create_archive(files, dest, ArchiveType.ZIP, compression_level=-5)
        assert result is True


# Get Archive Info Tests
class TestGetArchiveInfo:
    """Test archive information retrieval."""

    def test_get_archive_info_zip(self, zip_archive):
        """Test getting ZIP archive info."""
        info = get_archive_info(zip_archive)

        assert info['type'] == 'zip'
        assert info['file_count'] > 0
        assert info['total_size'] > 0
        assert info['compressed_size'] >= 0
        assert 'compression_ratio' in info

    def test_get_archive_info_tar(self, tar_archive):
        """Test getting TAR archive info."""
        info = get_archive_info(tar_archive)

        assert info['type'] == 'tar'
        assert info['file_count'] > 0

    def test_get_archive_info_compression_ratio(self, zip_archive):
        """Test compression ratio calculation in info."""
        info = get_archive_info(zip_archive)

        # ZIP compression ratio should be in valid range
        # Note: Small files may have 0% compression due to ZIP overhead
        assert info['compression_ratio'] >= 0
        assert info['compression_ratio'] <= 100

    def test_get_archive_info_directory_count(self, zip_archive):
        """Test directory counting in archive info."""
        info = get_archive_info(zip_archive)

        # Should count directories if present
        assert 'directory_count' in info
        assert info['directory_count'] >= 0


# Integration Tests
class TestArchiveHandlerIntegration:
    """Integration tests for archive operations."""

    def test_create_extract_workflow(self, test_files, tmp_path):
        """Test complete create and extract workflow."""
        # Create archive
        archive_path = tmp_path / "workflow.zip"
        files = list(test_files.rglob('*.txt'))

        create_archive(files, archive_path, ArchiveType.ZIP)
        assert archive_path.exists()

        # List contents
        entries = list_archive_contents(archive_path)
        assert len(entries) > 0

        # Extract
        extract_dir = tmp_path / "extracted"
        extract_archive(archive_path, extract_dir)

        # Verify extracted files
        assert (extract_dir / "file1.txt").exists()
        assert (extract_dir / "file2.txt").exists()

    def test_multiple_format_workflow(self, test_files, tmp_path):
        """Test creating and extracting multiple archive formats."""
        files = [test_files / "file1.txt"]

        formats = [
            (ArchiveType.ZIP, "test.zip"),
            (ArchiveType.TAR, "test.tar"),
            (ArchiveType.TAR_GZ, "test.tar.gz"),
        ]

        for archive_type, filename in formats:
            # Create
            archive_path = tmp_path / filename
            create_archive(files, archive_path, archive_type)
            assert archive_path.exists()

            # Extract
            extract_dir = tmp_path / f"extracted_{archive_type.value}"
            extract_archive(archive_path, extract_dir)
            assert (extract_dir / "file1.txt").exists()

    def test_archive_info_after_creation(self, test_files, tmp_path):
        """Test getting archive info after creation."""
        archive_path = tmp_path / "info_test.zip"
        files = list(test_files.rglob('*.txt'))

        # Create archive
        create_archive(files, archive_path, ArchiveType.ZIP, base_dir=test_files)

        # Get info
        info = get_archive_info(archive_path)

        assert info['file_count'] == len(files)
        assert info['total_size'] > 0
        assert info['type'] == 'zip'
