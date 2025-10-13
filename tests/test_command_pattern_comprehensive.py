"""Comprehensive tests for Command Pattern implementation.

Tests undo/redo functionality for file operations including
copy, move, delete, create directory, and rename operations.
"""

import pytest
from pathlib import Path
from patterns.command_pattern import (
    CopyFileCommand,
    MoveFileCommand,
    DeleteFileCommand,
    CreateDirectoryCommand,
    RenameFileCommand,
    CommandHistory
)


class TestCopyFileCommand:
    """Test CopyFileCommand operations."""

    def test_execute_file_copy(self, tmp_path):
        """Test executing file copy command."""
        source = tmp_path / "source.txt"
        source.write_text("Test content")

        dest = tmp_path / "dest.txt"

        cmd = CopyFileCommand(source, dest)
        result = cmd.execute()

        assert result is True
        assert dest.exists()
        assert dest.read_text() == "Test content"

    def test_execute_directory_copy(self, tmp_path):
        """Test executing directory copy command."""
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")

        dest_dir = tmp_path / "dest_dir"

        cmd = CopyFileCommand(source_dir, dest_dir)
        result = cmd.execute()

        assert result is True
        assert dest_dir.exists()
        assert (dest_dir / "file.txt").exists()

    def test_undo_file_copy(self, tmp_path):
        """Test undoing file copy."""
        source = tmp_path / "source.txt"
        source.write_text("Test content")

        dest = tmp_path / "dest.txt"

        cmd = CopyFileCommand(source, dest)
        cmd.execute()

        result = cmd.undo()

        assert result is True
        assert not dest.exists()
        assert source.exists()  # Source should remain

    def test_undo_directory_copy(self, tmp_path):
        """Test undoing directory copy."""
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")

        dest_dir = tmp_path / "dest_dir"

        cmd = CopyFileCommand(source_dir, dest_dir)
        cmd.execute()
        cmd.undo()

        assert not dest_dir.exists()

    def test_undo_without_execute(self, tmp_path):
        """Test undo fails if execute wasn't called."""
        source = tmp_path / "source.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        cmd = CopyFileCommand(source, dest)
        result = cmd.undo()

        assert result is False

    def test_execute_nonexistent_source(self, tmp_path):
        """Test execute fails with nonexistent source."""
        source = tmp_path / "nonexistent.txt"
        dest = tmp_path / "dest.txt"

        cmd = CopyFileCommand(source, dest)
        result = cmd.execute()

        assert result is False

    def test_description(self, tmp_path):
        """Test command description."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "subdir" / "dest.txt"

        cmd = CopyFileCommand(source, dest)
        desc = cmd.description()

        assert "Copy" in desc
        assert "source.txt" in desc


class TestMoveFileCommand:
    """Test MoveFileCommand operations."""

    def test_execute_move(self, tmp_path):
        """Test executing move command."""
        source = tmp_path / "source.txt"
        source.write_text("Test content")

        dest = tmp_path / "dest.txt"

        cmd = MoveFileCommand(source, dest)
        result = cmd.execute()

        assert result is True
        assert not source.exists()
        assert dest.exists()
        assert dest.read_text() == "Test content"

    def test_undo_move(self, tmp_path):
        """Test undoing move."""
        source = tmp_path / "source.txt"
        source.write_text("Test content")

        dest = tmp_path / "dest.txt"

        cmd = MoveFileCommand(source, dest)
        cmd.execute()
        result = cmd.undo()

        assert result is True
        assert source.exists()
        assert not dest.exists()

    def test_undo_without_execute(self, tmp_path):
        """Test undo fails if execute wasn't called."""
        source = tmp_path / "source.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        cmd = MoveFileCommand(source, dest)
        result = cmd.undo()

        assert result is False

    def test_execute_nonexistent_source(self, tmp_path):
        """Test execute fails with nonexistent source."""
        source = tmp_path / "nonexistent.txt"
        dest = tmp_path / "dest.txt"

        cmd = MoveFileCommand(source, dest)
        result = cmd.execute()

        assert result is False

    def test_description(self, tmp_path):
        """Test command description."""
        source = tmp_path / "source.txt"
        dest = tmp_path / "subdir" / "dest.txt"

        cmd = MoveFileCommand(source, dest)
        desc = cmd.description()

        assert "Move" in desc
        assert "source.txt" in desc


