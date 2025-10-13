"""
File Type Detection System

Provides comprehensive file type detection using:
- Extension-based detection
- Magic bytes analysis
- Content inspection
- MIME type detection
"""

import mimetypes
from pathlib import Path
from enum import Enum
from typing import Optional, Dict, List, Tuple
import logging


logger = logging.getLogger(__name__)


class FileType(Enum):
    """File type categories."""
    TEXT = "text"
    BINARY = "binary"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    DOCUMENT = "document"
    CODE = "code"
    EXECUTABLE = "executable"
    DATABASE = "database"
    CONFIG = "config"
    UNKNOWN = "unknown"


# Magic bytes signatures
MAGIC_BYTES: Dict[bytes, FileType] = {
    # Images
    b'\xff\xd8\xff': FileType.IMAGE,  # JPEG
    b'\x89PNG\r\n\x1a\n': FileType.IMAGE,  # PNG
    b'GIF87a': FileType.IMAGE,  # GIF87a
    b'GIF89a': FileType.IMAGE,  # GIF89a
    b'BM': FileType.IMAGE,  # BMP
    b'II*\x00': FileType.IMAGE,  # TIFF (little-endian)
    b'MM\x00*': FileType.IMAGE,  # TIFF (big-endian)
    b'RIFF': FileType.IMAGE,  # WEBP (needs further check)

    # Archives
    b'PK\x03\x04': FileType.ARCHIVE,  # ZIP
    b'PK\x05\x06': FileType.ARCHIVE,  # ZIP (empty)
    b'\x1f\x8b': FileType.ARCHIVE,  # GZIP
    b'BZh': FileType.ARCHIVE,  # BZIP2
    b'7z\xbc\xaf\x27\x1c': FileType.ARCHIVE,  # 7z
    b'Rar!\x1a\x07': FileType.ARCHIVE,  # RAR
    b'ustar': FileType.ARCHIVE,  # TAR (at offset 257)

    # Executables
    b'MZ': FileType.EXECUTABLE,  # Windows EXE/DLL
    b'\x7fELF': FileType.EXECUTABLE,  # Linux ELF
    b'\xca\xfe\xba\xbe': FileType.EXECUTABLE,  # Mach-O (macOS)
    b'#!': FileType.EXECUTABLE,  # Shell script

    # Documents
    b'%PDF': FileType.DOCUMENT,  # PDF
    b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1': FileType.DOCUMENT,  # MS Office (old)
    b'PK\x03\x04': FileType.DOCUMENT,  # MS Office (new, also ZIP)

    # Database
    b'SQLite format 3': FileType.DATABASE,  # SQLite3

    # Video
    b'\x00\x00\x00\x14ftyp': FileType.VIDEO,  # MP4
    b'\x00\x00\x00\x18ftyp': FileType.VIDEO,  # MP4
    b'\x00\x00\x00\x1cftyp': FileType.VIDEO,  # MP4
    b'\x00\x00\x00\x20ftyp': FileType.VIDEO,  # MP4
    b'RIFF': FileType.VIDEO,  # AVI (needs further check)

    # Audio
    b'ID3': FileType.AUDIO,  # MP3 with ID3
    b'\xff\xfb': FileType.AUDIO,  # MP3
    b'RIFF': FileType.AUDIO,  # WAV (needs further check)
    b'fLaC': FileType.AUDIO,  # FLAC
    b'OggS': FileType.AUDIO,  # OGG
}


