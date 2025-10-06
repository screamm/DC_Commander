# Modern Commander - Complete Project Structure

**Version**: 1.0.0
**Date**: 2025-10-05

This document provides the complete file and directory structure for the Modern Commander project with descriptions of each component.

---

## Directory Tree

```
modern-commander/
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                     # Continuous Integration pipeline
│   │   ├── release.yml                # Release automation
│   │   └── codeql.yml                 # Security analysis
│   │
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md              # Bug report template
│   │   └── feature_request.md         # Feature request template
│   │
│   └── pull_request_template.md       # PR template
│
├── docs/
│   ├── architecture.md                # System architecture documentation
│   ├── component-diagrams.md          # Visual component diagrams
│   ├── project-structure.md           # This file
│   ├── user-guide.md                  # End-user documentation
│   ├── developer-guide.md             # Developer setup and contribution guide
│   ├── api-reference.md               # API documentation
│   ├── keybindings.md                 # Keyboard shortcuts reference
│   └── screenshots/                   # Application screenshots
│       ├── main-view.png
│       ├── file-operations.png
│       └── search-dialog.png
│
├── config/
│   ├── default_config.toml            # Default application configuration
│   ├── keybindings.toml               # Default keyboard shortcuts
│   └── themes/
│       ├── classic.tcss               # Norton Commander classic theme
│       ├── modern.tcss                # Modern dark theme
│       └── light.tcss                 # Light theme
│
├── src/
│   └── modern_commander/
│       │
│       ├── __init__.py                # Package initialization
│       ├── __main__.py                # Entry point for python -m modern_commander
│       ├── app.py                     # Main application class
│       ├── config.py                  # Configuration management
│       ├── constants.py               # Application-wide constants
│       │
│       ├── core/                      # Core domain models and interfaces
│       │   ├── __init__.py
│       │   ├── interfaces.py          # Abstract interfaces (FileSystemInterface, etc.)
│       │   ├── models.py              # Data models (FileEntry, OperationResult, etc.)
│       │   ├── events.py              # Application events
│       │   ├── exceptions.py          # Custom exceptions
│       │   └── enums.py               # Enumerations (PlatformType, SortOrder, etc.)
│       │
│       ├── components/                # UI Components (Textual widgets)
│       │   ├── __init__.py
│       │   │
│       │   ├── file_panel.py          # Main dual-panel component
│       │   │   # - FilPanel class
│       │   │   # - Panel state management
│       │   │   # - Navigation logic
│       │   │
│       │   ├── command_bar.py         # F-key command bar
│       │   │   # - CommandBar class
│       │   │   # - Dynamic command display
│       │   │   # - Command execution
│       │   │
│       │   ├── status_bar.py          # Status information bar
│       │   │   # - StatusBar class
│       │   │   # - System info display
│       │   │   # - Selection info
│       │   │
│       │   ├── dialog_system.py       # Modal dialog manager
│       │   │   # - DialogSystem class
│       │   │   # - Confirmation dialogs
│       │   │   # - Input prompts
│       │   │   # - Progress dialogs
│       │   │
│       │   └── widgets/               # Reusable UI widgets
│       │       ├── __init__.py
│       │       │
│       │       ├── file_list.py       # File list widget
│       │       │   # - FileList class
│       │       │   # - Virtual scrolling
│       │       │   # - Selection handling
│       │       │
│       │       ├── breadcrumb.py      # Path navigation breadcrumb
│       │       │   # - Breadcrumb class
│       │       │   # - Clickable path segments
│       │       │
│       │       ├── progress_dialog.py # Progress indicator dialog
│       │       │   # - ProgressDialog class
│       │       │   # - Progress bar
│       │       │   # - Cancellation support
│       │       │
│       │       ├── search_dialog.py   # Search interface dialog
│       │       │   # - SearchDialog class
│       │       │   # - Search options
│       │       │   # - Results display
│       │       │
│       │       └── confirmation_dialog.py  # Yes/No confirmation
│       │           # - ConfirmationDialog class
│       │           # - Customizable buttons
│       │
│       ├── operations/                # Business logic layer
│       │   ├── __init__.py
│       │   │
│       │   ├── file_operations.py     # File system operations
│       │   │   # - FileOperations class
│       │   │   # - copy_files(), move_files(), delete_files()
│       │   │   # - Progress tracking
│       │   │   # - Error handling
│       │   │
│       │   ├── search_engine.py       # File search functionality
│       │   │   # - SearchEngine class
│       │   │   # - search_by_name(), search_by_content()
│       │   │   # - search_by_size(), search_by_date()
│       │   │   # - Async iteration
│       │   │
│       │   ├── archive_handler.py     # Archive management
│       │   │   # - ArchiveHandler class
│       │   │   # - create_archive(), extract_archive()
│       │   │   # - list_archive(), is_archive()
│       │   │   # - ZIP, TAR support
│       │   │
│       │   ├── file_viewer.py         # File viewing (F3)
│       │   │   # - FileViewer class
│       │   │   # - Text file display
│       │   │   # - Syntax highlighting
│       │   │   # - Search within file
│       │   │
│       │   ├── file_editor.py         # Text editing (F4)
│       │   │   # - FileEditor class
│       │   │   # - Text editing
│       │   │   # - Save/Save As
│       │   │   # - Syntax highlighting
│       │   │
│       │   ├── clipboard.py           # Clipboard operations
│       │   │   # - Clipboard class
│       │   │   # - copy(), paste(), clear()
│       │   │   # - System clipboard integration
│       │   │
│       │   └── bookmarks.py           # Bookmark management
│       │       # - BookmarkManager class
│       │       # - add_bookmark(), remove_bookmark()
│       │       # - list_bookmarks()
│       │
│       ├── handlers/                  # Event and input handlers
│       │   ├── __init__.py
│       │   │
│       │   ├── keyboard_handler.py    # Keyboard input coordinator
│       │   │   # - KeyboardHandler class
│       │   │   # - Key binding registration
│       │   │   # - Event routing
│       │   │   # - Context-aware handling
│       │   │
│       │   ├── action_handler.py      # Action dispatching
│       │   │   # - ActionHandler class
│       │   │   # - Command execution
│       │   │   # - Action validation
│       │   │
│       │   └── hotkey_manager.py      # Hotkey management
│       │       # - HotkeyManager class
│       │       # - Dynamic key binding
│       │       # - Conflict detection
│       │
│       ├── platform/                  # Platform abstraction layer
│       │   ├── __init__.py
│       │   │
│       │   ├── filesystem.py          # Filesystem adapter factory
│       │   │   # - FileSystemAdapter class
│       │   │   # - create() factory method
│       │   │   # - Platform detection
│       │   │
│       │   ├── system_info.py         # System information
│       │   │   # - SystemInfo class
│       │   │   # - get_platform(), get_drives()
│       │   │   # - get_disk_usage()
│       │   │
│       │   ├── process_utils.py       # Process execution
│       │   │   # - ProcessUtils class
│       │   │   # - execute_command()
│       │   │   # - shell_execute()
│       │   │
│       │   └── platform_specific/
│       │       ├── __init__.py
│       │       │
│       │       ├── windows.py         # Windows-specific implementation
│       │       │   # - WindowsFileSystem class
│       │       │   # - Drive letter handling
│       │       │   # - UNC path support
│       │       │   # - Long path support
│       │       │   # - File attributes
│       │       │
│       │       ├── linux.py           # Linux-specific implementation
│       │       │   # - LinuxFileSystem class
│       │       │   # - Mount point handling
│       │       │   # - Permission handling
│       │       │   # - Symlink support
│       │       │   # - Extended attributes
│       │       │
│       │       └── macos.py           # macOS-specific implementation
│       │           # - MacOSFileSystem class
│       │           # - Volume handling
│       │           # - App bundle support
│       │           # - .DS_Store handling
│       │           # - Metadata handling
│       │
│       ├── utils/                     # Shared utilities
│       │   ├── __init__.py
│       │   │
│       │   ├── formatting.py          # Display formatting
│       │   │   # - format_size() - Human-readable sizes
│       │   │   # - format_date() - Date formatting
│       │   │   # - format_permissions() - Permission strings
│       │   │
│       │   ├── validators.py          # Input validation
│       │   │   # - PathValidator class
│       │   │   # - is_safe_path()
│       │   │   # - sanitize_filename()
│       │   │   # - validate_input()
│       │   │
│       │   ├── async_utils.py         # Async helpers
│       │   │   # - AsyncQueue class
│       │   │   # - debounce() decorator
│       │   │   # - async_batch()
│       │   │
│       │   ├── cache.py               # Caching utilities
│       │   │   # - TTLCache class
│       │   │   # - FileSystemCache class
│       │   │   # - Cache invalidation
│       │   │
│       │   └── logging_config.py      # Logging configuration
│       │       # - setup_logging()
│       │       # - Logger configuration
│       │       # - File/console handlers
│       │
│       ├── themes/                    # Theming system
│       │   ├── __init__.py
│       │   │
│       │   ├── theme_manager.py       # Theme switching
│       │   │   # - ThemeManager class
│       │   │   # - load_theme()
│       │   │   # - switch_theme()
│       │   │
│       │   ├── classic.tcss           # Classic Norton Commander theme
│       │   ├── modern.tcss            # Modern dark theme
│       │   └── light.tcss             # Light theme
│       │
│       └── plugins/                   # Plugin system
│           ├── __init__.py
│           │
│           ├── plugin_interface.py    # Plugin base classes
│           │   # - PluginInterface (base)
│           │   # - FileViewerPlugin
│           │   # - FileOperationPlugin
│           │   # - EditorPlugin
│           │
│           ├── plugin_loader.py       # Plugin discovery and loading
│           │   # - PluginLoader class
│           │   # - load_plugins()
│           │   # - Plugin lifecycle management
│           │
│           └── builtin/               # Built-in plugins
│               ├── __init__.py
│               └── hex_viewer.py      # Hex viewer for binary files
│
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── conftest.py                    # Pytest configuration and fixtures
│   │
│   ├── unit/                          # Unit tests
│   │   ├── __init__.py
│   │   │
│   │   ├── test_file_operations.py   # FileOperations tests
│   │   ├── test_search_engine.py     # SearchEngine tests
│   │   ├── test_archive_handler.py   # ArchiveHandler tests
│   │   ├── test_filesystem_adapter.py # FileSystem adapter tests
│   │   ├── test_validators.py        # Validation tests
│   │   ├── test_formatting.py        # Formatting tests
│   │   └── test_config.py            # Configuration tests
│   │
│   ├── integration/                   # Integration tests
│   │   ├── __init__.py
│   │   │
│   │   ├── test_file_panel_integration.py    # Panel integration
│   │   ├── test_operations_integration.py    # Operation workflows
│   │   └── test_keyboard_integration.py      # Keyboard handling
│   │
│   ├── e2e/                           # End-to-end tests
│   │   ├── __init__.py
│   │   │
│   │   ├── test_basic_workflow.py     # Basic user workflows
│   │   ├── test_file_management.py    # File management workflows
│   │   └── test_search_workflow.py    # Search workflows
│   │
│   ├── platform/                      # Platform-specific tests
│   │   ├── __init__.py
│   │   ├── test_windows_specific.py   # Windows tests
│   │   ├── test_linux_specific.py     # Linux tests
│   │   └── test_macos_specific.py     # macOS tests
│   │
│   └── fixtures/                      # Test data
│       ├── sample_files/
│       │   ├── text.txt
│       │   ├── binary.bin
│       │   └── archive.zip
│       └── configs/
│           └── test_config.toml
│
├── scripts/                           # Development and build scripts
│   ├── setup_dev.sh                   # Development environment setup
│   ├── run_tests.sh                   # Test runner script
│   ├── build_package.sh               # Package building
│   ├── release.sh                     # Release automation
│   └── generate_docs.sh               # Documentation generation
│
├── examples/                          # Example plugins and configurations
│   ├── plugins/
│   │   ├── image_viewer.py            # Example image viewer plugin
│   │   ├── ftp_upload.py              # Example FTP upload plugin
│   │   └── custom_theme.py            # Example custom theme
│   │
│   └── configs/
│       ├── poweruser_config.toml      # Advanced configuration example
│       └── minimal_config.toml        # Minimal configuration example
│
├── .gitignore                         # Git ignore patterns
├── .editorconfig                      # Editor configuration
├── .pre-commit-config.yaml            # Pre-commit hooks configuration
│
├── pyproject.toml                     # Project metadata and dependencies
├── setup.py                           # Setup script (for compatibility)
├── requirements.txt                   # Runtime dependencies
├── requirements-dev.txt               # Development dependencies
│
├── README.md                          # Project overview and quick start
├── CHANGELOG.md                       # Version history
├── LICENSE                            # License (MIT)
├── CONTRIBUTING.md                    # Contribution guidelines
└── CODE_OF_CONDUCT.md                 # Code of conduct
```