class TestDeleteFileCommand:
    """Test DeleteFileCommand operations."""

    def test_execute_delete_file(self, tmp_path):
        """Test executing delete command."""
        file_path = tmp_path / "delete_me.txt"
        file_path.write_text("Delete this")

        cmd = DeleteFileCommand(file_path)
        result = cmd.execute()

        assert result is True
        assert not file_path.exists()

    def test_execute_delete_directory(self, tmp_path):
        """Test deleting directory."""
        dir_path = tmp_path / "delete_dir"
        dir_path.mkdir()
        (dir_path / "file.txt").write_text("content")

        cmd = DeleteFileCommand(dir_path)
        result = cmd.execute()

        assert result is True
        assert not dir_path.exists()

    def test_undo_restore_file(self, tmp_path):
        """Test undoing delete restores file."""
        file_path = tmp_path / "file.txt"
        original_content = "Original content"
        file_path.write_text(original_content)

        cmd = DeleteFileCommand(file_path)
        cmd.execute()

        result = cmd.undo()

        assert result is True
        assert file_path.exists()
        assert file_path.read_text() == original_content

    def test_undo_restore_directory(self, tmp_path):
        """Test undoing delete restores directory."""
        dir_path = tmp_path / "dir"
        dir_path.mkdir()
        (dir_path / "file.txt").write_text("content")

        cmd = DeleteFileCommand(dir_path)
        cmd.execute()
        cmd.undo()

        assert dir_path.exists()
        assert (dir_path / "file.txt").exists()

    def test_undo_without_execute(self, tmp_path):
        """Test undo fails if execute wasn't called."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        cmd = DeleteFileCommand(file_path)
        result = cmd.undo()

        assert result is False

    def test_custom_backup_dir(self, tmp_path):
        """Test delete with custom backup directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        backup_dir = tmp_path / "custom_backup"

        cmd = DeleteFileCommand(file_path, backup_dir=backup_dir)
        cmd.execute()

        assert backup_dir.exists()

    def test_description(self, tmp_path):
        """Test command description."""
        file_path = tmp_path / "file.txt"

        cmd = DeleteFileCommand(file_path)
        desc = cmd.description()

        assert "Delete" in desc
        assert "file.txt" in desc


class TestCreateDirectoryCommand:
    """Test CreateDirectoryCommand operations."""

    def test_execute_create_directory(self, tmp_path):
        """Test executing create directory command."""
        new_dir = tmp_path / "new_directory"

        cmd = CreateDirectoryCommand(new_dir)
        result = cmd.execute()

        assert result is True
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_undo_remove_directory(self, tmp_path):
        """Test undoing create directory."""
        new_dir = tmp_path / "new_directory"

        cmd = CreateDirectoryCommand(new_dir)
        cmd.execute()

        result = cmd.undo()

        assert result is True
        assert not new_dir.exists()

    def test_execute_existing_directory(self, tmp_path):
        """Test execute fails if directory exists."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        cmd = CreateDirectoryCommand(existing_dir)
        result = cmd.execute()

        assert result is False

    def test_undo_without_execute(self, tmp_path):
        """Test undo fails if execute wasn't called."""
        new_dir = tmp_path / "new_directory"

        cmd = CreateDirectoryCommand(new_dir)
        result = cmd.undo()

        assert result is False

    def test_description(self, tmp_path):
        """Test command description."""
        new_dir = tmp_path / "new_directory"

        cmd = CreateDirectoryCommand(new_dir)
        desc = cmd.description()

        assert "Create directory" in desc
        assert "new_directory" in desc


