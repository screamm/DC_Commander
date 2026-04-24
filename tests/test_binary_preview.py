"""Tests for binary file detection and hex-preview banner (Sprint 3 S3.6).

Covers the module-level helpers added to :mod:`features.file_viewer`:

* :func:`detect_binary_type` - magic-byte + extension fallback
* :func:`format_binary_size` - human-readable sizes
* :func:`build_binary_banner` - banner string shown above the hex dump

Also verifies the hex-dump format stays stable (offset + ASCII columns).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from features.file_viewer import (
    FileViewer,
    build_binary_banner,
    detect_binary_type,
    format_binary_size,
)


# --------------------------------------------------------------------------- #
# Magic-byte detection
# --------------------------------------------------------------------------- #
class TestBinarySignatureDetection:
    """Signature-based detection for common file types."""

    def test_png_signature_detected(self, tmp_path: Path) -> None:
        png = tmp_path / "image.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        assert detect_binary_type(png) == "PNG image"

    def test_jpeg_signature_detected(self, tmp_path: Path) -> None:
        jpg = tmp_path / "photo.jpg"
        jpg.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")

        assert detect_binary_type(jpg) == "JPEG image"

    def test_gif_signature_detected(self, tmp_path: Path) -> None:
        gif = tmp_path / "anim.gif"
        gif.write_bytes(b"GIF89a" + b"\x00" * 16)

        assert detect_binary_type(gif) == "GIF image"

    def test_zip_signature_detected(self, tmp_path: Path) -> None:
        zip_file = tmp_path / "archive.zip"
        zip_file.write_bytes(b"PK\x03\x04" + b"\x00" * 16)

        assert detect_binary_type(zip_file) == "ZIP archive"

    def test_gzip_signature_detected(self, tmp_path: Path) -> None:
        gz = tmp_path / "data.gz"
        gz.write_bytes(b"\x1f\x8b\x08\x00")

        assert detect_binary_type(gz) == "gzip archive"

    def test_pdf_signature_detected(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.7\n%" + b"\x00" * 16)

        assert detect_binary_type(pdf) == "PDF document"

    def test_elf_signature_detected(self, tmp_path: Path) -> None:
        elf = tmp_path / "binary"
        elf.write_bytes(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8)

        assert detect_binary_type(elf) == "ELF executable (Linux)"

    def test_mz_windows_executable_detected(self, tmp_path: Path) -> None:
        exe = tmp_path / "app.exe"
        exe.write_bytes(b"MZ\x90\x00\x03\x00")

        assert detect_binary_type(exe) == "Windows executable"


# --------------------------------------------------------------------------- #
# Extension & fallback behaviour
# --------------------------------------------------------------------------- #
class TestBinaryFallback:
    """Behaviour when no magic signature matches."""

    def test_unknown_binary_shows_fallback_label(self, tmp_path: Path) -> None:
        unknown = tmp_path / "mystery.xyz"
        unknown.write_bytes(b"\x01\x02\x03\x04\x05\x06\x07\x08")

        # No magic match, no extension match -> generic label.
        assert detect_binary_type(unknown) == "Binary data"

    def test_extension_fallback_for_dll(self, tmp_path: Path) -> None:
        dll = tmp_path / "library.dll"
        # Bytes that don't match MZ - force the extension path
        dll.write_bytes(b"\x00\x00\x00\x00\x00\x00")

        assert detect_binary_type(dll) == "Windows DLL"

    def test_extension_fallback_for_bin(self, tmp_path: Path) -> None:
        bin_file = tmp_path / "payload.bin"
        bin_file.write_bytes(b"\x01\x02\x03\x04")

        assert detect_binary_type(bin_file) == "Binary data"

    def test_explicit_header_argument_takes_precedence(self, tmp_path: Path) -> None:
        """Pre-read headers are used without touching the filesystem."""
        path = tmp_path / "does_not_exist.dat"
        # Note: we do NOT create the file; header arg must be enough.
        label = detect_binary_type(path, header=b"%PDF-1.4")
        assert label == "PDF document"

    def test_missing_file_returns_fallback(self, tmp_path: Path) -> None:
        """Unreadable path must not raise — returns Binary data fallback."""
        missing = tmp_path / "nope.xyz"
        assert detect_binary_type(missing) == "Binary data"


# --------------------------------------------------------------------------- #
# Text vs binary distinction
# --------------------------------------------------------------------------- #
class TestTextNotFlaggedAsBinary:
    """Detection must not misclassify pure text files."""

    def test_text_file_not_flagged_as_binary(self, tmp_path: Path) -> None:
        """Plain UTF-8 text should fall through to the fallback label.

        ``detect_binary_type`` only labels files — the viewer's binary
        *detection* is separate (``_is_binary_file``).  A text file that
        reaches this helper (e.g., the user manually toggled hex mode)
        will get the "Binary data" fallback, not an image/archive label.
        """
        txt = tmp_path / "notes.txt"
        txt.write_text("Hello, world!\nThis is readable text.\n", encoding="utf-8")

        label = detect_binary_type(txt)
        # Must NOT be any of the specific binary labels.
        forbidden = {
            "PNG image",
            "JPEG image",
            "GIF image",
            "ZIP archive",
            "PDF document",
            "ELF executable (Linux)",
            "Windows executable",
        }
        assert label not in forbidden
        assert label == "Binary data"  # No extension match either


# --------------------------------------------------------------------------- #
# Hex-dump format invariants
# --------------------------------------------------------------------------- #
class TestHexDumpFormat:
    """The hex dump itself should have offset, bytes, and ASCII columns."""

    def test_hex_dump_format_has_offset_and_ascii_columns(self, tmp_path: Path) -> None:
        # Build a tiny binary file and run it through FileViewer's formatter.
        data = b"Hello!\x00\xff" + bytes(range(16, 32))
        png = tmp_path / "sample.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + data)

        # Directly exercise the class helper without mounting Textual.
        viewer = FileViewer.__new__(FileViewer)  # Bypass __init__/super()
        viewer.file_path = png
        hex_lines = viewer._format_hex(png.read_bytes())

        assert len(hex_lines) >= 1
        first = hex_lines[0]

        # Offset column: 8 hex digits, starts at 00000000.
        assert first.startswith("00000000  "), f"Offset missing: {first!r}"

        # ASCII side-panel is wrapped in pipes.
        assert first.count("|") == 2, f"ASCII panel missing pipes: {first!r}"

        # The line should contain at least one byte token like "89" (PNG magic).
        assert " 89 " in first or first[10:12] == "89"


# --------------------------------------------------------------------------- #
# Banner construction
# --------------------------------------------------------------------------- #
class TestBinaryBanner:
    def test_banner_contains_type_and_size(self, tmp_path: Path) -> None:
        png = tmp_path / "x.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 1024)

        banner = build_binary_banner(png, png.stat().st_size, "PNG image")

        assert banner.startswith("Binary file:")
        assert "PNG image" in banner
        # Size must be formatted human-readably, not raw bytes.
        assert " B" in banner or " KB" in banner or " MB" in banner

    @pytest.mark.parametrize(
        ("size", "expected_unit"),
        [
            (0, "B"),
            (512, "B"),
            (2_048, "KB"),
            (5 * 1024 * 1024, "MB"),
            (3 * 1024**3, "GB"),
        ],
    )
    def test_format_binary_size_units(self, size: int, expected_unit: str) -> None:
        formatted = format_binary_size(size)
        assert formatted.endswith(expected_unit), (
            f"size={size} expected unit {expected_unit}, got {formatted!r}"
        )