---

## Core Package Structure

### `src/modern_commander/`

Main application package containing all source code.

#### `app.py` - Main Application
```python
"""
Main application entry point and dependency container.

Key Classes:
- ModernCommanderApp: Main Textual application
- DependencyContainer: Dependency injection container
"""
```

#### `config.py` - Configuration Management
```python
"""
Configuration loading and management.

Key Classes:
- Configuration: Application configuration
- ConfigLoader: Multi-source configuration loader

Features:
- TOML configuration files
- Environment variable overrides
- Command-line argument support
- Configuration validation
"""
```

#### `constants.py` - Application Constants
```python
"""
Application-wide constants and default values.

Constants:
- APP_NAME = "Modern Commander"
- APP_VERSION = "1.0.0"
- DEFAULT_CONFIG_PATH
- DEFAULT_KEYBINDINGS
"""
```

---

## Component Modules

### `core/` - Core Domain

**Purpose**: Domain models, interfaces, and core business entities.

#### `interfaces.py`
```python
"""
Abstract interfaces for dependency injection.

Interfaces:
- FileSystemInterface: Filesystem operations
- EventBusInterface: Event messaging
- ConfigInterface: Configuration access
- CacheInterface: Caching operations
"""
```

#### `models.py`
```python
"""
Data models and value objects.

Models:
- FileEntry: File/directory information
- OperationResult: Operation outcome
- SearchResult: Search match result
- DriveInfo: Drive/volume information
- DiskUsage: Disk space information
- CopyOptions: Copy operation options
"""
```

