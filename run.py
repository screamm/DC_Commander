#!/usr/bin/env python3
"""
Modern Commander - Launcher Script

Simple launcher for Modern Commander application.
Handles graceful startup and shutdown with error handling and
centralized logging to ~/.modern_commander/logs/.
"""

import platform
import sys
from pathlib import Path

from src.utils.crash_reporter import install_crash_handler
from src.utils.logging_config import get_logger, setup_logging

__version__ = "0.2.0"


def _read_project_version() -> str:
    """Return DC Commander version.

    Tries to read the version from pyproject.toml when available (for source
    checkouts), otherwise falls back to the module-level ``__version__``.
    The parse is intentionally dependency-free so it works on Python 3.10
    (no ``tomllib`` available).
    """
    pyproject = Path(__file__).resolve().parent / "pyproject.toml"
    try:
        with pyproject.open(encoding="utf-8") as fh:
            in_project = False
            for raw_line in fh:
                line = raw_line.strip()
                if line.startswith("["):
                    in_project = line == "[project]"
                    continue
                if in_project and line.startswith("version"):
                    # e.g. version = "0.2.0"
                    _, _, rhs = line.partition("=")
                    return rhs.strip().strip('"').strip("'")
    except OSError:
        pass
    return __version__


def main() -> None:
    """Launch Modern Commander application."""
    # Initialize central logging FIRST so any subsequent import or startup
    # failure lands in ~/.modern_commander/logs/ instead of disappearing.
    setup_logging()
    logger = get_logger(__name__)

    version = _read_project_version()

    # Install global crash handler AFTER logging is configured so uncaught
    # exceptions are both logged and written to ~/.modern_commander/crashes/.
    # Passed version ends up in every crash-dump header.
    install_crash_handler(version=version)
    logger.info("=" * 60)
    logger.info("DC Commander starting up")
    logger.info("Version : %s", version)
    logger.info("Python  : %s", sys.version.replace("\n", " "))
    logger.info("Platform: %s", platform.platform())
    logger.info("=" * 60)

    try:
        # Import application
        from modern_commander import ModernCommanderApp

        # Create and run application
        app = ModernCommanderApp()
        app.run()

    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        logger.info("Shutdown by user (Ctrl+C)")
        print("\nModern Commander interrupted by user.")
        sys.exit(0)

    except ImportError as e:
        logger.exception("Missing required dependency during startup")
        print("Error: Missing required dependencies.")
        print(f"Details: {e}")
        print("\nPlease install requirements:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    except Exception as e:
        logger.exception("Fatal error in application")
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
