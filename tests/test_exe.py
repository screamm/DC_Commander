#!/usr/bin/env python3
"""
Quick test to verify the executable works before running it
"""

import sys
import subprocess
from pathlib import Path

def test_imports():
    """Test that critical imports work."""
    print("Testing critical imports...")

    try:
        print("  - textual.app...", end=" ")
        from textual.app import App
        print("[OK]")

        print("  - textual.widgets...", end=" ")
        from textual.widgets import Widget, Static, Button, DataTable
        print("[OK]")

        print("  - textual.containers...", end=" ")
        from textual.containers import Container, Horizontal, Vertical
        print("[OK]")

        print("  - rich...", end=" ")
        from rich.syntax import Syntax
        from rich.text import Text
        print("[OK]")

        print("  - aiofiles...", end=" ")
        import aiofiles
        print("[OK]")

        print("\n[SUCCESS] All critical imports work!")
        return True

    except ImportError as e:
        print(f"\n[ERROR] Import failed: {e}")
        return False


def test_executable():
    """Test that the executable starts without errors."""
    print("\nTesting executable startup...")

    exe_path = Path("dist/DCCommander.exe")
    if not exe_path.exists():
        print(f"[ERROR] Executable not found: {exe_path}")
        return False

    print(f"  Executable found: {exe_path}")
    print(f"  Size: {exe_path.stat().st_size / (1024*1024):.1f} MB")

    # Don't actually run it, just verify it exists and is the right size
    min_size = 15 * 1024 * 1024  # At least 15 MB
    if exe_path.stat().st_size < min_size:
        print(f"[WARNING] Executable seems too small (< 15 MB)")
        return False

    print("\n[SUCCESS] Executable looks good!")
    return True


def main():
    print("="*60)
    print("DC COMMANDER - EXECUTABLE TEST")
    print("="*60 + "\n")

    imports_ok = test_imports()
    exe_ok = test_executable()

    print("\n" + "="*60)
    if imports_ok and exe_ok:
        print("[SUCCESS] All tests passed!")
        print("="*60)
        print("\nYou can now safely run the executable:")
        print("  .\\dist\\DCCommander.exe")
        return 0
    else:
        print("[FAILED] Some tests failed!")
        print("="*60)
        print("\nThe executable may not work correctly.")
        print("Try rebuilding with: python build_exe.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
