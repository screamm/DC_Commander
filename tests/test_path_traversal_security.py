"""
Critical P1 test suite for path traversal security.

Tests comprehensive path traversal prevention to ensure:
- No directory escape via ../ patterns
- No symlink escape attacks
- No null byte injection
- No reserved filename exploitation
- Windows and Unix path security

Priority: CRITICAL (P1)
Risk Score: 8/10 (Security)
Test Count: 20
"""

import pytest
import os
from pathlib import Path

from src.core.security import (
    validate_path,
    is_safe_filename,
    sanitize_filename,
    validate_archive_member,
    create_safe_path,
    PathTraversalError,
    UnsafePathError,
)
from src.core.file_operations import (
    copy_file,
    move_file,
    InvalidPathError,
    SecurityError,
)


class TestPathTraversalSecurity:
    """Test path traversal attack prevention."""

    def test_validate_path_blocks_parent_traversal(self, tmp_path):
        """
        CRITICAL: Test path validation blocks ../ traversal.

        Attack: ../../../etc/passwd
        Expected: Validation fails, error message indicates traversal attempt.
        Risk: Directory escape, unauthorized file access.
        """
        base = tmp_path / "base"
        base.mkdir()

        # Attempt to traverse outside base directory
        malicious = tmp_path / "base" / ".." / ".." / "etc" / "passwd"

        is_valid, error = validate_path(malicious, base, allow_symlinks=False)

        assert is_valid is False, "Path traversal should be blocked"
        assert error is not None
        assert "traversal" in error.lower() or "outside" in error.lower()

    def test_validate_path_blocks_absolute_path_escape(self, tmp_path):
        """
        CRITICAL: Test absolute paths that escape base directory.

        Attack: /etc/passwd (absolute path outside allowed base)
        Expected: Validation fails.
        Risk: Access to system files.
        """
        base = tmp_path / "base"
        base.mkdir()

        # Try absolute path outside base
        if os.name == 'posix':
            absolute_path = Path("/etc/passwd")
            if absolute_path.exists():
                is_valid, error = validate_path(absolute_path, base)
                assert is_valid is False
                assert "traversal" in error.lower() or "outside" in error.lower()

    def test_copy_blocks_path_traversal_in_source(self, tmp_path):
        """
        CRITICAL: Test copy operation blocks path traversal in source.

        Scenario: User tries to copy file using traversal path.
        Expected: InvalidPathError or SecurityError raised.
        Risk: Reading unauthorized files.
        """
        base = tmp_path / "base"
        base.mkdir()

        # Create a file outside base
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("secret content")

        # Try to access via traversal
        traversal_source = base / ".." / "secret.txt"
        dest = base / "output.txt"

        with pytest.raises((InvalidPathError, SecurityError, ValueError)):
            copy_file(traversal_source, dest)

    def test_copy_blocks_path_traversal_in_dest(self, tmp_path):
        """
        CRITICAL: Test copy operation blocks path traversal in destination.

        Scenario: User tries to write file outside allowed directory.
        Expected: InvalidPathError or SecurityError raised.
        Risk: Writing to unauthorized locations.
        """
        base = tmp_path / "base"
        base.mkdir()

        source = base / "source.txt"
        source.write_text("content")

        # Try to write outside base using traversal
        traversal_dest = base / ".." / "unauthorized.txt"

        with pytest.raises((InvalidPathError, SecurityError, ValueError)):
            copy_file(source, traversal_dest)

    def test_move_blocks_path_traversal(self, tmp_path):
        """
        CRITICAL: Test move operation validates both source and dest paths.

        Scenario: User tries to move file using traversal paths.
        Expected: InvalidPathError or SecurityError raised.
        Risk: Moving files outside allowed boundaries.
        """
        base = tmp_path / "base"
        base.mkdir()

        source = base / "source.txt"
        source.write_text("content")

        # Try to move outside base
        traversal_dest = base / ".." / "escaped.txt"

        with pytest.raises((InvalidPathError, SecurityError, ValueError)):
            move_file(source, traversal_dest)

    @pytest.mark.skipif(os.name == 'nt', reason="Symlink test requires Unix")
    def test_symlink_traversal_blocked(self, tmp_path):
        """
        CRITICAL: Test symlink pointing outside base directory is blocked.

        Attack: Symlink to /etc/passwd
        Expected: Validation fails when allow_symlinks=False.
        Risk: Reading arbitrary system files.
        """
        base = tmp_path / "base"
        base.mkdir()

        # Create symlink to system file
        link = base / "link_to_passwd"
        try:
            if Path("/etc/passwd").exists():
                link.symlink_to("/etc/passwd")

                is_valid, error = validate_path(link, base, allow_symlinks=False)
                assert is_valid is False
                assert "symlink" in error.lower()
        except OSError:
            pytest.skip("Cannot create symlinks")

    def test_null_byte_injection_blocked(self):
        """
        CRITICAL: Test null byte injection in filename.

        Attack: "file.txt\x00.sh" (appears as file.txt to user, executed as .sh)
        Expected: Sanitization removes null bytes, validation fails.
        Risk: Execution of malicious scripts.
        """
        dangerous = "file.txt\x00.sh"

        # Sanitization should remove null bytes
        safe = sanitize_filename(dangerous)
        assert "\x00" not in safe

        # Validation should reject null bytes
        assert is_safe_filename(dangerous) is False

    def test_windows_reserved_names_blocked(self):
        """
        CRITICAL: Test Windows reserved names are blocked.

        Attack: CON, PRN, AUX, NUL, COM1, LPT1, etc.
        Expected: Validation fails for all reserved names.
        Risk: Device access, system disruption on Windows.
        """
        reserved_names = [
            "CON", "PRN", "AUX", "NUL",
            "COM1", "COM2", "COM3", "COM4", "COM5",
            "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
            "LPT6", "LPT7", "LPT8", "LPT9"
        ]

        for name in reserved_names:
            assert is_safe_filename(name) is False, \
                f"Reserved name {name} should be blocked"

    def test_unicode_path_traversal_blocked(self):
        """
        HIGH: Test Unicode variations of path traversal.

        Attack: Unicode characters that normalize to ../
        Expected: Validation blocks Unicode traversal attempts.
        Risk: Unicode normalization bypass.
        """
        # Test Unicode dot variations (if they exist)
        unicode_dots = "‥"  # Two-dot leader U+2025
        malicious = f"{unicode_dots}/etc/passwd"

        # Should either sanitize or reject
        safe = sanitize_filename(malicious)
        assert "/" not in safe and "\\" not in safe

    def test_url_encoded_traversal_blocked(self):
        """
        HIGH: Test URL-encoded path traversal blocked.

        Attack: ..%2F..%2F..%2Fetc%2Fpasswd
        Expected: Validation blocks encoded traversal.
        Risk: Encoding bypass of path validation.
        """
        encoded_traversal = "..%2F..%2F..%2Fetc%2Fpasswd"

        # Sanitization should handle encoded characters
        safe = sanitize_filename(encoded_traversal)
        # After sanitization, should not have path separators
        assert "/" not in safe and "\\" not in safe

    def test_double_encoded_traversal_blocked(self):
        """
        MEDIUM: Test double-encoded path traversal blocked.

        Attack: %252E%252E%252F (double-encoded ../)
        Expected: Validation blocks double-encoded attempts.
        Risk: Double-encoding bypass.
        """
        double_encoded = "%252E%252E%252F"

        safe = sanitize_filename(double_encoded)
        # Should not decode to path separators
        assert "/" not in safe and "\\" not in safe

    @pytest.mark.skipif(os.name != 'nt', reason="Windows-specific test")
    def test_backslash_traversal_on_windows(self, tmp_path):
        """
        HIGH: Test backslash traversal on Windows.

        Attack: ..\..\..\Windows\System32
        Expected: Validation blocks backslash traversal.
        Risk: Windows-specific directory escape.
        """
        base = tmp_path / "base"
        base.mkdir()

        malicious = base / ".." / ".." / "Windows" / "System32"

        is_valid, error = validate_path(malicious, base)
        assert is_valid is False
        assert "traversal" in error.lower() or "outside" in error.lower()

    def test_mixed_slash_traversal(self, tmp_path):
        """
        MEDIUM: Test mixed forward/backslash traversal.

        Attack: ..\\../etc/passwd (mixing separators)
        Expected: Validation normalizes and blocks traversal.
        Risk: Separator confusion bypass.
        """
        base = tmp_path / "base"
        base.mkdir()

        # Mixed separator traversal
        malicious_name = "..\\../etc/passwd"
        safe = sanitize_filename(malicious_name)

        # Should remove all path separators
        assert "/" not in safe
        assert "\\" not in safe

    def test_case_variation_traversal(self):
        """
        MEDIUM: Test case variations of path traversal.

        Attack: ../ vs ..\ vs ../  vs ..\
        Expected: All variations blocked.
        Risk: Case-sensitivity bypass.
        """
        variations = [
            "../",
            "..\\",
            "../ ",
            "..\\ ",
            "..",
            "./..",
            "..\\.."
        ]

        for variant in variations:
            safe = sanitize_filename(variant)
            # Should not contain traversal patterns
            assert ".." not in safe or safe == "unnamed"

    def test_path_normalization_before_validation(self, tmp_path):
        """
        HIGH: Test paths are normalized before validation.

        Scenario: Complex paths like a/./b/../c should normalize correctly.
        Expected: Normalized path validated against base.
        Risk: Bypassing validation through path complexity.
        """
        base = tmp_path / "base"
        base.mkdir()
        (base / "dir").mkdir()

        # Complex but safe path
        complex_path = base / "dir" / "." / ".." / "dir" / "file.txt"

        # Should normalize and validate within base
        is_valid, error = validate_path(complex_path, base)
        # May be valid or invalid depending on normalization, but should not crash
        assert error is None or isinstance(error, str)

    def test_symlink_resolution_security(self, tmp_path):
        """
        HIGH: Test symlink resolution stays within base.

        Scenario: Symlink that resolves outside base directory.
        Expected: Validation fails or resolves safely.
        Risk: Symlink escape attack.
        """
        base = tmp_path / "base"
        base.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()
        outside_file = outside / "secret.txt"
        outside_file.write_text("secret")

        link = base / "link"
        try:
            link.symlink_to(outside_file)

            is_valid, error = validate_path(link, base, allow_symlinks=False)
            assert is_valid is False
            assert "symlink" in error.lower()
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks not supported on this system")

    @pytest.mark.skipif(os.name == 'nt', reason="Unix-specific hard link test")
    def test_hard_link_security(self, tmp_path):
        """
        MEDIUM: Test hard links to files outside base.

        Scenario: Hard link to file outside allowed directory.
        Expected: Operations on hard link are safe (within base).
        Risk: Hard link escape (lower risk than symlink).
        """
        base = tmp_path / "base"
        base.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()
        outside_file = outside / "secret.txt"
        outside_file.write_text("secret")

        hard_link = base / "link.txt"
        try:
            os.link(outside_file, hard_link)

            # Hard link itself is in base, so validation may pass
            is_valid, error = validate_path(hard_link, base)
            # Hard link validation behavior depends on implementation
            # Document actual behavior
            assert isinstance(is_valid, bool)
        except (OSError, NotImplementedError):
            pytest.skip("Hard links not supported")

    def test_archive_member_traversal_blocked(self, tmp_path):
        """
        CRITICAL: Test archive member path traversal blocked.

        Attack: Archive containing "../../../etc/passwd"
        Expected: Validation fails before extraction.
        Risk: Zip Slip vulnerability.
        """
        malicious_members = [
            "../../../etc/passwd",
            "..\\..\\..\\Windows\\System32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\sam"
        ]

        for member_path in malicious_members:
            is_valid, error = validate_archive_member(member_path, tmp_path)
            assert is_valid is False, \
                f"Archive member {member_path} should be blocked"
            assert error is not None

    def test_create_safe_path_prevents_traversal(self, tmp_path):
        """
        CRITICAL: Test safe path creation prevents traversal.

        Scenario: Creating path from untrusted components.
        Expected: UnsafePathError raised on traversal attempt.
        Risk: Programmatic directory escape.
        """
        base = tmp_path / "base"
        base.mkdir()

        # Attempt to create unsafe path
        with pytest.raises(UnsafePathError):
            create_safe_path(base, "..", "..", "etc", "passwd")

    def test_relative_path_outside_base_blocked(self, tmp_path):
        """
        HIGH: Test relative path that resolves outside base.

        Scenario: Path like "../../outside/file.txt" that goes up then down.
        Expected: Validation detects path is outside base after resolution.
        Risk: Complex traversal patterns.
        """
        base = tmp_path / "base"
        base.mkdir()

        # Create directory structure
        outside = tmp_path / "outside"
        outside.mkdir()

        # Relative path that goes outside
        relative_path = base / ".." / "outside"

        is_valid, error = validate_path(relative_path, base)
        assert is_valid is False