#### `events.py`
```python
"""
Application-wide events.

Events:
- PanelNavigationEvent: Panel navigation
- FileSelectionEvent: File selection
- OperationStartedEvent: Operation start
- OperationProgressEvent: Progress update
- OperationCompletedEvent: Operation completion
- ThemeChangedEvent: Theme change
"""
```

#### `exceptions.py`
```python
"""
Custom exception hierarchy.

Exceptions:
- ModernCommanderError: Base exception
- FileSystemError: Filesystem errors
- OperationError: Operation failures
- ConfigurationError: Config errors
- PluginError: Plugin errors
- SecurityError: Security violations
"""
```

---

### `components/` - UI Components

**Purpose**: Textual UI widgets and screens.

#### `file_panel.py`
```python
"""
Dual-panel file browser component.

Classes:
- FilPanel: Main panel widget
- PanelState: Panel state management

Features:
- Directory navigation
- File selection
- Sorting and filtering
- Reactive updates
"""
```

#### `command_bar.py`
```python
"""
F-key command bar.

Classes:
- CommandBar: Command display and execution

Features:
- Dynamic command labels
- Context-aware commands
- Visual feedback
"""
```

#### `dialog_system.py`
```python
"""
Modal dialog management.

Classes:
- DialogSystem: Dialog coordinator
- ConfirmDialog: Yes/No dialogs
- PromptDialog: Input dialogs
- ProgressDialog: Progress display

Features:
- Async dialog handling
- Input validation
- Cancellation support
"""
```

