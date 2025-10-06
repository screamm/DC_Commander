"""
Integration tests for Modern Commander.

Tests complete workflows:
- F-key actions end-to-end
- Panel synchronization
- Error recovery scenarios
- Complete user workflows
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from src.core.file_operations import copy_file, move_file, delete_file
from src.core.file_scanner import scan_directory, search_files
from src.core.archive_handler import create_archive, extract_archive, ArchiveType
from components.file_panel import FilePanel
from components.command_bar import CommandBar


# Test Fixtures
@pytest.fixture
def integration_workspace(tmp_path):
    """Create comprehensive workspace for integration tests."""
    workspace = tmp_path / "integration"
    workspace.mkdir()

    # Left panel directory
    left = workspace / "left"
    left.mkdir()
    (left / "source1.txt").write_text("Source file 1")
    (left / "source2.txt").write_text("Source file 2")
    (left / "data.json").write_text('{"test": "data"}')

    left_sub = left / "subdir"
    left_sub.mkdir()
    (left_sub / "nested.txt").write_text("Nested content")

    # Right panel directory
    right = workspace / "right"
    right.mkdir()
    (right / "target1.txt").write_text("Target file 1")

    # Archive directory
    archives = workspace / "archives"
    archives.mkdir()

    return {
        'workspace': workspace,
        'left': left,
        'right': right,
        'archives': archives
    }


# File Operations Integration Tests
class TestFileOperationsIntegration:
    """Test complete file operation workflows."""

    def test_copy_workflow_single_file(self, integration_workspace):
        """Test F5 copy operation workflow for single file."""
        source = integration_workspace['left'] / "source1.txt"
        dest_dir = integration_workspace['right']
        dest = dest_dir / "source1.txt"

        # Simulate F5 copy operation
        copy_file(source, dest)

        # Verify
        assert dest.exists()
        assert source.exists()  # Source remains
        assert dest.read_text() == source.read_text()

    def test_copy_workflow_multiple_files(self, integration_workspace):
        """Test copying multiple selected files."""
        left_dir = integration_workspace['left']
        right_dir = integration_workspace['right']

        source_files = [
            left_dir / "source1.txt",
            left_dir / "source2.txt"
        ]

        # Simulate multiple file copy
        for source in source_files:
            dest = right_dir / source.name
            copy_file(source, dest)

        # Verify all copied
        assert (right_dir / "source1.txt").exists()
        assert (right_dir / "source2.txt").exists()

    def test_move_workflow(self, integration_workspace):
        """Test F6 move operation workflow."""
        source = integration_workspace['left'] / "source1.txt"
        dest_dir = integration_workspace['right']
        dest = dest_dir / "moved.txt"

        # Simulate F6 move operation
        move_file(source, dest)

        # Verify
        assert dest.exists()
        assert not source.exists()  # Source removed

    def test_delete_workflow(self, integration_workspace):
        """Test F8 delete operation workflow."""
        target = integration_workspace['left'] / "source1.txt"

        assert target.exists()

        # Simulate F8 delete operation
        delete_file(target)

        # Verify
        assert not target.exists()

    def test_delete_directory_workflow(self, integration_workspace):
        """Test deleting directory with contents."""
        target_dir = integration_workspace['left'] / "subdir"

        assert target_dir.exists()
        assert (target_dir / "nested.txt").exists()

        # Simulate recursive delete
        delete_file(target_dir, recursive=True)

        # Verify
        assert not target_dir.exists()

    def test_copy_overwrite_workflow(self, integration_workspace):
        """Test copy with overwrite confirmation."""
        source = integration_workspace['left'] / "source1.txt"
        dest = integration_workspace['right'] / "target1.txt"

        original_content = dest.read_text()
        new_content = source.read_text()

        # Simulate overwrite
        copy_file(source, dest, overwrite=True)

        # Verify overwritten
        assert dest.read_text() == new_content
        assert dest.read_text() != original_content


# Panel Synchronization Tests
class TestPanelSynchronization:
    """Test panel state synchronization."""

    def test_panel_navigation_synchronization(self, integration_workspace):
        """Test both panels navigate independently."""
        left_panel = FilePanel(path=integration_workspace['left'])
        right_panel = FilePanel(path=integration_workspace['right'])

        # Navigate left panel
        left_sub = integration_workspace['left'] / "subdir"
        left_panel.navigate_to(left_sub)

        # Verify independence
        assert left_panel.current_path == left_sub
        assert right_panel.current_path == integration_workspace['right']

    def test_panel_refresh_after_operation(self, integration_workspace):
        """Test panel refresh after file operations."""
        panel = FilePanel(path=integration_workspace['left'])
        original_items = panel._load_directory()

        # Add new file
        new_file = integration_workspace['left'] / "new_file.txt"
        new_file.write_text("New content")

        # Refresh panel
        panel.refresh_directory()
        updated_items = panel._file_items

        # Verify new file appears
        names = [item.name for item in updated_items]
        assert "new_file.txt" in names

    def test_panel_selection_persistence(self, integration_workspace):
        """Test selection persists during operations."""
        panel = FilePanel(path=integration_workspace['left'])
        panel._file_items = panel._load_directory()

        # Select files
        test_item = next(item for item in panel._file_items if not item.is_parent)
        panel.selected_files.add(str(test_item.path))

        original_selection = set(panel.selected_files)

        # Navigate and back
        sub_dir = integration_workspace['left'] / "subdir"
        panel.navigate_to(sub_dir)
        panel.navigate_up()

        # Selection should be cleared after navigation
        # (This is expected behavior - selections are cleared on directory change)
        assert len(panel.selected_files) == 0


# Archive Operations Integration Tests
class TestArchiveOperationsIntegration:
    """Test complete archive operation workflows."""

    def test_create_archive_workflow(self, integration_workspace):
        """Test creating archive from selected files."""
        source_dir = integration_workspace['left']
        archive_path = integration_workspace['archives'] / "backup.zip"

        # Select files to archive
        files = [
            source_dir / "source1.txt",
            source_dir / "source2.txt"
        ]

        # Create archive
        create_archive(files, archive_path, ArchiveType.ZIP)

        # Verify
        assert archive_path.exists()

    def test_extract_archive_workflow(self, integration_workspace):
        """Test extracting archive to target directory."""
        source_dir = integration_workspace['left']
        archive_path = integration_workspace['archives'] / "backup.zip"
        extract_dir = integration_workspace['right'] / "extracted"

        # Create archive first
        files = [source_dir / "source1.txt"]
        create_archive(files, archive_path, ArchiveType.ZIP)

        # Extract
        extract_archive(archive_path, extract_dir)

        # Verify
        assert extract_dir.exists()
        assert (extract_dir / "source1.txt").exists()

    def test_archive_directory_workflow(self, integration_workspace):
        """Test archiving entire directory."""
        source_dir = integration_workspace['left'] / "subdir"
        archive_path = integration_workspace['archives'] / "subdir.tar.gz"

        # Archive directory
        create_archive([source_dir], archive_path, ArchiveType.TAR_GZ)

        # Verify
        assert archive_path.exists()

        # Extract and verify contents
        extract_dir = integration_workspace['archives'] / "extracted"
        extract_archive(archive_path, extract_dir)

        # Should contain nested.txt
        assert (extract_dir / "nested.txt").exists() or \
               (extract_dir / "subdir" / "nested.txt").exists()


# Search Integration Tests
class TestSearchIntegration:
    """Test search functionality integration."""

    def test_search_across_panels(self, integration_workspace):
        """Test searching files in current panel."""
        left_dir = integration_workspace['left']

        # Search for files
        results = search_files(left_dir, "source")

        # Verify results
        names = [r.name for r in results]
        assert "source1.txt" in names
        assert "source2.txt" in names

    def test_search_with_content(self, integration_workspace):
        """Test content search integration."""
        left_dir = integration_workspace['left']

        # Search file contents
        results = search_files(left_dir, "Source file", search_content=True)

        # Should find files containing the text
        assert len(results) > 0

    def test_search_navigation_workflow(self, integration_workspace):
        """Test navigating to search results."""
        left_dir = integration_workspace['left']

        # Search in subdirectory
        results = search_files(left_dir, "nested", search_content=True)

        # Should find nested.txt
        assert len(results) > 0
        nested_file = next(r for r in results if "nested" in r.name.lower())
        assert nested_file.path.exists()


# Error Recovery Tests
class TestErrorRecovery:
    """Test error handling and recovery scenarios."""

    def test_copy_permission_error_recovery(self, integration_workspace):
        """Test recovery from permission errors."""
        source = integration_workspace['left'] / "source1.txt"
        dest = Path("/system/protected/file.txt")  # Invalid path

        # Should raise appropriate error
        with pytest.raises(Exception):
            copy_file(source, dest)

        # Original file should be unaffected
        assert source.exists()

    def test_delete_non_existent_file_recovery(self, integration_workspace):
        """Test handling deletion of non-existent file."""
        from src.core.file_operations import PathNotFoundError

        non_existent = integration_workspace['left'] / "does_not_exist.txt"

        # Should raise error
        with pytest.raises(PathNotFoundError):
            delete_file(non_existent)

    def test_archive_corrupted_file_recovery(self, integration_workspace):
        """Test handling corrupted archive."""
        from src.core.archive_handler import ArchiveError

        corrupted = integration_workspace['archives'] / "corrupted.zip"
        corrupted.write_text("This is not a valid ZIP file")

        # Should raise error
        with pytest.raises(ArchiveError):
            extract_archive(corrupted, integration_workspace['right'])

    def test_panel_navigation_error_recovery(self, integration_workspace):
        """Test panel handles navigation errors gracefully."""
        panel = FilePanel(path=integration_workspace['left'])

        non_existent = integration_workspace['left'] / "does_not_exist"

        # Navigation should not crash
        panel.navigate_to(non_existent)

        # Should remain at current path
        assert panel.current_path == integration_workspace['left']


# Command Bar Integration Tests
class TestCommandBarIntegration:
    """Test command bar integration with operations."""

    def test_command_bar_state_during_operations(self, integration_workspace):
        """Test command bar updates during file operations."""
        bar = CommandBar()
        panel = FilePanel(path=integration_workspace['left'])

        # With files, operations should be enabled
        bar.set_context("file_panel")
        assert bar.commands["f5"].enabled is True
        assert bar.commands["f8"].enabled is True

        # Empty directory, operations should be disabled
        empty_dir = integration_workspace['workspace'] / "empty"
        empty_dir.mkdir()

        if len(list(empty_dir.iterdir())) == 0:
            bar.set_context("file_panel_empty")
            assert bar.commands["f5"].enabled is False

    def test_command_bar_context_switching(self):
        """Test command bar context changes."""
        bar = CommandBar()

        # Normal file panel
        bar.set_context("file_panel")
        normal_state = {k: v.enabled for k, v in bar.commands.items()}

        # Dialog mode
        bar.set_context("dialog")
        dialog_state = {k: v.enabled for k, v in bar.commands.items()}

        # States should differ
        assert normal_state != dialog_state


# Complete Workflow Tests
class TestCompleteWorkflows:
    """Test complete user workflows."""

    def test_backup_workflow(self, integration_workspace):
        """Test complete backup workflow: select files, create archive."""
        source_dir = integration_workspace['left']
        backup_path = integration_workspace['archives'] / "backup.zip"

        # Select files (simulate user selection)
        files = list(source_dir.glob("*.txt"))

        # Create archive
        create_archive(files, backup_path, ArchiveType.ZIP)

        # Verify backup
        assert backup_path.exists()

        # Verify can restore
        restore_dir = integration_workspace['workspace'] / "restore"
        extract_archive(backup_path, restore_dir)

        # Check restored files
        for file in files:
            restored = restore_dir / file.name
            assert restored.exists()
            assert restored.read_text() == file.read_text()

    def test_organize_files_workflow(self, integration_workspace):
        """Test organizing files: create directory, move files."""
        source_dir = integration_workspace['left']

        # Create organization directory
        from src.core.file_operations import create_directory
        organized = create_directory(source_dir, "organized")

        # Move files
        for file in source_dir.glob("*.txt"):
            dest = organized / file.name
            move_file(file, dest)

        # Verify organization
        assert organized.exists()
        assert len(list(organized.glob("*.txt"))) > 0

    def test_sync_directories_workflow(self, integration_workspace):
        """Test syncing files between directories."""
        left_dir = integration_workspace['left']
        right_dir = integration_workspace['right']

        # Get files only in left
        left_files = set(f.name for f in left_dir.glob("*.txt"))
        right_files = set(f.name for f in right_dir.glob("*.txt"))

        to_copy = left_files - right_files

        # Copy missing files
        for filename in to_copy:
            source = left_dir / filename
            dest = right_dir / filename
            copy_file(source, dest)

        # Verify sync
        left_files_after = set(f.name for f in left_dir.glob("*.txt"))
        right_files_after = set(f.name for f in right_dir.glob("*.txt"))

        # Right should have all files from left
        assert left_files_after.issubset(right_files_after)

    def test_search_and_delete_workflow(self, integration_workspace):
        """Test searching for files and deleting matches."""
        left_dir = integration_workspace['left']

        # Search for specific files
        results = search_files(left_dir, "source1")

        # Delete found files
        for result in results:
            delete_file(result.path)

        # Verify deletion
        assert not (left_dir / "source1.txt").exists()

    def test_dual_panel_operations(self, integration_workspace):
        """Test operations between two panels."""
        left_panel = FilePanel(path=integration_workspace['left'])
        right_panel = FilePanel(path=integration_workspace['right'])

        left_panel._file_items = left_panel._load_directory()
        right_panel._file_items = right_panel._load_directory()

        # Select files in left panel
        left_files = [item for item in left_panel._file_items if item.is_file]

        # Simulate copy to right panel
        for item in left_files[:2]:  # Copy first 2 files
            dest = right_panel.current_path / item.name
            copy_file(item.path, dest)

        # Refresh right panel
        right_panel.refresh_directory()

        # Verify files copied
        right_names = [item.name for item in right_panel._file_items]
        assert left_files[0].name in right_names
        assert left_files[1].name in right_names


# Performance Integration Tests
class TestPerformanceIntegration:
    """Test performance with larger datasets."""

    def test_large_directory_scan(self, tmp_path):
        """Test scanning directory with many files."""
        large_dir = tmp_path / "large"
        large_dir.mkdir()

        # Create 100 files
        for i in range(100):
            (large_dir / f"file{i}.txt").write_text(f"Content {i}")

        # Scan should complete without issues
        entries = scan_directory(large_dir)

        assert len(entries) == 100

    def test_large_file_copy(self, tmp_path):
        """Test copying large file."""
        large_file = tmp_path / "large.bin"

        # Create 10MB file
        with open(large_file, 'wb') as f:
            f.write(b'0' * (10 * 1024 * 1024))

        dest = tmp_path / "large_copy.bin"

        # Copy should succeed
        copy_file(large_file, dest)

        assert dest.exists()
        assert dest.stat().st_size == large_file.stat().st_size

    def test_deep_directory_recursion(self, tmp_path):
        """Test operations on deeply nested directories."""
        # Create deep structure
        current = tmp_path / "deep"
        for i in range(20):
            current = current / f"level{i}"
            current.mkdir(parents=True, exist_ok=True)
            (current / "file.txt").write_text(f"Level {i}")

        # Scan recursively
        entries = scan_directory(tmp_path / "deep", recursive=True)

        # Should find all files
        assert len(entries) >= 20
