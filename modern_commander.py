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

import asyncio
from pathlib import Path
from threading import Lock
from typing import Optional, Callable, List

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
from textual.screen import Screen
from textual.widget import Widget
from textual.worker import Worker, WorkerState

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Component imports
from components.file_panel import FilePanel
from components.command_bar import CommandBar
from components.top_menu_bar import TopMenuBar
from models.file_item import FileItem
from components.dialogs import (
    ConfirmDialog,
    InputDialog,
    MessageDialog,
    ErrorDialog,
    ProgressDialog
)
from components.menu_screen import MenuScreen
from components.theme_config_dialog import ThemeConfigDialog
from components.theme_selection_menu import ThemeSelectionMenu

# Feature imports
from features.file_viewer import FileViewer
from features.file_editor import FileEditor
from features.config_manager import ConfigManager
from features.theme_manager import ThemeManager

# Additional component imports
from components.find_file_dialog import FindFileDialog
from components.quick_view_widget import QuickViewWidget

# Service imports
from services.file_service import FileService
from services.file_service_async import AsyncFileService, AsyncOperationProgress

# Error boundary / user-friendly error mapping
from src.core.error_boundary import ErrorBoundary, get_error_boundary
from src.core.error_messages import format_user_error

# UI-level input validation (security + UX wrapper around src.core.security)
from src.core.ui_security import (
    UIValidationError,
    validate_user_filename,
    validate_user_path,
)

