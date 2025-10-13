#!/usr/bin/env python3
"""
DC Commander Build Script
Builds a standalone executable using PyInstaller
"""

import sys
import subprocess
from pathlib import Path


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def install_pyinstaller():
    """Install PyInstaller."""
    print("Installing PyInstaller...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install PyInstaller: {e}")
        return False


def build_executable():
    """Build the executable using PyInstaller."""
    print("\n" + "="*60)
    print("DC COMMANDER - BUILD EXECUTABLE")
    print("="*60 + "\n")

    # Check if PyInstaller is installed
    if not check_pyinstaller():
        print("PyInstaller not found. Installing...")
        if not install_pyinstaller():
            print("\n[ERROR] Build failed: Could not install PyInstaller")
            return False
    else:
        print("[OK] PyInstaller is installed")

    # Build with spec file
    print("\nBuilding executable...")
    print("This may take a few minutes...\n")

    try:
        spec_file = Path("dc_commander.spec")
        if not spec_file.exists():
            print(f"[ERROR] Spec file not found: {spec_file}")
            return False

        subprocess.check_call([
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            str(spec_file)
        ])

        print("\n" + "="*60)
        print("[SUCCESS] BUILD SUCCESSFUL!")
        print("="*60)

        exe_path = Path("dist") / "DCCommander.exe"
        if exe_path.exists():
            print(f"\nExecutable location:")
            print(f"  {exe_path.absolute()}")
            print(f"\nFile size: {exe_path.stat().st_size / (1024*1024):.1f} MB")
        else:
            print("\n[WARNING] Executable file not found at expected location")

        print("\nYou can now run DC Commander by double-clicking:")
        print("  DCCommander.exe")
        print("\nOr from command line:")
        print("  .\\dist\\DCCommander.exe")

        return True

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Build failed: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main build function."""
    success = build_executable()

    if success:
        print("\n" + "="*60)
        print("BUILD COMPLETE - READY TO RUN!")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("BUILD FAILED")
        print("="*60)
        print("\nPlease check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
