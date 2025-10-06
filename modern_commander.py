"""
Modern Commander - Complete File Manager Application

A modern, dual-pane file manager inspired by Norton Commander with:
- Two-panel layout with TAB switching
- All F-key functions (F1-F10)
- File viewing, editing, copying, moving, deleting
- Search functionality
- Configuration management
- Norton Commander retro aesthetics
"""

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual.screen import Screen

# Component imports
from components.file_panel import FilePanel, FileItem
from components.command_bar import CommandBar
from components.status_bar import StatusBar
from components.dialogs import (
    ConfirmDialog,
    InputDialog,
    MessageDialog,
    ErrorDialog,
    ProgressDialog
)

# Feature imports
from features.file_viewer import FileViewer
from features.file_editor import FileEditor
from features.config_manager import ConfigManager


class ModernCommanderApp(App):
    """Modern Commander - Dual-pane file manager application."""

    CSS = """
    ModernCommanderApp {
        background: $surface;
    }

    ModernCommanderApp Header {
        background: $primary;
        color: $text;
        height: 1;
        dock: top;
    }

    ModernCommanderApp Footer {
        background: $panel;
        color: $text;
        height: 1;
        dock: bottom;
    }

    .panel-container {
        height: 1fr;
        width: 1fr;
    }

    .panels-horizontal {
        height: 1fr;
        layout: horizontal;
    }

    .left-panel-container {
        width: 50%;
        height: 1fr;
    }

    .right-panel-container {
        width: 50%;
        height: 1fr;
    }

    .active-panel {
        border: heavy $primary;
    }

    .inactive-panel {
        border: solid $accent;
    }

    StatusBar {
        dock: bottom;
        height: 1;
    }

    CommandBar {
        dock: bottom;
        height: 1;
    }

    /* Norton Commander color scheme */
    $primary: #0000AA;
    $accent: #00AAAA;
    $surface: #000055;
    $panel: #0000AA;
    $text: #FFFF55;
    $warning: #FFAA00;
    $error: #FF5555;
    $success: #55FF55;
    """

    BINDINGS = [
        Binding("f1", "show_help", "Help", priority=True),
        Binding("f2", "show_menu", "Menu", priority=False),
        Binding("f3", "view_file", "View", priority=True),
        Binding("f4", "edit_file", "Edit", priority=True),
        Binding("f5", "copy_files", "Copy", priority=True),
        Binding("f6", "move_files", "Move", priority=True),
        Binding("f7", "create_directory", "NewDir", priority=True),
        Binding("f8", "delete_files", "Delete", priority=True),
        Binding("f9", "show_config", "Config", priority=True),
        Binding("f10,q", "quit_app", "Quit", priority=True),
        Binding("tab", "switch_panel", "Switch Panel", show=False),
        Binding("ctrl+r", "refresh_panels", "Refresh", show=False),
        Binding("ctrl+h", "toggle_hidden", "Hidden Files", show=False),
        Binding("escape", "clear_selection", "Clear Selection", show=False),
    ]

    TITLE = "Modern Commander"

    def __init__(self, config_path: Optional[str] = None):
        """Initialize Modern Commander application.

        Args:
            config_path: Optional custom configuration file path
        """
        super().__init__()

        # Configuration
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_config()

        # Panel state
        self.active_panel: str = "left"  # "left" or "right"
        self.left_panel: Optional[FilePanel] = None
        self.right_panel: Optional[FilePanel] = None

    def compose(self) -> ComposeResult:
        """Compose application layout."""
        yield Header()

        # Main panels container
        with Horizontal(classes="panels-horizontal"):
            # Left panel
            with Container(classes="left-panel-container active-panel", id="left-container"):
                left_path = Path(self.config.left_panel.start_path or Path.cwd())
                yield FilePanel(
                    path=left_path,
                    id="left-panel",
                    classes="panel-container"
                )

            # Right panel
            with Container(classes="right-panel-container inactive-panel", id="right-container"):
                right_path = Path(self.config.right_panel.start_path or Path.cwd())
                yield FilePanel(
                    path=right_path,
                    id="right-panel",
                    classes="panel-container"
                )

        # Status bar
        yield StatusBar(id="status-bar")

        # Command bar with F-key shortcuts
        yield CommandBar(id="command-bar")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize application on mount."""
        # Get panel references
        self.left_panel = self.query_one("#left-panel", FilePanel)
        self.right_panel = self.query_one("#right-panel", FilePanel)

        # Focus left panel initially
        self.left_panel.focus()

        # Update status bar
        self._update_status_bar()

        # Apply configuration
        self._apply_config()

    def _apply_config(self) -> None:
        """Apply configuration settings to UI."""
        # Apply panel settings
        if self.left_panel:
            self.left_panel.sort_column = self.config.left_panel.sort_by
            self.left_panel.sort_reverse = not self.config.left_panel.sort_ascending

        if self.right_panel:
            self.right_panel.sort_column = self.config.right_panel.sort_by
            self.right_panel.sort_reverse = not self.config.right_panel.sort_ascending

    def _get_active_panel(self) -> FilePanel:
        """Get currently active file panel.

        Returns:
            Active FilePanel instance
        """
        return self.left_panel if self.active_panel == "left" else self.right_panel

    def _get_inactive_panel(self) -> FilePanel:
        """Get currently inactive file panel.

        Returns:
            Inactive FilePanel instance
        """
        return self.right_panel if self.active_panel == "left" else self.left_panel

    def _update_panel_borders(self) -> None:
        """Update panel borders to show active/inactive state."""
        left_container = self.query_one("#left-container")
        right_container = self.query_one("#right-container")

        if self.active_panel == "left":
            left_container.remove_class("inactive-panel")
            left_container.add_class("active-panel")
            right_container.remove_class("active-panel")
            right_container.add_class("inactive-panel")
        else:
            right_container.remove_class("inactive-panel")
            right_container.add_class("active-panel")
            left_container.remove_class("active-panel")
            left_container.add_class("inactive-panel")

    def _update_status_bar(self) -> None:
        """Update status bar with current panel information."""
        status_bar = self.query_one("#status-bar", StatusBar)
        active_panel = self._get_active_panel()

        # Get current item
        current_item = active_panel.get_current_item()
        current_file = current_item.name if current_item and not current_item.is_parent else None

        # Get selected items
        selected_items = active_panel.get_selected_items()

        # Get all items (excluding parent)
        total_items = [item for item in active_panel._file_items if not item.is_parent]

        # Update status bar
        status_bar.update_from_panel(
            current_file=current_file,
            selected_items=selected_items,
            total_items=total_items,
            path=active_panel.current_path
        )

    def _update_command_bar_context(self) -> None:
        """Update command bar based on current context."""
        command_bar = self.query_one("#command-bar", CommandBar)
        active_panel = self._get_active_panel()

        # Check if panel has items
        has_items = len(active_panel._file_items) > 1  # Excluding parent entry

        if has_items:
            command_bar.set_context("file_panel")
        else:
            command_bar.set_context("file_panel_empty")

    # Panel message handlers
    def on_file_panel_directory_changed(self, message: FilePanel.DirectoryChanged) -> None:
        """Handle directory change in panels.

        Args:
            message: Directory changed message
        """
        self._update_status_bar()
        self._update_command_bar_context()

        # Save path to config
        if message.panel == self.left_panel:
            self.config_manager.update_left_panel_path(str(message.path))
        else:
            self.config_manager.update_right_panel_path(str(message.path))

    def on_file_panel_file_selected(self, message: FilePanel.FileSelected) -> None:
        """Handle file selection changes.

        Args:
            message: File selected message
        """
        self._update_status_bar()

    # Actions - Panel Management
    def action_switch_panel(self) -> None:
        """Switch active panel (TAB key)."""
        # Toggle active panel
        self.active_panel = "right" if self.active_panel == "left" else "left"

        # Update borders
        self._update_panel_borders()

        # Focus new active panel
        active_panel = self._get_active_panel()
        active_panel.focus()

        # Update status bar
        self._update_status_bar()

    def action_refresh_panels(self) -> None:
        """Refresh both panels."""
        if self.left_panel:
            self.left_panel.refresh_directory()
        if self.right_panel:
            self.right_panel.refresh_directory()

        self.notify("Panels refreshed")

    def action_toggle_hidden(self) -> None:
        """Toggle hidden files visibility."""
        # This would require adding show_hidden property to FilePanel
        self.notify("Toggle hidden files (not yet implemented)")

    def action_clear_selection(self) -> None:
        """Clear selection in active panel."""
        active_panel = self._get_active_panel()
        active_panel.clear_selection()
        self._update_status_bar()

    # Actions - F-Key Functions
    def action_show_help(self) -> None:
        """F1 - Show help dialog."""
        help_text = """# Modern Commander Help

