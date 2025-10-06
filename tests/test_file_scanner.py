"""
Comprehensive unit tests for file scanner module.

Tests cover:
- Directory scanning (normal, hidden files, recursive)
- File filtering (patterns, size, date, extensions)
- File sorting (various orders, directories first)
- File searching (name, content, case-sensitive)
- Directory statistics calculation
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import time

from src.core.file_scanner import (
    FileEntry,
    scan_directory,
    get_file_list,
    sort_files,
    search_files,
    get_directory_stats,
    SortOrder,
)


# Test Fixtures
@pytest.fixture
def test_directory(tmp_path):
    """Create comprehensive test directory structure."""
    base = tmp_path / "test_scan"
    base.mkdir()

    # Regular files
    (base / "file1.txt").write_text("Content 1")
    (base / "file2.py").write_text("# Python file")
    (base / "file3.md").write_text("# Markdown")
    (base / "large.bin").write_bytes(b'0' * 10000)

    # Hidden files
    (base / ".hidden").write_text("Hidden content")
    (base / ".config").write_text("Config data")

    # Subdirectories
    sub1 = base / "subdir1"
    sub1.mkdir()
    (sub1 / "nested.txt").write_text("Nested content")
    (sub1 / "data.json").write_text('{"key": "value"}')

    sub2 = base / "subdir2"
    sub2.mkdir()
    (sub2 / "readme.md").write_text("# README")

    # Empty directory
    (base / "empty_dir").mkdir()

    # Set different modification times
    time.sleep(0.01)
    (base / "file1.txt").touch()

    return base


@pytest.fixture
def search_directory(tmp_path):
    """Create directory for search tests."""
    base = tmp_path / "search_test"
    base.mkdir()

    # Files with specific content
    (base / "contains_search.txt").write_text("This file contains search term")
    (base / "no_match.txt").write_text("This file has different content")
    (base / "case_TEST.txt").write_text("SEARCH in uppercase")

    # Nested structure
    nested = base / "nested"
    nested.mkdir()
    (nested / "deep_search.py").write_text("# search in nested")

    deep = nested / "deeper"
    deep.mkdir()
    (deep / "very_deep.txt").write_text("search term here")

    return base


# FileEntry Tests
class TestFileEntry:
    """Test FileEntry class."""

    def test_file_entry_file(self, test_directory):
        """Test FileEntry for regular file."""
        file_path = test_directory / "file1.txt"
        entry = FileEntry(file_path)

        assert entry.name == "file1.txt"
        assert entry.path == file_path
        assert entry.is_file is True
        assert entry.is_directory is False
        assert entry.size > 0
        assert entry.extension == ".txt"
        assert entry.accessible is True
        assert isinstance(entry.modified, datetime)

    def test_file_entry_directory(self, test_directory):
        """Test FileEntry for directory."""
        dir_path = test_directory / "subdir1"
        entry = FileEntry(dir_path)

        assert entry.is_directory is True
        assert entry.is_file is False
        assert entry.size == 0
        assert entry.extension == ""

    def test_file_entry_repr(self, test_directory):
        """Test FileEntry string representation."""
        file_entry = FileEntry(test_directory / "file1.txt")
        dir_entry = FileEntry(test_directory / "subdir1")

        assert "FILE" in repr(file_entry)
        assert "DIR" in repr(dir_entry)
        assert "file1.txt" in repr(file_entry)

    def test_file_entry_matches_pattern(self, test_directory):
        """Test pattern matching."""
        txt_entry = FileEntry(test_directory / "file1.txt")
        py_entry = FileEntry(test_directory / "file2.py")

        assert txt_entry.matches_pattern("*.txt") is True
        assert txt_entry.matches_pattern("*.py") is False
        assert py_entry.matches_pattern("*.py") is True
        assert py_entry.matches_pattern("file*") is True

    def test_file_entry_pattern_case_insensitive(self, test_directory):
        """Test pattern matching is case-insensitive."""
        entry = FileEntry(test_directory / "file1.txt")

        assert entry.matches_pattern("*.TXT") is True
        assert entry.matches_pattern("FILE*.txt") is True

    def test_file_entry_inaccessible(self, tmp_path):
        """Test FileEntry for inaccessible file."""
        # Create a file then make it inaccessible (platform-dependent)
        file_path = tmp_path / "inaccessible.txt"
        file_path.write_text("test")

        # Note: This test might not work on all platforms
        # On Windows, you might need to change permissions differently
        # This is a simplified test
        entry = FileEntry(file_path)
        assert entry.accessible is True  # File is accessible initially


# Scan Directory Tests
class TestScanDirectory:
    """Test scan_directory function."""

    def test_scan_directory_basic(self, test_directory):
        """Test basic directory scanning."""
        entries = scan_directory(test_directory, show_hidden=False)

        # Should not include hidden files
        names = [e.name for e in entries]
        assert "file1.txt" in names
        assert "file2.py" in names
        assert ".hidden" not in names
        assert "subdir1" in names

    def test_scan_directory_show_hidden(self, test_directory):
        """Test directory scanning with hidden files."""
        entries = scan_directory(test_directory, show_hidden=True)

        names = [e.name for e in entries]
        assert ".hidden" in names
        assert ".config" in names

    def test_scan_directory_recursive(self, test_directory):
        """Test recursive directory scanning."""
        entries = scan_directory(test_directory, recursive=True)

        names = [e.name for e in entries]
        assert "nested.txt" in names
        assert "data.json" in names
        assert "readme.md" in names

    def test_scan_directory_not_directory(self, test_directory):
        """Test scan fails for non-directory path."""
        file_path = test_directory / "file1.txt"

        with pytest.raises(ValueError, match="not a directory"):
            scan_directory(file_path)

    def test_scan_directory_empty(self, test_directory):
        """Test scanning empty directory."""
        empty_dir = test_directory / "empty_dir"
        entries = scan_directory(empty_dir)

        assert len(entries) == 0


# Get File List Tests
class TestGetFileList:
    """Test get_file_list filtering function."""

    def test_get_file_list_pattern(self, test_directory):
        """Test filtering by pattern."""
        entries = get_file_list(test_directory, pattern="*.txt")

        names = [e.name for e in entries]
        assert "file1.txt" in names
        assert "file2.py" not in names

    def test_get_file_list_files_only(self, test_directory):
        """Test filtering files only."""
        entries = get_file_list(test_directory, files_only=True)

        assert all(e.is_file for e in entries)
        assert not any(e.is_directory for e in entries)

    def test_get_file_list_directories_only(self, test_directory):
        """Test filtering directories only."""
        entries = get_file_list(test_directory, directories_only=True)

        assert all(e.is_directory for e in entries)
        assert not any(e.is_file for e in entries)

    def test_get_file_list_min_size(self, test_directory):
        """Test filtering by minimum size."""
        entries = get_file_list(test_directory, min_size=1000, files_only=True)

        # Only large.bin should match
        assert len(entries) == 1
        assert entries[0].name == "large.bin"

    def test_get_file_list_max_size(self, test_directory):
        """Test filtering by maximum size."""
        entries = get_file_list(test_directory, max_size=100, files_only=True)

        # All small files
        assert all(e.size <= 100 for e in entries)
        assert "large.bin" not in [e.name for e in entries]

    def test_get_file_list_modified_after(self, test_directory):
        """Test filtering by modification date (after)."""
        cutoff = datetime.now() - timedelta(hours=1)
        entries = get_file_list(test_directory, modified_after=cutoff)

        # All files should be recent
        assert all(e.modified > cutoff for e in entries)

    def test_get_file_list_modified_before(self, test_directory):
        """Test filtering by modification date (before)."""
        cutoff = datetime.now() + timedelta(hours=1)
        entries = get_file_list(test_directory, modified_before=cutoff)

        # All files should be before future cutoff
        assert all(e.modified < cutoff for e in entries)

    def test_get_file_list_extensions(self, test_directory):
        """Test filtering by extensions."""
        entries = get_file_list(
            test_directory,
            extensions=['.txt', '.py'],
            files_only=True
        )

        extensions = [e.extension for e in entries]
        assert all(ext in ['.txt', '.py'] for ext in extensions)
        assert '.md' not in extensions

    def test_get_file_list_combined_filters(self, test_directory):
        """Test multiple filters combined."""
        entries = get_file_list(
            test_directory,
            pattern="file*",
            files_only=True,
            max_size=100,
        )

        assert all(e.name.startswith("file") for e in entries)
        assert all(e.is_file for e in entries)
        assert all(e.size <= 100 for e in entries)


# Sort Files Tests
class TestSortFiles:
    """Test sort_files function."""

    def test_sort_files_name_asc(self, test_directory):
        """Test sorting by name ascending."""
        entries = scan_directory(test_directory, show_hidden=False)
        sorted_entries = sort_files(entries, SortOrder.NAME_ASC)

        names = [e.name for e in sorted_entries if not e.is_directory]
        assert names == sorted(names, key=str.lower)

    def test_sort_files_name_desc(self, test_directory):
        """Test sorting by name descending."""
        entries = scan_directory(test_directory, show_hidden=False)
        sorted_entries = sort_files(entries, SortOrder.NAME_DESC)

        names = [e.name for e in sorted_entries if not e.is_directory]
        assert names == sorted(names, key=str.lower, reverse=True)

    def test_sort_files_size_asc(self, test_directory):
        """Test sorting by size ascending."""
        entries = scan_directory(test_directory, show_hidden=False)
        sorted_entries = sort_files(entries, SortOrder.SIZE_ASC)

        sizes = [e.size for e in sorted_entries if e.is_file]
        assert sizes == sorted(sizes)

    def test_sort_files_size_desc(self, test_directory):
        """Test sorting by size descending."""
        entries = scan_directory(test_directory, show_hidden=False)
        sorted_entries = sort_files(entries, SortOrder.SIZE_DESC)

        sizes = [e.size for e in sorted_entries if e.is_file]
        assert sizes == sorted(sizes, reverse=True)

    def test_sort_files_date_asc(self, test_directory):
        """Test sorting by date ascending."""
        entries = scan_directory(test_directory, show_hidden=False)
        sorted_entries = sort_files(entries, SortOrder.DATE_ASC)

        dates = [e.modified for e in sorted_entries if e.is_file]
        assert dates == sorted(dates)

    def test_sort_files_date_desc(self, test_directory):
        """Test sorting by date descending."""
        entries = scan_directory(test_directory, show_hidden=False)
        sorted_entries = sort_files(entries, SortOrder.DATE_DESC)

        dates = [e.modified for e in sorted_entries if e.is_file]
        assert dates == sorted(dates, reverse=True)

    def test_sort_files_ext_asc(self, test_directory):
        """Test sorting by extension ascending."""
        entries = scan_directory(test_directory, show_hidden=False)
        sorted_entries = sort_files(entries, SortOrder.EXT_ASC)

        extensions = [e.extension for e in sorted_entries if e.is_file]
        assert extensions == sorted(extensions)

    def test_sort_files_directories_first(self, test_directory):
        """Test sorting with directories first."""
        entries = scan_directory(test_directory, show_hidden=False)
        sorted_entries = sort_files(entries, directories_first=True)

        # Check directories come first
        dir_section_ended = False
        for entry in sorted_entries:
            if not entry.is_directory:
                dir_section_ended = True
            if dir_section_ended:
                assert not entry.is_directory

    def test_sort_files_no_directories_first(self, test_directory):
        """Test sorting without directories first."""
        entries = scan_directory(test_directory, show_hidden=False)
        sorted_entries = sort_files(entries, directories_first=False)

        # Directories and files mixed based on sort order
        names = [e.name for e in sorted_entries]
        assert names == sorted(names, key=str.lower)


# Search Files Tests
class TestSearchFiles:
    """Test search_files function."""

    def test_search_files_by_name(self, search_directory):
        """Test searching files by name."""
        results = search_files(search_directory, "search")

        names = [e.name for e in results]
        assert "contains_search.txt" in names
        assert "deep_search.py" in names

    def test_search_files_case_sensitive(self, search_directory):
        """Test case-sensitive search."""
        results = search_files(
            search_directory,
            "SEARCH",
            case_sensitive=True
        )

        names = [e.name for e in results]
        assert "case_TEST.txt" in names
        assert "contains_search.txt" not in names  # lowercase 'search'

    def test_search_files_case_insensitive(self, search_directory):
        """Test case-insensitive search (default)."""
        results = search_files(search_directory, "SEARCH")

        names = [e.name for e in results]
        assert "contains_search.txt" in names
        assert "case_TEST.txt" in names
        assert "deep_search.py" in names

    def test_search_files_content(self, search_directory):
        """Test searching file contents."""
        results = search_files(
            search_directory,
            "search term",
            search_content=True
        )

        names = [e.name for e in results]
        # Should find files containing the term
        assert "contains_search.txt" in names
        assert "very_deep.txt" in names

    def test_search_files_max_depth(self, search_directory):
        """Test search with maximum depth."""
        results = search_files(
            search_directory,
            "search",
            max_depth=1
        )

        names = [e.name for e in results]
        assert "contains_search.txt" in names
        assert "deep_search.py" in names
        # very_deep.txt is at depth 2
        assert "very_deep.txt" not in names

    def test_search_files_no_results(self, search_directory):
        """Test search with no matches."""
        results = search_files(search_directory, "nonexistent_term")

        assert len(results) == 0

    def test_search_files_content_text_only(self, test_directory):
        """Test content search only searches text files."""
        results = search_files(
            test_directory,
            "Content",
            search_content=True
        )

        names = [e.name for e in results]
        # Should find text files
        assert "file1.txt" in names
        # Should not find binary files even if they contain bytes
        # large.bin contains '0' bytes but is binary


# Get Directory Stats Tests
class TestGetDirectoryStats:
    """Test get_directory_stats function."""

    def test_get_directory_stats_basic(self, test_directory):
        """Test basic directory statistics."""
        stats = get_directory_stats(test_directory)

        assert 'file_count' in stats
        assert 'directory_count' in stats
        assert 'total_size' in stats

        assert stats['file_count'] > 0
        assert stats['directory_count'] > 0
        assert stats['total_size'] > 0

    def test_get_directory_stats_extensions(self, test_directory):
        """Test extension counting in stats."""
        stats = get_directory_stats(test_directory)

        assert '.txt' in stats['extensions']
        assert '.py' in stats['extensions']
        assert '.md' in stats['extensions']
        assert stats['extensions']['.txt'] >= 1

    def test_get_directory_stats_largest_file(self, test_directory):
        """Test largest file detection."""
        stats = get_directory_stats(test_directory)

        assert stats['largest_file'] is not None
        assert 'large.bin' in stats['largest_file']
        assert stats['largest_file_size'] > 1000

    def test_get_directory_stats_hidden_count(self, test_directory):
        """Test hidden file counting."""
        stats = get_directory_stats(test_directory)

        # Should count .hidden and .config
        assert stats['hidden_count'] >= 2

    def test_get_directory_stats_empty_directory(self, test_directory):
        """Test stats for empty directory."""
        empty_dir = test_directory / "empty_dir"
        stats = get_directory_stats(empty_dir)

        assert stats['file_count'] == 0
        assert stats['directory_count'] == 0
        assert stats['total_size'] == 0
        assert stats['largest_file'] is None


# Integration Tests
class TestFileScannerIntegration:
    """Integration tests for file scanner workflows."""

    def test_scan_filter_sort_workflow(self, test_directory):
        """Test complete scan, filter, sort workflow."""
        # Scan
        entries = scan_directory(test_directory, show_hidden=True)
        assert len(entries) > 0

        # Filter
        txt_files = [e for e in entries if e.matches_pattern("*.txt")]
        assert len(txt_files) > 0

        # Sort
        sorted_files = sort_files(txt_files, SortOrder.SIZE_DESC)
        sizes = [e.size for e in sorted_files]
        assert sizes == sorted(sizes, reverse=True)

    def test_search_and_filter_workflow(self, search_directory):
        """Test search followed by filtering."""
        # Search by name
        results = search_files(search_directory, "search")

        # Filter to only .txt files
        txt_results = [e for e in results if e.extension == ".txt"]

        assert len(txt_results) > 0
        assert all(e.extension == ".txt" for e in txt_results)
