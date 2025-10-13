"""
Image Preview Plugin for DC Commander

Shows image thumbnails and metadata in Quick View.
Demonstrates plugin integration with Quick View system and file hooks.
"""

from pathlib import Path
from typing import Dict, Callable, Optional
import mimetypes

from src.plugins.plugin_interface import PluginInterface, PluginMetadata


class ImagePreviewPlugin(PluginInterface):
    """
    Plugin that shows image previews in Quick View.

    Features:
    - Detect image files automatically
    - Show image dimensions and file size
    - Display basic EXIF data (if available)
    - Quick View integration
    """

    # Supported image formats
    SUPPORTED_FORMATS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp',
        '.webp', '.ico', '.tiff', '.tif'
    }

    def __init__(self):
        """Initialize image preview plugin."""
        self.app = None
        self.preview_enabled = True
        self._pil_available = False

        # Try to import PIL for advanced features
        try:
            from PIL import Image
            self._pil_available = True
        except ImportError:
            pass

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="image_preview_plugin",
            version="1.0.0",
            author="DC Commander Team",
            description="Show image thumbnails and metadata in Quick View",
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
        pil_status = "available" if self._pil_available else "not available"
        print(f"[ImagePreviewPlugin] Initialized v{self.metadata.version} (PIL: {pil_status})")

    def shutdown(self) -> None:
        """Clean up plugin resources."""
        self.app = None
        print("[ImagePreviewPlugin] Shutdown complete")

    def register_actions(self) -> Dict[str, Callable]:
        """
        Register plugin actions.

        Returns:
            Dictionary mapping action names to handlers
        """
        return {
            "toggle_image_preview": self.toggle_preview,
            "show_image_info": self.show_image_info
        }

    def register_commands(self) -> Dict[str, str]:
        """
        Register keyboard command mappings.

        Returns:
            Dictionary mapping keyboard shortcuts to action names
        """
        return {
            "ctrl+shift+i": "show_image_info"
        }

    def register_menu_items(self) -> Dict[str, Dict[str, str]]:
        """
        Register menu items.

        Returns:
            Dictionary mapping menu categories to items
        """
        return {
            "Commands": {
                "Toggle Image Preview": "toggle_image_preview",
                "Show Image Info": "show_image_info"
            }
        }

    def on_file_selected(self, file_path: str) -> None:
        """
        Hook called when file is selected.

        Automatically shows image info for image files.

        Args:
            file_path: Path to selected file
        """
        if not self.preview_enabled:
            return

        if self._is_image_file(file_path):
            # Image info will be shown automatically in Quick View
            # This hook could trigger additional processing if needed
            pass

    def toggle_preview(self) -> None:
        """Toggle image preview feature."""
        self.preview_enabled = not self.preview_enabled
        status = "enabled" if self.preview_enabled else "disabled"

        if self.app:
            self.app.notify(
                f"Image preview {status}",
                severity="information"
            )

    def show_image_info(self) -> None:
        """Display detailed image information."""
        file_path = self._get_selected_file_path()
        if not file_path:
            return

        if not self._is_image_file(file_path):
            if self.app:
                self.app.notify(
                    "Selected file is not an image",
                    severity="warning"
                )
            return

        # Get image info
        info = self._get_image_info(file_path)
        if not info:
            return

        # Format message
        message_lines = [
            f"File: {Path(file_path).name}",
            f"Format: {info['format']}",
            f"Size: {info['file_size']}",
        ]

        if info.get('dimensions'):
            width, height = info['dimensions']
            message_lines.append(f"Dimensions: {width} x {height} pixels")

        if info.get('mode'):
            message_lines.append(f"Mode: {info['mode']}")

        if info.get('exif_data'):
            message_lines.append("")
            message_lines.append("EXIF Data:")
            for key, value in list(info['exif_data'].items())[:5]:  # Show first 5
                message_lines.append(f"  {key}: {value}")

        message = "\n".join(message_lines)

        # Show dialog
        if self.app:
            from components.dialogs import MessageDialog
            dialog = MessageDialog(
                title="Image Information",
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
            return ""

        return str(current_item.path)

    def _is_image_file(self, file_path: str) -> bool:
        """
        Check if file is an image.

        Args:
            file_path: Path to file

        Returns:
            True if file is an image, False otherwise
        """
        path = Path(file_path)

        # Check extension
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            return False

        # Verify MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type and mime_type.startswith('image/'):
            return True

        return False

    def _get_image_info(self, file_path: str) -> Optional[Dict]:
        """
        Get image information.

        Args:
            file_path: Path to image file

        Returns:
            Dictionary with image info or None on error
        """
        try:
            path = Path(file_path)

            info = {
                'format': path.suffix.upper()[1:],  # Remove dot
                'file_size': self._format_file_size(path.stat().st_size)
            }

            # Use PIL if available for detailed info
            if self._pil_available:
                try:
                    from PIL import Image

                    with Image.open(path) as img:
                        info['dimensions'] = img.size
                        info['mode'] = img.mode

                        # Try to get EXIF data
                        if hasattr(img, '_getexif'):
                            exif = img._getexif()
                            if exif:
                                info['exif_data'] = {
                                    str(k): str(v) for k, v in list(exif.items())[:10]
                                }

                except Exception as e:
                    # PIL failed, but we still have basic info
                    pass

            return info

        except Exception as e:
            if self.app:
                self.app.notify(
                    f"Failed to read image info: {e}",
                    severity="error"
                )
            return None

    def _format_file_size(self, size: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            size: File size in bytes

        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def get_config_schema(self) -> Optional[Dict]:
        """
        Define plugin configuration schema.

        Returns:
            Configuration schema dictionary
        """
        return {
            "preview_enabled": {
                "type": "bool",
                "default": True,
                "description": "Enable automatic image preview"
            },
            "max_preview_size": {
                "type": "int",
                "default": 10 * 1024 * 1024,  # 10MB
                "description": "Maximum file size for preview (bytes)"
            }
        }
