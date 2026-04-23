"""F2 menu dispatch for ModernCommanderApp.

This module extracts the F2 (and top-menu-bar) dispatch logic from the
``modern_commander`` monolith into :class:`MenuDispatchController`.
The monolith previously held two tightly-coupled methods,
``_execute_menu_action`` and ``_execute_panel_action``, that together
routed every menu entry to the appropriate app action. Both now live
here.

``ModernCommanderApp`` holds a single instance and delegates its
legacy ``_execute_menu_action`` / ``_execute_panel_action`` entry
points to it. Behaviour is preserved byte-for-byte: each branch
executes exactly the same action call as before.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.utils.logging_config import get_logger

from components.file_panel import FilePanel

if TYPE_CHECKING:
    from modern_commander import ModernCommanderApp


logger = get_logger(__name__)


class MenuDispatchController:
    """Routes F2 menu selections to the appropriate app action.

    The F2 menu (and the top menu bar) yields string action
    identifiers. ``execute_menu_action`` decodes the identifier and
    calls the matching ``action_*`` method on the owning
    ``ModernCommanderApp`` (or delegates to ``execute_panel_action``
    for panel-scoped items that start with ``left_`` / ``right_``).

    Args:
        app: The owning ``ModernCommanderApp`` instance. Held as a
            back-reference so the controller can invoke app-level
            actions without re-implementing them.
    """

    def __init__(self, app: "ModernCommanderApp") -> None:
        self.app = app

    def execute_menu_action(self, action: str) -> None:
        """Execute menu action from F2 menu system.

        Args:
            action: Action identifier from menu
        """
        app = self.app

        # Left panel actions
        if action.startswith("left_"):
            panel = app.left_panel
            action_type = action[5:]  # Remove "left_" prefix
            self.execute_panel_action(panel, action_type, "left")

        # Right panel actions
        elif action.startswith("right_"):
            panel = app.right_panel
            action_type = action[6:]  # Remove "right_" prefix
            self.execute_panel_action(panel, action_type, "right")

        # File operations
        elif action == "view_file":
            app.action_view_file()
        elif action == "edit_file":
            app.action_edit_file()
        elif action == "copy_files":
            app.action_copy_files()
        elif action == "move_files":
            app.action_move_files()
        elif action == "create_dir":
            app.action_create_directory()
        elif action == "delete_files":
            app.action_delete_files()

        # Selection operations
        elif action == "select_group":
            active_panel = app._get_active_panel()
            active_panel.action_select_group()
        elif action == "deselect_group":
            active_panel = app._get_active_panel()
            active_panel.action_deselect_group()
        elif action == "invert_selection":
            active_panel = app._get_active_panel()
            active_panel.action_invert_selection()

        # Command operations
        elif action == "find_file":
            app.action_find_file()
        elif action == "toggle_quick_view":
            app.action_toggle_quick_view()
        elif action == "refresh_panels":
            app.action_refresh_panels()
        elif action == "compare_dirs":
            app.action_compare_dirs()
        elif action == "swap_panels":
            app.action_swap_panels()
        elif action == "panel_history":
            app.action_panel_history()
        elif action == "goto_dir":
            app.action_goto_dir()

        # Options
        elif action == "show_config":
            app.action_show_config()
        elif action == "cycle_theme":
            app.action_cycle_theme()
        elif action == "toggle_hidden":
            app.action_toggle_hidden()
        elif action == "toggle_sizes":
            app.action_toggle_sizes()
        elif action == "toggle_dates":
            app.action_toggle_dates()
        elif action == "save_setup":
            app.action_save_setup()

        else:
            app.notify(
                f"Action not implemented: {action}", severity="warning"
            )

    def execute_panel_action(
        self,
        panel: Optional[FilePanel],
        action_type: str,
        panel_name: str,
    ) -> None:
        """Execute panel-specific action.

        Args:
            panel: Target panel
            action_type: Type of action (brief, full, sort_name, etc.)
            panel_name: Panel identifier ("left" or "right")
        """
        app = self.app
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
            app.notify(
                f"{panel_name.title()} panel: Tree view "
                "(using brief view as fallback)",
                severity="information",
            )
        elif action_type == "info":
            from features.view_modes import ViewMode
            import platform
            if platform.system() == "Windows":
                # Info view requires Unix permissions - fallback to
                # full view on Windows
                panel.set_view_mode(ViewMode.FULL)
                app.notify(
                    f"{panel_name.title()} panel: Info view "
                    "(not available on Windows, using full view)",
                    severity="information",
                )
            else:
                panel.set_view_mode(ViewMode.INFO)

        # Sort actions
        elif action_type == "sort_name":
            panel.sort_column = "name"
            panel.sort_reverse = False
            panel.refresh_directory()
            app.notify(f"{panel_name.title()} panel: Sorted by name")
        elif action_type == "sort_ext":
            panel.sort_column = "ext"
            panel.sort_reverse = False
            panel.refresh_directory()
            app.notify(
                f"{panel_name.title()} panel: Sorted by extension"
            )
        elif action_type == "sort_size":
            panel.sort_column = "size"
            panel.sort_reverse = True  # Largest first
            panel.refresh_directory()
            app.notify(f"{panel_name.title()} panel: Sorted by size")
        elif action_type == "sort_date":
            panel.sort_column = "date"
            panel.sort_reverse = True  # Newest first
            panel.refresh_directory()
            app.notify(f"{panel_name.title()} panel: Sorted by date")

        # Refresh action
        elif action_type == "refresh":
            panel.refresh_directory()
            app.notify(f"{panel_name.title()} panel refreshed")
