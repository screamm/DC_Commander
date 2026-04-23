# Changelog

All notable changes to DC Commander will be documented in this file.

## [Unreleased]

### Sprint 4 — Distribution scaffolding (2026-04-23)

#### Added
- **NSIS installer** (`installer/windows/dc-commander.nsi`) — user-level Windows install, Start Menu shortcut, optional Desktop shortcut, conditional LICENSE page, uninstaller registered in Programs & Features.
- **Linux AppImage build script** (`installer/linux/build_appimage.sh`) — PyInstaller → AppDir → appimagetool pipeline with version arg. Bundled `.desktop` entry and icon fallback.
- **GitHub Actions release workflow** (`.github/workflows/release.yml`) — triggers on `v*` tags, builds Windows installer and Linux AppImage in parallel, publishes a GitHub Release with SHA256SUMS; auto-detects pre-release from tag format (`-rc1` → prerelease).
- **Installer documentation** (`installer/README.md`, `installer/linux/build_appimage.sh.README.md`).
- **CONTRIBUTING.md** (431 lines) — dev setup, project structure, code style, branching/commits, PR process, testing, running checks, reporting bugs.
- **docs/user-manual.md** (492 lines) — keyboard reference grounded in actual `BINDINGS`, file-op walkthroughs, configuration, troubleshooting, FAQ.
- **README.md Installation section** — per-OS install + source + SHA256 verification commands.

### Sprint 3 — Known-issue fixes (2026-04-23)

#### Fixed
- **F3 viewer crash** (`features/file_viewer.py`) — `FileViewer.__init__` was overriding Textual's read-only `Screen.scroll_offset` reactive. Renamed internal attribute to `_content_scroll_y`. Also removed an invalid `font-family: monospace` declaration from `.hex-view` CSS that Textual's parser silently rejected.
- **F9 config dialog crash** (`components/config_screen.py`) — three `Select` widgets had options in `(value, label)` order but Textual expects `(label, value)`. Swapped all three so the initial `value='name'` matches an option's value.
- **Ctrl+Q quick view crash** (`components/quick_view_widget.py`) — added `preview_file(path)` and `clear_preview()` methods to match the caller contract in `modern_commander.py`.

#### Added
- 15 regression tests across `tests/test_file_viewer_fix.py`, `tests/test_config_screen_fix.py`, `tests/test_quick_view_widget_fix.py`.

### Sprint 2 — Refactor: split the monolith (2026-04-23)

#### Changed
- **`modern_commander.py`** reduced from 2 122 → 1 299 lines (−39 %) by extracting into a new `app/` package with thin delegators remaining in the App class:
  - `app/file_actions.py` (905 lines) — `FileActionsController` owns F5 copy, F6 move, F7 mkdir, F8 delete, all sync/async variants, worker coroutines.
  - `app/navigation.py` (283 lines) — `NavigationController` owns panel switching, swap, refresh, goto-dir (with path validation), dir comparison, panel history.
  - `app/menu_dispatch.py` (204 lines) — `MenuDispatchController` routes action IDs from the F2 menu / top-menu-bar to the appropriate app action.

#### Added — test safety net
- `tests/characterization/test_app_integration.py` (459 lines, 13 behavioural tests + 3 pre-existing-bug xfails that the Sprint 3 fixes converted to XPASS). Textual `Pilot`-based golden-master tests that guarded the Sprint 2 extraction.

### Sprint 1 — Integration of existing infrastructure (2026-04-23)

#### Added
- **Central logging** via `src/utils/logging_config.setup_logging()` called from `run.py`; rotating file handlers in `~/.modern_commander/logs/dc_commander_YYYYMMDD.log` (10 MB × 5 backups) plus a separate ERROR-only log; console output at WARNING+ so the TUI terminal stays clean.
- **Global crash reporter** via `sys.excepthook` (`src/utils/crash_reporter.py`). Uncaught exceptions produce a dump in `~/.modern_commander/crashes/YYYY-MM-DD_HHMMSS.txt` with full traceback, environment info, and the last 100 log lines. The original excepthook is chained so stderr stack traces still appear.
- **Rich ErrorDialog** (`components/dialogs.py`) with Retry / Cancel, expandable technical details (press `d`), `Escape` cancels, `Enter` activates Retry if allowed.
- **UIValidationError** and `src/core/ui_security.py` helpers (`validate_user_filename`, `validate_user_path`) wired into F7 mkdir and goto-path prompts. Path-traversal, null bytes, reserved Windows names, and invalid characters are rejected with user-friendly errors and a retry loop that preserves the user's entry.
- **Error-to-user-message mapping** via `src/core/error_messages.format_user_error()` covering `PermissionError`, `FileNotFoundError`, `IsADirectoryError`, `FileExistsError`, `OSError` (ENOSPC, ENAMETOOLONG), custom file-operation exceptions, and a generic fallback.
- **Issue templates** (bug report, feature request) under `.github/ISSUE_TEMPLATE/`.

#### Changed
- F5/F6/F7/F8 handlers in `modern_commander.py` now wrap the dispatch path with an `ErrorBoundary`-style try/except that logs via `logger.exception()` and surfaces an `ErrorDialog`. Single-retry semantics prevent infinite loops.
- `claudedocs/` layout: 94 historical status reports moved to `claudedocs/archive/2025/`; canonical references kept at the root (ACTUAL_ARCHITECTURE, architecture, API, PLUGIN_API).

