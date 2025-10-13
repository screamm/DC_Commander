"""
Centralized Error Handling for DC Commander

Provides consistent error handling, logging, and user notification
throughout the application with context preservation and recovery strategies.
"""

import logging
import traceback
from typing import Optional, Callable, Any, Dict, TypeVar, cast
from functools import wraps
from pathlib import Path
from enum import Enum

from src.core.exceptions import (
    DCCommanderError,
    FileOperationError,
    PermissionDeniedError,
    PathNotFoundError,
    DirectoryNotEmptyError,
    DiskSpaceError,
    AsyncOperationCancelledError,
    ThemeLoadError,
    ConfigurationError,
    PluginError,
    SecurityError,
    UnsafePathError,
    ValidationError,
)


# Configure logging
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization."""
    CRITICAL = "critical"  # Application cannot continue
    ERROR = "error"  # Operation failed but app can continue
    WARNING = "warning"  # Potential issue but operation succeeded
    INFO = "info"  # Informational message


class ErrorRecoveryStrategy(Enum):
    """Recovery strategies for different error types."""
    RETRY = "retry"  # Operation can be retried
    SKIP = "skip"  # Skip failed item and continue
    FALLBACK = "fallback"  # Use fallback/default value
    ABORT = "abort"  # Abort operation completely
    USER_INPUT = "user_input"  # Require user decision


class ErrorContext:
    """
    Error context information for comprehensive error reporting.

    Captures error details, stack trace, and recovery suggestions
    for debugging and user feedback.
    """

    def __init__(
        self,
        exception: Exception,
        operation: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recovery: ErrorRecoveryStrategy = ErrorRecoveryStrategy.ABORT,
        user_message: Optional[str] = None,
        technical_details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize error context.

        Args:
            exception: The caught exception
            operation: Operation that was being performed
            severity: Error severity level
            recovery: Suggested recovery strategy
            user_message: User-friendly error message
            technical_details: Additional technical context
        """
        self.exception = exception
        self.operation = operation
        self.severity = severity
        self.recovery = recovery
        self.user_message = user_message or self._generate_user_message()
        self.technical_details = technical_details or {}
        self.stack_trace = traceback.format_exc()

    def _generate_user_message(self) -> str:
        """
        Generate user-friendly error message.

        Returns:
            Human-readable error description
        """
        if isinstance(self.exception, DCCommanderError):
            return self.exception.message

        # Map common exceptions to user messages
        exception_messages = {
            PermissionError: "Access denied. Check file permissions.",
            FileNotFoundError: "File or directory not found.",
            OSError: "System error occurred during operation.",
            ValueError: "Invalid value provided.",
            TypeError: "Invalid data type.",
        }

        for exc_type, message in exception_messages.items():
            if isinstance(self.exception, exc_type):
                return f"{message} {str(self.exception)}"

        return f"An error occurred: {str(self.exception)}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error context to dictionary.

        Returns:
            Dictionary with error details
        """
        return {
            "operation": self.operation,
            "severity": self.severity.value,
            "recovery": self.recovery.value,
            "user_message": self.user_message,
            "exception_type": type(self.exception).__name__,
            "exception_message": str(self.exception),
            "technical_details": self.technical_details,
            "stack_trace": self.stack_trace
        }


class ErrorHandler:
    """
    Centralized error handling with logging and recovery strategies.

    Provides consistent error processing, logging, and user notification
    throughout DC Commander with support for recovery strategies.
    """

    def __init__(self, logger_name: str = "dc_commander"):
        """
        Initialize error handler.

        Args:
            logger_name: Logger name for error messages
        """
        self.logger = logging.getLogger(logger_name)
        self._error_callbacks: list[Callable[[ErrorContext], None]] = []

    def register_error_callback(self, callback: Callable[[ErrorContext], None]) -> None:
        """
        Register callback for error notifications.

        Callbacks can be used to show user notifications, update UI,
        or perform custom error handling.

        Args:
            callback: Function to call with ErrorContext on errors
        """
        self._error_callbacks.append(callback)

    def handle_error(
        self,
        exception: Exception,
        operation: Optional[str] = None,
        severity: Optional[ErrorSeverity] = None,
        recovery: Optional[ErrorRecoveryStrategy] = None,
        user_message: Optional[str] = None,
        log_exception: bool = True,
        notify_user: bool = True
    ) -> ErrorContext:
        """
        Handle exception with logging and notification.

        Args:
            exception: Exception to handle
            operation: Operation that was being performed
            severity: Error severity (auto-detected if None)
            recovery: Recovery strategy (auto-detected if None)
            user_message: Custom user message
            log_exception: Whether to log the exception
            notify_user: Whether to notify user via callbacks

        Returns:
            ErrorContext with error details
        """
        # Auto-detect severity and recovery if not provided
        if severity is None:
            severity = self._detect_severity(exception)
        if recovery is None:
            recovery = self._suggest_recovery(exception)

        # Create error context
        context = ErrorContext(
            exception=exception,
            operation=operation,
            severity=severity,
            recovery=recovery,
            user_message=user_message
        )

        # Log error
        if log_exception:
            self._log_error(context)

        # Notify callbacks
        if notify_user:
            for callback in self._error_callbacks:
                try:
                    callback(context)
                except Exception as cb_error:
                    self.logger.error(f"Error in error callback: {cb_error}")

        return context

    def _detect_severity(self, exception: Exception) -> ErrorSeverity:
        """
        Auto-detect error severity based on exception type.

        Args:
            exception: Exception to analyze

        Returns:
            Appropriate severity level
        """
        # Critical errors that require app restart
        critical_types = (
            SystemError,
            MemoryError,
            KeyboardInterrupt,
        )
        if isinstance(exception, critical_types):
            return ErrorSeverity.CRITICAL

        # Errors that prevent operation but app can continue
        error_types = (
            DCCommanderError,
            PermissionError,
            FileNotFoundError,
            OSError,
            ValueError,
        )
        if isinstance(exception, error_types):
            return ErrorSeverity.ERROR

        # Warnings for recoverable issues
        warning_types = (
            UserWarning,
            DeprecationWarning,
        )
        if isinstance(exception, warning_types):
            return ErrorSeverity.WARNING

        # Default to error
        return ErrorSeverity.ERROR

    def _suggest_recovery(self, exception: Exception) -> ErrorRecoveryStrategy:
        """
        Suggest recovery strategy based on exception type.

        Args:
            exception: Exception to analyze

        Returns:
            Suggested recovery strategy
        """
        # Cancellations should skip gracefully
        if isinstance(exception, AsyncOperationCancelledError):
            return ErrorRecoveryStrategy.SKIP

        # Permission errors may need user intervention
        if isinstance(exception, (PermissionDeniedError, PermissionError)):
            return ErrorRecoveryStrategy.USER_INPUT

        # Not found errors can often be skipped
        if isinstance(exception, (PathNotFoundError, FileNotFoundError)):
            return ErrorRecoveryStrategy.SKIP

        # Configuration errors should use fallback
        if isinstance(exception, (ConfigurationError, ThemeLoadError)):
            return ErrorRecoveryStrategy.FALLBACK

        # Validation errors need user correction
        if isinstance(exception, (ValidationError, ValueError)):
            return ErrorRecoveryStrategy.USER_INPUT

        # Default to abort for safety
        return ErrorRecoveryStrategy.ABORT

    def _log_error(self, context: ErrorContext) -> None:
        """
        Log error with appropriate level and context.

        Args:
            context: Error context to log
        """
        log_message = f"{context.operation}: {context.user_message}" if context.operation else context.user_message

        # Add technical details if available
        if context.technical_details:
            details_str = ", ".join(f"{k}={v}" for k, v in context.technical_details.items())
            log_message += f" ({details_str})"

        # Log with appropriate level
        if context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=context.exception)
        elif context.severity == ErrorSeverity.ERROR:
            self.logger.error(log_message, exc_info=context.exception)
        elif context.severity == ErrorSeverity.WARNING:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """
    Get global error handler instance.

    Returns:
        ErrorHandler singleton instance
    """
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


# Type variable for decorator
F = TypeVar('F', bound=Callable[..., Any])


def handle_exceptions(
    operation: Optional[str] = None,
    severity: Optional[ErrorSeverity] = None,
    recovery: Optional[ErrorRecoveryStrategy] = None,
    user_message: Optional[str] = None,
    reraise: bool = False,
    default_return: Any = None
) -> Callable[[F], F]:
    """
    Decorator for automatic exception handling.

    Usage:
        @handle_exceptions(operation="file_copy", reraise=False)
        def copy_file(src, dst):
            # ... implementation

    Args:
        operation: Operation description for logging
        severity: Error severity override
        recovery: Recovery strategy override
        user_message: Custom user message
        reraise: Whether to re-raise exception after handling
        default_return: Value to return if exception occurs (when not reraising)

    Returns:
        Decorated function with error handling
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = get_error_handler()
                handler.handle_error(
                    exception=e,
                    operation=operation or func.__name__,
                    severity=severity,
                    recovery=recovery,
                    user_message=user_message
                )

                if reraise:
                    raise

                return default_return

        return cast(F, wrapper)
    return decorator


