"""
Custom Exception Hierarchy for DC Commander

Provides specific exception types for different error scenarios
throughout the application with clear categorization and context.
"""

from typing import Optional, Any, Dict
from pathlib import Path


class DCCommanderError(Exception):
    """
    Base exception for all DC Commander errors.

    All custom exceptions in DC Commander should inherit from this class
    to enable consistent error handling and categorization.

    Attributes:
        message: Human-readable error message
        context: Additional context information for debugging
        code: Optional error code for programmatic handling
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None
    ):
        """
        Initialize DC Commander error.

        Args:
            message: Human-readable error description
            context: Optional dictionary with additional error context
            code: Optional error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.code = code

    def __str__(self) -> str:
        """Format error message with optional context."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging/serialization.

        Returns:
            Dictionary with error details
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "code": self.code
        }


# ============================================================================
# File Operation Errors
# ============================================================================

class FileOperationError(DCCommanderError):
    """
    Base exception for file operation failures.

    Used when file/directory operations fail due to various reasons
    including permissions, missing files, or I/O errors.
    """

    def __init__(
        self,
        message: str,
        path: Optional[Path] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize file operation error.

        Args:
            message: Error description
            path: Path where operation failed
            operation: Type of operation (copy, move, delete, etc.)
            **kwargs: Additional context
        """
        context = kwargs.get('context', {})
        if path:
            context['path'] = str(path)
        if operation:
            context['operation'] = operation
        kwargs['context'] = context
        super().__init__(message, **kwargs)
        self.path = path
        self.operation = operation


class PermissionDeniedError(FileOperationError):
    """
    Exception raised when file operation is denied due to permissions.

    This indicates the application doesn't have sufficient permissions
    to perform the requested operation on the file or directory.
    """

    def __init__(self, message: str, path: Optional[Path] = None, **kwargs):
        """
        Initialize permission denied error.

        Args:
            message: Error description
            path: Path where permission was denied
            **kwargs: Additional context
        """
        super().__init__(
            message,
            path=path,
            code="PERMISSION_DENIED",
            **kwargs
        )


class PathNotFoundError(FileOperationError):
    """
    Exception raised when specified file or directory doesn't exist.

    Use this instead of generic FileNotFoundError for DC Commander specific
    path resolution failures.
    """

    def __init__(self, message: str, path: Optional[Path] = None, **kwargs):
        """
        Initialize path not found error.

        Args:
            message: Error description
            path: Path that wasn't found
            **kwargs: Additional context
        """
        super().__init__(
            message,
            path=path,
            code="PATH_NOT_FOUND",
            **kwargs
        )


class DirectoryNotEmptyError(FileOperationError):
    """
    Exception raised when attempting to delete non-empty directory.

    Used when directory deletion fails because directory contains files
    or subdirectories and recursive deletion wasn't specified.
    """

    def __init__(self, message: str, path: Optional[Path] = None, **kwargs):
        """
        Initialize directory not empty error.

        Args:
            message: Error description
            path: Directory path
            **kwargs: Additional context
        """
        super().__init__(
            message,
            path=path,
            operation="delete",
            code="DIRECTORY_NOT_EMPTY",
            **kwargs
        )