## Function Keys
F1  - Help
F3  - View file
F4  - Edit file
F5  - Copy files
F6  - Move files
F7  - Create directory
F8  - Delete files
F9  - Configuration
F10 - Quit

## Navigation
TAB - Switch panels
Enter - Open directory
Backspace - Parent directory
Insert - Select file
Ctrl+R - Refresh

## Selection
Insert - Toggle selection
Space - Toggle selection
Escape - Clear selection
"""

        dialog = MessageDialog(
            title="Help",
            message=help_text,
            message_type="info"
        )
        self.push_screen(dialog)

    def action_show_menu(self) -> None:
        """F2 - Show menu (not implemented)."""
        self.notify("Menu (F2) - Not yet implemented", severity="warning")

    def action_view_file(self) -> None:
        """F3 - View selected file."""
        active_panel = self._get_active_panel()
        current_item = active_panel.get_current_item()

        if not current_item:
            self.notify("No file selected", severity="warning")
            return

        if current_item.is_dir:
            self.notify("Cannot view directory", severity="warning")
            return

        # Open file viewer
        viewer = FileViewer(current_item.path)
        self.push_screen(viewer)

    def action_edit_file(self) -> None:
        """F4 - Edit selected file."""
        active_panel = self._get_active_panel()
        current_item = active_panel.get_current_item()

        if not current_item:
            self.notify("No file selected", severity="warning")
            return

        if current_item.is_dir:
            self.notify("Cannot edit directory", severity="warning")
            return

        # Open file editor
        editor = FileEditor(current_item.path)
        self.push_screen(editor)

    def action_copy_files(self) -> None:
        """F5 - Copy selected files to other panel."""
        active_panel = self._get_active_panel()
        inactive_panel = self._get_inactive_panel()

        # Get selected items or current item
        selected_items = active_panel.get_selected_items()
        if not selected_items:
            current_item = active_panel.get_current_item()
            if current_item and not current_item.is_parent:
                selected_items = [current_item]

        if not selected_items:
            self.notify("No files selected", severity="warning")
            return

        # Confirm copy
        count = len(selected_items)
        dest_path = inactive_panel.current_path

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                self._perform_copy(selected_items, dest_path)

        dialog = ConfirmDialog(
            title="Copy Files",
            message=f"Copy {count} file(s) to:\n{dest_path}",
            on_confirm=lambda: handle_confirm(True),
            on_cancel=lambda: handle_confirm(False)
        )

        self.push_screen(dialog, callback=handle_confirm)

    def action_move_files(self) -> None:
        """F6 - Move selected files to other panel."""
        active_panel = self._get_active_panel()
        inactive_panel = self._get_inactive_panel()

        # Get selected items or current item
        selected_items = active_panel.get_selected_items()
        if not selected_items:
            current_item = active_panel.get_current_item()
            if current_item and not current_item.is_parent:
                selected_items = [current_item]

        if not selected_items:
            self.notify("No files selected", severity="warning")
            return

        # Confirm move
        count = len(selected_items)
        dest_path = inactive_panel.current_path

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                self._perform_move(selected_items, dest_path)

        dialog = ConfirmDialog(
            title="Move Files",
            message=f"Move {count} file(s) to:\n{dest_path}",
            on_confirm=lambda: handle_confirm(True),
            on_cancel=lambda: handle_confirm(False),
            danger=True
        )

        self.push_screen(dialog, callback=handle_confirm)

    def action_create_directory(self) -> None:
        """F7 - Create new directory."""
        active_panel = self._get_active_panel()

        def handle_input(dir_name: Optional[str]) -> None:
            if dir_name:
                self._perform_create_directory(active_panel.current_path, dir_name)

        dialog = InputDialog(
            title="Create Directory",
            message="Enter directory name:",
            placeholder="New Folder",
            on_submit=handle_input
        )

        self.push_screen(dialog, callback=handle_input)

    def action_delete_files(self) -> None:
        """F8 - Delete selected files."""
        active_panel = self._get_active_panel()

        # Get selected items or current item
        selected_items = active_panel.get_selected_items()
        if not selected_items:
            current_item = active_panel.get_current_item()
            if current_item and not current_item.is_parent:
                selected_items = [current_item]

        if not selected_items:
            self.notify("No files selected", severity="warning")
            return

        # Confirm deletion
        count = len(selected_items)

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                self._perform_delete(selected_items)

        dialog = ConfirmDialog(
            title="Delete Files",
            message=f"Permanently delete {count} file(s)?",
            on_confirm=lambda: handle_confirm(True),
            on_cancel=lambda: handle_confirm(False),
            danger=True
        )

        self.push_screen(dialog, callback=handle_confirm)

    def action_show_config(self) -> None:
        """F9 - Show configuration."""
        self.notify("Configuration (F9) - Not yet implemented", severity="warning")

    def action_quit_app(self) -> None:
        """F10 - Quit application."""
        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                # Save configuration
                self.config_manager.save_config()
                self.exit()

        dialog = ConfirmDialog(
            title="Quit",
            message="Quit Modern Commander?",
            on_confirm=lambda: handle_confirm(True),
            on_cancel=lambda: handle_confirm(False)
        )

        self.push_screen(dialog, callback=handle_confirm)

    # File operations
    def _perform_copy(self, items: list[FileItem], dest_path: Path) -> None:
        """Perform copy operation.

        Args:
            items: List of items to copy
            dest_path: Destination directory
        """
        import shutil

        success_count = 0
        error_count = 0

        for item in items:
            try:
                dest_file = dest_path / item.name

                if item.is_dir:
                    shutil.copytree(item.path, dest_file, dirs_exist_ok=False)
                else:
                    shutil.copy2(item.path, dest_file)

                success_count += 1

            except Exception as e:
                error_count += 1
                self.notify(f"Failed to copy {item.name}: {e}", severity="error")

        # Refresh panels
        self.action_refresh_panels()

        # Show result
        if error_count == 0:
            self.notify(f"Successfully copied {success_count} file(s)", severity="information")
        else:
            self.notify(
                f"Copied {success_count} file(s) with {error_count} error(s)",
                severity="warning"
            )

    def _perform_move(self, items: list[FileItem], dest_path: Path) -> None:
        """Perform move operation.

        Args:
            items: List of items to move
            dest_path: Destination directory
        """
        import shutil

        success_count = 0
        error_count = 0

        for item in items:
            try:
                dest_file = dest_path / item.name
                shutil.move(str(item.path), str(dest_file))
                success_count += 1

            except Exception as e:
                error_count += 1
                self.notify(f"Failed to move {item.name}: {e}", severity="error")

        # Refresh panels
        self.action_refresh_panels()

        # Show result
        if error_count == 0:
            self.notify(f"Successfully moved {success_count} file(s)", severity="information")
        else:
            self.notify(
                f"Moved {success_count} file(s) with {error_count} error(s)",
                severity="warning"
            )

    def _perform_create_directory(self, parent_path: Path, dir_name: str) -> None:
        """Create new directory.

        Args:
            parent_path: Parent directory
            dir_name: Name of new directory
        """
        try:
            new_dir = parent_path / dir_name
            new_dir.mkdir(parents=False, exist_ok=False)

            # Refresh panels
            self.action_refresh_panels()

            self.notify(f"Created directory: {dir_name}", severity="information")

        except FileExistsError:
            self.notify(f"Directory already exists: {dir_name}", severity="error")
        except Exception as e:
            self.notify(f"Failed to create directory: {e}", severity="error")

    def _perform_delete(self, items: list[FileItem]) -> None:
        """Delete files/directories.

        Args:
            items: List of items to delete
        """
        import shutil

        success_count = 0
        error_count = 0

        for item in items:
            try:
                if item.is_dir:
                    shutil.rmtree(item.path)
                else:
                    item.path.unlink()

                success_count += 1

            except Exception as e:
                error_count += 1
                self.notify(f"Failed to delete {item.name}: {e}", severity="error")

        # Refresh panels
        self.action_refresh_panels()

        # Show result
        if error_count == 0:
            self.notify(f"Successfully deleted {success_count} file(s)", severity="information")
        else:
            self.notify(
                f"Deleted {success_count} file(s) with {error_count} error(s)",
                severity="warning"
            )


def main():
    """Application entry point."""
    app = ModernCommanderApp()
    app.run()


if __name__ == "__main__":
    main()