#### `widgets/file_list.py`
```python
"""
File list widget with virtual scrolling.

Classes:
- FileList: Scrollable file list
- FileListItem: Individual file entry

Features:
- Virtual scrolling for performance
- Multi-selection support
- Keyboard navigation
- Custom rendering
"""
```

---

### `operations/` - Business Logic

**Purpose**: File operations and business logic services.

#### `file_operations.py`
```python
"""
File system operations service.

Classes:
- FileOperations: Operation executor

Methods:
- copy_files(): Copy files/directories
- move_files(): Move files/directories
- delete_files(): Delete files/directories
- create_directory(): Create directory
- rename(): Rename file/directory

Features:
- Async operations
- Progress tracking
- Error recovery
- Conflict resolution
"""
```

#### `search_engine.py`
```python
"""
File search functionality.

Classes:
- SearchEngine: Search coordinator

Methods:
- search_by_name(): Name pattern search
- search_by_content(): Content search
- search_by_size(): Size range search
- search_by_date(): Date range search

Features:
- Async iteration
- Multiple search types
- Cancellation support
- Result streaming
"""
```

#### `archive_handler.py`
```python
"""
Archive file management.

Classes:
- ArchiveHandler: Archive operations

Methods:
- create_archive(): Create archive
- extract_archive(): Extract contents
- list_archive(): List contents
- is_archive(): Check if archive

Supported Formats:
- ZIP (read/write)
- TAR (read/write)
- TAR.GZ (read/write)
- 7Z (read, optional)
"""
```