class TestRenameFileCommand:
    """Test RenameFileCommand operations."""

    def test_execute_rename_file(self, tmp_path):
        """Test executing rename command."""
        old_path = tmp_path / "old_name.txt"
        old_path.write_text("content")

        cmd = RenameFileCommand(old_path, "new_name.txt")
        result = cmd.execute()

        assert result is True
        assert not old_path.exists()
        assert (tmp_path / "new_name.txt").exists()

    def test_execute_rename_directory(self, tmp_path):
        """Test renaming directory."""
        old_dir = tmp_path / "old_dir"
        old_dir.mkdir()

        cmd = RenameFileCommand(old_dir, "new_dir")
        result = cmd.execute()

        assert result is True
        assert not old_dir.exists()
        assert (tmp_path / "new_dir").exists()

    def test_undo_rename(self, tmp_path):
        """Test undoing rename."""
        old_path = tmp_path / "old_name.txt"
        old_path.write_text("content")

        cmd = RenameFileCommand(old_path, "new_name.txt")
        cmd.execute()

        result = cmd.undo()

        assert result is True
        assert old_path.exists()
        assert not (tmp_path / "new_name.txt").exists()

    def test_execute_target_exists(self, tmp_path):
        """Test execute fails if target exists."""
        old_path = tmp_path / "old.txt"
        old_path.write_text("old")

        existing = tmp_path / "existing.txt"
        existing.write_text("existing")

        cmd = RenameFileCommand(old_path, "existing.txt")
        result = cmd.execute()

        assert result is False

    def test_undo_without_execute(self, tmp_path):
        """Test undo fails if execute wasn't called."""
        old_path = tmp_path / "old.txt"
        old_path.write_text("content")

        cmd = RenameFileCommand(old_path, "new.txt")
        result = cmd.undo()

        assert result is False

    def test_description(self, tmp_path):
        """Test command description."""
        old_path = tmp_path / "old.txt"

        cmd = RenameFileCommand(old_path, "new.txt")
        desc = cmd.description()

        assert "Rename" in desc
        assert "old.txt" in desc
        assert "new.txt" in desc


