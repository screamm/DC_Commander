# Changelog

All notable changes to DC Commander will be documented in this file.

## [Unreleased]

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
