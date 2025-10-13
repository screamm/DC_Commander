"""Encoding detection utilities for DC Commander."""

from pathlib import Path
from typing import Optional


def is_binary_file(file_path: Path, chunk_size: int = 8192) -> bool:
    """Check if a file is binary."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(chunk_size)
        if b'\x00' in chunk:
            return True
        try:
            chunk.decode('utf-8')
            return False
        except UnicodeDecodeError:
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    chunk.decode(encoding)
                    return False
                except UnicodeDecodeError:
                    continue
            return True
    except Exception:
        return True


def detect_encoding(file_path: Path) -> Optional[str]:
    """Detect the encoding of a text file."""
    if is_binary_file(file_path):
        return None
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)
        for encoding in encodings:
            try:
                chunk.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue
        return 'utf-8'
    except Exception:
        return None
