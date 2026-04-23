; ============================================================================
; DC Commander - NSIS Installer Script
; ============================================================================
;
; Builds a user-level (no admin required) installer for Windows.
;
; Usage:
;   makensis /DVERSION=0.9.0 installer\windows\dc-commander.nsi
;
; Output:
;   dc-commander-setup-<VERSION>.exe   (written next to this .nsi file)
;
; Source layout expected:
;   dist\DCCommander.exe                (PyInstaller one-file output)
;   -- OR --
;   dist\DC_Commander\*                 (PyInstaller one-folder output, future)
;
; NOTE: The current dc_commander.spec produces a single-file binary at
;   dist\DCCommander.exe. This installer targets that layout. If the spec is
;   later switched to one-folder mode (directory dist\DC_Commander\), update
;   the Install section's File directives accordingly.
; ============================================================================

!ifndef VERSION
  !define VERSION "0.9.0"
!endif

!define APP_NAME        "DC Commander"
!define APP_PUBLISHER   "DC Commander Contributors"
!define APP_EXE         "DC Commander.exe"
!define APP_REG_KEY     "Software\Microsoft\Windows\CurrentVersion\Uninstall\DCCommander"
!define APP_URL         "https://github.com/davidrydgren/DC-Commander"

; Modern UI
!include "MUI2.nsh"
!include "FileFunc.nsh"

; Paths are resolved relative to this .nsi file's directory so the script
; works regardless of where makensis is invoked from.
; ${__FILEDIR__} is a built-in NSIS 3 macro that expands at compile time
; to the directory containing the current source file.
!define REPO_ROOT "${__FILEDIR__}\..\.."

; ----------------------------------------------------------------------------
; General
; ----------------------------------------------------------------------------
Name               "${APP_NAME} ${VERSION}"
; OutFile path is resolved relative to makensis's CWD. We anchor it to the
; .nsi directory so the installer always lands next to this script.
OutFile            "${__FILEDIR__}\dc-commander-setup-${VERSION}.exe"
Unicode            true
RequestExecutionLevel user
InstallDir         "$LOCALAPPDATA\Programs\DC Commander"
InstallDirRegKey   HKCU "Software\DCCommander" "InstallDir"
ShowInstDetails    show
ShowUninstDetails  show
SetCompressor      /SOLID lzma

; Version metadata embedded in the installer .exe itself
VIProductVersion   "${VERSION}.0"
VIAddVersionKey    "ProductName"     "${APP_NAME}"
VIAddVersionKey    "CompanyName"     "${APP_PUBLISHER}"
VIAddVersionKey    "FileDescription" "${APP_NAME} Installer"
VIAddVersionKey    "FileVersion"     "${VERSION}"
VIAddVersionKey    "ProductVersion"  "${VERSION}"
VIAddVersionKey    "LegalCopyright"  "MIT License"

; ----------------------------------------------------------------------------
; Modern UI configuration
; ----------------------------------------------------------------------------
!define MUI_ABORTWARNING
!define MUI_ICON   "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME

; License page — only shown if LICENSE file is found at build time.
!define LICENSE_FILE_PATH "${REPO_ROOT}\LICENSE"
!if /FileExists "${LICENSE_FILE_PATH}"
  !insertmacro MUI_PAGE_LICENSE "${LICENSE_FILE_PATH}"
!endif

!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME}"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ----------------------------------------------------------------------------
; Sections
; ----------------------------------------------------------------------------
Section "Install" SEC_CORE
  SectionIn RO  ; required

  SetOutPath "$INSTDIR"

  ; Primary payload: the PyInstaller single-file binary, renamed at install
  ; time to the friendly "DC Commander.exe".
  File /oname=${APP_EXE} "${REPO_ROOT}\dist\DCCommander.exe"

  ; Bundle README and CHANGELOG if present (best-effort; non-fatal if missing).
  File /nonfatal "${REPO_ROOT}\README.md"
  File /nonfatal "${REPO_ROOT}\CHANGELOG.md"
  File /nonfatal "${REPO_ROOT}\LICENSE"

  ; Start Menu shortcut
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
                 "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" \
                 "$INSTDIR\Uninstall.exe"

  ; Write uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Remember install location
  WriteRegStr HKCU "Software\DCCommander" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\DCCommander" "Version"    "${VERSION}"

  ; Register with Programs & Features (HKCU — per-user, matches user-level install)
  WriteRegStr HKCU "${APP_REG_KEY}" "DisplayName"          "${APP_NAME}"
  WriteRegStr HKCU "${APP_REG_KEY}" "DisplayVersion"       "${VERSION}"
  WriteRegStr HKCU "${APP_REG_KEY}" "Publisher"            "${APP_PUBLISHER}"
  WriteRegStr HKCU "${APP_REG_KEY}" "DisplayIcon"          "$INSTDIR\${APP_EXE}"
  WriteRegStr HKCU "${APP_REG_KEY}" "UninstallString"      "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKCU "${APP_REG_KEY}" "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
  WriteRegStr HKCU "${APP_REG_KEY}" "InstallLocation"      "$INSTDIR"
  WriteRegStr HKCU "${APP_REG_KEY}" "URLInfoAbout"         "${APP_URL}"
  WriteRegDWORD HKCU "${APP_REG_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${APP_REG_KEY}" "NoRepair" 1

  ; Estimated size (KB) for Programs & Features UI
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKCU "${APP_REG_KEY}" "EstimatedSize" "$0"
SectionEnd

Section "Desktop shortcut" SEC_DESKTOP
  ; Optional — opt-in by default (selected unless user unchecks it).
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" \
                 "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
SectionEnd

; Section descriptions (hover text in Components page)
LangString DESC_SEC_CORE    ${LANG_ENGLISH} "Install ${APP_NAME} core files (required)."
LangString DESC_SEC_DESKTOP ${LANG_ENGLISH} "Create a shortcut on the Desktop."

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_CORE}    $(DESC_SEC_CORE)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_DESKTOP} $(DESC_SEC_DESKTOP)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ----------------------------------------------------------------------------
; Uninstaller
; ----------------------------------------------------------------------------
Section "Uninstall"
  ; Remove shortcuts
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
  RMDir  "$SMPROGRAMS\${APP_NAME}"

  ; Remove files
  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\CHANGELOG.md"
  Delete "$INSTDIR\LICENSE"
  Delete "$INSTDIR\Uninstall.exe"

  ; Attempt to clean install directory (only removes if empty)
  RMDir "$INSTDIR"

  ; Remove registry keys
  DeleteRegKey HKCU "${APP_REG_KEY}"
  DeleteRegKey HKCU "Software\DCCommander"
SectionEnd
