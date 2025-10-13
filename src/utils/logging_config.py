"""
Logging Configuration for DC Commander

Provides centralized logging setup with file rotation, formatting,
and severity levels for debugging and monitoring.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from datetime import datetime


class DCCommanderFormatter(logging.Formatter):
    """
    Custom log formatter with color support and structured output.

    Provides consistent log formatting with timestamps, levels,
    and contextual information.
    """

    # ANSI color codes for terminal output
    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'  # Reset
    }

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        use_colors: bool = True
    ):
        """
        Initialize formatter.

        Args:
            fmt: Log message format
            datefmt: Date format
            use_colors: Whether to use ANSI colors (for terminal output)
        """
        if fmt is None:
            fmt = '[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s'
        if datefmt is None:
            datefmt = '%Y-%m-%d %H:%M:%S'

        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with optional colors.

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        # Add color to levelname if terminal output
        if self.use_colors and record.levelname in self.COLORS:
            levelname_color = self.COLORS[record.levelname]
            reset_color = self.COLORS['RESET']
            record.levelname = f"{levelname_color}{record.levelname}{reset_color}"

        return super().format(record)


class LoggingConfig:
    """
    Centralized logging configuration for DC Commander.

    Sets up loggers with file rotation, console output, and appropriate
    formatting for debugging and monitoring.
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        log_level: int = logging.INFO,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_output: bool = True,
        file_output: bool = True
    ):
        """
        Initialize logging configuration.

        Args:
            log_dir: Directory for log files (default: logs/)
            log_level: Minimum log level
            max_bytes: Maximum size per log file before rotation
            backup_count: Number of backup log files to keep
            console_output: Enable console logging
            file_output: Enable file logging
        """
        self.log_dir = log_dir or Path("logs")
        self.log_level = log_level
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.console_output = console_output
        self.file_output = file_output

        # Ensure log directory exists
        if self.file_output:
            self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configure root logger
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up logging handlers and formatters."""
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

        # Remove existing handlers
        root_logger.handlers.clear()

        # Console handler with colors
        if self.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            console_formatter = DCCommanderFormatter(use_colors=True)
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)

        # File handler with rotation
        if self.file_output:
            log_file = self.log_dir / f"dc_commander_{datetime.now().strftime('%Y%m%d')}.log"

            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level)
            file_formatter = DCCommanderFormatter(use_colors=False)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

            # Create separate error log
            error_log_file = self.log_dir / f"dc_commander_errors_{datetime.now().strftime('%Y%m%d')}.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_formatter = DCCommanderFormatter(use_colors=False)
            error_handler.setFormatter(error_formatter)
            root_logger.addHandler(error_handler)

        # Configure DC Commander logger
        dc_logger = logging.getLogger('dc_commander')
        dc_logger.setLevel(self.log_level)

    def set_level(self, level: int) -> None:
        """
        Change logging level dynamically.

        Args:
            level: New logging level (logging.DEBUG, INFO, etc.)
        """
        self.log_level = level
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        for handler in root_logger.handlers:
            handler.setLevel(level)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get logger for specific module.

        Args:
            name: Logger name (typically __name__)

        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)

    def disable_console_logging(self) -> None:
        """Disable console output (useful for production)."""
        root_logger = logging.getLogger()
        handlers_to_remove = [
            h for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        for handler in handlers_to_remove:
            root_logger.removeHandler(handler)

    def enable_debug_logging(self) -> None:
        """Enable debug level logging for troubleshooting."""
        self.set_level(logging.DEBUG)
        logger = self.get_logger(__name__)
        logger.debug("Debug logging enabled")

    def cleanup_old_logs(self, days_to_keep: int = 7) -> int:
        """
        Clean up old log files.

        Args:
            days_to_keep: Keep logs from last N days

        Returns:
            Number of files deleted
        """
        if not self.log_dir.exists():
            return 0

        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    deleted_count += 1
                except OSError:
                    pass

        return deleted_count


# Global logging config instance
_logging_config: Optional[LoggingConfig] = None


def setup_logging(
    log_dir: Optional[Path] = None,
    log_level: int = logging.INFO,
    console_output: bool = True,
    file_output: bool = True
) -> LoggingConfig:
    """
    Set up application-wide logging.

    Args:
        log_dir: Directory for log files
        log_level: Minimum log level
        console_output: Enable console logging
        file_output: Enable file logging

    Returns:
        LoggingConfig instance
    """
    global _logging_config

    _logging_config = LoggingConfig(
        log_dir=log_dir,
        log_level=log_level,
        console_output=console_output,
        file_output=file_output
    )

    return _logging_config


def get_logging_config() -> LoggingConfig:
    """
    Get global logging configuration.

    Returns:
        LoggingConfig instance
    """
    global _logging_config

    if _logging_config is None:
        _logging_config = LoggingConfig()

    return _logging_config


def get_logger(name: str) -> logging.Logger:
    """
    Get configured logger for module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger
    """
    config = get_logging_config()
    return config.get_logger(name)