---

### `handlers/` - Event Handlers

**Purpose**: Input and event handling coordination.

#### `keyboard_handler.py`
```python
"""
Keyboard input coordination.

Classes:
- KeyboardHandler: Input coordinator
- KeyBinding: Key binding definition

Features:
- Priority-based handling
- Context-aware routing
- Dynamic bindings
- Conflict detection
"""
```

#### `action_handler.py`
```python
"""
Action dispatching and execution.

Classes:
- ActionHandler: Action executor
- Action: Action definition

Features:
- Command validation
- Async execution
- Error handling
"""
```

---

### `platform/` - Platform Abstraction

**Purpose**: Cross-platform filesystem and OS integration.

#### `filesystem.py`
```python
"""
Filesystem adapter factory.

Classes:
- FileSystemAdapter: Factory class

Methods:
- create(): Create platform-specific filesystem

Features:
- Automatic platform detection
- Factory pattern
- Interface implementation
"""
```

#### `platform_specific/windows.py`
```python
"""
Windows-specific filesystem implementation.

Classes:
- WindowsFileSystem: Windows adapter

Features:
- Drive letter support
- UNC path handling
- Long path support (\\?\)
- Windows file attributes
"""
```

#### `platform_specific/linux.py`
```python
"""
Linux-specific filesystem implementation.

Classes:
- LinuxFileSystem: Linux adapter

Features:
- Mount point detection
- Unix permissions
- Symlink handling
- Extended attributes
"""
```

#### `platform_specific/macos.py`
```python
"""
macOS-specific filesystem implementation.

Classes:
- MacOSFileSystem: macOS adapter

Features:
- Volume handling
- Application bundle support
- .DS_Store filtering
- macOS metadata
"""
```

---

### `utils/` - Utilities

**Purpose**: Shared helper functions and utilities.

#### `formatting.py`
```python
"""
Display formatting utilities.

Functions:
- format_size(bytes: int) -> str
  # "1.5 MB", "234 KB"

- format_date(dt: datetime) -> str
  # "2025-10-05 14:30"

- format_permissions(mode: int) -> str
  # "rwxr-xr-x"

- format_duration(seconds: float) -> str
  # "2m 34s"
"""
```

#### `validators.py`
```python
"""
Input validation utilities.

Classes:
- PathValidator: Path validation

Functions:
- is_safe_path(path: Path, base: Path) -> bool
- sanitize_filename(name: str) -> str
- validate_archive_path(path: Path) -> bool
"""
```

#### `async_utils.py`
```python
"""
Async helper utilities.

Functions:
- debounce(wait: float): Debounce decorator
- async_batch(items, size): Batch processing
- AsyncQueue: Thread-safe async queue

Utilities:
- Async context managers
- Async iteration helpers
"""
```

---

## Testing Structure

### `tests/unit/`

Unit tests for individual components.

**Coverage Target**: >90% for business logic

**Example Structure**:
```python
# tests/unit/test_file_operations.py

import pytest
from modern_commander.operations.file_operations import FileOperations

@pytest.fixture
def file_ops(mock_filesystem):
    return FileOperations(
        file_system=mock_filesystem,
        event_bus=Mock(),
    )

@pytest.mark.asyncio
async def test_copy_single_file(file_ops, tmp_path):
    """Test basic file copy operation"""
    # Test implementation
```

### `tests/integration/`

Integration tests for component interaction.

**Coverage Target**: Key user workflows