class TestCommandHistory:
    """Test CommandHistory operations."""

    def test_init_default(self):
        """Test default initialization."""
        history = CommandHistory()

        assert history.max_history == 100
        assert history._current_index == -1
        assert len(history._history) == 0

    def test_init_custom_max_history(self):
        """Test initialization with custom max history."""
        history = CommandHistory(max_history=50)

        assert history.max_history == 50

    def test_execute_command(self, tmp_path):
        """Test executing command through history."""
        history = CommandHistory()

        source = tmp_path / "source.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        cmd = CopyFileCommand(source, dest)
        result = history.execute_command(cmd)

        assert result is True
        assert dest.exists()
        assert history._current_index == 0
        assert len(history._history) == 1

    def test_execute_multiple_commands(self, tmp_path):
        """Test executing multiple commands."""
        history = CommandHistory()

        for i in range(3):
            source = tmp_path / f"source{i}.txt"
            source.write_text(f"content{i}")

            dest = tmp_path / f"dest{i}.txt"

            cmd = CopyFileCommand(source, dest)
            history.execute_command(cmd)

        assert len(history._history) == 3
        assert history._current_index == 2

    def test_undo_single_command(self, tmp_path):
        """Test undoing single command."""
        history = CommandHistory()

        source = tmp_path / "source.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        cmd = CopyFileCommand(source, dest)
        history.execute_command(cmd)

        result = history.undo()

        assert result is True
        assert not dest.exists()
        assert history._current_index == -1

    def test_undo_multiple_commands(self, tmp_path):
        """Test undoing multiple commands."""
        history = CommandHistory()

        # Execute 3 commands
        for i in range(3):
            source = tmp_path / f"source{i}.txt"
            source.write_text(f"content{i}")

            dest = tmp_path / f"dest{i}.txt"

            cmd = CopyFileCommand(source, dest)
            history.execute_command(cmd)

        # Undo 2 commands
        history.undo()
        history.undo()

        assert history._current_index == 0
        assert (tmp_path / "dest0.txt").exists()
        assert not (tmp_path / "dest1.txt").exists()
        assert not (tmp_path / "dest2.txt").exists()

    def test_redo_single_command(self, tmp_path):
        """Test redoing single command."""
        history = CommandHistory()

        source = tmp_path / "source.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        cmd = CopyFileCommand(source, dest)
        history.execute_command(cmd)
        history.undo()

        result = history.redo()

        assert result is True
        assert dest.exists()
        assert history._current_index == 0

    def test_redo_multiple_commands(self, tmp_path):
        """Test redoing multiple commands."""
        history = CommandHistory()

        # Execute and undo 3 commands
        for i in range(3):
            source = tmp_path / f"source{i}.txt"
            source.write_text(f"content{i}")

            dest = tmp_path / f"dest{i}.txt"

            cmd = CopyFileCommand(source, dest)
            history.execute_command(cmd)

        history.undo()
        history.undo()
        history.undo()

        # Redo 2 commands
        history.redo()
        history.redo()

        assert history._current_index == 1
        assert (tmp_path / "dest0.txt").exists()
        assert (tmp_path / "dest1.txt").exists()
        assert not (tmp_path / "dest2.txt").exists()

    def test_can_undo(self, tmp_path):
        """Test can_undo method."""
        history = CommandHistory()

        assert history.can_undo() is False

        source = tmp_path / "source.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        cmd = CopyFileCommand(source, dest)
        history.execute_command(cmd)

        assert history.can_undo() is True

        history.undo()

        assert history.can_undo() is False

    def test_can_redo(self, tmp_path):
        """Test can_redo method."""
        history = CommandHistory()

        assert history.can_redo() is False

        source = tmp_path / "source.txt"
        source.write_text("content")

        dest = tmp_path / "dest.txt"

        cmd = CopyFileCommand(source, dest)
        history.execute_command(cmd)

        assert history.can_redo() is False

        history.undo()

        assert history.can_redo() is True

    def test_new_command_clears_redo_history(self, tmp_path):
        """Test executing new command clears redo history."""
        history = CommandHistory()

        # Execute 3 commands
        for i in range(3):
            source = tmp_path / f"source{i}.txt"
            source.write_text(f"content{i}")

            dest = tmp_path / f"dest{i}.txt"

            cmd = CopyFileCommand(source, dest)
            history.execute_command(cmd)

        # Undo 2 commands
        history.undo()
        history.undo()

        # Execute new command
        source = tmp_path / "new_source.txt"
        source.write_text("new")

        dest = tmp_path / "new_dest.txt"

        cmd = CopyFileCommand(source, dest)
        history.execute_command(cmd)

        # Redo should not be available
        assert history.can_redo() is False
        assert len(history._history) == 2  # Only 2 commands remain

    def test_max_history_limit(self, tmp_path):
        """Test history respects max_history limit."""
        history = CommandHistory(max_history=3)

        # Execute 5 commands
        for i in range(5):
            source = tmp_path / f"source{i}.txt"
            source.write_text(f"content{i}")

            dest = tmp_path / f"dest{i}.txt"

            cmd = CopyFileCommand(source, dest)
            history.execute_command(cmd)

        # Only last 3 should remain
        assert len(history._history) == 3
        assert history._current_index == 2

    def test_get_history(self, tmp_path):
        """Test get_history returns descriptions."""
        history = CommandHistory()

        # Execute commands
        for i in range(3):
            source = tmp_path / f"source{i}.txt"
            source.write_text(f"content{i}")

            dest = tmp_path / f"dest{i}.txt"

            cmd = CopyFileCommand(source, dest)
            history.execute_command(cmd)

        descriptions = history.get_history()

        assert len(descriptions) == 3
        assert all("Copy" in desc for desc in descriptions)

    def test_clear_history(self, tmp_path):
        """Test clearing history."""
        history = CommandHistory()

        # Execute commands
        for i in range(3):
            source = tmp_path / f"source{i}.txt"
            source.write_text(f"content{i}")

            dest = tmp_path / f"dest{i}.txt"

            cmd = CopyFileCommand(source, dest)
            history.execute_command(cmd)

        history.clear()

        assert len(history._history) == 0
        assert history._current_index == -1
        assert not history.can_undo()
        assert not history.can_redo()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_undo_redo_sequence(self, tmp_path):
        """Test complex undo/redo sequence."""
        history = CommandHistory()

        # Execute 3 commands
        for i in range(3):
            dir_path = tmp_path / f"dir{i}"
            cmd = CreateDirectoryCommand(dir_path)
            history.execute_command(cmd)

        # Undo all
        history.undo()
        history.undo()
        history.undo()

        # Redo 2
        history.redo()
        history.redo()

        # Undo 1
        history.undo()

        # Verify state
        assert (tmp_path / "dir0").exists()
        assert not (tmp_path / "dir1").exists()
        assert not (tmp_path / "dir2").exists()

    def test_command_failure_not_added_to_history(self, tmp_path):
        """Test failed commands aren't added to history."""
        history = CommandHistory()

        # Try to copy nonexistent file
        source = tmp_path / "nonexistent.txt"
        dest = tmp_path / "dest.txt"

        cmd = CopyFileCommand(source, dest)
        result = history.execute_command(cmd)

        assert result is False
        assert len(history._history) == 0

    def test_empty_history_undo(self):
        """Test undo on empty history."""
        history = CommandHistory()

        result = history.undo()

        assert result is False

    def test_empty_history_redo(self):
        """Test redo on empty history."""
        history = CommandHistory()

        result = history.redo()

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
