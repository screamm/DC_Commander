"""Panel coordination for ModernCommander.

Manages file panel operations and coordination between left and right panels.
Handles panel switching, synchronization, and active/inactive state management.
"""

from typing import Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from components.file_panel import FilePanel
    from features.view_modes import ViewMode


class PanelCoordinator:
    """Manages file panel operations and coordination.

    Responsibilities:
    - Track active panel state
    - Coordinate panel switching
    - Manage panel synchronization
    - Handle panel refresh operations
    """

    def __init__(self, left_panel: "FilePanel", right_panel: "FilePanel"):
        """Initialize panel coordinator.

        Args:
            left_panel: Left file panel instance
            right_panel: Right file panel instance
        """
        self.left_panel = left_panel
        self.right_panel = right_panel
        self._active_panel = "left"

    @property
    def active_panel_side(self) -> str:
        """Get active panel side identifier.

        Returns:
            Either "left" or "right"
        """
        return self._active_panel

    def get_active_panel(self) -> "FilePanel":
        """Get currently active file panel.

        Returns:
            Active FilePanel instance
        """
        return self.left_panel if self._active_panel == "left" else self.right_panel

    def get_inactive_panel(self) -> "FilePanel":
        """Get currently inactive file panel.

        Returns:
            Inactive FilePanel instance
        """
        return self.right_panel if self._active_panel == "left" else self.left_panel

    def set_active_panel(self, side: str) -> None:
        """Set active panel by side identifier.

        Args:
            side: Either "left" or "right"
        """
        if side not in ("left", "right"):
            raise ValueError(f"Invalid panel side: {side}")
        self._active_panel = side

    def switch_panel(self) -> str:
        """Switch active panel to the other panel.

        Returns:
            New active panel side ("left" or "right")
        """
        self._active_panel = "right" if self._active_panel == "left" else "left"
        return self._active_panel

    def swap_panels(self) -> None:
        """Swap directories between left and right panels."""
        left_path = self.left_panel.current_path
        right_path = self.right_panel.current_path

        self.left_panel.navigate_to(right_path)
        self.right_panel.navigate_to(left_path)

    def refresh_panels(self) -> None:
        """Refresh both file panels."""
        self.left_panel.refresh_directory()
        self.right_panel.refresh_directory()

    def sync_panel_view_modes(self, mode: "ViewMode") -> None:
        """Synchronize view mode across both panels.

        Args:
            mode: ViewMode to apply to both panels
        """
        self.left_panel.set_view_mode(mode)
        self.right_panel.set_view_mode(mode)

    def get_panel_paths(self) -> tuple[Path, Path]:
        """Get current paths of both panels.

        Returns:
            Tuple of (left_path, right_path)
        """
        return (self.left_panel.current_path, self.right_panel.current_path)

    def navigate_active_to(self, path: Path) -> None:
        """Navigate active panel to specified path.

        Args:
            path: Target directory path
        """
        active = self.get_active_panel()
        active.navigate_to(path)

    def toggle_hidden_files(self) -> None:
        """Toggle hidden files visibility in active panel."""
        active = self.get_active_panel()
        active.toggle_hidden_files()

    def clear_selection(self) -> None:
        """Clear selection in active panel."""
        active = self.get_active_panel()
        active.clear_selection()
