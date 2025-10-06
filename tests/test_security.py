"""
Security module tests for Modern Commander.

Tests security protections against path traversal, archive bombs,
and other attack vectors.
"""

import pytest
import zipfile
import tarfile
import io
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.security import (
    validate_path,
    is_safe_path,
    sanitize_filename,
    is_safe_filename,
    check_archive_bomb,
    validate_archive_member,
    check_permissions,
    create_safe_path,
    SecurityConfig,
    get_security_config,
    set_security_config,
    PathTraversalError,
    ArchiveBombError,
    UnsafePathError
)


class TestPathValidation:
    """Test path traversal prevention."""

    def test_validate_safe_path(self, tmp_path):
        """Test validation of safe paths."""
        safe_file = tmp_path / "safe" / "file.txt"
        safe_file.parent.mkdir(parents=True)
        safe_file.write_text("test")

        is_valid, error = validate_path(safe_file, tmp_path)
        assert is_valid is True
        assert error is None

    def test_validate_path_traversal_dotdot(self, tmp_path):
        """Test detection of .. path traversal."""
        unsafe_path = tmp_path / ".." / "etc" / "passwd"

        is_valid, error = validate_path(unsafe_path, tmp_path)
        assert is_valid is False
        assert "traversal" in error.lower()

    def test_validate_path_traversal_absolute(self, tmp_path):
        """Test detection of absolute path traversal."""
        if Path("/etc/passwd").exists():
            unsafe_path = Path("/etc/passwd")
            is_valid, error = validate_path(unsafe_path, tmp_path)
            assert is_valid is False
            assert "traversal" in error.lower()

    def test_validate_symlink_blocked(self, tmp_path):
        """Test symlinks are blocked by default."""
        target = tmp_path / "target.txt"
        target.write_text("target")

        link = tmp_path / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this system")

        is_valid, error = validate_path(link, tmp_path, allow_symlinks=False)
        assert is_valid is False
        assert "symlink" in error.lower()

    def test_validate_symlink_allowed(self, tmp_path):
        """Test symlinks can be allowed."""
        target = tmp_path / "target.txt"
        target.write_text("target")

        link = tmp_path / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this system")

        is_valid, error = validate_path(link, tmp_path, allow_symlinks=True)
        assert is_valid is True
        assert error is None

    def test_is_safe_path_convenience(self, tmp_path):
        """Test is_safe_path convenience wrapper."""
        safe_file = tmp_path / "safe.txt"
        safe_file.write_text("test")

        assert is_safe_path(safe_file, tmp_path) is True

        unsafe_path = tmp_path / ".." / "etc"
        assert is_safe_path(unsafe_path, tmp_path) is False


class TestFilenameSanitization:
    """Test filename sanitization."""

    def test_sanitize_path_separators(self):
        """Test path separators are removed."""
        dangerous = "../../../etc/passwd"
        safe = sanitize_filename(dangerous)
        assert "/" not in safe
        assert "\\" not in safe
        assert ".." not in safe

    def test_sanitize_dangerous_chars(self):
        """Test dangerous characters are removed."""
        dangerous = 'file<>:"|?*.txt'
        safe = sanitize_filename(dangerous)
        assert "<" not in safe
        assert ">" not in safe
        assert ":" not in safe
        assert '"' not in safe
        assert "|" not in safe
        assert "?" not in safe
        assert "*" not in safe

    def test_sanitize_null_bytes(self):
        """Test null bytes are removed."""
        dangerous = "file\x00name.txt"
        safe = sanitize_filename(dangerous)
        assert "\x00" not in safe

    def test_sanitize_control_chars(self):
        """Test control characters are removed."""
        dangerous = "file\x01\x02\x03name.txt"
        safe = sanitize_filename(dangerous)
        assert not any(ord(c) < 32 for c in safe)

    def test_sanitize_empty_result(self):
        """Test empty filename gets default name."""
        dangerous = "/../../../"
        safe = sanitize_filename(dangerous)
        assert safe == "unnamed"

    def test_sanitize_long_filename(self):
        """Test long filenames are truncated."""
        long_name = "a" * 300 + ".txt"
        safe = sanitize_filename(long_name)
        assert len(safe) <= 255

    def test_is_safe_filename_valid(self):
        """Test valid filenames are recognized."""
        assert is_safe_filename("file.txt") is True
        assert is_safe_filename("my_file-123.txt") is True

    def test_is_safe_filename_invalid(self):
        """Test invalid filenames are detected."""
        assert is_safe_filename("..") is False
        assert is_safe_filename("file/path.txt") is False
        assert is_safe_filename("file\x00.txt") is False
        assert is_safe_filename("file<>.txt") is False
        assert is_safe_filename("CON") is False  # Windows reserved


