"""
Theme Manager for Modern Commander

Provides dynamic theme switching with support for built-in and custom themes.
Manages theme loading, validation, and CSS generation for Textual applications.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class ThemeType(Enum):
    """Theme type classification."""
    BUILT_IN = "built_in"
    CUSTOM = "custom"


@dataclass
class ThemeMetadata:
    """
    Theme metadata for enhanced theme management.

    Attributes:
        theme_id: Unique theme identifier (matches theme file name)
        display_name: Human-readable theme name
        theme_type: Classification as built-in or custom theme
        description: Theme description for user reference
        author: Theme creator name
        created_date: ISO format creation timestamp
        modified_date: ISO format last modification timestamp
        is_editable: Whether theme can be modified by user
    """
    theme_id: str
    display_name: str
    theme_type: ThemeType
    description: str = ""
    author: str = "Unknown"
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_date: str = field(default_factory=lambda: datetime.now().isoformat())
    is_editable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metadata to dictionary for JSON serialization.

        Returns:
            Dictionary representation with theme_type as string
        """
        data = asdict(self)
        data['theme_type'] = self.theme_type.value
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ThemeMetadata':
        """
        Create metadata from dictionary.

        Args:
            data: Dictionary with metadata fields

        Returns:
            ThemeMetadata object with validated fields
        """
        theme_type_str = data.get('theme_type', ThemeType.BUILT_IN.value)
        try:
            theme_type = ThemeType(theme_type_str)
        except ValueError:
            logger.warning(f"Invalid theme_type '{theme_type_str}', defaulting to BUILT_IN")
            theme_type = ThemeType.BUILT_IN

        return ThemeMetadata(
            theme_id=data.get('theme_id', 'unknown'),
            display_name=data.get('display_name', 'Unknown Theme'),
            theme_type=theme_type,
            description=data.get('description', ''),
            author=data.get('author', 'Unknown'),
            created_date=data.get('created_date', datetime.now().isoformat()),
            modified_date=data.get('modified_date', datetime.now().isoformat()),
            is_editable=data.get('is_editable', True)
        )


