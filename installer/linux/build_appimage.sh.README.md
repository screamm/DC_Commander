# Linux AppImage Build

Produces `DC_Commander-<VERSION>-x86_64.AppImage` at the repository root.

## Prerequisites

Install on the build host (these are **not** pip-installable):

| Tool | How to install (Debian/Ubuntu) | Notes |
|------|-------------------------------|-------|
| `python3` (>=3.10) | `sudo apt install python3 python3-pip` | |
| `pyinstaller` | `pip install pyinstaller` | Also installed by `pip install -e ".[dev]"` once pyinstaller is added to dev deps. |
| `appimagetool` | Download the AppImage from [AppImageKit releases](https://github.com/AppImage/AppImageKit/releases/latest), `chmod +x`, and place on `PATH` as `appimagetool`. | |
| `libfuse2` | `sudo apt install libfuse2` | Required at **runtime** by AppImage (both during build and for end-users on older distros). |

## Running

```bash
# Default version (0.9.0)
./installer/linux/build_appimage.sh

# Explicit version via env var
VERSION=1.0.0 ./installer/linux/build_appimage.sh

# Explicit version via flag (accepts leading "v" — stripped automatically)
./installer/linux/build_appimage.sh --version v1.0.0
```

The script is idempotent — it cleans `dc-commander.AppDir/` on each run.

## Output

```
<repo-root>/
└── DC_Commander-<VERSION>-x86_64.AppImage
```

Users run it with:

```bash
chmod +x DC_Commander-*.AppImage
./DC_Commander-*.AppImage
```

Because DC Commander is a TUI, the `.desktop` entry sets `Terminal=true`, so launching it from a file manager / menu will spawn a terminal.

## Troubleshooting

**`ERROR: appimagetool not on PATH`**
Download the appimagetool AppImage and place it on `PATH`:
```bash
wget -O /usr/local/bin/appimagetool \
  https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x /usr/local/bin/appimagetool
```

**`appimagetool: failed to extract runtime` / FUSE errors**
Install libfuse2: `sudo apt install libfuse2`. On containers / CI, also add `--appimage-extract-and-run` usage, or run inside a privileged container.

**`AppRun` doesn't launch the binary**
Check that `dist/DCCommander` (or `dist/dc-commander`) was produced by PyInstaller and has the executable bit set. The script sets it explicitly via `install -m 0755`.

**Icon is 1x1 transparent**
The script falls back to a placeholder when no icon is found under `assets/`. Drop a real `assets/dc-commander.png` (recommended 256×256 PNG) and re-run.

**`libpython3.X.so` missing on end-user machine**
PyInstaller's `--onefile` / spec default bundles Python; this shouldn't happen. If it does, confirm the build was run on a distro with **older glibc** than the target (build on Ubuntu 20.04 LTS for broad compatibility).
