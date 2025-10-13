"""
Async file operations for DC Commander.

Provides non-blocking file I/O operations using aiofiles.
To be integrated in Phase 2.1 (see ROADMAP.md).

Usage:
    from src.utils.async_file_ops import AsyncFileOperations

    async def copy_large_file():
        ops = AsyncFileOperations()
        await ops.copy_file_async(
            source=Path("large_file.dat"),
            dest=Path("backup/large_file.dat"),
            progress_callback=lambda b: print(f"Copied {b} bytes")
        )
"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional, Callable, AsyncIterator, Tuple
import aiofiles
import aiofiles.os
from dataclasses import dataclass


@dataclass
class CopyProgress:
    """Progress information for file copy operations."""
    bytes_copied: int
    total_bytes: int
    current_file: str
    files_completed: int
    total_files: int

    @property
    def percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_copied / self.total_bytes) * 100.0


class AsyncFileOperations:
    """
    Async file operations for non-blocking I/O.

    Prevents UI freezing during large file operations by yielding
    control to the event loop regularly.
    """

    def __init__(self, chunk_size: int = 64 * 1024):
        """
        Initialize async file operations.

        Args:
            chunk_size: Bytes to read/write per chunk (default 64KB)
        """
        self.chunk_size = chunk_size
        self._canceled = False

    def cancel(self) -> None:
        """Cancel current operation."""
        self._canceled = True

    async def copy_file_async(
        self,
        source: Path,
        dest: Path,
        *,
        progress_callback: Optional[Callable[[int], None]] = None,
        overwrite: bool = True
    ) -> None:
        """
        Atomically copy file asynchronously with progress reporting.

        Uses a two-stage copy process to prevent data loss:
        1. Copy source to temporary location
        2. Atomically replace destination with temporary file

        Args:
            source: Source file path
            dest: Destination file path
            progress_callback: Optional callback called with bytes copied
            overwrite: If True, overwrite existing destination

        Raises:
            FileNotFoundError: If source doesn't exist
            PermissionError: If insufficient permissions
            asyncio.CancelledError: If operation is canceled
            FileExistsError: If destination exists and overwrite is False
        """
        # Check if already canceled before starting
        if self._canceled:
            raise asyncio.CancelledError("Copy operation canceled")

        # Check if destination exists when overwrite is False
        if dest.exists() and not overwrite:
            raise FileExistsError(f"Destination already exists: {dest}")

        # Ensure destination parent directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Stage 1: Copy to temporary location (safe)
        temp_dest = dest.parent / f".tmp_{dest.name}_{uuid.uuid4().hex[:8]}"

        try:
            total_size = source.stat().st_size
            bytes_copied = 0

            async with aiofiles.open(source, 'rb') as src:
                async with aiofiles.open(temp_dest, 'wb') as dst:
                    while True:
                        if self._canceled:
                            raise asyncio.CancelledError("Copy operation canceled")

                        chunk = await src.read(self.chunk_size)
                        if not chunk:
                            break

                        await dst.write(chunk)
                        bytes_copied += len(chunk)

                        if progress_callback:
                            progress_callback(bytes_copied)

                        # Yield to event loop every chunk
                        await asyncio.sleep(0)

            # Stage 2: Atomic replacement
            if dest.exists():
                # Backup old version during replacement
                backup = dest.parent / f".backup_{dest.name}_{uuid.uuid4().hex[:8]}"
                try:
                    # Atomic rename operations
                    await aiofiles.os.rename(dest, backup)  # Move old file to backup
                    await aiofiles.os.rename(temp_dest, dest)  # Move new file to destination

                    # Cleanup old version on success
                    await aiofiles.os.remove(backup)

                except Exception as e:
                    # Rollback: restore from backup if rename failed
                    if backup.exists() and not dest.exists():
                        try:
                            await aiofiles.os.rename(backup, dest)
                        except:
                            pass  # Best effort rollback
                    raise
            else:
                # Simple case: just rename temp to dest (atomic)
                await aiofiles.os.rename(temp_dest, dest)

        except asyncio.CancelledError:
            # Cleanup temporary file on cancellation
            if temp_dest.exists():
                try:
                    await aiofiles.os.remove(temp_dest)
                except:
                    pass  # Best effort cleanup
            raise
        except Exception as e:
            # Cleanup temporary file on any failure
            if temp_dest.exists():
                try:
                    await aiofiles.os.remove(temp_dest)
                except:
                    pass  # Best effort cleanup
            raise

    async def copy_directory_async(
        self,
        source: Path,
        dest: Path,
        *,
        progress_callback: Optional[Callable[[CopyProgress], None]] = None
    ) -> AsyncIterator[Tuple[Path, bool, Optional[str]]]:
        """
        Copy directory asynchronously, yielding progress for each file.

        Args:
            source: Source directory
            dest: Destination directory
            progress_callback: Optional callback for progress updates

        Yields:
            Tuple of (file_path, success, error_message)
        """
        self._canceled = False

        # Create destination directory
        await aiofiles.os.makedirs(dest, exist_ok=True)

        # Count files for progress
        all_files = list(source.rglob("*"))
        total_files = len([f for f in all_files if f.is_file()])
        total_bytes = sum(f.stat().st_size for f in all_files if f.is_file())

        files_completed = 0
        bytes_copied = 0

        for item in all_files:
            if self._canceled:
                raise asyncio.CancelledError("Copy operation canceled")

            try:
                relative_path = item.relative_to(source)
                dest_item = dest / relative_path

                if item.is_dir():
                    await aiofiles.os.makedirs(dest_item, exist_ok=True)
                else:
                    # Copy file with progress
                    await self.copy_file_async(
                        item,
                        dest_item,
                        progress_callback=lambda b: None  # Aggregate progress below
                    )
                    files_completed += 1
                    bytes_copied += item.stat().st_size

                    if progress_callback:
                        progress = CopyProgress(
                            bytes_copied=bytes_copied,
                            total_bytes=total_bytes,
                            current_file=str(relative_path),
                            files_completed=files_completed,
                            total_files=total_files
                        )
                        progress_callback(progress)

                yield (item, True, None)

            except Exception as e:
                yield (item, False, str(e))

            await asyncio.sleep(0)  # Yield to event loop

    async def move_file_async(
        self,
        source: Path,
        dest: Path,
        overwrite: bool = True
    ) -> None:
        """
        Atomically move file asynchronously.

        On same filesystem, uses atomic rename (fast).
        Across filesystems, uses atomic copy then delete (slower but safe).

        Args:
            source: Source file path
            dest: Destination file path
            overwrite: If True, overwrite existing destination

        Raises:
            FileExistsError: If destination exists and overwrite is False
            OSError: If move operation fails
        """
        # Check if destination exists when overwrite is False
        if dest.exists() and not overwrite:
            raise FileExistsError(f"Destination already exists: {dest}")

        # Ensure destination parent directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Try atomic rename first (only works on same filesystem)
        try:
            if dest.exists():
                # Backup and replace atomically
                backup = dest.parent / f".backup_{dest.name}_{uuid.uuid4().hex[:8]}"
                try:
                    await aiofiles.os.rename(dest, backup)  # Atomic backup
                    await aiofiles.os.rename(source, dest)  # Atomic move

                    # Cleanup old version on success
                    await aiofiles.os.remove(backup)

                except Exception as e:
                    # Rollback: restore backup if rename failed
                    if backup.exists() and not dest.exists():
                        try:
                            await aiofiles.os.rename(backup, dest)
                        except:
                            pass  # Best effort rollback
                    raise
            else:
                # Simple atomic rename
                await aiofiles.os.rename(source, dest)

        except OSError as e:
            # Rename failed (likely cross-filesystem), fall back to atomic copy-then-delete
            if e.errno in (18, 17):  # EXDEV (cross-device link) or EEXIST
                # Use atomic copy then delete source
                await self.copy_file_async(source, dest, overwrite=overwrite)
                # Only delete source after successful copy
                await aiofiles.os.remove(source)
            else:
                raise

    async def delete_file_async(self, path: Path) -> None:
        """
        Delete file asynchronously.

        Args:
            path: File path to delete
        """
        if path.is_dir():
            # Remove directory contents first
            for item in path.rglob("*"):
                if item.is_file():
                    await aiofiles.os.remove(item)
                await asyncio.sleep(0)  # Yield to event loop
            await aiofiles.os.rmdir(path)
        else:
            await aiofiles.os.remove(path)

    async def calculate_directory_size_async(
        self,
        path: Path,
        *,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> int:
        """
        Calculate directory size asynchronously.

        Args:
            path: Directory path
            progress_callback: Optional callback(file_count, total_bytes)

        Returns:
            Total size in bytes
        """
        # Check if already canceled before starting
        if self._canceled:
            raise asyncio.CancelledError("Size calculation canceled")

        total_size = 0
        file_count = 0

        for item in path.rglob("*"):
            if self._canceled:
                raise asyncio.CancelledError("Size calculation canceled")

            if item.is_file():
                try:
                    total_size += item.stat().st_size
                    file_count += 1

                    if progress_callback and file_count % 100 == 0:
                        progress_callback(file_count, total_size)

                    await asyncio.sleep(0)  # Yield every file
                except OSError:
                    pass  # Skip inaccessible files

        return total_size


# Example usage in modern_commander.py:
"""
class ModernCommander(App):
    def __init__(self):
        self.async_ops = AsyncFileOperations()

    async def action_copy_files(self):
        # Get files to copy
        active_panel = self.get_active_panel()
        items = active_panel.get_selected_items()

        # Show progress dialog
        progress_dialog = ProgressDialog("Copying Files", len(items))
        self.push_screen(progress_dialog)

        # Copy asynchronously
        try:
            async for file, success, error in self.async_ops.copy_directory_async(
                source=items[0].path,
                dest=destination,
                progress_callback=lambda p: progress_dialog.update(p)
            ):
                if not success:
                    self.notify(f"Failed: {file.name} - {error}", severity="error")

        except asyncio.CancelledError:
            self.notify("Copy operation canceled")
        finally:
            self.pop_screen()
            active_panel.refresh_directory()
"""