def safe_execute(
    func: Callable[..., Any],
    *args: Any,
    operation: Optional[str] = None,
    default_return: Any = None,
    **kwargs: Any
) -> tuple[bool, Any, Optional[ErrorContext]]:
    """
    Execute function with comprehensive error handling.

    Args:
        func: Function to execute
        *args: Function arguments
        operation: Operation description
        default_return: Default return value on error
        **kwargs: Function keyword arguments

    Returns:
        Tuple of (success, result, error_context)
    """
    try:
        result = func(*args, **kwargs)
        return (True, result, None)
    except Exception as e:
        handler = get_error_handler()
        context = handler.handle_error(
            exception=e,
            operation=operation or func.__name__
        )
        return (False, default_return, context)


def format_file_error(
    exception: Exception,
    path: Optional[Path] = None,
    operation: Optional[str] = None
) -> str:
    """
    Format file operation error for user display.

    Args:
        exception: Exception that occurred
        path: File path involved
        operation: Operation being performed

    Returns:
        Formatted error message
    """
    base_msg = ""

    if isinstance(exception, PermissionDeniedError):
        base_msg = "Permission denied"
    elif isinstance(exception, PathNotFoundError):
        base_msg = "File not found"
    elif isinstance(exception, DirectoryNotEmptyError):
        base_msg = "Directory is not empty"
    elif isinstance(exception, DiskSpaceError):
        base_msg = "Insufficient disk space"
    elif isinstance(exception, FileOperationError):
        base_msg = "File operation failed"
    else:
        base_msg = "Error"

    if operation:
        base_msg = f"{operation.capitalize()} failed: {base_msg}"

    if path:
        base_msg += f"\nPath: {path}"

    if hasattr(exception, 'message'):
        base_msg += f"\nDetails: {exception.message}"
    elif str(exception):
        base_msg += f"\nDetails: {str(exception)}"

    return base_msg


def log_exception(
    logger_obj: logging.Logger,
    exception: Exception,
    operation: Optional[str] = None,
    **context: Any
) -> None:
    """
    Log exception with context information.

    Args:
        logger_obj: Logger to use
        exception: Exception to log
        operation: Operation description
        **context: Additional context key-value pairs
    """
    message = f"{operation}: {str(exception)}" if operation else str(exception)

    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        message += f" ({context_str})"

    if isinstance(exception, DCCommanderError):
        logger_obj.error(message, extra=exception.to_dict())
    else:
        logger_obj.error(message, exc_info=exception)