**Example Structure**:
```python
# tests/integration/test_file_panel_integration.py

@pytest.mark.asyncio
async def test_panel_navigation_and_selection(app):
    """Test navigation and file selection workflow"""
    # Test implementation
```

### `tests/e2e/`

End-to-end tests for complete workflows.

**Coverage Target**: Critical user paths

**Example Structure**:
```python
# tests/e2e/test_file_management.py

@pytest.mark.asyncio
async def test_complete_copy_workflow(tmp_path):
    """Test complete file copy workflow from user perspective"""
    # Test implementation
```

---

## Configuration Files

### `pyproject.toml`

**Purpose**: Project metadata, dependencies, and tool configuration

```toml
[project]
name = "modern-commander"
version = "1.0.0"
description = "A cross-platform Norton Commander-like file manager"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}

dependencies = [
    "textual>=0.40.0",
    "aiofiles>=23.0.0",
    "rich>=13.0.0",
    "tomli>=2.0.0; python_version < '3.11'",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
    "pre-commit>=3.0.0",
]

archive = [
    "py7zr>=0.20.0",
]

[project.scripts]
mc = "modern_commander.app:main"
modern-commander = "modern_commander.app:main"

[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
asyncio_mode = "auto"

[tool.black]
line-length = 88
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.ruff]
line-length = 88
target-version = "py311"
```

### `config/default_config.toml`

**Purpose**: Default application configuration

```toml
[general]
startup_directory = "~"
show_hidden_files = false
confirm_deletions = true
confirm_overwrites = true
save_session_state = true

[appearance]
theme = "classic"
show_icons = true
date_format = "%Y-%m-%d %H:%M"
size_format = "binary"  # binary (KiB) or decimal (KB)
show_breadcrumb = true

[panels]
sync_navigation = false
show_preview = false
sort_by = "name"  # name, size, date, extension
sort_order = "ascending"
panel_ratio = 0.5  # 50/50 split

[keybindings]
# Norton Commander compatible defaults
help = "F1"
menu = "F2"
view = "F3"
edit = "F4"
copy = "F5"
move = "F6"
mkdir = "F7"
delete = "F8"
config = "F9"
quit = "F10"

# Additional shortcuts
switch_panel = "Tab"
refresh = "Ctrl+R"
toggle_panels = "Ctrl+O"
search = "Alt+F7"
quick_search = "/"

[file_operations]
copy_buffer_size = 65536  # 64KB
verify_checksums = false
preserve_timestamps = true
follow_symlinks = false
max_concurrent_operations = 10

[search]
max_results = 1000
search_timeout_seconds = 30
case_sensitive = false
include_hidden = false

[archive]
default_format = "zip"
compression_level = "normal"  # none, fast, normal, best
extract_to_subfolder = true

[plugins]
enabled = true
plugin_directory = "~/.config/modern-commander/plugins"
auto_load = true
```

---

## Development Files

### `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Project specific
*.log
config/user_config.toml
.modern-commander/
```

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.284
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

---

## Documentation Files

### `README.md` Structure

```markdown
# Modern Commander

A modern, cross-platform Norton Commander-like file manager built with Python and Textual.

## Features
- Dual-panel interface
- Cross-platform (Linux, Windows, macOS)
- Keyboard-driven navigation
- Archive support (ZIP, TAR, 7Z)
- File search
- Built-in viewer and editor
- Plugin system

## Installation
```bash
pip install modern-commander
```

## Quick Start
```bash
mc  # or modern-commander
```

## Documentation
- [User Guide](docs/user-guide.md)
- [Developer Guide](docs/developer-guide.md)
- [Architecture](docs/architecture.md)

## License
MIT
```

### `CONTRIBUTING.md` Structure

```markdown
# Contributing to Modern Commander

## Development Setup
1. Clone repository
2. Install dependencies: `pip install -e ".[dev]"`
3. Install pre-commit hooks: `pre-commit install`

## Running Tests
```bash
pytest
```

## Code Style
- Black for formatting
- Ruff for linting
- Type hints required

## Pull Request Process
1. Fork the repository
2. Create feature branch
3. Write tests
4. Ensure all tests pass
5. Submit PR
```

---

**End of Project Structure Documentation**

*Version 1.0.0 - 2025-10-05*
