#!/usr/bin/env bash
# =============================================================================
# DC Commander - Linux AppImage builder
# =============================================================================
#
# Produces: DC_Commander-<VERSION>-x86_64.AppImage  (at repo root)
#
# Usage:
#   ./installer/linux/build_appimage.sh                  # uses VERSION=0.9.0
#   VERSION=1.0.0 ./installer/linux/build_appimage.sh
#   ./installer/linux/build_appimage.sh --version 1.0.0
#
# Requirements on PATH:
#   - python3 (3.10+)
#   - pyinstaller  (pip install pyinstaller)
#   - appimagetool (https://github.com/AppImage/AppImageKit/releases)
#   - libfuse2 installed system-wide (AppImage runtime dependency)
#
# Exits non-zero on any failure. Safe to re-run (cleans previous AppDir).
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Locate repo root (two levels up from this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ---------------------------------------------------------------------------
# Parse version argument / env var
# ---------------------------------------------------------------------------
VERSION="${VERSION:-0.9.0}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="$2"
      shift 2
      ;;
    --version=*)
      VERSION="${1#*=}"
      shift
      ;;
    -h|--help)
      sed -n '2,22p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

# Strip leading "v" if someone passes a tag name like v1.0.0.
VERSION="${VERSION#v}"

echo "==> Building DC Commander AppImage v${VERSION}"
echo "    repo root: ${REPO_ROOT}"

# ---------------------------------------------------------------------------
# Tool checks
# ---------------------------------------------------------------------------
command -v python3     >/dev/null 2>&1 || { echo "ERROR: python3 not on PATH"      >&2; exit 1; }
command -v pyinstaller >/dev/null 2>&1 || { echo "ERROR: pyinstaller not on PATH (pip install pyinstaller)" >&2; exit 1; }
command -v appimagetool>/dev/null 2>&1 || { echo "ERROR: appimagetool not on PATH" >&2; exit 1; }

cd "${REPO_ROOT}"

# ---------------------------------------------------------------------------
# 1. Build the binary via PyInstaller
#    Prefer the existing spec file (one-file build -> dist/DCCommander).
# ---------------------------------------------------------------------------
echo "==> Running PyInstaller"
if [[ -f dc_commander.spec ]]; then
  pyinstaller --clean --noconfirm dc_commander.spec
  # Spec names the EXE "DCCommander". On Linux the file has no extension.
  PYI_BIN="dist/DCCommander"
else
  pyinstaller --onefile --clean --noconfirm --name dc-commander run.py
  PYI_BIN="dist/dc-commander"
fi

if [[ ! -f "${PYI_BIN}" ]]; then
  echo "ERROR: PyInstaller output not found at ${PYI_BIN}" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Assemble AppDir
# ---------------------------------------------------------------------------
APPDIR="dc-commander.AppDir"
echo "==> Assembling ${APPDIR}"

rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin"

# Install the binary under a stable name.
install -m 0755 "${PYI_BIN}" "${APPDIR}/usr/bin/dc-commander"

# AppRun: entrypoint script the AppImage runtime executes.
cat > "${APPDIR}/AppRun" <<'APPRUN_EOF'
#!/usr/bin/env bash
# DC Commander AppRun — launches the bundled binary.
HERE="$(cd "$(dirname "$(readlink -f "${0}")")" && pwd)"
exec "${HERE}/usr/bin/dc-commander" "$@"
APPRUN_EOF
chmod +x "${APPDIR}/AppRun"

# Desktop entry (required by appimagetool).
cat > "${APPDIR}/dc-commander.desktop" <<DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=DC Commander
GenericName=File Manager
Comment=Norton Commander-style TUI file manager
Exec=dc-commander
Icon=dc-commander
Terminal=true
Categories=Utility;FileTools;System;
Keywords=file;manager;tui;norton;commander;
DESKTOP_EOF

# Icon: appimagetool REQUIRES a PNG matching the Icon= field.
# If the project ships an icon under assets/, prefer it; otherwise synthesize
# a minimal 1x1 transparent PNG so the build still succeeds. Replace with a
# real icon before a public release.
if [[ -f "assets/dc-commander.png" ]]; then
  cp "assets/dc-commander.png" "${APPDIR}/dc-commander.png"
elif [[ -f "assets/icon.png" ]]; then
  cp "assets/icon.png" "${APPDIR}/dc-commander.png"
else
  # NOTE: placeholder — a 1x1 transparent PNG, base64-encoded.
  # Replace assets/dc-commander.png with a real icon for production builds.
  echo "    (no icon in assets/, writing 1x1 placeholder PNG)"
  base64 -d > "${APPDIR}/dc-commander.png" <<'PNG_EOF'
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8A
AAAASUVORK5CYII=
PNG_EOF
fi

# ---------------------------------------------------------------------------
# 3. Run appimagetool
# ---------------------------------------------------------------------------
OUTPUT="DC_Commander-${VERSION}-x86_64.AppImage"
echo "==> Running appimagetool -> ${OUTPUT}"

# ARCH env var required by appimagetool when it can't detect.
ARCH="${ARCH:-x86_64}" appimagetool "${APPDIR}" "${OUTPUT}"

echo
echo "==> Built: ${REPO_ROOT}/${OUTPUT}"
ls -lh "${OUTPUT}"