#### Removed
- `coordinators/` (5 files, 882 lines of unused code) — never imported from production.
- `src/di/` (258 lines) and `src/core/dependency_container.py` (141 lines) — two incompatible DI containers, zero production callers. Plain constructor injection is sufficient for this app's scale.
- `tests/test_di_integration.py` (477 lines) — the only remaining caller of the deleted DI containers.

#### Tests
- Added 107 tests across 6 new files: `test_logging.py` (4), `test_crash_reporter.py` (6), `test_error_messages.py` (17), `test_error_dialog.py` (12), `test_error_boundary_integration.py` (3 + 1 skipped), `test_ui_security.py` (65 including a 100-payload fuzz suite).

### Added - Production-Ready Features

#### UI Enhancements
- **Top Menu Bar**: Norton Commander style menu (Left, Files, Commands, Options, Right)
- **Authentic Color Scheme**: Brighter cyan/yellow colors matching Norton Commander
- **Cursor Highlighting**: Solid yellow background with dark blue text for better visibility
- **Directory Display**: Uppercase directories in brackets format [DIRNAME]
- **Split Date/Time**: Separate Date and Time columns instead of single Modified column
- **Command Bar Format**: Clean format without colons (1Help, 2Menu, 3View...)

#### Group Selection (Norton Commander Gray +/-/*)
- Select files matching wildcard patterns with Gray + (numpad +)
- Deselect files matching patterns with Gray - (numpad -)
- Invert selection with Gray * (numpad *)
- Case-sensitive and case-insensitive pattern matching
- Interactive pattern input dialogs

#### Quick Search (Type-to-Filter)
- Incremental search as you type
- Automatically jump to matching files
- Search status display at bottom of panel
- Backspace to edit search text
- ESC to cancel search mode

#### Find File Dialog (Ctrl+F)
- Search across entire directory trees
- Wildcard pattern support (*.py, test_*)
- Regex pattern matching
- Subdirectory recursion toggle
- Case-sensitive search option
- Navigate directly to found files

#### Multiple View Modes (Ctrl+V)
- **Full View**: Name, Size, Date, Time (default Norton Commander style)
- **Brief View**: Name only, maximizes visible files
- **Info View**: Full details + permissions and owner (Unix systems)
- Cycle through modes with Ctrl+V
- Dynamic column adjustment per view mode

### Architecture Improvements

#### Service Layer
- **FileService**: High-level file operations with comprehensive error handling
- Operation result tracking (Success, Partial, Failure)
- Detailed error reporting per file
- Overwrite protection with configurable behavior
- Copy, Move, Delete, Rename, Create Directory operations

#### Repository Pattern
- **FileRepository**: Data access abstraction for file system
- Directory contents retrieval with filtering
- File statistics and metadata access
- Directory tree traversal with depth control
- Drive/volume information queries
- Hidden file support

#### Command Pattern (Undo/Redo)
- Full command history with undo/redo support
- CopyFileCommand with rollback capability
- MoveFileCommand with reversal
- DeleteFileCommand with backup/restore
- CreateDirectoryCommand with cleanup
- RenameFileCommand with reversion
- CommandHistory manager with configurable depth (default 100 commands)

#### Strategy Pattern (Flexible Sorting)
- **NameSortStrategy**: Alphabetical sorting, directories first
- **SizeSortStrategy**: Sort by file size
- **DateModifiedSortStrategy**: Sort by modification timestamp
- **ExtensionSortStrategy**: Sort by file extension
- **TypeSortStrategy**: Sort by file type (directories, files, symlinks)
- SortContext for runtime strategy switching
- SortStrategyFactory for easy strategy creation

### Utilities

#### Formatters
- Shared file size formatting across components
- Consistent date formatting (YY-MM-DD)
- Consistent time formatting (HH:MM)
- Eliminates code duplication

#### Encoding Detection
- Binary file detection
- Automatic encoding detection (UTF-8, Latin-1, CP1252, ISO-8859-1)
- Safe file reading with fallback encodings

### Configuration
- Automatic configuration persistence
- Per-panel start path and sort preferences
- JSON-based configuration file (~/.modern_commander/config.json)
- Auto-save on navigation and preference changes

### Removed
- StatusBar widget (simplified UI)
- Header and Footer widgets (cleaner Norton Commander look)
- Colon separators in command bar (authentic NC format)

## [0.1.0] - Initial Release

### Added
- Dual-pane file manager interface
- Basic file operations (Copy, Move, Delete)
- File viewer (F3) and editor (F4)
- Directory navigation
- File selection
- Basic search functionality
- Configuration management
- Norton Commander inspired UI

## Future Versions

### [0.3.0] - Planned
- Quick View mode implementation
- Plugin system architecture
- Theme system for custom colors
- Undo/Redo UI integration (Ctrl+Z/Ctrl+Y)

### [0.4.0] - Planned
- Archive support (ZIP, TAR, 7Z)
- Hidden files toggle (Ctrl+H)
- Bookmarks and favorites
- Batch rename functionality

### [0.5.0] - Planned
- FTP/SFTP support
- Compare directories
- Tab support for multiple panels
- File permissions editor
