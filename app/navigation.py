"""Navigation and panel-switching action handlers for ModernCommanderApp.

This module extracts panel navigation logic from the
``modern_commander`` monolith into :class:`NavigationController`:
switching the active panel, refreshing panels, swapping panel
directories, go-to-directory (with validation), compare panels, and
the stub panel-history dialog. ``ModernCommanderApp`` holds a single
instance and delegates the corresponding ``action_*`` methods to it.

Behaviour is preserved verbatim: each public method mirrors the
previous monolith method one-for-one. The controller reads and writes
to the owning app so no state is duplicated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.utils.logging_config import get_logger

from components.dialogs import ErrorDialog, InputDialog, MessageDialog
from src.core.ui_security import UIValidationError, validate_user_path

if TYPE_CHECKING:
    from modern_commander import ModernCommanderApp


logger = get_logger(__name__)


class NavigationController:
    """Panel navigation action handlers extracted from ModernCommanderApp.

    Owns the TAB (switch panel), Ctrl+R (refresh), and the swap / goto
    / compare / panel-history actions. The controller holds no state;
    it reads and writes to the owning ``ModernCommanderApp`` so the
    refactor is purely organisational.

    Args:
        app: The owning ``ModernCommanderApp`` instance. Held as a
            back-reference so the controller can reach shared panels
            without re-implementing them.
    """

    def __init__(self, app: "ModernCommanderApp") -> None:
        self.app = app

    # ------------------------------------------------------------------
    # Panel management
    # ------------------------------------------------------------------
    def switch_panel(self) -> None:
        """Switch active panel (TAB key)."""
        app = self.app
        # Toggle active panel
        app.active_panel = "right" if app.active_panel == "left" else "left"

        # Update borders
        app._update_panel_borders()

        # Focus new active panel
        active_panel = app._get_active_panel()
        active_panel.focus()

        # Update Quick View for new active panel
        app._update_quick_view()

    def refresh_panels(self) -> None:
        """Refresh both panels."""
        app = self.app
        if app.left_panel:
            app.left_panel.refresh_directory()
        if app.right_panel:
            app.right_panel.refresh_directory()

        app.notify("Panels refreshed")

    def swap_panels(self) -> None:
        """Swap directories between left and right panels."""
        app = self.app
        if app.left_panel and app.right_panel:
            # Get current paths
            left_path = app.left_panel.current_path
            right_path = app.right_panel.current_path

            # Swap paths
            app.left_panel.navigate_to(right_path)
            app.right_panel.navigate_to(left_path)

            app.notify("Panels swapped")

    # ------------------------------------------------------------------
    # Go-to directory with validation
    # ------------------------------------------------------------------
    def goto_dir(self) -> None:
        """Navigate active panel to a specific directory.

        User input is validated via :func:`validate_user_path` before
        navigation. The path is resolved, checked for existence, and
        must point at a directory. Invalid input shows a retry-capable
        :class:`ErrorDialog`.
        """
        app = self.app
        active_panel = app._get_active_panel()
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

                    app.push_screen(
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

                    app.push_screen(
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
            app.push_screen(dialog)

        prompt()

    # ------------------------------------------------------------------
    # Comparison and history
    # ------------------------------------------------------------------
    def compare_dirs(self) -> None:
        """Compare directories between left and right panels."""
        app = self.app
        if not app.left_panel or not app.right_panel:
            return

        # Get file lists from both panels
        left_files = {
            item.name: item
            for item in app.left_panel._file_items
            if not item.is_parent
        }
        right_files = {
            item.name: item
            for item in app.right_panel._file_items
            if not item.is_parent
        }

        # Find differences
        only_left = set(left_files.keys()) - set(right_files.keys())
        only_right = set(right_files.keys()) - set(left_files.keys())
        common = set(left_files.keys()) & set(right_files.keys())

        # Find files with different sizes or dates
        different = []
        for name in common:
            left_item = left_files[name]
            right_item = right_files[name]
            if (
                left_item.size != right_item.size
                or left_item.modified != right_item.modified
            ):
                different.append(name)

        # Build comparison message
        message_lines = [
            f"**Left panel**: {app.left_panel.current_path}",
            f"**Right panel**: {app.right_panel.current_path}",
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
                message_lines.append(
                    f"  ... and {len(only_left) - 10} more"
                )

        if only_right:
            message_lines.append("")
            message_lines.append("**Files only in right:**")
            for name in sorted(list(only_right)[:10]):  # Show first 10
                message_lines.append(f"  • {name}")
            if len(only_right) > 10:
                message_lines.append(
                    f"  ... and {len(only_right) - 10} more"
                )

        if different:
            message_lines.append("")
            message_lines.append("**Files with differences:**")
            for name in sorted(different[:10]):  # Show first 10
                message_lines.append(f"  • {name}")
            if len(different) > 10:
                message_lines.append(
                    f"  ... and {len(different) - 10} more"
                )

        dialog = MessageDialog(
            title="Compare Directories",
            message="\n".join(message_lines),
            message_type="info",
        )
        app.push_screen(dialog)

    def panel_history(self) -> None:
        """Show panel navigation history (stub dialog)."""
        app = self.app
        active_panel = app._get_active_panel()

        # For now, show a placeholder - full history tracking would
        # require maintaining a history list. This could be enhanced by
        # adding a history stack to FilePanel.
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
            message_type="info",
        )
        app.push_screen(dialog)
