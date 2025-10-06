#!/usr/bin/env python3
"""
Modern Commander - Launcher Script

Simple launcher for Modern Commander application.
Handles graceful startup and shutdown with error handling.
"""

import sys
from pathlib import Path


def main():
    """Launch Modern Commander application."""
    try:
        # Import application
        from modern_commander import ModernCommanderApp

        # Create and run application
        app = ModernCommanderApp()
        app.run()

    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        print("\nModern Commander interrupted by user.")
        sys.exit(0)

    except ImportError as e:
        print(f"Error: Missing required dependencies.")
        print(f"Details: {e}")
        print("\nPlease install requirements:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
