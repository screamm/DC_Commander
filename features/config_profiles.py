"""
Configuration Profiles System

Provides pre-configured profiles for different use cases:
- Performance Mode: Optimized for speed
- Safety Mode: Maximum confirmations and safety
- Power User: All advanced features enabled
- Minimal: Basic features only
- Custom profiles
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from pathlib import Path
from enum import Enum
import json
import logging


logger = logging.getLogger(__name__)


class ProfileType(Enum):
    """Available profile types."""
    PERFORMANCE = "performance"
    SAFETY = "safety"
    POWER_USER = "power_user"
    MINIMAL = "minimal"
    CUSTOM = "custom"


@dataclass
class CacheSettings:
    """Cache configuration settings."""
    enabled: bool = True
    maxsize: int = 100
    ttl_seconds: int = 60
    show_stats: bool = False
    predictive_preload: bool = False


@dataclass
class UISettings:
    """UI configuration settings."""
    theme: str = "norton_commander"
    show_hidden_files: bool = True
    quick_search_enabled: bool = True
    status_bar_enabled: bool = True
    compact_mode: bool = False


@dataclass
class OperationSettings:
    """File operation settings."""
    confirm_delete: bool = True
    confirm_overwrite: bool = True
    use_async_threshold: int = 1048576  # 1MB
    show_progress: bool = True
    enable_undo: bool = True
    max_undo_levels: int = 10


@dataclass
class PerformanceSettings:
    """Performance-related settings."""
    incremental_loading: bool = False
    batch_size: int = 1000
    background_refresh: bool = False
    refresh_interval: int = 60
    memory_optimization: bool = False


@dataclass
class SafetySettings:
    """Safety and validation settings."""
    validate_paths: bool = True
    sandbox_mode: bool = False
    audit_logging: bool = False
    backup_before_delete: bool = False
    max_path_length_check: bool = True


@dataclass
class DebugSettings:
    """Debug and logging settings."""
    debug_mode: bool = False
    log_level: str = "INFO"
    performance_tracking: bool = False
    show_debug_overlay: bool = False


@dataclass
class ConfigProfile:
    """Complete configuration profile."""
    name: str
    profile_type: ProfileType
    cache: CacheSettings
    ui: UISettings
    operations: OperationSettings
    performance: PerformanceSettings
    safety: SafetySettings
    debug: DebugSettings
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary.

        Returns:
            Profile dictionary
        """
        return {
            'name': self.name,
            'profile_type': self.profile_type.value,
            'cache': asdict(self.cache),
            'ui': asdict(self.ui),
            'operations': asdict(self.operations),
            'performance': asdict(self.performance),
            'safety': asdict(self.safety),
            'debug': asdict(self.debug),
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigProfile':
        """Create profile from dictionary.

        Args:
            data: Profile dictionary

        Returns:
            ConfigProfile instance
        """
        return cls(
            name=data['name'],
            profile_type=ProfileType(data['profile_type']),
            cache=CacheSettings(**data['cache']),
            ui=UISettings(**data['ui']),
            operations=OperationSettings(**data['operations']),
            performance=PerformanceSettings(**data['performance']),
            safety=SafetySettings(**data['safety']),
            debug=DebugSettings(**data['debug']),
            description=data.get('description', '')
        )


class ProfileManager:
    """Manage configuration profiles."""

    # Pre-defined profiles
    BUILTIN_PROFILES: Dict[ProfileType, ConfigProfile] = {
        ProfileType.PERFORMANCE: ConfigProfile(
            name="Performance Mode",
            profile_type=ProfileType.PERFORMANCE,
            cache=CacheSettings(
                enabled=True,
                maxsize=200,
                ttl_seconds=120,
                show_stats=False,
                predictive_preload=True
            ),
            ui=UISettings(
                theme="modern_dark",
                show_hidden_files=False,
                quick_search_enabled=True,
                status_bar_enabled=True,
                compact_mode=True
            ),
            operations=OperationSettings(
                confirm_delete=False,
                confirm_overwrite=False,
                use_async_threshold=524288,  # 512KB
                show_progress=False,
                enable_undo=False,
                max_undo_levels=0
            ),
            performance=PerformanceSettings(
                incremental_loading=True,
                batch_size=2000,
                background_refresh=True,
                refresh_interval=30,
                memory_optimization=True
            ),
            safety=SafetySettings(
                validate_paths=True,
                sandbox_mode=False,
                audit_logging=False,
                backup_before_delete=False,
                max_path_length_check=False
            ),
            debug=DebugSettings(
                debug_mode=False,
                log_level="WARNING",
                performance_tracking=True,
                show_debug_overlay=False
            ),
            description="Optimized for maximum speed with minimal confirmations"
        ),

        ProfileType.SAFETY: ConfigProfile(
            name="Safety Mode",
            profile_type=ProfileType.SAFETY,
            cache=CacheSettings(
                enabled=True,
                maxsize=50,
                ttl_seconds=30,
                show_stats=True,
                predictive_preload=False
            ),
            ui=UISettings(
                theme="norton_commander",
                show_hidden_files=True,
                quick_search_enabled=True,
                status_bar_enabled=True,
                compact_mode=False
            ),
            operations=OperationSettings(
                confirm_delete=True,
                confirm_overwrite=True,
                use_async_threshold=2097152,  # 2MB
                show_progress=True,
                enable_undo=True,
                max_undo_levels=20
            ),
            performance=PerformanceSettings(
                incremental_loading=False,
                batch_size=500,
                background_refresh=False,
                refresh_interval=120,
                memory_optimization=False
            ),
            safety=SafetySettings(
                validate_paths=True,
                sandbox_mode=True,
                audit_logging=True,
                backup_before_delete=True,
                max_path_length_check=True
            ),
            debug=DebugSettings(
                debug_mode=False,
                log_level="INFO",
                performance_tracking=False,
                show_debug_overlay=False
            ),
            description="Maximum safety with confirmations for all operations"
        ),

        ProfileType.POWER_USER: ConfigProfile(
            name="Power User",
            profile_type=ProfileType.POWER_USER,
            cache=CacheSettings(
                enabled=True,
                maxsize=150,
                ttl_seconds=90,
                show_stats=True,
                predictive_preload=True
            ),
            ui=UISettings(
                theme="midnight_blue",
                show_hidden_files=True,
                quick_search_enabled=True,
                status_bar_enabled=True,
                compact_mode=False
            ),
            operations=OperationSettings(
                confirm_delete=True,
                confirm_overwrite=True,
                use_async_threshold=1048576,  # 1MB
                show_progress=True,
                enable_undo=True,
                max_undo_levels=15
            ),
            performance=PerformanceSettings(
                incremental_loading=True,
                batch_size=1500,
                background_refresh=True,
                refresh_interval=45,
                memory_optimization=True
            ),
            safety=SafetySettings(
                validate_paths=True,
                sandbox_mode=False,
                audit_logging=True,
                backup_before_delete=False,
                max_path_length_check=True
            ),
            debug=DebugSettings(
                debug_mode=True,
                log_level="DEBUG",
                performance_tracking=True,
                show_debug_overlay=True
            ),
            description="All features enabled for advanced users"
        ),

        ProfileType.MINIMAL: ConfigProfile(
            name="Minimal",
            profile_type=ProfileType.MINIMAL,
            cache=CacheSettings(
                enabled=False,
                maxsize=0,
                ttl_seconds=0,
                show_stats=False,
                predictive_preload=False
            ),
            ui=UISettings(
                theme="norton_commander",
                show_hidden_files=False,
                quick_search_enabled=False,
                status_bar_enabled=False,
                compact_mode=True
            ),
            operations=OperationSettings(
                confirm_delete=True,
                confirm_overwrite=True,
                use_async_threshold=10485760,  # 10MB
                show_progress=False,
                enable_undo=False,
                max_undo_levels=0
            ),
            performance=PerformanceSettings(
                incremental_loading=False,
                batch_size=500,
                background_refresh=False,
                refresh_interval=0,
                memory_optimization=True
            ),
            safety=SafetySettings(
                validate_paths=True,
                sandbox_mode=False,
                audit_logging=False,
                backup_before_delete=False,
                max_path_length_check=True
            ),
            debug=DebugSettings(
                debug_mode=False,
                log_level="ERROR",
                performance_tracking=False,
                show_debug_overlay=False
            ),
            description="Basic features only for minimal resource usage"
        )
    }

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize profile manager.

        Args:
            config_dir: Directory for profile storage
        """
        if config_dir is None:
            config_dir = Path.home() / '.dc-commander' / 'profiles'

        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.custom_profiles: Dict[str, ConfigProfile] = {}
        self._load_custom_profiles()

    def get_profile(self, profile_type: ProfileType) -> ConfigProfile:
        """Get profile by type.

        Args:
            profile_type: Profile type to get

        Returns:
            Configuration profile
        """
        if profile_type in self.BUILTIN_PROFILES:
            return self.BUILTIN_PROFILES[profile_type]

        raise ValueError(f"Unknown profile type: {profile_type}")

    def get_custom_profile(self, name: str) -> Optional[ConfigProfile]:
        """Get custom profile by name.

        Args:
            name: Profile name

        Returns:
            Configuration profile or None
        """
        return self.custom_profiles.get(name)

    def save_custom_profile(self, profile: ConfigProfile) -> None:
        """Save custom profile.

        Args:
            profile: Profile to save
        """
        profile_path = self.config_dir / f"{profile.name}.json"

        try:
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2)

            self.custom_profiles[profile.name] = profile
            logger.info(f"Saved custom profile: {profile.name}")

        except Exception as e:
            logger.error(f"Failed to save profile {profile.name}: {e}")
            raise

    def delete_custom_profile(self, name: str) -> bool:
        """Delete custom profile.

        Args:
            name: Profile name

        Returns:
            True if deleted successfully
        """
        profile_path = self.config_dir / f"{name}.json"

        try:
            if profile_path.exists():
                profile_path.unlink()

            if name in self.custom_profiles:
                del self.custom_profiles[name]

            logger.info(f"Deleted custom profile: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete profile {name}: {e}")
            return False

    def list_profiles(self) -> Dict[str, ConfigProfile]:
        """List all available profiles.

        Returns:
            Dictionary of profile name to profile
        """
        profiles = {}

        # Add built-in profiles
        for profile_type, profile in self.BUILTIN_PROFILES.items():
            profiles[profile.name] = profile

        # Add custom profiles
        profiles.update(self.custom_profiles)

        return profiles

    def _load_custom_profiles(self) -> None:
        """Load custom profiles from disk."""
        if not self.config_dir.exists():
            return

        for profile_file in self.config_dir.glob("*.json"):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                profile = ConfigProfile.from_dict(data)
                self.custom_profiles[profile.name] = profile

                logger.info(f"Loaded custom profile: {profile.name}")

            except Exception as e:
                logger.error(f"Failed to load profile {profile_file}: {e}")


# Global profile manager
_profile_manager: Optional[ProfileManager] = None


def get_profile_manager() -> ProfileManager:
    """Get global profile manager.

    Returns:
        Profile manager instance
    """
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager
