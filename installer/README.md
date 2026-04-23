# DC Commander — Installer Tooling

This directory contains platform-specific packaging scripts. Each subfolder is self-contained and invoked by `.github/workflows/release.yml` on a `v*` tag push; they can also be run locally.

## Layout

```
installer/
├── README.md                           (this file)
├── windows/
│   └── dc-commander.nsi                 NSIS installer script
└── linux/
    ├── build_appimage.sh                AppImage builder
    └── build_appimage.sh.README.md      Linux-specific build notes
```

macOS (`.dmg`) packaging is intentionally out of scope for v1.0.x — see `ROADMAP.md`.

## Windows — local build

Requirements: Python 3.10+, PyInstaller, [NSIS 3.x](https://nsis.sourceforge.io/Download) (`makensis` on `PATH`).

```powershell
# 1. Build the PyInstaller binary (produces dist\DCCommander.exe)
python build_exe.py

# 2. Build the NSIS installer (produces dc-commander-setup-<VERSION>.exe
#    next to the .nsi file)
makensis /DVERSION=0.9.0 installer\windows\dc-commander.nsi
```

The installer is user-level (no admin prompt), installs to `%LOCALAPPDATA%\Programs\DC Commander`, and registers an entry in **Programs & Features** (per-user, HKCU).

## Linux — local build

See [`linux/build_appimage.sh.README.md`](linux/build_appimage.sh.README.md) for full prerequisites.

```bash
# Produces DC_Commander-0.9.0-x86_64.AppImage at repo root
./installer/linux/build_appimage.sh --version 0.9.0
```

## CI / release flow

The release workflow (`.github/workflows/release.yml`) triggers on any `v*` tag push and:

1. Builds the Windows installer on `windows-latest`.
2. Builds the Linux AppImage on `ubuntu-latest`.
3. Generates `SHA256SUMS` across all artifacts.
4. Creates a GitHub Release with the artifacts attached.

Prerelease is auto-detected: tags containing `-` (e.g. `v1.0.0-rc1`) become prereleases; clean tags (e.g. `v1.0.0`) are marked stable.

## Signing

**Not performed in v1.0.x.** Users verify artifact integrity via the published `SHA256SUMS` file attached to each GitHub Release. Code-signing (Windows Authenticode, macOS notarization) is tracked for a future release.