class DiskSpaceError(FileOperationError):
    """
    Exception raised when insufficient disk space for operation.

    Used when file operations fail due to lack of available disk space
    on the target filesystem.
    """

    def __init__(
        self,
        message: str,
        path: Optional[Path] = None,
        required_bytes: Optional[int] = None,
        available_bytes: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize disk space error.

        Args:
            message: Error description
            path: Target path
            required_bytes: Bytes required for operation
            available_bytes: Bytes currently available
            **kwargs: Additional context
        """
        context = kwargs.get('context', {})
        if required_bytes:
            context['required_bytes'] = required_bytes
        if available_bytes:
            context['available_bytes'] = available_bytes
        kwargs['context'] = context

        super().__init__(
            message,
            path=path,
            code="DISK_SPACE_ERROR",
            **kwargs
        )


class FileAlreadyExistsError(FileOperationError):
    """
    Exception raised when target file already exists.

    Used when file operations fail because destination already exists
    and overwrite wasn't specified.
    """

    def __init__(self, message: str, path: Optional[Path] = None, **kwargs):
        """
        Initialize file already exists error.

        Args:
            message: Error description
            path: Existing file path
            **kwargs: Additional context
        """
        super().__init__(
            message,
            path=path,
            code="FILE_ALREADY_EXISTS",
            **kwargs
        )


# ============================================================================
# Async Operation Errors
# ============================================================================

class AsyncOperationError(DCCommanderError):
    """
    Base exception for async operation failures.

    Used for errors during async file operations, background tasks,
    and concurrent processing.
    """
    pass


class AsyncOperationCancelledError(AsyncOperationError):
    """
    Exception raised when async operation is cancelled.

    Indicates user-initiated cancellation or timeout of async operation.
    Not an error condition but signals early termination.
    """

    def __init__(
        self,
        message: str = "Operation cancelled by user",
        operation: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize async operation cancelled error.

        Args:
            message: Error description
            operation: Type of operation cancelled
            **kwargs: Additional context
        """
        context = kwargs.get('context', {})
        if operation:
            context['operation'] = operation
        kwargs['context'] = context

        super().__init__(
            message,
            code="OPERATION_CANCELLED",
            **kwargs
        )


class AsyncTimeoutError(AsyncOperationError):
    """
    Exception raised when async operation times out.

    Used when async operations exceed configured timeout limits.
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        """
        Initialize async timeout error.

        Args:
            message: Error description
            timeout_seconds: Timeout threshold that was exceeded
            **kwargs: Additional context
        """
        context = kwargs.get('context', {})
        if timeout_seconds:
            context['timeout_seconds'] = timeout_seconds
        kwargs['context'] = context

        super().__init__(
            message,
            code="ASYNC_TIMEOUT",
            **kwargs
        )


# ============================================================================
# Theme and UI Errors
# ============================================================================

class ThemeError(DCCommanderError):
    """
    Base exception for theme-related errors.

    Used for theme loading, validation, and application failures.
    """
    pass


class ThemeLoadError(ThemeError):
    """
    Exception raised when theme fails to load.

    Indicates theme file is missing, corrupted, or contains invalid data.
    """

    def __init__(
        self,
        message: str,
        theme_id: Optional[str] = None,
        theme_path: Optional[Path] = None,
        **kwargs
    ):
        """
        Initialize theme load error.

        Args:
            message: Error description
            theme_id: Theme identifier that failed to load
            theme_path: Path to theme file
            **kwargs: Additional context
        """
        context = kwargs.get('context', {})
        if theme_id:
            context['theme_id'] = theme_id
        if theme_path:
            context['theme_path'] = str(theme_path)
        kwargs['context'] = context

        super().__init__(
            message,
            code="THEME_LOAD_ERROR",
            **kwargs
        )


class ThemeValidationError(ThemeError):
    """
    Exception raised when theme validation fails.

    Used when theme has missing required fields, invalid color formats,
    or other validation failures.
    """

    def __init__(
        self,
        message: str,
        validation_errors: Optional[list] = None,
        **kwargs
    ):
        """
        Initialize theme validation error.

        Args:
            message: Error description
            validation_errors: List of specific validation failures
            **kwargs: Additional context
        """
        context = kwargs.get('context', {})
        if validation_errors:
            context['validation_errors'] = validation_errors
        kwargs['context'] = context

        super().__init__(
            message,
            code="THEME_VALIDATION_ERROR",
            **kwargs
        )


# ============================================================================
# Configuration Errors
# ============================================================================

class ConfigurationError(DCCommanderError):
    """
    Exception raised for configuration-related errors.

    Used when configuration loading, validation, or saving fails.
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[Path] = None,
        **kwargs
    ):
        """
        Initialize configuration error.

        Args:
            message: Error description
            config_key: Configuration key that caused error
            config_file: Path to configuration file
            **kwargs: Additional context
        """
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        if config_file:
            context['config_file'] = str(config_file)
        kwargs['context'] = context

        super().__init__(
            message,
            code="CONFIGURATION_ERROR",
            **kwargs
        )


