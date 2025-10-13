"""
File Hash Plugin for DC Commander

Calculates cryptographic hashes (MD5, SHA256) for selected files.
Demonstrates plugin action registration and file operation hooks.
"""

import hashlib
from pathlib import Path
from typing import Dict, Callable

from src.plugins.plugin_interface import PluginInterface, PluginMetadata


class FileHashPlugin(PluginInterface):
    """
    Plugin that calculates file hashes.

    Features:
    - Calculate MD5 hash of selected file
    - Calculate SHA256 hash of selected file
    - Automatic hash calculation on file selection (optional)
    - Display hash in notification
    """

    def __init__(self):
        """Initialize file hash plugin."""
        self.app = None
        self.auto_hash_enabled = False
        self.last_hash: Dict[str, str] = {}

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="file_hash_plugin",
            version="1.0.0",
            author="DC Commander Team",
            description="Calculate cryptographic hashes (MD5, SHA256) for files",
            dependencies=[],
            min_app_version="1.0.0"
        )

    def initialize(self, app) -> None:
        """
        Initialize plugin with app reference.

        Args:
            app: ModernCommanderApp instance
        """
        self.app = app
        print(f"[FileHashPlugin] Initialized v{self.metadata.version}")

    def shutdown(self) -> None:
        """Clean up plugin resources."""
        self.app = None
        self.last_hash.clear()
        print("[FileHashPlugin] Shutdown complete")

    def register_actions(self) -> Dict[str, Callable]:
        """
        Register plugin actions.

        Returns:
            Dictionary mapping action names to handlers
        """
        return {
            "calculate_md5": self.calculate_md5_hash,
            "calculate_sha256": self.calculate_sha256_hash,
            "toggle_auto_hash": self.toggle_auto_hash,
            "show_last_hash": self.show_last_hash
        }

    def register_commands(self) -> Dict[str, str]:
        """
        Register keyboard command mappings.

        Returns:
            Dictionary mapping keyboard shortcuts to action names
        """
        return {
            "ctrl+shift+m": "calculate_md5",
            "ctrl+shift+s": "calculate_sha256",
            "ctrl+shift+h": "show_last_hash"
        }

    def register_menu_items(self) -> Dict[str, Dict[str, str]]:
        """
        Register menu items.

        Returns:
            Dictionary mapping menu categories to items
        """
        return {
            "Commands": {
                "Calculate MD5": "calculate_md5",
                "Calculate SHA256": "calculate_sha256",
                "Toggle Auto-Hash": "toggle_auto_hash",
                "Show Last Hash": "show_last_hash"
            }
        }

    def on_file_selected(self, file_path: str) -> None:
        """
        Hook called when file is selected.

        Args:
            file_path: Path to selected file
        """
        if self.auto_hash_enabled:
            # Auto-calculate hash for small files only
            path = Path(file_path)
            if path.is_file() and path.stat().st_size < 1024 * 1024:  # < 1MB
                self._calculate_hash(file_path, "sha256", notify=False)

    def calculate_md5_hash(self) -> None:
        """Calculate MD5 hash of selected file."""
        file_path = self._get_selected_file_path()
        if file_path:
            hash_value = self._calculate_hash(file_path, "md5", notify=True)
            if hash_value:
                self.last_hash = {"file": file_path, "algorithm": "MD5", "hash": hash_value}

    def calculate_sha256_hash(self) -> None:
        """Calculate SHA256 hash of selected file."""
        file_path = self._get_selected_file_path()
        if file_path:
            hash_value = self._calculate_hash(file_path, "sha256", notify=True)
            if hash_value:
                self.last_hash = {"file": file_path, "algorithm": "SHA256", "hash": hash_value}

    def toggle_auto_hash(self) -> None:
        """Toggle automatic hash calculation on file selection."""
        self.auto_hash_enabled = not self.auto_hash_enabled
        status = "enabled" if self.auto_hash_enabled else "disabled"

        if self.app:
            self.app.notify(
                f"Auto-hash calculation {status}",
                severity="information"
            )

    def show_last_hash(self) -> None:
        """Display the last calculated hash."""
        if not self.last_hash:
            if self.app:
                self.app.notify(
                    "No hash calculated yet",
                    severity="information"
                )
            return

        message = (
            f"File: {Path(self.last_hash['file']).name}\n"
            f"Algorithm: {self.last_hash['algorithm']}\n"
            f"Hash: {self.last_hash['hash']}"
        )

        if self.app:
            from components.dialogs import MessageDialog
            dialog = MessageDialog(
                title="Last Calculated Hash",
                message=message,
                message_type="info"
            )
            self.app.push_screen(dialog)

    def _get_selected_file_path(self) -> str:
        """
        Get currently selected file path from active panel.

        Returns:
            File path or empty string if no file selected
        """
        if not self.app:
            return ""

        # Get active panel
        active_panel = self.app._get_active_panel()
        if not active_panel:
            return ""

        # Get current item
        current_item = active_panel.get_current_item()
        if not current_item or current_item.is_dir or current_item.is_parent:
            if self.app:
                self.app.notify(
                    "Please select a file",
                    severity="warning"
                )
            return ""

        return str(current_item.path)

    def _calculate_hash(
        self,
        file_path: str,
        algorithm: str,
        notify: bool = True
    ) -> str:
        """
        Calculate hash of file.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm ("md5" or "sha256")
            notify: Whether to show notification

        Returns:
            Hash value as hex string
        """
        try:
            path = Path(file_path)

            # Check file exists and is not too large (max 100MB for hash)
            if not path.is_file():
                if notify and self.app:
                    self.app.notify(
                        "Not a file",
                        severity="error"
                    )
                return ""

            file_size = path.stat().st_size
            if file_size > 100 * 1024 * 1024:  # 100MB limit
                if notify and self.app:
                    self.app.notify(
                        "File too large for hashing (max 100MB)",
                        severity="error"
                    )
                return ""

            # Calculate hash
            if algorithm == "md5":
                hasher = hashlib.md5()
            elif algorithm == "sha256":
                hasher = hashlib.sha256()
            else:
                if notify and self.app:
                    self.app.notify(
                        f"Unknown algorithm: {algorithm}",
                        severity="error"
                    )
                return ""

            # Read file in chunks
            with open(path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)

            hash_value = hasher.hexdigest()

            # Show notification
            if notify and self.app:
                self.app.notify(
                    f"{algorithm.upper()}: {hash_value[:16]}...",
                    severity="information",
                    timeout=5
                )

            return hash_value

        except Exception as e:
            if notify and self.app:
                self.app.notify(
                    f"Hash calculation failed: {e}",
                    severity="error"
                )
            return ""