@dataclass
class Theme:
    """
    Theme definition with comprehensive color palette.

    Attributes:
        name: Theme identifier
        display_name: Human-readable theme name
        primary: Primary accent color (borders, highlights)
        accent: Secondary accent color (inactive borders)
        surface: Background color for main surface
        panel: Panel background color
        text: Primary text color
        text_muted: Muted/secondary text color
        warning: Warning message color
        error: Error message color
        success: Success message color
        selection: Selected item highlight color
        selection_text: Text color for selected items
        metadata: Optional theme metadata for enhanced management
    """
    name: str
    display_name: str
    primary: str
    accent: str
    surface: str
    panel: str
    text: str
    text_muted: str
    warning: str
    error: str
    success: str
    selection: str
    selection_text: str
    metadata: Optional[ThemeMetadata] = None

    def to_css_variables(self) -> str:
        """
        Generate CSS variable declarations for this theme.

        Returns:
            CSS string with variable definitions
        """
        return f"""
    /* {self.display_name} Theme */
    $primary: {self.primary};
    $accent: {self.accent};
    $surface: {self.surface};
    $panel: {self.panel};
    $text: {self.text};
    $text-muted: {self.text_muted};
    $warning: {self.warning};
    $error: {self.error};
    $success: {self.success};
    $selection: {self.selection};
    $selection-text: {self.selection_text};
"""

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert theme to dictionary for JSON serialization.

        Returns:
            Dictionary representation with colors and optional metadata
        """
        data = {
            'name': self.name,
            'display_name': self.display_name,
            'primary': self.primary,
            'accent': self.accent,
            'surface': self.surface,
            'panel': self.panel,
            'text': self.text,
            'text_muted': self.text_muted,
            'warning': self.warning,
            'error': self.error,
            'success': self.success,
            'selection': self.selection,
            'selection_text': self.selection_text
        }

        if self.metadata:
            data['metadata'] = self.metadata.to_dict()

        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Theme':
        """
        Create theme from dictionary with backward compatibility.

        Handles both old format (colors only) and new format (colors + metadata).
        If metadata is missing, defaults to BUILT_IN theme type.

        Args:
            data: Dictionary with theme data

        Returns:
            Theme object with validated fields
        """
        # Extract metadata if present (new format)
        metadata = None
        if 'metadata' in data:
            metadata = ThemeMetadata.from_dict(data['metadata'])
        else:
            # Backward compatibility: Create default metadata for old format
            theme_id = data.get('name', 'unknown')
            metadata = ThemeMetadata(
                theme_id=theme_id,
                display_name=data.get('display_name', 'Unknown Theme'),
                theme_type=ThemeType.BUILT_IN,
                description=f"Legacy theme '{theme_id}'",
                author="Unknown",
                is_editable=False
            )
            logger.debug(f"Created default metadata for legacy theme '{theme_id}'")

        return Theme(
            name=data.get('name', 'unknown'),
            display_name=data.get('display_name', 'Unknown Theme'),
            primary=data.get('primary', '#0000AA'),
            accent=data.get('accent', '#00FFFF'),
            surface=data.get('surface', '#000055'),
            panel=data.get('panel', '#0000AA'),
            text=data.get('text', '#FFFF77'),
            text_muted=data.get('text_muted', '#AAAAAA'),
            warning=data.get('warning', '#FFFF00'),
            error=data.get('error', '#FF5555'),
            success=data.get('success', '#55FF55'),
            selection=data.get('selection', '#FFFF00'),
            selection_text=data.get('selection_text', '#000000'),
            metadata=metadata
        )

    def validate(self) -> List[str]:
        """
        Validate theme definition.

        Returns:
            List of validation errors (empty if valid)
        """
        issues = []

        # Check all color fields are defined
        required_fields = [
            'primary', 'accent', 'surface', 'panel', 'text', 'text_muted',
            'warning', 'error', 'success', 'selection', 'selection_text'
        ]

        for field in required_fields:
            value = getattr(self, field, None)
            if not value:
                issues.append(f"Missing required color field: {field}")
            elif not self._is_valid_color(value):
                issues.append(f"Invalid color format for {field}: {value}")

        return issues

    @staticmethod
    def _is_valid_color(color: str) -> bool:
        """
        Validate color string format.

        Args:
            color: Color string to validate

        Returns:
            True if valid color format
        """
        if not color:
            return False

        # Support hex colors (#RGB, #RRGGBB, #RRGGBBAA)
        if color.startswith('#'):
            hex_part = color[1:]
            if len(hex_part) in (3, 6, 8):
                try:
                    int(hex_part, 16)
                    return True
                except ValueError:
                    pass

        # Support named colors and rgb/rgba
        if color.lower() in ['transparent', 'inherit', 'currentcolor']:
            return True

        if color.startswith(('rgb(', 'rgba(', 'hsl(', 'hsla(')):
            return True

        # Support Textual color names
        textual_colors = [
            'black', 'white', 'red', 'green', 'blue', 'yellow', 'magenta', 'cyan',
            'gray', 'grey', 'darkgray', 'darkgrey', 'lightgray', 'lightgrey'
        ]

        if color.lower() in textual_colors:
            return True

        return False


class ThemeManager:
    """
    Manages theme loading, switching, and persistence.

    Handles both built-in themes (from features/themes/) and custom user themes.
    Provides dynamic theme application and configuration integration with support
    for theme toggling and custom theme management.

    Constants:
        BUILT_IN_THEMES: List of built-in theme identifiers
        CUSTOM_THEME_SLOTS: Available slots for custom themes
        MAX_CUSTOM_THEMES: Maximum number of custom themes allowed
    """

    # Built-in theme identifiers
    BUILT_IN_THEMES = ["norton_commander", "modern_dark", "solarized", "midnight_blue"]

    # Custom theme configuration
    CUSTOM_THEME_SLOTS = ["custom1", "custom2"]
    MAX_CUSTOM_THEMES = 2

    def __init__(self, themes_dir: Optional[Path] = None):
        """
        Initialize theme manager.

        Args:
            themes_dir: Directory containing theme files. If None, uses default.
        """
        if themes_dir is None:
            # Default to features/themes directory
            self.themes_dir = Path(__file__).parent / "themes"
        else:
            self.themes_dir = Path(themes_dir)

        # Ensure themes directory exists
        self.themes_dir.mkdir(parents=True, exist_ok=True)

        # Cache loaded themes
        self._themes_cache: Dict[str, Theme] = {}

        # Current active theme
        self._current_theme: Optional[Theme] = None

        logger.debug(f"ThemeManager initialized with themes_dir: {self.themes_dir}")

    def get_toggle_themes(self) -> List[str]:
        """
        Get list of themes for toggle cycling.

        Returns built-in themes plus existing custom themes only.
        Custom themes are included only if they exist on disk.

        Returns:
            List of theme identifiers available for toggling
        """
        toggle_list = []

        # Add all built-in themes
        toggle_list.extend(self.BUILT_IN_THEMES)

        # Add only existing custom themes
        for slot in self.CUSTOM_THEME_SLOTS:
            theme_file = self.themes_dir / f"{slot}.json"
            if theme_file.exists():
                toggle_list.append(slot)
                logger.debug(f"Added custom theme '{slot}' to toggle list")

        logger.debug(f"Toggle themes: {toggle_list}")
        return toggle_list

    def toggle_theme(self) -> Optional[str]:
        """
        Toggle to next theme in the toggle list.

        Cycles through get_toggle_themes() list, not all available themes.
        If no current theme is set, returns first theme in toggle list.

        Returns:
            Next theme identifier in cycle, or None if no themes available
        """
        toggle_list = self.get_toggle_themes()

        if not toggle_list:
            logger.warning("No themes available for toggling")
            return None

        if not self._current_theme:
            # No current theme, return first in list
            next_theme = toggle_list[0]
            logger.debug(f"No current theme, selecting first: {next_theme}")
            return next_theme

        current_name = self._current_theme.name

        try:
            current_index = toggle_list.index(current_name)
            next_index = (current_index + 1) % len(toggle_list)
            next_theme = toggle_list[next_index]
            logger.debug(f"Toggling from '{current_name}' to '{next_theme}'")
            return next_theme
        except ValueError:
            # Current theme not in toggle list, return first
            next_theme = toggle_list[0]
            logger.warning(f"Current theme '{current_name}' not in toggle list, selecting first: {next_theme}")
            return next_theme

    def apply_theme(self, theme_id: str) -> bool:
        """
        Apply theme and persist to configuration.

        Loads the specified theme and sets it as current. The caller is responsible
        for persisting the theme_id to configuration (e.g., ConfigManager).

        Args:
            theme_id: Theme identifier to apply

        Returns:
            True if theme applied successfully, False otherwise
        """
        if not theme_id:
            logger.error("Cannot apply theme: theme_id is empty")
            return False

        # Validate theme_id for security (prevent directory traversal)
        if not self._is_valid_theme_id(theme_id):
            logger.error(f"Invalid theme_id format: {theme_id}")
            return False

        theme = self.load_theme(theme_id)

        if theme is None:
            logger.error(f"Failed to apply theme: theme '{theme_id}' not found or invalid")
            return False

        self._current_theme = theme
        logger.info(f"Applied theme: {theme_id} ({theme.display_name})")
        return True

    def get_all_themes(self) -> List[Theme]:
        """
        Get all available themes (built-in and custom).

        Returns:
            List of Theme objects for all available themes
        """
        themes = []

        for theme_name in self.get_available_themes():
            theme = self.load_theme(theme_name)
            if theme:
                themes.append(theme)

        logger.debug(f"Retrieved {len(themes)} total themes")
        return themes

    def get_built_in_themes(self) -> List[Theme]:
        """
        Get only built-in themes.

        Returns:
            List of Theme objects for built-in themes only
        """
        themes = []

        for theme_name in self.BUILT_IN_THEMES:
            theme = self.load_theme(theme_name)
            if theme:
                themes.append(theme)

        logger.debug(f"Retrieved {len(themes)} built-in themes")
        return themes

    def get_custom_themes(self) -> List[Theme]:
        """
        Get only custom themes.

        Returns:
            List of Theme objects for custom themes only
        """
        themes = []

        for slot in self.CUSTOM_THEME_SLOTS:
            theme = self.load_theme(slot)
            if theme:
                themes.append(theme)

        logger.debug(f"Retrieved {len(themes)} custom themes")
        return themes

    def save_custom_theme(self, slot: str, theme: Theme) -> bool:
        """
        Save theme to a custom theme slot.

        Validates that slot is one of the allowed custom slots (custom1, custom2).
        Updates theme metadata to mark as custom and set appropriate dates.

        Args:
            slot: Custom theme slot identifier (must be in CUSTOM_THEME_SLOTS)
            theme: Theme object to save

        Returns:
            True if saved successfully, False otherwise

        Raises:
            ValueError: If slot is not a valid custom theme slot
        """
        if slot not in self.CUSTOM_THEME_SLOTS:
            raise ValueError(f"Invalid custom theme slot '{slot}'. Must be one of: {self.CUSTOM_THEME_SLOTS}")

        # Validate theme
        issues = theme.validate()
        if issues:
            logger.error(f"Cannot save custom theme: validation failed")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False

        # Update theme metadata for custom theme
        now = datetime.now().isoformat()
        if theme.metadata:
            theme.metadata.theme_id = slot
            theme.metadata.theme_type = ThemeType.CUSTOM
            theme.metadata.modified_date = now
            theme.metadata.is_editable = True
        else:
            theme.metadata = ThemeMetadata(
                theme_id=slot,
                display_name=theme.display_name,
                theme_type=ThemeType.CUSTOM,
                description=f"Custom theme in slot {slot}",
                author="User",
                created_date=now,
                modified_date=now,
                is_editable=True
            )

        # Update theme name to match slot
        theme.name = slot

        try:
            theme_file = self.themes_dir / f"{slot}.json"

            # Ensure directory exists
            theme_file.parent.mkdir(parents=True, exist_ok=True)

            # Validate path for security
            if not self._is_safe_path(theme_file):
                logger.error(f"Security error: invalid path for theme file")
                return False

            # Convert to dictionary
            theme_dict = theme.to_dict()

            # Write with pretty formatting
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme_dict, f, indent=2, ensure_ascii=False)

            # Update cache
            self._themes_cache[slot] = theme

            logger.info(f"Saved custom theme to slot '{slot}'")
            return True

        except (IOError, OSError) as e:
            logger.error(f"Error saving custom theme to slot '{slot}': {e}")
            return False

    def delete_custom_theme(self, slot: str) -> bool:
        """
        Delete a custom theme from the specified slot.

        Removes the theme file from disk and clears it from cache.
        Only works for custom theme slots.

        Args:
            slot: Custom theme slot identifier (must be in CUSTOM_THEME_SLOTS)

        Returns:
            True if deleted successfully, False otherwise

        Raises:
            ValueError: If slot is not a valid custom theme slot
        """
        if slot not in self.CUSTOM_THEME_SLOTS:
            raise ValueError(f"Invalid custom theme slot '{slot}'. Must be one of: {self.CUSTOM_THEME_SLOTS}")

        theme_file = self.themes_dir / f"{slot}.json"

        if not theme_file.exists():
            logger.warning(f"Custom theme '{slot}' does not exist, nothing to delete")
            return True  # Already deleted

        try:
            # Validate path for security
            if not self._is_safe_path(theme_file):
                logger.error(f"Security error: invalid path for theme file")
                return False

            # Delete file
            theme_file.unlink()

            # Remove from cache
            if slot in self._themes_cache:
                del self._themes_cache[slot]

            logger.info(f"Deleted custom theme from slot '{slot}'")
            return True

        except (IOError, OSError) as e:
            logger.error(f"Error deleting custom theme from slot '{slot}': {e}")
            return False

    def has_custom_slot_available(self) -> bool:
        """
        Check if any custom theme slot is available.

        Returns:
            True if at least one custom slot is free, False otherwise
        """
        return self.get_available_custom_slot() is not None

    def get_available_custom_slot(self) -> Optional[str]:
        """
        Get the first available custom theme slot.

        Returns:
            First free custom slot identifier, or None if all slots are full
        """
        for slot in self.CUSTOM_THEME_SLOTS:
            theme_file = self.themes_dir / f"{slot}.json"
            if not theme_file.exists():
                logger.debug(f"Found available custom slot: {slot}")
                return slot

        logger.debug("No custom slots available")
        return None

    def get_available_themes(self) -> List[str]:
        """
        Get list of available theme names.

        Returns:
            List of theme identifiers
        """
        themes = []

        if self.themes_dir.exists():
            for theme_file in self.themes_dir.glob("*.json"):
                theme_name = theme_file.stem
                themes.append(theme_name)

        return sorted(themes)

    def load_theme(self, theme_name: str) -> Optional[Theme]:
        """
        Load theme by name.

        Args:
            theme_name: Theme identifier (without .json extension)

        Returns:
            Theme object if successful, None otherwise
        """
        if not theme_name:
            logger.error("Cannot load theme: theme_name is empty")
            return None

        # Validate theme_name for security
        if not self._is_valid_theme_id(theme_name):
            logger.error(f"Invalid theme_name format: {theme_name}")
            return None

        # Check cache first
        if theme_name in self._themes_cache:
            logger.debug(f"Loading theme '{theme_name}' from cache")
            return self._themes_cache[theme_name]

        # Load from file
        theme_file = self.themes_dir / f"{theme_name}.json"

        if not theme_file.exists():
            logger.warning(f"Theme file not found: {theme_file}")
            return None

        # Validate path for security
        if not self._is_safe_path(theme_file):
            logger.error(f"Security error: invalid path for theme file")
            return None

        try:
            with open(theme_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Create theme object with backward compatibility
            theme = Theme.from_dict(data)

            # Validate theme
            issues = theme.validate()
            if issues:
                logger.warning(f"Theme '{theme_name}' has validation issues:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
                return None

            # Cache theme
            self._themes_cache[theme_name] = theme

            logger.debug(f"Loaded theme '{theme_name}' successfully")
            return theme

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error loading theme '{theme_name}': {e}")
            return None
        except (KeyError, TypeError) as e:
            logger.error(f"Data structure error loading theme '{theme_name}': {e}")
            return None
        except (IOError, OSError) as e:
            logger.error(f"File I/O error loading theme '{theme_name}': {e}")
            return None

    def save_theme(self, theme: Theme) -> bool:
        """
        Save theme to file.

        Args:
            theme: Theme object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate theme
            issues = theme.validate()
            if issues:
                logger.error(f"Cannot save theme: validation failed")
                for issue in issues:
                    logger.error(f"  - {issue}")
                return False

            theme_file = self.themes_dir / f"{theme.name}.json"

            # Ensure directory exists
            theme_file.parent.mkdir(parents=True, exist_ok=True)

            # Validate path for security
            if not self._is_safe_path(theme_file):
                logger.error(f"Security error: invalid path for theme file")
                return False

            # Convert to dictionary
            theme_dict = theme.to_dict()

            # Write with pretty formatting
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme_dict, f, indent=2, ensure_ascii=False)

            # Update cache
            self._themes_cache[theme.name] = theme

            logger.info(f"Saved theme '{theme.name}' successfully")
            return True

        except (IOError, OSError) as e:
            logger.error(f"Error saving theme '{theme.name}': {e}")
            return False

    def get_current_theme(self) -> Optional[Theme]:
        """
        Get currently active theme.

        Returns:
            Current Theme object or None
        """
        return self._current_theme

    def set_current_theme(self, theme_name: str) -> bool:
        """
        Set active theme by name.

        Args:
            theme_name: Theme identifier to activate

        Returns:
            True if successful, False otherwise
        """
        theme = self.load_theme(theme_name)

        if theme is None:
            logger.error(f"Cannot set current theme: theme '{theme_name}' not found")
            return False

        self._current_theme = theme
        logger.info(f"Set current theme to '{theme_name}'")
        return True

    def get_next_theme_name(self, current_theme_name: str) -> str:
        """
        Get next theme name for cycling through themes.

        Args:
            current_theme_name: Current theme identifier

        Returns:
            Next theme identifier in cycle
        """
        available = self.get_available_themes()

        if not available:
            logger.warning("No themes available for cycling")
            return current_theme_name

        try:
            current_index = available.index(current_theme_name)
            next_index = (current_index + 1) % len(available)
            next_theme = available[next_index]
            logger.debug(f"Next theme after '{current_theme_name}': {next_theme}")
            return next_theme
        except ValueError:
            # Current theme not in list, return first
            logger.warning(f"Current theme '{current_theme_name}' not found, returning first theme")
            return available[0]

    def generate_css(self, theme_name: Optional[str] = None) -> str:
        """
        Generate CSS for specified theme.

        Args:
            theme_name: Theme to generate CSS for. If None, uses current theme.

        Returns:
            CSS string with theme variables
        """
        if theme_name:
            theme = self.load_theme(theme_name)
        else:
            theme = self._current_theme

        if theme is None:
            logger.warning("No theme available for CSS generation")
            return ""

        return theme.to_css_variables()

    def generate_full_app_css(self, theme_name: Optional[str] = None) -> str:
        """
        Generate complete application CSS with theme variables.

        This method generates the full CSS needed for dynamic theme application,
        including all component styles with theme variable substitutions.

        CRITICAL FIX: CSS variables MUST be defined BEFORE usage.
        Textual's CSS parser processes top-to-bottom, so variables defined at the
        bottom won't be available when styles reference them at the top.

        Args:
            theme_name: Theme to generate CSS for. If None, uses current theme.

        Returns:
            Complete CSS string with theme-specific styles
        """
        if theme_name:
            theme = self.load_theme(theme_name)
        else:
            theme = self._current_theme

        if theme is None:
            logger.warning("No theme available for CSS generation")
            return ""

        # CRITICAL: Define CSS variables FIRST, then use them in styles
        # This ensures variables are available when styles reference them
        css = f"""
/* Theme: {theme.display_name} */
/* CRITICAL: Variables MUST be defined before usage */

/* Theme Variables - DEFINED FIRST */
$primary: {theme.primary};
$accent: {theme.accent};
$surface: {theme.surface};
$panel: {theme.panel};
$text: {theme.text};
$text-muted: {theme.text_muted};
$warning: {theme.warning};
$error: {theme.error};
$success: {theme.success};
$selection: {theme.selection};
$selection-text: {theme.selection_text};

/* Component Styles - Using variables defined above */
ModernCommanderApp {{
    background: $surface;
}}

ModernCommanderApp Header {{
    background: $primary;
    color: $text;
    height: 1;
    dock: top;
}}

ModernCommanderApp Footer {{
    background: $panel;
    color: $text;
    height: 1;
    dock: bottom;
}}

.panel-container {{
    height: 1fr;
    width: 1fr;
}}

.panels-horizontal {{
    height: 1fr;
    layout: horizontal;
}}

.left-panel-container {{
    width: 50%;
    height: 1fr;
}}

.right-panel-container {{
    width: 50%;
    height: 1fr;
}}

.active-panel {{
    border: heavy $primary;
}}

.inactive-panel {{
    border: solid $accent;
}}

CommandBar {{
    dock: bottom;
    height: 1;
}}

QuickViewWidget {{
    display: none;
    height: 50%;
}}

QuickViewWidget.visible {{
    display: block;
}}
"""
        return css

    def create_default_themes(self) -> None:
        """
        Create default theme files if they don't exist.
        Useful for initial setup.
        """
        # Norton Commander theme
        norton = Theme(
            name="norton_commander",
            display_name="Norton Commander",
            primary="#0000AA",
            accent="#00FFFF",
            surface="#000055",
            panel="#0000AA",
            text="#FFFF77",
            text_muted="#8888AA",
            warning="#FFFF00",
            error="#FF5555",
            success="#55FF55",
            selection="#FFFF00",
            selection_text="#000000",
            metadata=ThemeMetadata(
                theme_id="norton_commander",
                display_name="Norton Commander",
                theme_type=ThemeType.BUILT_IN,
                description="Classic Norton Commander color scheme",
                author="DC Commander",
                is_editable=False
            )
        )

        # Modern Dark theme
        modern_dark = Theme(
            name="modern_dark",
            display_name="Modern Dark",
            primary="#1E90FF",
            accent="#00CED1",
            surface="#1A1A1A",
            panel="#2A2A2A",
            text="#E0E0E0",
            text_muted="#888888",
            warning="#FFA500",
            error="#FF4444",
            success="#44FF44",
            selection="#1E90FF",
            selection_text="#FFFFFF",
            metadata=ThemeMetadata(
                theme_id="modern_dark",
                display_name="Modern Dark",
                theme_type=ThemeType.BUILT_IN,
                description="Modern dark theme with blue accents",
                author="DC Commander",
                is_editable=False
            )
        )

        # Solarized Dark theme
        solarized = Theme(
            name="solarized",
            display_name="Solarized Dark",
            primary="#268BD2",
            accent="#2AA198",
            surface="#002B36",
            panel="#073642",
            text="#839496",
            text_muted="#586E75",
            warning="#B58900",
            error="#DC322F",
            success="#859900",
            selection="#268BD2",
            selection_text="#FDF6E3",
            metadata=ThemeMetadata(
                theme_id="solarized",
                display_name="Solarized Dark",
                theme_type=ThemeType.BUILT_IN,
                description="Solarized Dark color scheme",
                author="Ethan Schoonover",
                is_editable=False
            )
        )

        # Midnight Blue theme
        midnight_blue = Theme(
            name="midnight_blue",
            display_name="Midnight Blue",
            primary="#4169E1",
            accent="#6495ED",
            surface="#191970",
            panel="#000080",
            text="#F0F8FF",
            text_muted="#B0C4DE",
            warning="#FFD700",
            error="#FF6347",
            success="#98FB98",
            selection="#4169E1",
            selection_text="#FFFFFF",
            metadata=ThemeMetadata(
                theme_id="midnight_blue",
                display_name="Midnight Blue",
                theme_type=ThemeType.BUILT_IN,
                description="Deep blue theme with royal blue accents",
                author="DC Commander",
                is_editable=False
            )
        )

        # Save themes if they don't exist
        for theme in [norton, modern_dark, solarized, midnight_blue]:
            theme_file = self.themes_dir / f"{theme.name}.json"
            if not theme_file.exists():
                self.save_theme(theme)
                logger.info(f"Created default theme: {theme.name}")

    def _is_valid_theme_id(self, theme_id: str) -> bool:
        """
        Validate theme identifier for security.

        Prevents directory traversal attacks and ensures valid filename.

        Args:
            theme_id: Theme identifier to validate

        Returns:
            True if valid and safe, False otherwise
        """
        if not theme_id:
            return False

        # Prevent directory traversal
        if '..' in theme_id or '/' in theme_id or '\\' in theme_id:
            return False

        # Must be alphanumeric with underscores only
        if not all(c.isalnum() or c == '_' for c in theme_id):
            return False

        return True

    def _is_safe_path(self, path: Path) -> bool:
        """
        Validate that path is safe and within themes directory.

        Prevents directory traversal attacks.

        Args:
            path: Path to validate

        Returns:
            True if path is safe, False otherwise
        """
        try:
            # Resolve to absolute path
            resolved = path.resolve()
            themes_resolved = self.themes_dir.resolve()

            # Check if path is within themes directory
            return resolved.parent == themes_resolved

        except (OSError, RuntimeError):
            return False


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager(themes_dir: Optional[Path] = None) -> ThemeManager:
    """
    Get global theme manager instance.

    Args:
        themes_dir: Optional custom themes directory

    Returns:
        ThemeManager instance
    """
    global _theme_manager

    if _theme_manager is None or themes_dir is not None:
        _theme_manager = ThemeManager(themes_dir)

    return _theme_manager