class ConfigValidationError(ConfigurationError):
    """
    Exception raised when configuration validation fails.

    Indicates configuration contains invalid values or missing required fields.
    """

    def __init__(
        self,
        message: str,
        validation_errors: Optional[list] = None,
        **kwargs
    ):
        """
        Initialize config validation error.

        Args:
            message: Error description
            validation_errors: List of specific validation failures
            **kwargs: Additional context
        """
        context = kwargs.get('context', {})
        if validation_errors:
            context['validation_errors'] = validation_errors
        kwargs['context'] = context

        super().__init__(
            message,
            code="CONFIG_VALIDATION_ERROR",
            **kwargs
        )


# ============================================================================
# Plugin and Extension Errors
# ============================================================================

class PluginError(DCCommanderError):
    """
    Exception raised for plugin system errors.

    Used when plugin loading, initialization, or execution fails.
    """

    def __init__(
        self,
        message: str,
        plugin_name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize plugin error.

        Args:
            message: Error description
            plugin_name: Name of plugin that caused error
            **kwargs: Additional context
        """
        context = kwargs.get('context', {})
        if plugin_name:
            context['plugin_name'] = plugin_name
        kwargs['context'] = context

        super().__init__(
            message,
            code="PLUGIN_ERROR",
            **kwargs
        )


class PluginLoadError(PluginError):
    """
    Exception raised when plugin fails to load.

    Indicates plugin file is missing, has syntax errors, or failed initialization.
    """

    def __init__(self, message: str, plugin_name: Optional[str] = None, **kwargs):
        """
        Initialize plugin load error.

        Args:
            message: Error description
            plugin_name: Name of plugin that failed to load
            **kwargs: Additional context
        """
        super().__init__(
            message,
            plugin_name=plugin_name,
            code="PLUGIN_LOAD_ERROR",
            **kwargs
        )


# ============================================================================
# Security Errors
# ============================================================================

class SecurityError(DCCommanderError):
    """
    Exception raised for security-related errors.

    Used when security validation fails or unsafe operations are attempted.
    """

    def __init__(self, message: str, **kwargs):
        """
        Initialize security error.

        Args:
            message: Error description
            **kwargs: Additional context
        """
        super().__init__(
            message,
            code="SECURITY_ERROR",
            **kwargs
        )


class UnsafePathError(SecurityError):
    """
    Exception raised when path validation fails.

    Indicates path contains unsafe characters, attempts directory traversal,
    or violates security constraints.
    """

    def __init__(
        self,
        message: str,
        path: Optional[Path] = None,
        **kwargs
    ):
        """
        Initialize unsafe path error.

        Args:
            message: Error description
            path: Unsafe path
            **kwargs: Additional context
        """
        context = kwargs.get('context', {})
        if path:
            context['path'] = str(path)
        kwargs['context'] = context

        super().__init__(
            message,
            code="UNSAFE_PATH",
            **kwargs
        )


# ============================================================================
# Data Validation Errors
# ============================================================================

class ValidationError(DCCommanderError):
    """
    Exception raised for general data validation failures.

    Used when input data doesn't meet validation requirements.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize validation error.

        Args:
            message: Error description
            field: Field name that failed validation
            value: Invalid value
            **kwargs: Additional context
        """
        context = kwargs.get('context', {})
        if field:
            context['field'] = field
        if value is not None:
            context['value'] = str(value)
        kwargs['context'] = context

        super().__init__(
            message,
            code="VALIDATION_ERROR",
            **kwargs
        )