# Extension-based type mapping
EXTENSION_TYPES: Dict[str, FileType] = {
    # Text files
    '.txt': FileType.TEXT,
    '.md': FileType.TEXT,
    '.rst': FileType.TEXT,
    '.log': FileType.TEXT,

    # Code files
    '.py': FileType.CODE,
    '.js': FileType.CODE,
    '.ts': FileType.CODE,
    '.jsx': FileType.CODE,
    '.tsx': FileType.CODE,
    '.java': FileType.CODE,
    '.cpp': FileType.CODE,
    '.c': FileType.CODE,
    '.h': FileType.CODE,
    '.cs': FileType.CODE,
    '.go': FileType.CODE,
    '.rs': FileType.CODE,
    '.rb': FileType.CODE,
    '.php': FileType.CODE,
    '.html': FileType.CODE,
    '.css': FileType.CODE,
    '.scss': FileType.CODE,
    '.sass': FileType.CODE,
    '.sql': FileType.CODE,
    '.sh': FileType.CODE,
    '.bash': FileType.CODE,
    '.zsh': FileType.CODE,
    '.fish': FileType.CODE,
    '.ps1': FileType.CODE,
    '.bat': FileType.CODE,
    '.cmd': FileType.CODE,

    # Config files
    '.json': FileType.CONFIG,
    '.yaml': FileType.CONFIG,
    '.yml': FileType.CONFIG,
    '.toml': FileType.CONFIG,
    '.ini': FileType.CONFIG,
    '.cfg': FileType.CONFIG,
    '.conf': FileType.CONFIG,
    '.xml': FileType.CONFIG,

    # Images
    '.jpg': FileType.IMAGE,
    '.jpeg': FileType.IMAGE,
    '.png': FileType.IMAGE,
    '.gif': FileType.IMAGE,
    '.bmp': FileType.IMAGE,
    '.tiff': FileType.IMAGE,
    '.tif': FileType.IMAGE,
    '.webp': FileType.IMAGE,
    '.svg': FileType.IMAGE,
    '.ico': FileType.IMAGE,

    # Documents
    '.pdf': FileType.DOCUMENT,
    '.doc': FileType.DOCUMENT,
    '.docx': FileType.DOCUMENT,
    '.xls': FileType.DOCUMENT,
    '.xlsx': FileType.DOCUMENT,
    '.ppt': FileType.DOCUMENT,
    '.pptx': FileType.DOCUMENT,
    '.odt': FileType.DOCUMENT,
    '.ods': FileType.DOCUMENT,
    '.odp': FileType.DOCUMENT,

    # Archives
    '.zip': FileType.ARCHIVE,
    '.tar': FileType.ARCHIVE,
    '.gz': FileType.ARCHIVE,
    '.bz2': FileType.ARCHIVE,
    '.xz': FileType.ARCHIVE,
    '.7z': FileType.ARCHIVE,
    '.rar': FileType.ARCHIVE,
    '.tar.gz': FileType.ARCHIVE,
    '.tgz': FileType.ARCHIVE,
    '.tar.bz2': FileType.ARCHIVE,
    '.tbz2': FileType.ARCHIVE,

    # Video
    '.mp4': FileType.VIDEO,
    '.avi': FileType.VIDEO,
    '.mkv': FileType.VIDEO,
    '.mov': FileType.VIDEO,
    '.wmv': FileType.VIDEO,
    '.flv': FileType.VIDEO,
    '.webm': FileType.VIDEO,
    '.m4v': FileType.VIDEO,
    '.mpg': FileType.VIDEO,
    '.mpeg': FileType.VIDEO,

    # Audio
    '.mp3': FileType.AUDIO,
    '.wav': FileType.AUDIO,
    '.flac': FileType.AUDIO,
    '.m4a': FileType.AUDIO,
    '.aac': FileType.AUDIO,
    '.ogg': FileType.AUDIO,
    '.wma': FileType.AUDIO,
    '.opus': FileType.AUDIO,

    # Executable
    '.exe': FileType.EXECUTABLE,
    '.dll': FileType.EXECUTABLE,
    '.so': FileType.EXECUTABLE,
    '.dylib': FileType.EXECUTABLE,
    '.app': FileType.EXECUTABLE,

    # Database
    '.db': FileType.DATABASE,
    '.sqlite': FileType.DATABASE,
    '.sqlite3': FileType.DATABASE,
    '.mdb': FileType.DATABASE,
}


