"""
Archive security integration tests for Modern Commander.

Tests archive handler with security validation enabled.
"""

import pytest
import zipfile
import tarfile
import io
from pathlib import Path

from src.core.archive_handler import (
    extract_archive,
    create_archive,
    ArchiveType,
    ArchiveError
)
from src.core.security import (
    PathTraversalError,
    ArchiveBombError
)


class TestZipSecureExtraction:
    """Test secure ZIP extraction."""

    def test_extract_safe_zip(self, tmp_path):
        """Test extraction of safe ZIP archive."""
        # Create safe ZIP
        archive_path = tmp_path / "safe.zip"
        extract_path = tmp_path / "extract"

        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("dir/file2.txt", "content2")

        # Extract with security validation
        result = extract_archive(archive_path, extract_path, validate_safety=True)
        assert result is True

        # Verify extracted files
        assert (extract_path / "file1.txt").exists()
        assert (extract_path / "dir" / "file2.txt").exists()
        assert (extract_path / "file1.txt").read_text() == "content1"

    def test_extract_zip_path_traversal_blocked(self, tmp_path):
        """Test ZIP with path traversal is blocked."""
        # Create malicious ZIP
        archive_path = tmp_path / "malicious.zip"

        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr("safe.txt", "safe content")
            zf.writestr("../../../tmp/evil.txt", "malicious content")

        extract_path = tmp_path / "extract"

        # Should raise PathTraversalError
        with pytest.raises(PathTraversalError) as exc_info:
            extract_archive(archive_path, extract_path, validate_safety=True)

        assert "traversal" in str(exc_info.value).lower()

    def test_extract_zip_absolute_path_blocked(self, tmp_path):
        """Test ZIP with absolute paths is blocked."""
        archive_path = tmp_path / "absolute.zip"

        with zipfile.ZipFile(archive_path, 'w') as zf:
            if Path("/tmp").exists():
                zf.writestr("/tmp/absolute.txt", "absolute path")
            else:
                zf.writestr("C:/Windows/absolute.txt", "absolute path")

        extract_path = tmp_path / "extract"

        with pytest.raises(PathTraversalError):
            extract_archive(archive_path, extract_path, validate_safety=True)

    def test_extract_zip_bomb_blocked(self, tmp_path):
        """Test ZIP bomb is detected and blocked."""
        archive_path = tmp_path / "bomb.zip"

        # Create a ZIP with high compression ratio
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            # Create highly compressible data
            massive_data = b'\x00' * 200_000_000  # 200MB of zeros
            zf.writestr("bomb.txt", massive_data)

        extract_path = tmp_path / "extract"

        # Should detect compression bomb
        with pytest.raises(ArchiveBombError) as exc_info:
            extract_archive(archive_path, extract_path, validate_safety=True)

        error_msg = str(exc_info.value).lower()
        assert "bomb" in error_msg or "ratio" in error_msg or "large" in error_msg

    def test_extract_zip_without_validation(self, tmp_path):
        """Test extraction without security validation (unsafe)."""
        archive_path = tmp_path / "test.zip"
        extract_path = tmp_path / "extract"

        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr("file.txt", "content")

        # Extract without validation
        result = extract_archive(
            archive_path,
            extract_path,
            validate_safety=False
        )
        assert result is True


