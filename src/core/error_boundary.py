"""
Error Boundary System for DC Commander

Provides application-level error handling with recovery options.
Prevents crashes and provides user-friendly error recovery dialogs.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Callable, Any
from collections import deque


logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Available recovery actions."""
    RETRY = "retry"
    SKIP = "skip"
    SKIP_ALL = "skip_all"
    ABORT = "abort"
    VIEW_DETAILS = "view_details"
    IGNORE = "ignore"


@dataclass
class ErrorContext:
    """Context information for an error."""
    error: Exception
    operation: str
    context: str
    timestamp: datetime = field(default_factory=datetime.now)
    severity: ErrorSeverity = ErrorSeverity.ERROR
    recoverable: bool = True
    details: Optional[dict] = None
    stack_trace: Optional[str] = None


class ErrorHistory:
    """Maintains history of errors for analysis and debugging."""

    def __init__(self, max_size: int = 100):
        """Initialize error history.

        Args:
            max_size: Maximum number of errors to keep
        """
        self.errors: deque[ErrorContext] = deque(maxlen=max_size)
        self.error_counts: dict[str, int] = {}

    def add_error(self, error_context: ErrorContext) -> None:
        """Add error to history.

        Args:
            error_context: Error context to add
        """
        self.errors.append(error_context)

        # Track error type counts
        error_type = type(error_context.error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        logger.error(
            f"Error recorded: {error_context.operation} - "
            f"{error_type}: {str(error_context.error)}"
        )

    def get_recent_errors(self, count: int = 10) -> List[ErrorContext]:
        """Get most recent errors.

        Args:
            count: Number of errors to retrieve

        Returns:
            List of recent error contexts
        """
        return list(self.errors)[-count:]

    def get_error_summary(self) -> dict:
        """Get summary of error history.

        Returns:
            Dictionary with error statistics
        """
        return {
            'total_errors': len(self.errors),
            'error_types': dict(self.error_counts),
            'recent_errors': len([e for e in self.errors
                                 if (datetime.now() - e.timestamp).seconds < 300])
        }

    def clear(self) -> None:
        """Clear error history."""
        self.errors.clear()
        self.error_counts.clear()


class ErrorBoundary:
    """Application-level error boundary with recovery capabilities."""

    def __init__(self):
        """Initialize error boundary."""
        self.history = ErrorHistory()
        self.error_handlers: dict[type, Callable] = {}
        self.global_handler: Optional[Callable] = None
        self._suppress_all = False

    def register_handler(
        self,
        error_type: type[Exception],
        handler: Callable[[ErrorContext], RecoveryAction]
    ) -> None:
        """Register custom error handler for specific error type.

        Args:
            error_type: Exception type to handle
            handler: Handler function that returns recovery action
        """
        self.error_handlers[error_type] = handler
        logger.info(f"Registered handler for {error_type.__name__}")

    def set_global_handler(
        self,
        handler: Callable[[ErrorContext], RecoveryAction]
    ) -> None:
        """Set global error handler for unhandled errors.

        Args:
            handler: Global handler function
        """
        self.global_handler = handler
        logger.info("Global error handler registered")

    async def handle_error(
        self,
        error: Exception,
        operation: str,
        context: str = "",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recoverable: bool = True,
        details: Optional[dict] = None
    ) -> RecoveryAction:
        """Handle error with recovery options.

        Args:
            error: Exception that occurred
            operation: Operation being performed
            context: Additional context information
            severity: Error severity level
            recoverable: Whether error is recoverable
            details: Additional details dictionary

        Returns:
            Recovery action chosen by handler
        """
        # Create error context
        import traceback
        error_context = ErrorContext(
            error=error,
            operation=operation,
            context=context,
            severity=severity,
            recoverable=recoverable,
            details=details or {},
            stack_trace=traceback.format_exc()
        )

        # Add to history
        self.history.add_error(error_context)

        # If suppressing all errors, return skip
        if self._suppress_all:
            return RecoveryAction.SKIP_ALL

        # Try specific handler first
        error_type = type(error)
        if error_type in self.error_handlers:
            try:
                return await self._call_handler(
                    self.error_handlers[error_type],
                    error_context
                )
            except Exception as handler_error:
                logger.error(f"Error in handler: {handler_error}")

        # Try global handler
        if self.global_handler:
            try:
                return await self._call_handler(
                    self.global_handler,
                    error_context
                )
            except Exception as handler_error:
                logger.error(f"Error in global handler: {handler_error}")

        # Default: abort on critical, skip on recoverable
        if severity == ErrorSeverity.CRITICAL:
            return RecoveryAction.ABORT
        elif recoverable:
            return RecoveryAction.SKIP
        else:
            return RecoveryAction.ABORT

    async def _call_handler(
        self,
        handler: Callable,
        error_context: ErrorContext
    ) -> RecoveryAction:
        """Call error handler (sync or async).

        Args:
            handler: Handler to call
            error_context: Error context

        Returns:
            Recovery action
        """
        import asyncio
        import inspect

        if inspect.iscoroutinefunction(handler):
            return await handler(error_context)
        else:
            return handler(error_context)

    def suppress_all_errors(self, suppress: bool = True) -> None:
        """Suppress all errors (skip all).

        Args:
            suppress: Whether to suppress errors
        """
        self._suppress_all = suppress
        if suppress:
            logger.warning("Error suppression ENABLED - all errors will be skipped")
        else:
            logger.info("Error suppression DISABLED")

    def get_history(self) -> ErrorHistory:
        """Get error history.

        Returns:
            Error history object
        """
        return self.history


class FileOperationError(Exception):
    """Base class for file operation errors."""
    pass


class PermissionDeniedError(FileOperationError):
    """Permission denied during file operation."""
    pass


class FileNotFoundError(FileOperationError):
    """File not found during operation."""
    pass


class DiskFullError(FileOperationError):
    """Disk full error."""
    pass


class PathTooLongError(FileOperationError):
    """Path exceeds maximum length."""
    pass


class InvalidFileNameError(FileOperationError):
    """Invalid filename."""
    pass


# Global error boundary instance
_global_error_boundary: Optional[ErrorBoundary] = None


def get_error_boundary() -> ErrorBoundary:
    """Get global error boundary instance.

    Returns:
        Global error boundary
    """
    global _global_error_boundary
    if _global_error_boundary is None:
        _global_error_boundary = ErrorBoundary()
    return _global_error_boundary


def set_error_boundary(boundary: ErrorBoundary) -> None:
    """Set global error boundary.

    Args:
        boundary: Error boundary to set as global
    """
    global _global_error_boundary
    _global_error_boundary = boundary