class FileTypeDetector:
    """Detect file types using multiple methods."""

    @staticmethod
    def detect_type(path: Path) -> FileType:
        """Detect file type using multiple methods.

        Args:
            path: File path to analyze

        Returns:
            Detected file type
        """
        if not path.exists() or not path.is_file():
            return FileType.UNKNOWN

        # 1. Try magic bytes detection
        magic_type = FileTypeDetector._detect_by_magic(path)
        if magic_type != FileType.UNKNOWN:
            return magic_type

        # 2. Try extension-based detection
        ext_type = FileTypeDetector._detect_by_extension(path)
        if ext_type != FileType.UNKNOWN:
            return ext_type

        # 3. Try content analysis for text files
        text_type = FileTypeDetector._detect_text_encoding(path)
        if text_type == FileType.TEXT:
            return FileType.TEXT

        # 4. Default to binary
        return FileType.BINARY

    @staticmethod
    def _detect_by_magic(path: Path) -> FileType:
        """Detect file type by magic bytes.

        Args:
            path: File path

        Returns:
            Detected file type
        """
        try:
            with open(path, 'rb') as f:
                # Read first 512 bytes for magic detection
                header = f.read(512)

                # Check magic bytes
                for magic, file_type in MAGIC_BYTES.items():
                    if header.startswith(magic):
                        return file_type

                    # Special case: TAR has magic at offset 257
                    if magic == b'ustar' and len(header) > 257:
                        if header[257:257+5] == magic:
                            return FileType.ARCHIVE

        except Exception as e:
            logger.debug(f"Magic bytes detection failed for {path}: {e}")

        return FileType.UNKNOWN

    @staticmethod
    def _detect_by_extension(path: Path) -> FileType:
        """Detect file type by extension.

        Args:
            path: File path

        Returns:
            Detected file type
        """
        # Get extension (lowercase)
        ext = path.suffix.lower()

        # Check compound extensions (e.g., .tar.gz)
        if path.name.count('.') > 1:
            compound_ext = ''.join(path.suffixes[-2:]).lower()
            if compound_ext in EXTENSION_TYPES:
                return EXTENSION_TYPES[compound_ext]

        # Check simple extension
        if ext in EXTENSION_TYPES:
            return EXTENSION_TYPES[ext]

        return FileType.UNKNOWN

    @staticmethod
    def _detect_text_encoding(path: Path, sample_size: int = 8192) -> FileType:
        """Detect if file is text by checking encoding.

        Args:
            path: File path
            sample_size: Number of bytes to sample

        Returns:
            FileType.TEXT if text, FileType.UNKNOWN otherwise
        """
        try:
            with open(path, 'rb') as f:
                sample = f.read(sample_size)

            # Check for null bytes (indicator of binary)
            if b'\x00' in sample:
                return FileType.UNKNOWN

            # Try to decode as text
            try:
                sample.decode('utf-8')
                return FileType.TEXT
            except UnicodeDecodeError:
                # Try other encodings
                for encoding in ['latin-1', 'cp1252', 'ascii']:
                    try:
                        sample.decode(encoding)
                        return FileType.TEXT
                    except UnicodeDecodeError:
                        continue

        except Exception as e:
            logger.debug(f"Text encoding detection failed for {path}: {e}")

        return FileType.UNKNOWN

    @staticmethod
    def get_mime_type(path: Path) -> Optional[str]:
        """Get MIME type for file.

        Args:
            path: File path

        Returns:
            MIME type string or None
        """
        mime_type, _ = mimetypes.guess_type(str(path))
        return mime_type

    @staticmethod
    def is_text_file(path: Path) -> bool:
        """Check if file is text.

        Args:
            path: File path

        Returns:
            True if text file
        """
        file_type = FileTypeDetector.detect_type(path)
        return file_type in [FileType.TEXT, FileType.CODE, FileType.CONFIG]

    @staticmethod
    def is_binary_file(path: Path) -> bool:
        """Check if file is binary.

        Args:
            path: File path

        Returns:
            True if binary file
        """
        return not FileTypeDetector.is_text_file(path)

    @staticmethod
    def is_image(path: Path) -> bool:
        """Check if file is an image.

        Args:
            path: File path

        Returns:
            True if image file
        """
        return FileTypeDetector.detect_type(path) == FileType.IMAGE

    @staticmethod
    def is_archive(path: Path) -> bool:
        """Check if file is an archive.

        Args:
            path: File path

        Returns:
            True if archive file
        """
        return FileTypeDetector.detect_type(path) == FileType.ARCHIVE

    @staticmethod
    def get_preview_method(path: Path) -> str:
        """Get appropriate preview method for file.

        Args:
            path: File path

        Returns:
            Preview method name
        """
        file_type = FileTypeDetector.detect_type(path)

        preview_map = {
            FileType.TEXT: "text",
            FileType.CODE: "syntax_highlighted",
            FileType.CONFIG: "text",
            FileType.IMAGE: "image_ascii",
            FileType.ARCHIVE: "archive_listing",
            FileType.DOCUMENT: "document_preview",
            FileType.BINARY: "hex",
            FileType.DATABASE: "database_schema",
            FileType.UNKNOWN: "hex"
        }

        return preview_map.get(file_type, "hex")

    @staticmethod
    def get_file_category(path: Path) -> str:
        """Get user-friendly file category.

        Args:
            path: File path

        Returns:
            Category string
        """
        file_type = FileTypeDetector.detect_type(path)

        category_map = {
            FileType.TEXT: "Text Document",
            FileType.CODE: "Source Code",
            FileType.CONFIG: "Configuration",
            FileType.IMAGE: "Image",
            FileType.VIDEO: "Video",
            FileType.AUDIO: "Audio",
            FileType.ARCHIVE: "Archive",
            FileType.DOCUMENT: "Document",
            FileType.EXECUTABLE: "Executable",
            FileType.DATABASE: "Database",
            FileType.BINARY: "Binary File",
            FileType.UNKNOWN: "Unknown"
        }

        return category_map.get(file_type, "Unknown")