class TestArchiveBombDetection:
    """Test archive bomb protection."""

    def test_check_safe_archive(self):
        """Test normal archive passes validation."""
        compressed = 1000
        uncompressed = 50000  # 50:1 ratio
        file_count = 100

        is_safe, error = check_archive_bomb(compressed, uncompressed, file_count)
        assert is_safe is True
        assert error is None

    def test_check_high_compression_ratio(self):
        """Test detection of excessive compression ratio."""
        compressed = 1000
        uncompressed = 500_000_000  # 500,000:1 ratio
        file_count = 10

        is_safe, error = check_archive_bomb(compressed, uncompressed, file_count)
        assert is_safe is False
        assert "ratio" in error.lower()

    def test_check_max_extracted_size(self):
        """Test detection of excessive extracted size."""
        compressed = 1_000_000
        uncompressed = 2_000_000_000  # 2GB
        file_count = 10

        is_safe, error = check_archive_bomb(compressed, uncompressed, file_count)
        assert is_safe is False
        assert "large" in error.lower()

    def test_check_max_file_count(self):
        """Test detection of excessive file count."""
        compressed = 1000
        uncompressed = 50000
        file_count = 50000

        is_safe, error = check_archive_bomb(compressed, uncompressed, file_count)
        assert is_safe is False
        assert "many files" in error.lower()

    def test_check_custom_config(self):
        """Test custom security configuration."""
        original_config = get_security_config()

        try:
            # Set stricter limits
            custom_config = SecurityConfig(
                max_compression_ratio=50.0,
                max_extracted_size=100_000_000,  # 100MB
                max_file_count=1000
            )
            set_security_config(custom_config)

            # This should now fail with stricter limits
            compressed = 1000
            uncompressed = 100_000  # 100:1 ratio
            file_count = 10

            is_safe, error = check_archive_bomb(compressed, uncompressed, file_count)
            assert is_safe is False

        finally:
            set_security_config(original_config)


class TestArchiveMemberValidation:
    """Test archive member path validation."""

    def test_validate_safe_member(self, tmp_path):
        """Test safe archive member path."""
        is_valid, error = validate_archive_member("safe/file.txt", tmp_path)
        assert is_valid is True
        assert error is None

    def test_validate_member_path_traversal(self, tmp_path):
        """Test detection of path traversal in member."""
        is_valid, error = validate_archive_member("../../../etc/passwd", tmp_path)
        assert is_valid is False
        assert "traversal" in error.lower()

    def test_validate_member_absolute_path(self, tmp_path):
        """Test detection of absolute paths in member."""
        is_valid, error = validate_archive_member("/etc/passwd", tmp_path)
        assert is_valid is False
        assert "absolute" in error.lower()

    def test_validate_member_dangerous_filename(self, tmp_path):
        """Test detection of dangerous filenames."""
        is_valid, error = validate_archive_member("safe/file\x00.txt", tmp_path)
        assert is_valid is False
        assert "null byte" in error.lower() or "unsafe" in error.lower()

    def test_validate_member_windows_separator(self, tmp_path):
        """Test handling of Windows path separators."""
        is_valid, error = validate_archive_member(r"safe\file.txt", tmp_path)
        assert is_valid is True  # Should be normalized


class TestPermissionChecks:
    """Test permission validation."""

    def test_check_read_permission(self, tmp_path):
        """Test read permission check."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        is_allowed, error = check_permissions(test_file, 'r')
        assert is_allowed is True
        assert error is None

    def test_check_write_permission(self, tmp_path):
        """Test write permission check."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        is_allowed, error = check_permissions(test_file, 'w')
        assert is_allowed is True
        assert error is None

    def test_check_nonexistent_path(self, tmp_path):
        """Test permission check on nonexistent path."""
        nonexistent = tmp_path / "nonexistent.txt"

        is_allowed, error = check_permissions(nonexistent, 'r')
        assert is_allowed is False
        assert "not exist" in error.lower()