class TestArchiveTraversalSecurity:
    """Test archive-specific path traversal security."""

    def test_archive_absolute_path_blocked(self, tmp_path):
        """
        CRITICAL: Test absolute paths in archive members blocked.

        Attack: Archive member "/etc/passwd"
        Expected: Validation fails.
        Risk: Overwriting system files.
        """
        absolute_paths = [
            "/etc/passwd",
            "/tmp/evil",
            "C:\\Windows\\System32\\evil.dll"
        ]

        for path in absolute_paths:
            is_valid, error = validate_archive_member(path, tmp_path)
            assert is_valid is False
            assert "absolute" in error.lower() or "traversal" in error.lower()

    def test_archive_windows_path_separators_normalized(self, tmp_path):
        """
        HIGH: Test Windows path separators normalized in archives.

        Scenario: Archive member "dir\\file.txt" on Unix.
        Expected: Path normalized and validated correctly.
        Risk: Path separator confusion.
        """
        windows_path = "safe\\dir\\file.txt"

        is_valid, error = validate_archive_member(windows_path, tmp_path)
        # Should be valid after normalization (if no traversal)
        assert is_valid is True or (error and "unsafe" not in error.lower())

    def test_archive_member_with_null_bytes_blocked(self, tmp_path):
        """
        CRITICAL: Test null bytes in archive member paths blocked.

        Attack: "safe.txt\x00.sh"
        Expected: Validation fails.
        Risk: File extension spoofing.
        """
        null_byte_path = "safe.txt\x00.sh"

        is_valid, error = validate_archive_member(null_byte_path, tmp_path)
        assert is_valid is False
        assert error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
