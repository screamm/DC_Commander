"""Command pattern implementation for Modern Commander.

Provides undo/redo functionality for file operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from pathlib import Path
import shutil
from dataclasses import dataclass


class Command(ABC):
    """Base class for all commands."""

    @abstractmethod
    def execute(self) -> bool:
        """Execute the command.

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Undo the command.

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def description(self) -> str:
        """Get command description.

        Returns:
            Human-readable description
        """
        pass


class CopyFileCommand(Command):
    """Command to copy files."""

    def __init__(self, source: Path, destination: Path):
        """Initialize copy command.

        Args:
            source: Source file path
            destination: Destination file path
        """
        self.source = source
        self.destination = destination
        self._copied = False

    def execute(self) -> bool:
        """Execute copy operation."""
        try:
            if self.source.is_dir():
                shutil.copytree(self.source, self.destination)
            else:
                shutil.copy2(self.source, self.destination)
            self._copied = True
            return True
        except Exception:
            return False

    def undo(self) -> bool:
        """Undo copy by deleting destination."""
        if not self._copied:
            return False

        try:
            if self.destination.is_dir():
                shutil.rmtree(self.destination)
            else:
                self.destination.unlink()
            return True
        except Exception:
            return False

    def description(self) -> str:
        """Get description."""
        return f"Copy {self.source.name} to {self.destination.parent}"


class MoveFileCommand(Command):
    """Command to move files."""

    def __init__(self, source: Path, destination: Path):
        """Initialize move command.

        Args:
            source: Source file path
            destination: Destination file path
        """
        self.source = source
        self.destination = destination
        self._moved = False

    def execute(self) -> bool:
        """Execute move operation."""
        try:
            shutil.move(str(self.source), str(self.destination))
            self._moved = True
            return True
        except Exception:
            return False

    def undo(self) -> bool:
        """Undo move by moving back."""
        if not self._moved:
            return False

        try:
            shutil.move(str(self.destination), str(self.source))
            return True
        except Exception:
            return False

    def description(self) -> str:
        """Get description."""
        return f"Move {self.source.name} to {self.destination.parent}"


class DeleteFileCommand(Command):
    """Command to delete files."""

    def __init__(self, path: Path, backup_dir: Optional[Path] = None):
        """Initialize delete command.

        Args:
            path: File path to delete
            backup_dir: Optional backup directory for undo
        """
        self.path = path
        self.backup_dir = backup_dir or Path.home() / ".modern_commander" / "trash"
        self.backup_path: Optional[Path] = None
        self._deleted = False

    def execute(self) -> bool:
        """Execute delete operation."""
        try:
            # Backup for undo
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.backup_path = self.backup_dir / self.path.name

            # Remove existing backup if it exists
            if self.backup_path.exists():
                if self.backup_path.is_dir():
                    shutil.rmtree(self.backup_path)
                else:
                    self.backup_path.unlink()

            if self.path.is_dir():
                shutil.copytree(self.path, self.backup_path)
                shutil.rmtree(self.path)
            else:
                shutil.copy2(self.path, self.backup_path)
                self.path.unlink()

            self._deleted = True
            return True
        except Exception:
            return False

    def undo(self) -> bool:
        """Undo delete by restoring from backup."""
        if not self._deleted or not self.backup_path:
            return False

        try:
            if self.backup_path.is_dir():
                shutil.copytree(self.backup_path, self.path)
            else:
                shutil.copy2(self.backup_path, self.path)
            return True
        except Exception:
            return False

    def description(self) -> str:
        """Get description."""
        return f"Delete {self.path.name}"


class CreateDirectoryCommand(Command):
    """Command to create directories."""

    def __init__(self, path: Path):
        """Initialize create directory command.

        Args:
            path: Directory path to create
        """
        self.path = path
        self._created = False

    def execute(self) -> bool:
        """Execute directory creation."""
        try:
            self.path.mkdir(parents=False, exist_ok=False)
            self._created = True
            return True
        except Exception:
            return False

    def undo(self) -> bool:
        """Undo by removing directory."""
        if not self._created:
            return False

        try:
            self.path.rmdir()
            return True
        except Exception:
            return False

    def description(self) -> str:
        """Get description."""
        return f"Create directory {self.path.name}"


class RenameFileCommand(Command):
    """Command to rename files."""

    def __init__(self, old_path: Path, new_name: str):
        """Initialize rename command.

        Args:
            old_path: Current file path
            new_name: New file name
        """
        self.old_path = old_path
        self.new_path = old_path.parent / new_name
        self._renamed = False

    def execute(self) -> bool:
        """Execute rename operation."""
        try:
            self.old_path.rename(self.new_path)
            self._renamed = True
            return True
        except Exception:
            return False

    def undo(self) -> bool:
        """Undo rename."""
        if not self._renamed:
            return False

        try:
            self.new_path.rename(self.old_path)
            return True
        except Exception:
            return False

    def description(self) -> str:
        """Get description."""
        return f"Rename {self.old_path.name} to {self.new_path.name}"


class CommandHistory:
    """Manages command history for undo/redo."""

    def __init__(self, max_history: int = 100):
        """Initialize command history.

        Args:
            max_history: Maximum commands to keep in history
        """
        self.max_history = max_history
        self._history: List[Command] = []
        self._current_index = -1

    def execute_command(self, command: Command) -> bool:
        """Execute command and add to history.

        Args:
            command: Command to execute

        Returns:
            True if successful
        """
        if command.execute():
            # Remove any commands after current index (redo history)
            self._history = self._history[:self._current_index + 1]

            # Add new command
            self._history.append(command)
            self._current_index += 1

            # Trim history if needed
            if len(self._history) > self.max_history:
                self._history = self._history[-self.max_history:]
                self._current_index = len(self._history) - 1

            return True
        return False

    def undo(self) -> bool:
        """Undo last command.

        Returns:
            True if successful
        """
        if self._current_index < 0:
            return False

        command = self._history[self._current_index]
        if command.undo():
            self._current_index -= 1
            return True
        return False

    def redo(self) -> bool:
        """Redo next command.

        Returns:
            True if successful
        """
        if self._current_index >= len(self._history) - 1:
            return False

        self._current_index += 1
        command = self._history[self._current_index]
        return command.execute()

    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return self._current_index >= 0

    def can_redo(self) -> bool:
        """Check if redo is possible."""
        return self._current_index < len(self._history) - 1

    def get_history(self) -> List[str]:
        """Get command history descriptions."""
        return [cmd.description() for cmd in self._history]

    def clear(self) -> None:
        """Clear command history."""
        self._history = []
        self._current_index = -1