# Controllers — purpose-driven composition modules that own slices of
# behaviour previously inlined in this monolith. See app/__init__.py.
from app.file_actions import FileActionsController


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

    CommandBar {
        dock: bottom;
        height: 1;
    }

    QuickViewWidget {
        display: none;
        height: 50%;
    }

    QuickViewWidget.visible {
        display: block;
    }

    /* Theme colors loaded dynamically via stylesheet.add_source() */
    /* Class-level CSS variables removed to allow dynamic theme switching */
    /* Variables now come from ThemeManager.generate_full_app_css() */
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
        Binding("ctrl+f", "find_file", "Find File", show=False),
        Binding("t", "cycle_theme", "Toggle Theme", show=False, priority=True),
        Binding("ctrl+t", "cycle_theme", "Change Theme", show=False),
        Binding("ctrl+q", "toggle_quick_view", "Quick View", show=False),
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

        # Theme management
        self.theme_manager = ThemeManager()

        # CRITICAL: DON'T load CSS here because:
        # 1. CSS variables are IMMUTABLE in Textual
        # 2. $panel collides with Textual's internal variable
        # 3. We use direct widget styling in on_mount() instead

        # Set Norton Commander as default theme
        initial_theme = self.config.theme if self.config.theme else "norton_commander"
        self.theme_manager.set_current_theme(initial_theme)  # Just set, don't apply CSS

        # Panel state
        self.active_panel: str = "left"  # "left" or "right"
        self.left_panel: Optional[FilePanel] = None
        self.right_panel: Optional[FilePanel] = None

        # Quick View state
        self.quick_view_visible: bool = False
        self.left_quick_view: Optional[QuickViewWidget] = None
        self.right_quick_view: Optional[QuickViewWidget] = None

        # File operation services
        self.file_service = FileService()
        self.async_file_service = AsyncFileService()

        # Progress dialog reference with thread-safe access
        self._progress_dialog: Optional[ProgressDialog] = None
        self._progress_dialog_lock = Lock()

        # Central error boundary (shared, lazily-initialized global).
        # Used for error history / future recovery handlers. The
        # per-action wrappers in this class go through
        # ``_show_error_dialog`` which also records to the boundary.
        self._error_boundary: ErrorBoundary = get_error_boundary()

        # Controllers (purpose-driven composition). Instantiate after
        # all state they read is established.
        self._file_actions: FileActionsController = FileActionsController(self)

    @property
    def progress_dialog(self) -> Optional[ProgressDialog]:
        """Thread-safe progress dialog accessor.

        Returns:
            Current progress dialog instance or None
        """
        with self._progress_dialog_lock:
            return self._progress_dialog

    @progress_dialog.setter
    def progress_dialog(self, value: Optional[ProgressDialog]) -> None:
        """Thread-safe progress dialog setter.

        Args:
            value: Progress dialog instance or None
        """
        with self._progress_dialog_lock:
            self._progress_dialog = value

    def _update_progress_safely(self, percentage: int, message: str) -> None:
        """Thread-safe progress update helper.

        This method atomically checks and updates the progress dialog,
        preventing race conditions between check and use.

        Args:
            percentage: Progress percentage (0-100)
            message: Progress message to display
        """
        with self._progress_dialog_lock:
            if self._progress_dialog is not None:
                self._progress_dialog.update_progress(percentage, message)

    def _show_error_dialog(
        self,
        exc: BaseException,
        *,
        operation_label: str,
        retry_callable: Optional[Callable[[], None]] = None,
    ) -> None:
        """Surface a file-operation exception through :class:`ErrorDialog`.

        Thin delegator to :meth:`FileActionsController.show_error_dialog`.
        Kept on the app class because call sites outside the file
        actions (e.g. ``action_goto_dir``) and tests still reach it
        through ``self._show_error_dialog``.

        Args:
            exc: The exception that was caught.
            operation_label: Short human label such as ``"Copy"`` used
                in the dialog title.
            retry_callable: Zero-argument callable that re-executes the
                failed operation. ``None`` disables the Retry button.
        """
        self._file_actions.show_error_dialog(
            exc,
            operation_label=operation_label,
            retry_callable=retry_callable,
        )

    def compose(self) -> ComposeResult:
        """Compose application layout."""
        # Top menu bar
        yield TopMenuBar(id="top-menu")

        # Main panels container
        with Horizontal(classes="panels-horizontal"):
            # Left panel with Quick View
            with Vertical(classes="left-panel-container active-panel", id="left-container"):
                left_path = Path(self.config.left_panel.start_path or Path.cwd())
                yield FilePanel(
                    path=left_path,
                    id="left-panel",
                    classes="panel-container"
                )
                yield QuickViewWidget(id="left-quick-view")

            # Right panel with Quick View
            with Vertical(classes="right-panel-container inactive-panel", id="right-container"):
                right_path = Path(self.config.right_panel.start_path or Path.cwd())
                yield FilePanel(
                    path=right_path,
                    id="right-panel",
                    classes="panel-container"
                )
                yield QuickViewWidget(id="right-quick-view")

        # Command bar with F-key shortcuts
        yield CommandBar(id="command-bar")

    def on_mount(self) -> None:
        """Initialize application on mount."""
        # Get panel references
        self.left_panel = self.query_one("#left-panel", FilePanel)
        self.right_panel = self.query_one("#right-panel", FilePanel)

        # Get Quick View references
        self.left_quick_view = self.query_one("#left-quick-view", QuickViewWidget)
        self.right_quick_view = self.query_one("#right-quick-view", QuickViewWidget)

        # Apply theme visually (colors to widgets)
        self._apply_theme(self.config.theme)

        # Focus left panel initially
        self.left_panel.focus()

        # Apply configuration
        self._apply_config()

    def _apply_config(self) -> None:
        """Apply configuration settings to UI."""
        # Theme already applied in __init__ - no need to reapply here
        # This prevents double-application and ensures CSS is loaded before compose()

        # Apply panel settings
        if self.left_panel:
            self.left_panel.sort_column = self.config.left_panel.sort_by
            self.left_panel.sort_reverse = not self.config.left_panel.sort_ascending

        if self.right_panel:
            self.right_panel.sort_column = self.config.right_panel.sort_by
            self.right_panel.sort_reverse = not self.config.right_panel.sort_ascending

    def _apply_theme(self, theme_name: str) -> None:
        """Apply theme to application dynamically without restart.

        Args:
            theme_name: Name of theme to apply
        """
        try:
            # Validate theme_name is not None or empty
            if not theme_name or not isinstance(theme_name, str):
                return

            # Load and apply theme
            if self.theme_manager.set_current_theme(theme_name):
                # Generate new CSS for the theme
                new_css = self.theme_manager.generate_full_app_css(theme_name)

                if new_css:
                    # CRITICAL: We DON'T apply CSS because:
                    # 1. CSS variables are IMMUTABLE in Textual (first definition wins)
                    # 2. $panel variable name collides with Textual internal variable
                    # 3. Direct widget styling is the ONLY way to change colors dynamically

                    # SKIP CSS application entirely - go straight to direct widget styling
                    # self.stylesheet.add_source(new_css, is_default_css=True)  # SKIP
                    # self.refresh_css(animate=False)  # SKIP

                    # CRITICAL FIX: Apply colors DIRECTLY to widgets (bypasses CSS entirely)
                    self._apply_theme_colors_to_widgets(theme_name)

                    # Update panel borders with new theme colors
                    self._update_panel_borders()

                    # Get theme display name
                    theme = self.theme_manager.get_current_theme()
                    if theme:
                        self.notify(
                            f"Theme '{theme.display_name}' applied successfully!",
                            severity="information",
                            timeout=2
                        )

        except Exception as e:
            # CRITICAL FIX: Catch all exceptions to prevent app crash
            import traceback
            self.notify(f"Theme application error: {str(e)}", severity="error", timeout=5)

    def _apply_theme_colors_to_widgets(self, theme_name: str) -> None:
        """Apply theme colors directly to widget styles.

        CRITICAL WORKAROUND: Textual CSS variables are immutable - the first definition wins.
        We must bypass CSS variables entirely and apply colors directly to widget inline styles.

        Inline styles have HIGHEST priority and override both CSS variables and DEFAULT_CSS.

        Args:
            theme_name: Name of theme to apply
        """
        # Get theme colors
        theme = self.theme_manager.load_theme(theme_name)
        if not theme:
            return

        # Apply to app background with inline style
        self.styles.background = theme.surface

        # Apply to top menu bar with INLINE styles (highest priority)
        try:
            menu_bar = self.query_one("#top-menu", TopMenuBar)
            menu_bar.styles.background = theme.primary
            menu_bar.styles.color = theme.text

            # Apply to EACH menu item individually
            for menu_item in menu_bar.query("MenuItem"):
                menu_item.styles.background = theme.primary
                menu_item.styles.color = theme.text
                menu_item.refresh()  # Force immediate refresh
        except Exception:
            pass

        # Apply to file panels and their DataTable widgets
        try:
            if self.left_panel:
                self.left_panel.styles.background = theme.panel

                # Style DataTable within panel
                try:
                    datatable = self.left_panel.query_one("DataTable")
                    datatable.styles.background = theme.panel
                    datatable.styles.color = theme.text
                    # Note: DataTable selection colors are controlled by Textual internally
                    # We can set cursor colors via styles if needed
                    datatable.refresh()
                except Exception:
                    pass  # DataTable might not exist yet

            if self.right_panel:
                self.right_panel.styles.background = theme.panel

                # Style DataTable within panel
                try:
                    datatable = self.right_panel.query_one("DataTable")
                    datatable.styles.background = theme.panel
                    datatable.styles.color = theme.text
                    datatable.refresh()
                except Exception:
                    pass  # DataTable might not exist yet
        except Exception:
            pass

        # Apply to command bar with INLINE styles
        try:
            command_bar = self.query_one("#command-bar", CommandBar)
            command_bar.styles.background = theme.panel
            command_bar.styles.color = theme.text

            # Apply to command buttons within CommandBar
            for button in command_bar.query("CommandButton"):
                button.styles.background = theme.accent
                button.styles.color = theme.text
                button.refresh()
        except Exception:
            pass

        # Apply to Quick View widgets
        try:
            if self.left_quick_view:
                self.left_quick_view.styles.background = theme.panel
                self.left_quick_view.styles.color = theme.text
                self.left_quick_view.refresh()

            if self.right_quick_view:
                self.right_quick_view.styles.background = theme.panel
                self.right_quick_view.styles.color = theme.text
                self.right_quick_view.refresh()
        except Exception:
            pass

        # Apply to panel containers (borders)
        try:
            left_container = self.query_one("#left-container")
            right_container = self.query_one("#right-container")

            # Update borders with theme colors
            if self.active_panel == "left":
                left_container.styles.border = ("heavy", theme.primary)
                right_container.styles.border = ("solid", theme.accent)
            else:
                right_container.styles.border = ("heavy", theme.primary)
                left_container.styles.border = ("solid", theme.accent)
        except Exception:
            pass

        # Force complete refresh
        self.refresh(layout=True)

    def action_cycle_theme(self) -> None:
        """Cycle to next theme (Ctrl+T)."""
        try:
            # Use ThemeManager.toggle_theme() for cycling
            next_theme_id = self.theme_manager.toggle_theme()

            if not next_theme_id:
                self.notify("No themes available", severity="error")
                return

            # Apply the theme using helper method
            self._apply_theme_by_id(next_theme_id)

        except Exception as e:
            # CRITICAL FIX: Catch all exceptions to prevent app crash
            self.notify(f"Theme cycle error: {str(e)}", severity="error")

    def _apply_theme_by_id(self, theme_id: str) -> None:
        """Apply theme by ID and update configuration with live preview.

        Args:
            theme_id: Theme identifier to apply
        """
        try:
            # Update config first
            self.config.theme = theme_id
            self.config_manager.update_theme(theme_id)
            self.config_manager.save_config()

            # Apply theme dynamically (no restart needed)
            self._apply_theme(theme_id)

        except Exception as e:
            self.notify(f"Theme application error: {str(e)}", severity="error")

    # TopMenuBar message handlers
    def on_top_menu_bar_menu_selected(self, event: TopMenuBar.MenuSelected) -> None:
        """Handle menu selections from top menu bar.

        Args:
            event: Menu selected event containing menu_id
        """
        if event.menu_id == "menu-left":
            self._show_left_panel_menu()
        elif event.menu_id == "menu-files":
            self._show_files_menu()
        elif event.menu_id == "menu-commands":
            self._show_commands_menu()
        elif event.menu_id == "menu-options":
            self.action_show_theme_menu()
        elif event.menu_id == "menu-right":
            self._show_right_panel_menu()

    def _show_left_panel_menu(self) -> None:
        """Show left panel menu."""
        self.notify("Left Panel Menu - Use F2 for full menu system", severity="information", timeout=2)

    def _show_files_menu(self) -> None:
        """Show files menu."""
        self.notify("Files Menu - Use F2 for full menu system", severity="information", timeout=2)

    def _show_commands_menu(self) -> None:
        """Show commands menu."""
        self.notify("Commands Menu - Use F2 for full menu system", severity="information", timeout=2)

    def _show_right_panel_menu(self) -> None:
        """Show right panel menu."""
        self.notify("Right Panel Menu - Use F2 for full menu system", severity="information", timeout=2)

    def action_show_theme_menu(self) -> None:
        """Show theme selection menu."""
        def handle_result(theme_id: Optional[str]) -> None:
            if theme_id:
                self._apply_theme_by_id(theme_id)

        self.push_screen(
            ThemeSelectionMenu(self.theme_manager, self.config.theme),
            handle_result
        )

    # ThemeSelectionMenu message handlers
    def on_theme_selection_menu_theme_selected(self, event: ThemeSelectionMenu.ThemeSelected) -> None:
        """Handle theme selected from menu.

        Args:
            event: Theme selected event containing theme_id
        """
        self._apply_theme_by_id(event.theme_id)

    def on_theme_selection_menu_create_custom_theme(self, event: ThemeSelectionMenu.CreateCustomTheme) -> None:
        """Handle create custom theme request.

        Args:
            event: Create custom theme event
        """
        # Check slot availability
        if not self.theme_manager.has_custom_slot_available():
            self.notify(
                f"Maximum {self.theme_manager.MAX_CUSTOM_THEMES} custom themes allowed",
                severity="error",
                timeout=3
            )
            return

        # Show theme config dialog
        dialog = ThemeConfigDialog(theme=None, slot=None)
        self.push_screen(dialog)

    def on_theme_selection_menu_edit_custom_theme(self, event: ThemeSelectionMenu.EditCustomTheme) -> None:
        """Handle edit custom theme request.

        Args:
            event: Edit custom theme event containing theme_id
        """
        # Load theme
        theme = self.theme_manager.load_theme(event.theme_id)
        if not theme:
            self.notify(f"Failed to load theme: {event.theme_id}", severity="error")
            return

        # Show theme config dialog with theme
        dialog = ThemeConfigDialog(theme=theme, slot=event.theme_id)
        self.push_screen(dialog)

    def on_theme_selection_menu_delete_custom_theme(self, event: ThemeSelectionMenu.DeleteCustomTheme) -> None:
        """Handle delete custom theme request.

        Args:
            event: Delete custom theme event containing theme_id
        """
        # Get theme display name
        theme = self.theme_manager.load_theme(event.theme_id)
        display_name = theme.display_name if theme else event.theme_id

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                # Delete theme
                try:
                    if self.theme_manager.delete_custom_theme(event.theme_id):
                        self.notify(f"Deleted theme: {display_name}", severity="information")

                        # If deleted theme was current, switch to default
                        if self.config.theme == event.theme_id:
                            self._apply_theme_by_id("norton_commander")
                    else:
                        self.notify(f"Failed to delete theme: {display_name}", severity="error")

                except Exception as e:
                    self.notify(f"Error deleting theme: {str(e)}", severity="error")

        # Show confirmation dialog
        dialog = ConfirmDialog(
            title="Delete Custom Theme",
            message=f"Delete custom theme '{display_name}'?\nThis action cannot be undone.",
            on_confirm=lambda: handle_confirm(True),
            on_cancel=lambda: handle_confirm(False),
            danger=True
        )
        self.push_screen(dialog, callback=handle_confirm)

    # ThemeConfigDialog message handler
    def on_theme_config_dialog_theme_saved(self, event: ThemeConfigDialog.ThemeSaved) -> None:
        """Handle theme saved from config dialog.

        Args:
            event: Theme saved event containing theme and slot
        """
        try:
            # Save theme to ThemeManager
            if self.theme_manager.save_custom_theme(event.slot, event.theme):
                self.notify(
                    f"Saved custom theme: {event.theme.display_name}",
                    severity="information"
                )

                # Optionally apply the new theme
                # Uncomment if you want to apply immediately:
                # self._apply_theme_by_id(event.slot)
            else:
                self.notify(
                    f"Failed to save custom theme: {event.theme.display_name}",
                    severity="error"
                )

        except Exception as e:
            self.notify(f"Error saving custom theme: {str(e)}", severity="error")

    def _get_active_panel(self) -> Optional[FilePanel]:
        """Get currently active file panel.

        Returns:
            Active FilePanel instance
        """
        if self.active_panel == "left":
            return self.left_panel
        return self.right_panel

    def _get_inactive_panel(self) -> Optional[FilePanel]:
        """Get currently inactive file panel.

        Returns:
            Inactive FilePanel instance
        """
        if self.active_panel == "left":
            return self.right_panel
        return self.left_panel

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
        self._update_command_bar_context()
        self._update_quick_view()

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
        pass

    def on_file_panel_group_select_request(self, message: FilePanel.GroupSelectRequest) -> None:
        """Handle group selection pattern input request.

        Args:
            message: Group select request message
        """
        operation = message.operation
        panel = message.panel

        def handle_input(pattern: Optional[str]) -> None:
            if pattern:
                if operation == "select":
                    panel.select_group(pattern)
                elif operation == "deselect":
                    panel.deselect_group(pattern)

        dialog_title = "Select Group" if operation == "select" else "Deselect Group"
        dialog = InputDialog(
            title=dialog_title,
            message="Enter wildcard pattern:",
            placeholder="*.py",
            on_submit=handle_input
        )

        self.push_screen(dialog)  # Removed duplicate callback parameter

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

        # Update Quick View for new active panel
        self._update_quick_view()

    def action_refresh_panels(self) -> None:
        """Refresh both panels."""
        if self.left_panel:
            self.left_panel.refresh_directory()
        if self.right_panel:
            self.right_panel.refresh_directory()

        self.notify("Panels refreshed")

    def action_toggle_hidden(self) -> None:
        """Toggle hidden files visibility (Ctrl+H)."""
        active_panel = self._get_active_panel()
        if active_panel:
            active_panel.toggle_hidden_files()

    def action_clear_selection(self) -> None:
        """Clear selection in active panel."""
        active_panel = self._get_active_panel()
        active_panel.clear_selection()

    def action_toggle_quick_view(self) -> None:
        """Toggle Quick View visibility (Ctrl+Q)."""
        self.quick_view_visible = not self.quick_view_visible

        if self.quick_view_visible:
            # Show Quick View widgets
            if self.left_quick_view:
                self.left_quick_view.add_class("visible")
            if self.right_quick_view:
                self.right_quick_view.add_class("visible")

            # Update Quick View for active panel
            self._update_quick_view()

            self.notify("Quick View enabled")
        else:
            # Hide Quick View widgets
            if self.left_quick_view:
                self.left_quick_view.remove_class("visible")
            if self.right_quick_view:
                self.right_quick_view.remove_class("visible")

            self.notify("Quick View disabled")

    def _update_quick_view(self) -> None:
        """Update Quick View for opposite panel based on active panel cursor."""
        if not self.quick_view_visible:
            return

        active_panel = self._get_active_panel()
        current_item = active_panel.get_current_item()

        # Determine which Quick View to update (opposite panel's)
        if self.active_panel == "left" and self.right_quick_view:
            if current_item and not current_item.is_parent:
                self.right_quick_view.preview_file(current_item.path)
            else:
                self.right_quick_view.clear_preview()
        elif self.active_panel == "right" and self.left_quick_view:
            if current_item and not current_item.is_parent:
                self.left_quick_view.preview_file(current_item.path)
            else:
                self.left_quick_view.clear_preview()

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
        """F2 - Show interactive dropdown menu system."""
        menu = MenuScreen(active_panel=self.active_panel)

        def handle_menu_result(action: Optional[str]) -> None:
            if action:
                self._execute_menu_action(action)

        self.push_screen(menu, callback=handle_menu_result)

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
        """F5 - Copy selected files to other panel.

        Delegates to :class:`FileActionsController`.
        """
        self._file_actions.copy_files()

    def action_move_files(self) -> None:
        """F6 - Move selected files to other panel.

        Delegates to :class:`FileActionsController`.
        """
        self._file_actions.move_files()

    def action_create_directory(self) -> None:
        """F7 - Create new directory.

        Delegates to :class:`FileActionsController`. See the
        controller docstring for validation behaviour.
        """
        self._file_actions.create_directory()

    def action_delete_files(self) -> None:
        """F8 - Delete selected files.

        Delegates to :class:`FileActionsController`.
        """
        self._file_actions.delete_files()

    def action_show_config(self) -> None:
        """F9 - Show configuration screen."""
        from components.config_screen import ConfigScreen
        from features.config_manager import Config

        def handle_config_saved(config: Config) -> None:
            """Handle configuration save.

            Args:
                config: Saved configuration
            """
            # Reload configuration
            self.config = self.config_manager.get_config()

            # Apply new configuration
            self._apply_config()
            self.notify("Configuration saved successfully", severity="information")

        config_screen = ConfigScreen(
            config_manager=self.config_manager,
            theme_manager=self.theme_manager,
            on_save=handle_config_saved
        )

        self.push_screen(config_screen)

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

    def action_find_file(self) -> None:
        """Ctrl+F - Find file in directory tree."""
        active_panel = self._get_active_panel()

        def handle_file_selected(file_path: Optional[Path]) -> None:
            if file_path and file_path.exists():
                # Navigate to the parent directory and select the file
                if file_path.is_file():
                    active_panel.navigate_to(file_path.parent)
                    # Use call_after_refresh to select file after directory loads
                    self.call_after_refresh(lambda: active_panel.select_file_by_path(file_path))
                else:
                    active_panel.navigate_to(file_path)

        dialog = FindFileDialog(
            start_path=active_panel.current_path,
            on_file_selected=handle_file_selected
        )

        self.push_screen(dialog, callback=handle_file_selected)

    def action_swap_panels(self) -> None:
        """Swap directories between left and right panels."""
        if self.left_panel and self.right_panel:
            # Get current paths
            left_path = self.left_panel.current_path
            right_path = self.right_panel.current_path

            # Swap paths
            self.left_panel.navigate_to(right_path)
            self.right_panel.navigate_to(left_path)

            self.notify("Panels swapped")

    def action_goto_dir(self) -> None:
        """Navigate active panel to a specific directory.

        User input is validated via :func:`validate_user_path` before
        navigation. The path is resolved, checked for existence, and
        must point at a directory. Invalid input shows a retry-capable
        :class:`ErrorDialog`.
        """
        active_panel = self._get_active_panel()
        placeholder = str(active_panel.current_path)

        def prompt(default: str = "") -> None:
            """Open the goto-directory InputDialog (retry-reusable)."""

            def handle_input(dir_path: Optional[str]) -> None:
                if not dir_path:
                    return
                try:
                    target_path = validate_user_path(
                        dir_path, must_exist=True
                    )
                except UIValidationError as exc:
                    def on_close(action: Optional[str]) -> None:
                        if action == "retry":
                            prompt(default=dir_path)

                    self.push_screen(
                        ErrorDialog(
                            message=exc.user_message,
                            title="Invalid input",
                            details=exc.technical_details,
                            allow_retry=True,
                            allow_cancel=True,
                            on_close=on_close,
                        )
                    )
                    return

                if not target_path.is_dir():
                    logger.warning(
                        "Goto directory: %r resolved to %s which is "
                        "not a directory",
                        dir_path,
                        target_path,
                    )

                    def on_close(action: Optional[str]) -> None:
                        if action == "retry":
                            prompt(default=dir_path)

                    self.push_screen(
                        ErrorDialog(
                            message="Not a directory.",
                            title="Invalid input",
                            details=(
                                f"{target_path} exists but is not a "
                                "directory."
                            ),
                            allow_retry=True,
                            allow_cancel=True,
                            on_close=on_close,
                        )
                    )
                    return

                active_panel.navigate_to(target_path)

            dialog = InputDialog(
                title="Go to Directory",
                message="Enter directory path:",
                placeholder=placeholder,
                default=default,
                on_submit=handle_input,
            )
            self.push_screen(dialog)

        prompt()

    def action_compare_dirs(self) -> None:
        """Compare directories between left and right panels."""
        if not self.left_panel or not self.right_panel:
            return

        # Get file lists from both panels
        left_files = {item.name: item for item in self.left_panel._file_items if not item.is_parent}
        right_files = {item.name: item for item in self.right_panel._file_items if not item.is_parent}

        # Find differences
        only_left = set(left_files.keys()) - set(right_files.keys())
        only_right = set(right_files.keys()) - set(left_files.keys())
        common = set(left_files.keys()) & set(right_files.keys())

        # Find files with different sizes or dates
        different = []
        for name in common:
            left_item = left_files[name]
            right_item = right_files[name]
            if left_item.size != right_item.size or left_item.modified != right_item.modified:
                different.append(name)

        # Build comparison message
        message_lines = [
            f"**Left panel**: {self.left_panel.current_path}",
            f"**Right panel**: {self.right_panel.current_path}",
            "",
            f"**Only in left**: {len(only_left)} file(s)",
            f"**Only in right**: {only_right} file(s)",
            f"**Different**: {len(different)} file(s)",
            f"**Identical**: {len(common) - len(different)} file(s)",
        ]

        if only_left:
            message_lines.append("")
            message_lines.append("**Files only in left:**")
            for name in sorted(list(only_left)[:10]):  # Show first 10
                message_lines.append(f"  • {name}")
            if len(only_left) > 10:
                message_lines.append(f"  ... and {len(only_left) - 10} more")

        if only_right:
            message_lines.append("")
            message_lines.append("**Files only in right:**")
            for name in sorted(list(only_right)[:10]):  # Show first 10
                message_lines.append(f"  • {name}")
            if len(only_right) > 10:
                message_lines.append(f"  ... and {len(only_right) - 10} more")

        if different:
            message_lines.append("")
            message_lines.append("**Files with differences:**")
            for name in sorted(different[:10]):  # Show first 10
                message_lines.append(f"  • {name}")
            if len(different) > 10:
                message_lines.append(f"  ... and {len(different) - 10} more")

        dialog = MessageDialog(
            title="Compare Directories",
            message="\n".join(message_lines),
            message_type="info"
        )
        self.push_screen(dialog)

    def action_panel_history(self) -> None:
        """Show panel navigation history."""
        active_panel = self._get_active_panel()

        # For now, show a placeholder - full history tracking would require maintaining a history list
        # This could be enhanced by adding a history stack to FilePanel
        message = f"""**Panel History**

Current directory:
  {active_panel.current_path}

**Note**: Full navigation history tracking will be available in a future version.

For now, you can use:
  • Backspace - Go to parent directory
  • Ctrl+F - Find file in directory tree
  • Enter - Navigate into selected directory"""

        dialog = MessageDialog(
            title="Panel History",
            message=message,
            message_type="info"
        )
        self.push_screen(dialog)

    def action_toggle_sizes(self) -> None:
        """Toggle file size display in panels."""
        # This would require modifying ViewMode to support toggling sizes
        # For now, inform user that sizes are always shown in FULL view
        message = """**File Size Display**

File sizes are controlled by view mode:

• **Brief View** - Sizes not shown (compact)
• **Full View** - Sizes always shown
• **Info View** - Sizes always shown with permissions

Use F2 menu → Left/Right → Brief/Full to change view mode."""

        self.notify("Sizes are controlled by view mode (Brief/Full)", severity="information")

        dialog = MessageDialog(
            title="Toggle Sizes",
            message=message,
            message_type="info"
        )
        self.push_screen(dialog)

    def action_toggle_dates(self) -> None:
        """Toggle file date display in panels."""
        # This would require modifying ViewMode to support toggling dates
        # For now, inform user that dates are always shown in FULL view
        message = """**File Date Display**

File dates are controlled by view mode:

• **Brief View** - Dates not shown (compact)
• **Full View** - Dates always shown
• **Info View** - Dates always shown with permissions

Use F2 menu → Left/Right → Brief/Full to change view mode."""

        self.notify("Dates are controlled by view mode (Brief/Full)", severity="information")

        dialog = MessageDialog(
            title="Toggle Dates",
            message=message,
            message_type="info"
        )
        self.push_screen(dialog)

    def action_save_setup(self) -> None:
        """Save current panel setup to configuration."""
        # Save current paths and settings
        if self.left_panel:
            self.config_manager.update_left_panel_path(str(self.left_panel.current_path))
            self.config_manager.update_config("left_panel", "sort_by", self.left_panel.sort_column)
            self.config_manager.update_config("left_panel", "sort_ascending", not self.left_panel.sort_reverse)

        if self.right_panel:
            self.config_manager.update_right_panel_path(str(self.right_panel.current_path))
            self.config_manager.update_config("right_panel", "sort_by", self.right_panel.sort_column)
            self.config_manager.update_config("right_panel", "sort_ascending", not self.right_panel.sort_reverse)

        # Save current theme
        self.config_manager.update_theme(self.config.theme)

        # Save to disk
        self.config_manager.save_config()

        self.notify("Current setup saved to configuration", severity="information")

    def _execute_menu_action(self, action: str) -> None:
        """Execute menu action from F2 menu system.

        Args:
            action: Action identifier from menu
        """
        # Left panel actions
        if action.startswith("left_"):
            panel = self.left_panel
            action_type = action[5:]  # Remove "left_" prefix
            self._execute_panel_action(panel, action_type, "left")

        # Right panel actions
        elif action.startswith("right_"):
            panel = self.right_panel
            action_type = action[6:]  # Remove "right_" prefix
            self._execute_panel_action(panel, action_type, "right")

        # File operations
        elif action == "view_file":
            self.action_view_file()
        elif action == "edit_file":
            self.action_edit_file()
        elif action == "copy_files":
            self.action_copy_files()
        elif action == "move_files":
            self.action_move_files()
        elif action == "create_dir":
            self.action_create_directory()
        elif action == "delete_files":
            self.action_delete_files()

        # Selection operations
        elif action == "select_group":
            active_panel = self._get_active_panel()
            active_panel.action_select_group()
        elif action == "deselect_group":
            active_panel = self._get_active_panel()
            active_panel.action_deselect_group()
        elif action == "invert_selection":
            active_panel = self._get_active_panel()
            active_panel.action_invert_selection()

        # Command operations
        elif action == "find_file":
            self.action_find_file()
        elif action == "toggle_quick_view":
            self.action_toggle_quick_view()
        elif action == "refresh_panels":
            self.action_refresh_panels()
        elif action == "compare_dirs":
            self.action_compare_dirs()
        elif action == "swap_panels":
            self.action_swap_panels()
        elif action == "panel_history":
            self.action_panel_history()
        elif action == "goto_dir":
            self.action_goto_dir()

        # Options
        elif action == "show_config":
            self.action_show_config()
        elif action == "cycle_theme":
            self.action_cycle_theme()
        elif action == "toggle_hidden":
            self.action_toggle_hidden()
        elif action == "toggle_sizes":
            self.action_toggle_sizes()
        elif action == "toggle_dates":
            self.action_toggle_dates()
        elif action == "save_setup":
            self.action_save_setup()

        else:
            self.notify(f"Action not implemented: {action}", severity="warning")

    def _execute_panel_action(self, panel: Optional[FilePanel], action_type: str, panel_name: str) -> None:
        """Execute panel-specific action.

        Args:
            panel: Target panel
            action_type: Type of action (brief, full, sort_name, etc.)
            panel_name: Panel identifier ("left" or "right")
        """
        if not panel:
            return

        # View mode actions
        if action_type == "brief":
            from features.view_modes import ViewMode
            panel.set_view_mode(ViewMode.BRIEF)
        elif action_type == "full":
            from features.view_modes import ViewMode
            panel.set_view_mode(ViewMode.FULL)
        elif action_type == "tree":
            # Tree view is not yet implemented - fallback to brief view
            from features.view_modes import ViewMode
            panel.set_view_mode(ViewMode.BRIEF)
            self.notify(f"{panel_name.title()} panel: Tree view (using brief view as fallback)", severity="information")
        elif action_type == "info":
            from features.view_modes import ViewMode
            import platform
            if platform.system() == "Windows":
                # Info view requires Unix permissions - fallback to full view on Windows
                panel.set_view_mode(ViewMode.FULL)
                self.notify(f"{panel_name.title()} panel: Info view (not available on Windows, using full view)", severity="information")
            else:
                panel.set_view_mode(ViewMode.INFO)

        # Sort actions
        elif action_type == "sort_name":
            panel.sort_column = "name"
            panel.sort_reverse = False
            panel.refresh_directory()
            self.notify(f"{panel_name.title()} panel: Sorted by name")
        elif action_type == "sort_ext":
            panel.sort_column = "ext"
            panel.sort_reverse = False
            panel.refresh_directory()
            self.notify(f"{panel_name.title()} panel: Sorted by extension")
        elif action_type == "sort_size":
            panel.sort_column = "size"
            panel.sort_reverse = True  # Largest first
            panel.refresh_directory()
            self.notify(f"{panel_name.title()} panel: Sorted by size")
        elif action_type == "sort_date":
            panel.sort_column = "date"
            panel.sort_reverse = True  # Newest first
            panel.refresh_directory()
            self.notify(f"{panel_name.title()} panel: Sorted by date")

        # Refresh action
        elif action_type == "refresh":
            panel.refresh_directory()
            self.notify(f"{panel_name.title()} panel refreshed")

    # File operations — delegated to FileActionsController.
    # These thin wrappers are retained so that legacy call sites
    # (e.g. any code still reaching ``self._perform_copy``) and tests
    # that patch them continue to work. The behavioural logic lives in
    # ``app.file_actions``.
    def _perform_copy(self, items: list[FileItem], dest_path: Path) -> None:
        """Perform copy operation. Delegates to FileActionsController.

        Args:
            items: List of items to copy
            dest_path: Destination directory
        """
        self._file_actions._perform_copy(items, dest_path)

    def _perform_copy_sync(
        self, items: list[FileItem], dest_path: Path
    ) -> None:
        """Synchronous copy. Delegates to FileActionsController.

        Args:
            items: List of items to copy
            dest_path: Destination directory
        """
        self._file_actions._perform_copy_sync(items, dest_path)

    def _perform_copy_async(
        self, items: list[FileItem], dest_path: Path
    ) -> None:
        """Asynchronous copy. Delegates to FileActionsController.

        Args:
            items: List of items to copy
            dest_path: Destination directory
        """
        self._file_actions._perform_copy_async(items, dest_path)

    async def _copy_worker(
        self, items: List[Path], dest_path: Path
    ) -> None:
        """Async copy worker. Delegates to FileActionsController.

        Args:
            items: List of paths to copy
            dest_path: Destination directory
        """
        await self._file_actions._copy_worker(items, dest_path)

    def _perform_move(self, items: list[FileItem], dest_path: Path) -> None:
        """Perform move operation. Delegates to FileActionsController.

        Args:
            items: List of items to move
            dest_path: Destination directory
        """
        self._file_actions._perform_move(items, dest_path)

    def _perform_move_sync(
        self, items: list[FileItem], dest_path: Path
    ) -> None:
        """Synchronous move. Delegates to FileActionsController.

        Args:
            items: List of items to move
            dest_path: Destination directory
        """
        self._file_actions._perform_move_sync(items, dest_path)

    def _perform_move_async(
        self, items: list[FileItem], dest_path: Path
    ) -> None:
        """Asynchronous move. Delegates to FileActionsController.

        Args:
            items: List of items to move
            dest_path: Destination directory
        """
        self._file_actions._perform_move_async(items, dest_path)

    async def _move_worker(
        self, items: List[Path], dest_path: Path
    ) -> None:
        """Async move worker. Delegates to FileActionsController.

        Args:
            items: List of paths to move
            dest_path: Destination directory
        """
        await self._file_actions._move_worker(items, dest_path)

    def _perform_create_directory(
        self, parent_path: Path, dir_name: str
    ) -> None:
        """Create directory. Delegates to FileActionsController.

        Args:
            parent_path: Parent directory
            dir_name: Name of new directory
        """
        self._file_actions._perform_create_directory(parent_path, dir_name)

    def _perform_delete(self, items: list[FileItem]) -> None:
        """Delete files/directories. Delegates to FileActionsController.

        Args:
            items: List of items to delete
        """
        self._file_actions._perform_delete(items)

    def _perform_delete_sync(self, items: list[FileItem]) -> None:
        """Synchronous delete. Delegates to FileActionsController.

        Args:
            items: List of items to delete
        """
        self._file_actions._perform_delete_sync(items)

    def _perform_delete_async(self, items: list[FileItem]) -> None:
        """Asynchronous delete. Delegates to FileActionsController.

        Args:
            items: List of items to delete
        """
        self._file_actions._perform_delete_async(items)

    async def _delete_worker(self, items: List[Path]) -> None:
        """Async delete worker. Delegates to FileActionsController.

        Args:
            items: List of paths to delete
        """
        await self._file_actions._delete_worker(items)


def main() -> None:
    """Application entry point."""
    app: ModernCommanderApp = ModernCommanderApp()
    # Start with larger window size for better visibility (140x40 characters)
    app.run(size=(140, 40))


if __name__ == "__main__":
    main()