class TestTarSecureExtraction:
    """Test secure TAR extraction."""

    def test_extract_safe_tar(self, tmp_path):
        """Test extraction of safe TAR archive."""
        archive_path = tmp_path / "safe.tar.gz"
        extract_path = tmp_path / "extract"

        with tarfile.open(archive_path, 'w:gz') as tf:
            # Create temporary files
            file1 = tmp_path / "file1.txt"
            file1.write_text("content1")

            subdir = tmp_path / "subdir"
            subdir.mkdir()
            file2 = subdir / "file2.txt"
            file2.write_text("content2")

            tf.add(file1, arcname="file1.txt")
            tf.add(file2, arcname="subdir/file2.txt")

        result = extract_archive(archive_path, extract_path, validate_safety=True)
        assert result is True

        assert (extract_path / "file1.txt").exists()
        assert (extract_path / "subdir" / "file2.txt").exists()

    def test_extract_tar_path_traversal_blocked(self, tmp_path):
        """Test TAR with path traversal is blocked."""
        archive_path = tmp_path / "malicious.tar"

        # Create file to add
        safe_file = tmp_path / "safe.txt"
        safe_file.write_text("safe")

        with tarfile.open(archive_path, 'w') as tf:
            tf.add(safe_file, arcname="safe.txt")

            # Add member with dangerous path manually
            info = tarfile.TarInfo(name="../../../tmp/evil.txt")
            info.size = 4
            tf.addfile(info, io.BytesIO(b"evil"))

        extract_path = tmp_path / "extract"

        with pytest.raises(PathTraversalError):
            extract_archive(archive_path, extract_path, validate_safety=True)

    def test_extract_tar_symlink_escape_blocked(self, tmp_path):
        """Test TAR with escaping symlink is blocked."""
        archive_path = tmp_path / "symlink.tar"

        try:
            # Create symlink pointing outside
            link = tmp_path / "link"
            target = tmp_path / ".." / "outside.txt"
            link.symlink_to(target)

            with tarfile.open(archive_path, 'w') as tf:
                tf.add(link, arcname="link")

            extract_path = tmp_path / "extract"

            with pytest.raises(PathTraversalError):
                extract_archive(archive_path, extract_path, validate_safety=True)

        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported")

    def test_extract_tar_absolute_symlink_blocked(self, tmp_path):
        """Test TAR with absolute symlink is blocked."""
        archive_path = tmp_path / "absolute_link.tar"

        with tarfile.open(archive_path, 'w') as tf:
            # Create symlink with absolute target
            info = tarfile.TarInfo(name="link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tf.addfile(info)

        extract_path = tmp_path / "extract"

        with pytest.raises(PathTraversalError) as exc_info:
            extract_archive(archive_path, extract_path, validate_safety=True)

        assert "absolute" in str(exc_info.value).lower()


class TestSecureMemberSelection:
    """Test secure extraction of specific members."""

    def test_extract_specific_safe_members(self, tmp_path):
        """Test extracting specific safe members."""
        archive_path = tmp_path / "multi.zip"

        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("file2.txt", "content2")
            zf.writestr("file3.txt", "content3")

        extract_path = tmp_path / "extract"

        # Extract only file1 and file2
        result = extract_archive(
            archive_path,
            extract_path,
            members=["file1.txt", "file2.txt"],
            validate_safety=True
        )
        assert result is True

        assert (extract_path / "file1.txt").exists()
        assert (extract_path / "file2.txt").exists()
        assert not (extract_path / "file3.txt").exists()

    def test_extract_members_with_traversal_blocked(self, tmp_path):
        """Test extracting specific members blocks traversal."""
        archive_path = tmp_path / "mixed.zip"

        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr("safe.txt", "safe")
            zf.writestr("../evil.txt", "evil")

        extract_path = tmp_path / "extract"

        # Even selecting only the evil member should be blocked
        with pytest.raises(PathTraversalError):
            extract_archive(
                archive_path,
                extract_path,
                members=["../evil.txt"],
                validate_safety=True
            )


class TestArchiveCreation:
    """Test secure archive creation."""

    def test_create_zip_archive(self, tmp_path):
        """Test creating ZIP archive."""
        # Create source files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")

        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")

        # Create archive
        archive_path = tmp_path / "output.zip"
        files = [source_dir / "file1.txt", subdir]

        result = create_archive(
            files,
            archive_path,
            archive_type=ArchiveType.ZIP,
            base_dir=source_dir
        )
        assert result is True
        assert archive_path.exists()

        # Verify archive contents
        with zipfile.ZipFile(archive_path, 'r') as zf:
            names = zf.namelist()
            assert "file1.txt" in names
            assert "subdir/file3.txt" in names

    def test_create_tar_archive(self, tmp_path):
        """Test creating TAR archive."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")

        archive_path = tmp_path / "output.tar.gz"

        result = create_archive(
            [source_dir / "file1.txt"],
            archive_path,
            archive_type=ArchiveType.TAR_GZ,
            base_dir=source_dir
        )
        assert result is True
        assert archive_path.exists()


class TestSecurityEdgeCases:
    """Test edge cases in security validation."""

    def test_extract_empty_archive(self, tmp_path):
        """Test extracting empty archive."""
        archive_path = tmp_path / "empty.zip"

        with zipfile.ZipFile(archive_path, 'w') as zf:
            pass  # Empty archive

        extract_path = tmp_path / "extract"

        result = extract_archive(archive_path, extract_path, validate_safety=True)
        assert result is True

    def test_extract_nested_directories(self, tmp_path):
        """Test extracting deeply nested directories."""
        archive_path = tmp_path / "nested.zip"

        with zipfile.ZipFile(archive_path, 'w') as zf:
            # Create deeply nested structure
            zf.writestr("a/b/c/d/e/file.txt", "deep content")

        extract_path = tmp_path / "extract"

        result = extract_archive(archive_path, extract_path, validate_safety=True)
        assert result is True
        assert (extract_path / "a" / "b" / "c" / "d" / "e" / "file.txt").exists()

    def test_extract_unicode_filenames(self, tmp_path):
        """Test extracting files with Unicode names."""
        archive_path = tmp_path / "unicode.zip"

        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr("файл.txt", "unicode content")
            zf.writestr("文件.txt", "chinese content")

        extract_path = tmp_path / "extract"

        result = extract_archive(archive_path, extract_path, validate_safety=True)
        assert result is True

    def test_extract_max_file_count(self, tmp_path):
        """Test archive with many files."""
        archive_path = tmp_path / "many.zip"

        with zipfile.ZipFile(archive_path, 'w') as zf:
            # Create archive with many files (but within limit)
            for i in range(100):
                zf.writestr(f"file{i}.txt", f"content{i}")

        extract_path = tmp_path / "extract"

        # Should succeed as it's within default limit (10000)
        result = extract_archive(archive_path, extract_path, validate_safety=True)
        assert result is True

    def test_extract_exactly_at_compression_limit(self, tmp_path):
        """Test archive at exact compression ratio limit."""
        archive_path = tmp_path / "limit.zip"

        # Create data that compresses to exactly 100:1
        data_size = 100_000  # 100KB uncompressed
        compressible_data = b'\x00' * data_size

        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("data.bin", compressible_data)

        extract_path = tmp_path / "extract"

        # Check if compression is high but within limit
        archive_size = archive_path.stat().st_size
        ratio = data_size / archive_size

        if ratio > 100:
            # If over limit, should be blocked
            with pytest.raises(ArchiveBombError):
                extract_archive(archive_path, extract_path, validate_safety=True)
        else:
            # If within limit, should succeed
            result = extract_archive(archive_path, extract_path, validate_safety=True)
            assert result is True


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_extract_project_backup(self, tmp_path):
        """Test extracting a typical project backup."""
        # Create a typical project structure
        project = tmp_path / "project"
        project.mkdir()

        (project / "README.md").write_text("# Project")
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("print('hello')")
        (project / "tests").mkdir()
        (project / "tests" / "test_main.py").write_text("def test(): pass")

        # Create archive
        archive_path = tmp_path / "backup.tar.gz"
        create_archive(
            [project],
            archive_path,
            archive_type=ArchiveType.TAR_GZ,
            base_dir=tmp_path
        )

        # Extract to new location
        extract_path = tmp_path / "restored"
        result = extract_archive(archive_path, extract_path, validate_safety=True)
        assert result is True

        # Verify structure
        assert (extract_path / "project" / "README.md").exists()
        assert (extract_path / "project" / "src" / "main.py").exists()
        assert (extract_path / "project" / "tests" / "test_main.py").exists()

    def test_extract_user_upload(self, tmp_path):
        """Test extracting user-uploaded archive with validation."""
        # Simulate user uploading a safe archive
        archive_path = tmp_path / "user_upload.zip"

        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr("document.pdf", b"PDF content")
            zf.writestr("images/photo.jpg", b"JPEG content")

        extract_path = tmp_path / "uploads"

        # Extract with full validation
        result = extract_archive(archive_path, extract_path, validate_safety=True)
        assert result is True

        assert (extract_path / "document.pdf").exists()
        assert (extract_path / "images" / "photo.jpg").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