class TestSafePath:
    """Test safe path creation."""

    def test_create_safe_path(self, tmp_path):
        """Test creating safe paths."""
        safe_path = create_safe_path(tmp_path, "subdir", "file.txt")
        assert safe_path.parent.name == "subdir"
        assert safe_path.name == "file.txt"

        # Verify it's within base directory
        assert tmp_path in safe_path.parents

    def test_create_safe_path_sanitizes(self, tmp_path):
        """Test safe path sanitizes dangerous components."""
        safe_path = create_safe_path(tmp_path, "sub<>dir", "file|?.txt")
        assert "<" not in str(safe_path)
        assert ">" not in str(safe_path)
        assert "|" not in str(safe_path)
        assert "?" not in str(safe_path)

    def test_create_safe_path_prevents_traversal(self, tmp_path):
        """Test safe path prevents traversal."""
        with pytest.raises(UnsafePathError):
            create_safe_path(tmp_path, "..", "..", "etc", "passwd")


class TestSecurityConfig:
    """Test security configuration."""

    def test_default_config(self):
        """Test default security configuration."""
        config = SecurityConfig()
        assert config.max_compression_ratio == 100.0
        assert config.max_extracted_size == 1_073_741_824  # 1GB
        assert config.max_file_count == 10000

    def test_custom_config(self):
        """Test custom security configuration."""
        config = SecurityConfig(
            max_compression_ratio=50.0,
            max_extracted_size=500_000_000,
            max_file_count=5000
        )
        assert config.max_compression_ratio == 50.0
        assert config.max_extracted_size == 500_000_000
        assert config.max_file_count == 5000

    def test_forbidden_filenames(self):
        """Test forbidden filenames in config."""
        config = SecurityConfig()
        assert ".." in config.forbidden_filenames
        assert "CON" in config.forbidden_filenames
        assert "NUL" in config.forbidden_filenames


class TestAttackScenarios:
    """Test real-world attack scenarios."""

    def test_zip_slip_attack(self, tmp_path):
        """Test protection against Zip Slip attack."""
        # Member with path traversal
        dangerous_member = "../../../tmp/evil.txt"

        is_valid, error = validate_archive_member(dangerous_member, tmp_path)
        assert is_valid is False
        assert "traversal" in error.lower()

    def test_symlink_escape_attack(self, tmp_path):
        """Test protection against symlink escape."""
        # Symlink pointing outside allowed directory
        try:
            link = tmp_path / "link"
            link.symlink_to("/etc/passwd")

            is_valid, error = validate_path(link, tmp_path, allow_symlinks=False)
            assert is_valid is False
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported")

    def test_null_byte_injection(self):
        """Test protection against null byte injection."""
        dangerous = "file.txt\x00.sh"
        safe = sanitize_filename(dangerous)
        assert "\x00" not in safe
        assert is_safe_filename(dangerous) is False

    def test_windows_reserved_names(self):
        """Test protection against Windows reserved names."""
        reserved = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]

        for name in reserved:
            assert is_safe_filename(name) is False

    def test_compression_bomb_42zip(self):
        """Test detection of 42.zip style compression bomb."""
        # Simulated 42.zip: 42 KB -> 4.5 PB
        compressed = 42_000  # 42 KB
        uncompressed = 4_500_000_000_000_000  # 4.5 PB

        is_safe, error = check_archive_bomb(compressed, uncompressed, 1)
        assert is_safe is False
        assert "ratio" in error.lower() or "large" in error.lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_filename(self):
        """Test handling of empty filename."""
        safe = sanitize_filename("")
        assert safe == "unnamed"

    def test_only_dots_filename(self):
        """Test handling of filename with only dots."""
        safe = sanitize_filename("...")
        assert safe != "..."  # Should be sanitized

    def test_unicode_filename(self):
        """Test handling of Unicode filenames."""
        unicode_name = "файл.txt"
        safe = sanitize_filename(unicode_name)
        # Should preserve valid Unicode
        assert len(safe) > 0

    def test_zero_compression_ratio(self):
        """Test handling of zero-byte file."""
        is_safe, error = check_archive_bomb(100, 0, 1)
        assert is_safe is True

    def test_exact_limit_compression(self):
        """Test compression at exact limit."""
        compressed = 1000
        uncompressed = 100_000  # Exactly 100:1

        is_safe, error = check_archive_bomb(compressed, uncompressed, 1)
        assert is_safe is True  # Should be allowed at limit

    def test_exact_limit_plus_one(self):
        """Test compression just over limit."""
        compressed = 1000
        uncompressed = 100_001  # Just over 100:1

        is_safe, error = check_archive_bomb(compressed, uncompressed, 1)
        assert is_safe is False  # Should be blocked


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
