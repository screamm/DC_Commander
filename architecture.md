# Modern Commander - System Architecture Documentation

**Version**: 1.0.0
**Date**: 2025-10-05
**Framework**: Python 3.11+ with Textual TUI
**Target Platforms**: Linux, Windows 11, macOS

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architectural Overview](#architectural-overview)
3. [System Design Principles](#system-design-principles)
4. [Component Architecture](#component-architecture)
5. [File Structure](#file-structure)
6. [Component Specifications](#component-specifications)
7. [Dependency Graph](#dependency-graph)
8. [Data Flow Architecture](#data-flow-architecture)
9. [Cross-Platform Considerations](#cross-platform-considerations)
10. [Security Architecture](#security-architecture)
11. [Performance Considerations](#performance-considerations)
12. [Extension Points](#extension-points)
13. [Testing Strategy](#testing-strategy)
14. [Deployment Architecture](#deployment-architecture)

---

## Executive Summary

Modern Commander is a cross-platform terminal user interface (TUI) file manager inspired by Norton Commander. Built with Python and the Textual framework, it provides a dual-panel interface for efficient file management operations with keyboard-driven navigation.

### Key Architectural Goals

- **Modularity**: Clear component boundaries with single responsibilities
- **Cross-Platform**: Native behavior on Linux, Windows 11, and macOS
- **Extensibility**: Plugin architecture for custom operations
- **Performance**: Async operations for large directory operations
- **Testability**: Dependency injection for comprehensive testing
- **Maintainability**: Clean architecture with documented design decisions

---

## Architectural Overview

### High-Level Architecture Pattern

Modern Commander follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────┐
│          Presentation Layer (Textual UI)            │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │  FilPanel    │  │ CommandBar   │  │  Dialogs  │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│           Application Layer (Business Logic)         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │FileOperations│  │SearchEngine  │  │FileViewer │ │
│  │              │  │              │  │           │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│  ┌──────────────┐  ┌──────────────┐                │
│  │ArchiveHandler│  │KeyboardHandler│               │
│  └──────────────┘  └──────────────┘                │
└─────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│         Infrastructure Layer (OS/Platform)           │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │SystemInfo    │  │FileSystem    │  │ Platform  │ │
│  │              │  │  Adapter     │  │  Utils    │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
```

### Architectural Style: Clean Architecture Principles

1. **Dependency Rule**: Dependencies point inward toward business logic
2. **Interface Segregation**: Components depend on abstractions, not concrete implementations
3. **Single Responsibility**: Each component has one reason to change
4. **Open/Closed**: Open for extension through plugin system, closed for modification

---

## System Design Principles

### 1. Separation of Concerns

**Rationale**: Each component handles one aspect of functionality, making the system maintainable and testable.

- **UI Components**: Handle rendering and user interaction only
- **Business Logic**: File operations, search, archive handling
- **Infrastructure**: Platform-specific filesystem access and system integration

### 2. Dependency Injection

**Rationale**: Enables testing with mock implementations and allows runtime configuration.

```python
class FilPanel:
    def __init__(
        self,
        file_operations: FileOperationsInterface,
        file_system: FileSystemInterface
    ):
        self.file_ops = file_operations
        self.fs = file_system
```

### 3. Event-Driven Architecture

**Rationale**: Loose coupling between components through Textual's message system.

Components communicate through:
- **Messages**: Custom Textual messages for application events
- **Reactive**: Textual's reactive properties for state synchronization
- **Callbacks**: Observer pattern for notifications

### 4. Async-First Design

**Rationale**: Non-blocking operations for file I/O and long-running tasks.

```python
async def copy_files(self, sources: List[Path], destination: Path) -> None:
    """Async file copying with progress updates"""
    for source in sources:
        await self._copy_single_file(source, destination)
        self.emit_progress(...)
```

### 5. Immutable Configuration

**Rationale**: Thread-safe configuration with clear change points.

Configuration loaded at startup, changes require restart for consistency.

---

## Component Architecture

### Component Relationship Diagram

```
┌──────────────────────────────────────────────────────────┐
│                     ModernCommanderApp                    │
│                    (Main Textual App)                     │
└────────────┬─────────────────────────────────────────────┘
             │
     ┌───────┴────────┬─────────────┬──────────────┐
     ▼                ▼             ▼              ▼
┌─────────┐    ┌──────────┐  ┌──────────┐   ┌──────────┐
│FilPanel │    │FilPanel  │  │CommandBar│   │StatusBar │
│ (Left)  │    │ (Right)  │  │          │   │          │
└────┬────┘    └────┬─────┘  └────┬─────┘   └──────────┘
     │              │             │
     └──────┬───────┴─────────────┘
            │
            ▼
     ┌─────────────────┐
     │KeyboardHandler  │
     │  (Coordinator)  │
     └────────┬────────┘
              │
    ┌─────────┼──────────┬──────────┬─────────────┐
    ▼         ▼          ▼          ▼             ▼
┌────────┐ ┌─────┐ ┌─────────┐ ┌────────┐ ┌──────────┐
│FileOps │ │Search│ │FileView│ │Archive │ │Dialog    │
│        │ │Engine│ │/Editor │ │Handler │ │System    │
└────┬───┘ └──────┘ └─────────┘ └────────┘ └──────────┘
     │
     ▼
┌──────────────┐
│FileSystem    │
│Adapter       │
└──────────────┘
```

### Component Communication Patterns

1. **Parent-Child (Composition)**: ModernCommanderApp → FilPanel
2. **Sibling Communication (Events)**: FilPanel ↔ FilPanel (via messages)
3. **Service Access (Dependency Injection)**: FilPanel → FileOperations
4. **Platform Abstraction (Adapter)**: FileOperations → FileSystemAdapter

---

## File Structure

```
modern-commander/
│
├── src/
│   └── modern_commander/
│       │
│       ├── __init__.py                    # Package initialization
│       ├── app.py                         # Main application entry point
│       ├── config.py                      # Configuration management
│       │
│       ├── core/                          # Core business logic
│       │   ├── __init__.py
│       │   ├── interfaces.py              # Abstract interfaces/protocols
│       │   ├── models.py                  # Data models (FileEntry, etc.)
│       │   ├── events.py                  # Application-wide events
│       │   └── exceptions.py              # Custom exceptions
│       │
│       ├── components/                    # UI Components (Presentation Layer)
│       │   ├── __init__.py
│       │   ├── file_panel.py              # Dual-panel file browser
│       │   ├── command_bar.py             # F-key command bar
│       │   ├── status_bar.py              # Status information display
│       │   ├── dialog_system.py           # Modal dialogs
│       │   └── widgets/                   # Reusable UI widgets
│       │       ├── __init__.py
│       │       ├── file_list.py           # File list widget
│       │       ├── breadcrumb.py          # Path breadcrumb navigation
│       │       └── progress_dialog.py     # Progress indicator
│       │
│       ├── operations/                    # Business Logic Layer
│       │   ├── __init__.py
│       │   ├── file_operations.py         # Copy/Move/Delete/Create operations
│       │   ├── search_engine.py           # File search functionality
│       │   ├── archive_handler.py         # ZIP/Archive management
│       │   ├── file_viewer.py             # File viewing (F3)
│       │   ├── file_editor.py             # Text editing (F4)
│       │   └── clipboard.py               # Clipboard operations
│       │
│       ├── handlers/                      # Event and Input Handlers
│       │   ├── __init__.py
│       │   ├── keyboard_handler.py        # Keyboard input coordination
│       │   ├── action_handler.py          # Action dispatching
│       │   └── hotkey_manager.py          # Hotkey registration/management
│       │
│       ├── platform/                      # Infrastructure Layer
│       │   ├── __init__.py
│       │   ├── filesystem.py              # Cross-platform filesystem adapter
│       │   ├── system_info.py             # System information provider
│       │   ├── process_utils.py           # Process execution utilities
│       │   └── platform_specific/
│       │       ├── __init__.py
│       │       ├── linux.py               # Linux-specific implementations
│       │       ├── windows.py             # Windows-specific implementations
│       │       └── macos.py               # macOS-specific implementations
│       │
│       ├── utils/                         # Shared Utilities
│       │   ├── __init__.py
│       │   ├── formatting.py              # Size/date formatting
│       │   ├── validators.py              # Input validation
│       │   └── async_utils.py             # Async helpers
│       │
│       └── themes/                        # Visual Theming
│           ├── __init__.py
│           ├── classic.tcss               # Norton Commander classic theme
│           ├── modern.tcss                # Modern dark theme
│           └── theme_manager.py           # Theme switching logic
│
├── tests/                                 # Test Suite
│   ├── __init__.py
│   ├── conftest.py                        # Pytest configuration
│   ├── unit/                              # Unit tests
│   │   ├── test_file_operations.py
│   │   ├── test_search_engine.py
│   │   └── ...
│   ├── integration/                       # Integration tests
│   │   ├── test_file_panel_integration.py
│   │   └── ...
│   └── e2e/                               # End-to-end tests
│       └── test_basic_workflow.py
│
├── docs/                                  # Documentation
│   ├── architecture.md                    # This file
│   ├── user_guide.md                      # User documentation
│   ├── developer_guide.md                 # Developer documentation
│   └── api_reference.md                   # API documentation
│
├── config/                                # Configuration Files
│   ├── default_config.toml                # Default configuration
│   └── keybindings.toml                   # Keyboard shortcuts
│
├── .github/                               # GitHub Actions
│   └── workflows/
│       ├── ci.yml                         # Continuous Integration
│       └── release.yml                    # Release automation
│
├── pyproject.toml                         # Project metadata & dependencies
├── README.md                              # Project overview
├── LICENSE                                # License information
└── .gitignore                             # Git ignore patterns
```

### File Structure Design Decisions

**Decision 1: Layered Package Structure**
**Rationale**: Clear separation between presentation (components), business logic (operations), and infrastructure (platform) enables independent testing and modification.

**Decision 2: Platform-Specific Module**
**Rationale**: Isolates OS-specific code in dedicated modules, making cross-platform support explicit and testable.

**Decision 3: Separate Handlers Package**
**Rationale**: Input handling is complex enough to warrant dedicated coordination layer between UI and business logic.

**Decision 4: Theme System with TCSS**
**Rationale**: Textual's CSS-like theming allows visual customization without code changes.

---

## Component Specifications

### 1. FilPanel (File Panel Component)

**Responsibility**: Display and manage file/directory listing in one panel

**Location**: `src/modern_commander/components/file_panel.py`

**Interface**:
```python
class FilPanel(Container):
    """Dual-panel file browser component"""

    # Reactive properties
    current_path: Reactive[Path] = Reactive(Path.home())
    selected_files: Reactive[List[FileEntry]] = Reactive([])
    is_active: Reactive[bool] = Reactive(False)

    # Dependencies (injected)
    def __init__(
        self,
        file_system: FileSystemInterface,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self.fs = file_system

    # Public methods
    async def navigate_to(self, path: Path) -> None:
        """Navigate to specified directory"""

    async def refresh(self) -> None:
        """Reload current directory contents"""

    def get_selected_entries(self) -> List[FileEntry]:
        """Get currently selected file entries"""

    def select_entry(self, entry: FileEntry) -> None:
        """Select/deselect file entry"""

    # Event handlers
    def on_key(self, event: Key) -> None:
        """Handle keyboard input"""

    def on_mount(self) -> None:
        """Initialize panel on mount"""
```

**Dependencies**:
- `FileSystemInterface`: Filesystem abstraction
- `FileList` widget: Displays file entries
- `Breadcrumb` widget: Path navigation

**Composition**:
```
FilPanel
├── Breadcrumb (path display)
├── FileList (file entries)
└── StatusLine (selection info)
```

**State Management**:
- `current_path`: Currently displayed directory
- `selected_files`: Multi-selection state
- `is_active`: Focus state (left vs right panel)

---

### 2. FileOperations (File Operations Service)

**Responsibility**: Execute file system operations with error handling and progress reporting

**Location**: `src/modern_commander/operations/file_operations.py`

**Interface**:
```python
class FileOperations:
    """Service for file system operations"""

    def __init__(
        self,
        file_system: FileSystemInterface,
        event_bus: EventBusInterface,
    ):
        self.fs = file_system
        self.events = event_bus

    async def copy_files(
        self,
        sources: List[Path],
        destination: Path,
        options: CopyOptions = CopyOptions(),
    ) -> OperationResult:
        """Copy files/directories with progress tracking"""

    async def move_files(
        self,
        sources: List[Path],
        destination: Path,
        options: MoveOptions = MoveOptions(),
    ) -> OperationResult:
        """Move files/directories"""

    async def delete_files(
        self,
        targets: List[Path],
        options: DeleteOptions = DeleteOptions(),
    ) -> OperationResult:
        """Delete files/directories"""

    async def create_directory(
        self,
        path: Path,
        parents: bool = True,
    ) -> OperationResult:
        """Create new directory"""

    async def rename(
        self,
        old_path: Path,
        new_path: Path,
    ) -> OperationResult:
        """Rename file or directory"""
```

**Key Features**:
- **Async operations**: Non-blocking I/O for large operations
- **Progress events**: Emits progress updates via event bus
- **Error recovery**: Graceful handling of permission errors, conflicts
- **Atomic operations**: Rollback capability for failed operations
- **Conflict resolution**: User prompts for overwrite/skip/rename

**Design Pattern**: **Command Pattern** with async execution

---

### 3. FileViewer (File Viewing Component)

**Responsibility**: Display file contents in read-only mode (F3 functionality)

**Location**: `src/modern_commander/operations/file_viewer.py`

**Interface**:
```python
class FileViewer(ModalScreen):
    """File viewing modal screen (F3)"""

    def __init__(
        self,
        file_path: Path,
        encoding: str = "utf-8",
    ):
        super().__init__()
        self.file_path = file_path
        self.encoding = encoding

    async def on_mount(self) -> None:
        """Load and display file contents"""

    def on_key(self, event: Key) -> None:
        """Handle navigation keys (arrows, page up/down, etc)"""

    async def search(self, query: str) -> None:
        """Search within file contents"""
```

**Features**:
- **Large file support**: Chunked loading for files >100MB
- **Syntax highlighting**: Detect file type and apply highlighting
- **Search**: In-file text search with navigation
- **Encoding detection**: Auto-detect or manual encoding selection
- **Binary file handling**: Hex view for binary files

**Plugin Points**: Custom viewers for specific file types (images, PDFs)

---

### 4. FileEditor (Text Editor Component)

**Responsibility**: Edit text files (F4 functionality)

**Location**: `src/modern_commander/operations/file_editor.py`

**Interface**:
```python
class FileEditor(ModalScreen):
    """Text file editor modal screen (F4)"""

    def __init__(
        self,
        file_path: Path | None = None,
        encoding: str = "utf-8",
    ):
        super().__init__()
        self.file_path = file_path
        self.encoding = encoding
        self.modified = False

    async def save(self) -> bool:
        """Save file contents"""

    async def save_as(self, new_path: Path) -> bool:
        """Save file to new location"""

    def on_key(self, event: Key) -> None:
        """Handle editing keys"""
```

**Features**:
- **Basic editing**: Insert, delete, undo/redo
- **Syntax highlighting**: Language-aware highlighting
- **Line numbers**: Optional line number display
- **Auto-save**: Optional auto-save on interval
- **Dirty flag**: Track unsaved changes
- **Encoding**: Support multiple text encodings

**Design Decision**: Use Textual's `TextArea` widget for core editing functionality

---

### 5. DialogSystem (Modal Dialog Manager)

**Responsibility**: Display modal dialogs for confirmations, prompts, and messages

**Location**: `src/modern_commander/components/dialog_system.py`

**Interface**:
```python
class DialogSystem:
    """Manager for modal dialogs"""

    async def confirm(
        self,
        message: str,
        title: str = "Confirm",
        default: bool = False,
    ) -> bool:
        """Show yes/no confirmation dialog"""

    async def prompt(
        self,
        message: str,
        title: str = "Input",
        default: str = "",
        validator: Callable[[str], bool] | None = None,
    ) -> str | None:
        """Show input prompt dialog"""

    async def alert(
        self,
        message: str,
        title: str = "Alert",
        severity: Literal["info", "warning", "error"] = "info",
    ) -> None:
        """Show alert message"""

    async def progress(
        self,
        title: str,
        total: int,
    ) -> ProgressDialog:
        """Show progress dialog for long operations"""

    async def choice(
        self,
        message: str,
        choices: List[str],
        title: str = "Select",
    ) -> str | None:
        """Show multiple choice dialog"""
```

**Dialog Types**:
- **Confirmation**: Yes/No/Cancel decisions
- **Prompt**: Text input with validation
- **Alert**: Information/warning/error messages
- **Progress**: Long-running operation progress
- **Choice**: Multiple option selection
- **File conflict**: Overwrite/Skip/Rename options

---

### 6. SearchEngine (File Search Component)

**Responsibility**: Search for files by name, content, or attributes

**Location**: `src/modern_commander/operations/search_engine.py`

**Interface**:
```python
class SearchEngine:
    """File search functionality"""

    def __init__(
        self,
        file_system: FileSystemInterface,
    ):
        self.fs = file_system

    async def search_by_name(
        self,
        root: Path,
        pattern: str,
        recursive: bool = True,
        case_sensitive: bool = False,
    ) -> AsyncIterator[FileEntry]:
        """Search files by name pattern"""

    async def search_by_content(
        self,
        root: Path,
        query: str,
        file_pattern: str = "*",
        case_sensitive: bool = False,
    ) -> AsyncIterator[SearchResult]:
        """Search file contents (grep-like)"""

    async def search_by_size(
        self,
        root: Path,
        min_size: int | None = None,
        max_size: int | None = None,
    ) -> AsyncIterator[FileEntry]:
        """Search files by size range"""

    async def search_by_date(
        self,
        root: Path,
        modified_after: datetime | None = None,
        modified_before: datetime | None = None,
    ) -> AsyncIterator[FileEntry]:
        """Search files by modification date"""
```

**Features**:
- **Pattern matching**: Glob patterns and regex support
- **Content search**: Full-text search with context
- **Attribute filtering**: Size, date, permissions
- **Async streaming**: Yield results as found
- **Cancellation**: Support for user cancellation

**Performance**: Index-based search for large directories (optional feature)

---

### 7. ArchiveHandler (Archive Management)

**Responsibility**: Create, extract, and browse archive files (ZIP, TAR, etc.)

**Location**: `src/modern_commander/operations/archive_handler.py`

**Interface**:
```python
class ArchiveHandler:
    """Archive file management"""

    async def create_archive(
        self,
        sources: List[Path],
        archive_path: Path,
        format: ArchiveFormat = ArchiveFormat.ZIP,
        compression: CompressionLevel = CompressionLevel.NORMAL,
    ) -> OperationResult:
        """Create archive from files"""

    async def extract_archive(
        self,
        archive_path: Path,
        destination: Path,
        selected_files: List[str] | None = None,
    ) -> OperationResult:
        """Extract archive contents"""

    async def list_archive(
        self,
        archive_path: Path,
    ) -> List[ArchiveEntry]:
        """List archive contents"""

    def is_archive(self, path: Path) -> bool:
        """Check if file is supported archive"""

    def get_supported_formats(self) -> List[ArchiveFormat]:
        """Get list of supported archive formats"""
```

**Supported Formats**:
- **ZIP**: Read/write support via `zipfile`
- **TAR**: Read/write support via `tarfile` (.tar, .tar.gz, .tar.bz2)
- **7Z**: Read-only via `py7zr` (optional)
- **RAR**: Read-only via external tool (optional)

**Design Decision**: Virtual filesystem support - browse archives like directories

---

### 8. SystemInfo (System Information Provider)

**Responsibility**: Provide system and platform information

**Location**: `src/modern_commander/platform/system_info.py`

**Interface**:
```python
class SystemInfo:
    """System information provider"""

    @staticmethod
    def get_platform() -> PlatformType:
        """Get current platform (Linux/Windows/macOS)"""

    @staticmethod
    def get_drives() -> List[DriveInfo]:
        """Get available drives/mount points"""

    @staticmethod
    def get_disk_usage(path: Path) -> DiskUsage:
        """Get disk space information"""

    @staticmethod
    def get_memory_info() -> MemoryInfo:
        """Get system memory information"""

    @staticmethod
    def get_environment_variable(name: str) -> str | None:
        """Get environment variable value"""

    @staticmethod
    def get_user_home() -> Path:
        """Get user home directory"""

    @staticmethod
    def get_temp_dir() -> Path:
        """Get system temp directory"""
```

**Cross-Platform Handling**:
- **Windows**: Drive letters, UNC paths, registry access
- **Linux/macOS**: Mount points, symlinks, permissions
- **Common**: Home directory, temp directory, environment variables

---

### 9. CommandBar (Command Bar Component)

**Responsibility**: Display F-key shortcuts and execute commands

**Location**: `src/modern_commander/components/command_bar.py`

**Interface**:
```python
class CommandBar(Widget):
    """F-key command bar component"""

    def __init__(self):
        super().__init__()
        self.commands = self._default_commands()

    def set_commands(self, commands: Dict[str, Command]) -> None:
        """Update command mappings"""

    def get_command(self, key: str) -> Command | None:
        """Get command by key"""

    def _default_commands(self) -> Dict[str, Command]:
        """Norton Commander default commands"""
        return {
            "F1": Command("Help", self.show_help),
            "F2": Command("Menu", self.show_menu),
            "F3": Command("View", self.view_file),
            "F4": Command("Edit", self.edit_file),
            "F5": Command("Copy", self.copy_files),
            "F6": Command("Move", self.move_files),
            "F7": Command("MkDir", self.create_directory),
            "F8": Command("Delete", self.delete_files),
            "F9": Command("Config", self.show_config),
            "F10": Command("Quit", self.quit_app),
        }
```

**Features**:
- **Dynamic updates**: Change command labels based on context
- **Visual feedback**: Highlight active commands
- **Keyboard shortcuts**: Direct F-key handling
- **Customization**: User-defined command mappings

---

### 10. KeyboardHandler (Keyboard Input Coordinator)

**Responsibility**: Centralized keyboard input handling and routing

**Location**: `src/modern_commander/handlers/keyboard_handler.py`

**Interface**:
```python
class KeyboardHandler:
    """Centralized keyboard input coordinator"""

    def __init__(self, app: ModernCommanderApp):
        self.app = app
        self.bindings: Dict[str, ActionHandler] = {}
        self._register_default_bindings()

    def register_binding(
        self,
        key: str,
        action: ActionHandler,
        description: str = "",
        priority: int = 0,
    ) -> None:
        """Register keyboard shortcut"""

    def handle_key(self, event: Key) -> bool:
        """Handle keyboard event, return True if handled"""

    def get_bindings(self) -> List[KeyBinding]:
        """Get all registered key bindings"""

    def _register_default_bindings(self) -> None:
        """Register Norton Commander compatible bindings"""
```

**Default Bindings** (Norton Commander compatible):
- **F1-F10**: Function key commands
- **Tab**: Switch between panels
- **Insert**: Select/deselect file
- **Ctrl+R**: Refresh panel
- **Ctrl+O**: Show/hide panels
- **Ctrl+U**: Swap panels
- **Alt+F7**: Search files
- **Ctrl+\\**: Quick directory change

**Design Pattern**: **Chain of Responsibility** for key handling priority

---

## Dependency Graph

### Component Dependencies

```
ModernCommanderApp
├── FilPanel (left)
│   ├── FileSystemInterface
│   ├── FileList widget
│   └── Breadcrumb widget
│
├── FilPanel (right)
│   ├── FileSystemInterface
│   ├── FileList widget
│   └── Breadcrumb widget
│
├── CommandBar
│   └── ActionHandler
│
├── KeyboardHandler
│   ├── FileOperations
│   ├── SearchEngine
│   ├── ArchiveHandler
│   ├── FileViewer
│   ├── FileEditor
│   └── DialogSystem
│
├── FileOperations
│   ├── FileSystemInterface
│   └── EventBusInterface
│
├── SearchEngine
│   └── FileSystemInterface
│
├── ArchiveHandler
│   └── FileSystemInterface
│
├── FileViewer
│   └── FileSystemInterface
│
├── FileEditor
│   └── FileSystemInterface
│
├── DialogSystem
│   └── (no dependencies)
│
└── StatusBar
    └── SystemInfo
```

### Dependency Injection Container

**Location**: `src/modern_commander/app.py`

```python
class DependencyContainer:
    """Simple dependency injection container"""

    def __init__(self):
        # Platform-specific implementations
        self.file_system = self._create_file_system()
        self.system_info = SystemInfo()

        # Event bus for component communication
        self.event_bus = EventBus()

        # Services
        self.file_operations = FileOperations(
            file_system=self.file_system,
            event_bus=self.event_bus,
        )
        self.search_engine = SearchEngine(
            file_system=self.file_system,
        )
        self.archive_handler = ArchiveHandler(
            file_system=self.file_system,
        )

    def _create_file_system(self) -> FileSystemInterface:
        """Create platform-specific filesystem adapter"""
        platform = SystemInfo.get_platform()
        if platform == PlatformType.WINDOWS:
            return WindowsFileSystem()
        elif platform == PlatformType.LINUX:
            return LinuxFileSystem()
        elif platform == PlatformType.MACOS:
            return MacOSFileSystem()
        else:
            return GenericFileSystem()
```

### Interface Definitions

**Location**: `src/modern_commander/core/interfaces.py`

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator, List

class FileSystemInterface(ABC):
    """Abstract interface for filesystem operations"""

    @abstractmethod
    async def list_directory(self, path: Path) -> List[FileEntry]:
        """List directory contents"""

    @abstractmethod
    async def get_file_info(self, path: Path) -> FileInfo:
        """Get file metadata"""

    @abstractmethod
    async def read_file(self, path: Path) -> bytes:
        """Read file contents"""

    @abstractmethod
    async def write_file(self, path: Path, content: bytes) -> None:
        """Write file contents"""

    @abstractmethod
    async def delete(self, path: Path) -> None:
        """Delete file or directory"""

    @abstractmethod
    async def copy(self, source: Path, destination: Path) -> None:
        """Copy file or directory"""

    @abstractmethod
    async def move(self, source: Path, destination: Path) -> None:
        """Move file or directory"""


class EventBusInterface(ABC):
    """Abstract interface for event messaging"""

    @abstractmethod
    def emit(self, event: Event) -> None:
        """Emit event to subscribers"""

    @abstractmethod
    def subscribe(
        self,
        event_type: type[Event],
        handler: Callable[[Event], None]
    ) -> None:
        """Subscribe to event type"""
```

---

## Data Flow Architecture

### File Operation Flow

```
User Action (F5 - Copy)
    │
    ▼
KeyboardHandler.handle_key()
    │
    ▼
FilPanel.get_selected_entries()
    │
    ▼
DialogSystem.confirm("Copy X files?")
    │
    ▼
FileOperations.copy_files()
    │
    ├─► EventBus.emit(CopyStartedEvent)
    │       │
    │       ▼
    │   ProgressDialog.show()
    │
    ├─► FileSystemInterface.copy() (per file)
    │       │
    │       ▼
    │   EventBus.emit(FileProgressEvent)
    │       │
    │       ▼
    │   ProgressDialog.update()
    │
    ▼
EventBus.emit(CopyCompletedEvent)
    │
    ▼
FilPanel.refresh()
    │
    ▼
StatusBar.update("X files copied")
```

### Search Flow

```
User Action (Alt+F7 - Search)
    │
    ▼
DialogSystem.prompt("Search for:")
    │
    ▼
SearchEngine.search_by_name()
    │
    ├─► AsyncIterator yields results
    │       │
    │       ▼
    │   SearchResultsDialog.add_result()
    │
    ▼
User selects result
    │
    ▼
FilPanel.navigate_to(result.parent)
    │
    ▼
FilPanel.select_entry(result)
```

### Panel Synchronization

```
FilPanel (Left) - User navigates to /home/user/docs
    │
    ▼
Emits: PanelNavigationEvent(panel="left", path="/home/user/docs")
    │
    ▼
StatusBar subscribes → Updates path display
    │
FilPanel (Right) subscribes → Can auto-sync if configured
```

---

## Cross-Platform Considerations

### Platform Abstraction Strategy

**Decision**: Use **Adapter Pattern** for platform-specific filesystem operations

### Windows-Specific Handling

**Location**: `src/modern_commander/platform/platform_specific/windows.py`

```python
class WindowsFileSystem(FileSystemInterface):
    """Windows-specific filesystem implementation"""

    async def list_directory(self, path: Path) -> List[FileEntry]:
        """Handle Windows-specific aspects:
        - Drive letters (C:, D:, etc.)
        - UNC paths (\\server\share)
        - Hidden/system file attributes
        - Case-insensitive paths
        """

    def get_drives(self) -> List[DriveInfo]:
        """Get Windows drive letters"""
        import string
        from ctypes import windll

        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(DriveInfo(
                    path=Path(f"{letter}:\\"),
                    label=self._get_drive_label(letter),
                ))
            bitmask >>= 1
        return drives
```

**Windows Challenges**:
- Long path support (>260 chars): Use `\\?\` prefix
- File locking: Handle `PermissionError` gracefully
- Path separators: Normalize with `Path`
- Registry access: For configuration storage (optional)

### Linux-Specific Handling

**Location**: `src/modern_commander/platform/platform_specific/linux.py`

```python
class LinuxFileSystem(FileSystemInterface):
    """Linux-specific filesystem implementation"""

    async def list_directory(self, path: Path) -> List[FileEntry]:
        """Handle Linux-specific aspects:
        - Symlinks and link targets
        - File permissions (rwxrwxrwx)
        - Hidden files (dot files)
        - Case-sensitive paths
        - Extended attributes
        """

    async def get_file_info(self, path: Path) -> FileInfo:
        """Include Unix permissions and ownership"""
        stat_info = await asyncio.to_thread(path.stat)
        return FileInfo(
            path=path,
            size=stat_info.st_size,
            modified=datetime.fromtimestamp(stat_info.st_mtime),
            permissions=self._format_permissions(stat_info.st_mode),
            owner=self._get_owner(stat_info.st_uid),
            group=self._get_group(stat_info.st_gid),
        )
```

**Linux Challenges**:
- Mount points: Detect with `/proc/mounts`
- Permissions: Handle `PermissionError` for system files
- Symlinks: Show link target, handle circular links
- Case sensitivity: Preserve exact case

### macOS-Specific Handling

**Location**: `src/modern_commander/platform/platform_specific/macos.py`

```python
class MacOSFileSystem(FileSystemInterface):
    """macOS-specific filesystem implementation"""

    async def list_directory(self, path: Path) -> List[FileEntry]:
        """Handle macOS-specific aspects:
        - .DS_Store files (hide by default)
        - Application bundles (.app as directories)
        - Resource forks (deprecated but may exist)
        - Case-insensitive but case-preserving HFS+
        """

    def get_volumes(self) -> List[VolumeInfo]:
        """Get mounted volumes from /Volumes"""
        volumes_path = Path("/Volumes")
        return [
            VolumeInfo(path=vol, label=vol.name)
            for vol in volumes_path.iterdir()
            if vol.is_dir()
        ]
```

**macOS Challenges**:
- Application bundles: Treat `.app` specially
- Spotlight metadata: Optional integration
- Trash location: `~/.Trash`
- iCloud Drive: Handle cloud-only files

### Common Cross-Platform Utilities

**Location**: `src/modern_commander/platform/filesystem.py`

```python
class FileSystemAdapter:
    """Factory for platform-specific filesystem"""

    @staticmethod
    def create() -> FileSystemInterface:
        """Create appropriate filesystem implementation"""
        platform = SystemInfo.get_platform()

        implementations = {
            PlatformType.WINDOWS: WindowsFileSystem,
            PlatformType.LINUX: LinuxFileSystem,
            PlatformType.MACOS: MacOSFileSystem,
        }

        impl_class = implementations.get(
            platform,
            GenericFileSystem  # Fallback
        )
        return impl_class()
```

---

## Security Architecture

### Threat Model

**Threats Considered**:
1. **Path Traversal**: Malicious paths escaping intended directories
2. **Symlink Attacks**: Symlinks pointing to sensitive system files
3. **Permission Escalation**: Operations on files requiring elevated permissions
4. **Resource Exhaustion**: Large file operations consuming system resources
5. **Archive Bombs**: Malicious archives with extreme compression ratios

### Security Measures

#### 1. Path Validation

**Location**: `src/modern_commander/utils/validators.py`

```python
class PathValidator:
    """Validate and sanitize file paths"""

    @staticmethod
    def is_safe_path(path: Path, base: Path) -> bool:
        """Ensure path doesn't escape base directory"""
        try:
            resolved = path.resolve()
            base_resolved = base.resolve()
            return resolved.is_relative_to(base_resolved)
        except (OSError, ValueError):
            return False

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove dangerous characters from filename"""
        # Remove null bytes, path separators, control chars
        dangerous_chars = '\0/\\:<>"|?*'
        sanitized = ''.join(
            c for c in filename
            if c not in dangerous_chars and ord(c) >= 32
        )
        # Prevent reserved names on Windows
        reserved = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT1'}
        if sanitized.upper() in reserved:
            sanitized = f"_{sanitized}"
        return sanitized
```

#### 2. Permission Handling

```python
class FileOperations:
    async def _check_permissions(self, path: Path, operation: str) -> bool:
        """Verify permissions before operations"""
        try:
            if operation == "read":
                return os.access(path, os.R_OK)
            elif operation == "write":
                return os.access(path, os.W_OK)
            elif operation == "execute":
                return os.access(path, os.X_OK)
            return False
        except OSError:
            return False
```

#### 3. Archive Bomb Protection

```python
class ArchiveHandler:
    MAX_EXTRACTION_RATIO = 100  # Max compression ratio
    MAX_EXTRACTION_SIZE = 10 * 1024 * 1024 * 1024  # 10GB

    async def _validate_archive(self, archive_path: Path) -> None:
        """Check for archive bombs"""
        compressed_size = archive_path.stat().st_size
        uncompressed_size = 0

        # Calculate total uncompressed size
        for entry in self.list_archive(archive_path):
            uncompressed_size += entry.size

        # Check compression ratio
        if uncompressed_size / compressed_size > self.MAX_EXTRACTION_RATIO:
            raise SecurityError("Suspicious compression ratio detected")

        # Check total size
        if uncompressed_size > self.MAX_EXTRACTION_SIZE:
            raise SecurityError("Archive too large to extract safely")
```

#### 4. Resource Limits

```python
class FileOperations:
    MAX_FILE_SIZE_MEMORY = 100 * 1024 * 1024  # 100MB

    async def read_file(self, path: Path) -> bytes:
        """Read file with size limit"""
        size = path.stat().st_size

        if size > self.MAX_FILE_SIZE_MEMORY:
            raise ValueError(f"File too large: {size} bytes")

        async with aiofiles.open(path, "rb") as f:
            return await f.read()
```

### Security Best Practices

1. **Principle of Least Privilege**: Never request elevated permissions unless absolutely necessary
2. **Input Validation**: Validate all user input, especially file paths
3. **Safe Defaults**: Secure settings by default (e.g., confirm destructive operations)
4. **Error Messages**: Don't leak sensitive path information in errors
5. **Audit Logging**: Log security-relevant operations (optional feature)

---

## Performance Considerations

### Performance Goals

- **Startup Time**: <500ms to interactive UI
- **Directory Listing**: <100ms for typical directories (<1000 files)
- **File Operations**: Progress feedback within 100ms
- **Search**: <1s for first results in typical directories
- **Memory**: <50MB baseline, scale with file operations

### Optimization Strategies

#### 1. Async I/O for Non-Blocking Operations

**Decision**: Use `asyncio` and `aiofiles` for all I/O operations

**Rationale**: Keeps UI responsive during long file operations

```python
import asyncio
import aiofiles

async def copy_file(source: Path, dest: Path) -> None:
    """Non-blocking file copy"""
    async with aiofiles.open(source, 'rb') as src:
        async with aiofiles.open(dest, 'wb') as dst:
            while chunk := await src.read(64 * 1024):  # 64KB chunks
                await dst.write(chunk)
                await asyncio.sleep(0)  # Yield to event loop
```

#### 2. Lazy Loading for Large Directories

**Decision**: Virtual scrolling with on-demand loading

**Rationale**: Instant display for directories with thousands of files

```python
class FileList(ListView):
    """File list with lazy loading"""

    CHUNK_SIZE = 100  # Load 100 entries at a time

    async def load_directory(self, path: Path) -> None:
        """Load directory in chunks"""
        entries = []
        async for entry in self.fs.list_directory(path):
            entries.append(entry)
            if len(entries) >= self.CHUNK_SIZE:
                self.add_entries(entries)
                entries = []
                await asyncio.sleep(0)  # Yield

        if entries:
            self.add_entries(entries)
```

#### 3. Caching for Repeated Operations

**Decision**: LRU cache for directory listings and file stats

**Rationale**: Avoid redundant filesystem calls

```python
from functools import lru_cache

class FileSystemCache:
    """Caching layer for filesystem operations"""

    def __init__(self, fs: FileSystemInterface):
        self.fs = fs
        self.cache = TTLCache(maxsize=1000, ttl=60)  # 1 minute TTL

    async def list_directory(self, path: Path) -> List[FileEntry]:
        """Cached directory listing"""
        cache_key = str(path)

        if cache_key in self.cache:
            return self.cache[cache_key]

        entries = await self.fs.list_directory(path)
        self.cache[cache_key] = entries
        return entries

    def invalidate(self, path: Path) -> None:
        """Invalidate cache for path"""
        self.cache.pop(str(path), None)
```

#### 4. Parallel File Operations

**Decision**: Concurrent file operations with `asyncio.gather`

**Rationale**: Maximize throughput for multi-file operations

```python
async def copy_files(
    self,
    sources: List[Path],
    destination: Path
) -> None:
    """Copy multiple files concurrently"""

    # Limit concurrency to avoid overwhelming system
    semaphore = asyncio.Semaphore(10)

    async def copy_with_semaphore(source: Path) -> None:
        async with semaphore:
            await self._copy_single_file(source, destination)

    await asyncio.gather(*[
        copy_with_semaphore(source)
        for source in sources
    ])
```

#### 5. Debouncing for User Input

**Decision**: Debounce rapid user input events

**Rationale**: Avoid excessive redraws and filesystem calls

```python
class FilPanel:
    DEBOUNCE_DELAY = 0.1  # 100ms

    def __init__(self):
        self._search_timer = None

    def on_key(self, event: Key) -> None:
        """Debounced search input"""
        if self._search_timer:
            self._search_timer.cancel()

        self._search_timer = self.set_timer(
            self.DEBOUNCE_DELAY,
            lambda: self._execute_search(event.character)
        )
```

### Performance Monitoring

**Location**: `src/modern_commander/utils/performance.py`

```python
import time
from contextlib import contextmanager

@contextmanager
def measure_time(operation: str):
    """Context manager for performance measurement"""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        if duration > 0.1:  # Log slow operations
            logger.debug(f"{operation} took {duration:.3f}s")
```

---

## Extension Points

### Plugin Architecture

**Goal**: Allow users to extend functionality without modifying core code

**Location**: `src/modern_commander/plugins/`

#### Plugin Interface

```python
from abc import ABC, abstractmethod

class PluginInterface(ABC):
    """Base interface for plugins"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""

    @abstractmethod
    async def initialize(self, app: ModernCommanderApp) -> None:
        """Initialize plugin"""

    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup on shutdown"""


class FileViewerPlugin(PluginInterface):
    """Plugin for custom file viewers"""

    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Check if plugin can handle file type"""

    @abstractmethod
    async def view_file(self, file_path: Path) -> Widget:
        """Return widget to view file"""


class FileOperationPlugin(PluginInterface):
    """Plugin for custom file operations"""

    @abstractmethod
    def get_commands(self) -> List[Command]:
        """Get plugin commands"""

    @abstractmethod
    async def execute(self, command: str, context: OperationContext) -> None:
        """Execute plugin command"""
```

#### Plugin Examples

**Image Viewer Plugin**:
```python
class ImageViewerPlugin(FileViewerPlugin):
    name = "Image Viewer"
    version = "1.0.0"

    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}

    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.SUPPORTED_FORMATS

    async def view_file(self, file_path: Path) -> Widget:
        # Use PIL/Pillow to render image in terminal
        from PIL import Image
        # Convert image to ASCII art or use terminal graphics protocol
        return ImageWidget(file_path)
```

**FTP Upload Plugin**:
```python
class FTPUploadPlugin(FileOperationPlugin):
    name = "FTP Upload"
    version = "1.0.0"

    def get_commands(self) -> List[Command]:
        return [
            Command(
                key="Alt+U",
                label="FTP Upload",
                handler=self.upload_to_ftp,
            )
        ]

    async def execute(self, command: str, context: OperationContext) -> None:
        if command == "ftp_upload":
            await self.upload_to_ftp(context.selected_files)
```

#### Plugin Loader

**Location**: `src/modern_commander/plugins/plugin_loader.py`

```python
class PluginLoader:
    """Load and manage plugins"""

    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir
        self.plugins: List[PluginInterface] = []

    async def load_plugins(self) -> None:
        """Discover and load plugins"""
        if not self.plugin_dir.exists():
            return

        for plugin_file in self.plugin_dir.glob("*.py"):
            try:
                plugin = await self._load_plugin(plugin_file)
                self.plugins.append(plugin)
                logger.info(f"Loaded plugin: {plugin.name} v{plugin.version}")
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_file}: {e}")

    async def _load_plugin(self, plugin_file: Path) -> PluginInterface:
        """Load single plugin file"""
        spec = importlib.util.spec_from_file_location(
            plugin_file.stem,
            plugin_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find plugin class
        for item in dir(module):
            obj = getattr(module, item)
            if (isinstance(obj, type) and
                issubclass(obj, PluginInterface) and
                obj != PluginInterface):
                return obj()

        raise ValueError(f"No plugin class found in {plugin_file}")
```

### Configuration Extension

**Goal**: User-customizable settings and themes

**Location**: `config/default_config.toml`

```toml
[general]
startup_directory = "~"
show_hidden_files = false
confirm_deletions = true
confirm_overwrites = true

[appearance]
theme = "classic"  # classic, modern, custom
show_icons = true
date_format = "%Y-%m-%d %H:%M"
size_format = "binary"  # binary (KiB) or decimal (KB)

[panels]
sync_navigation = false
show_preview = false
sort_by = "name"  # name, size, date, extension
sort_order = "ascending"

[keybindings]
# Custom keybindings override defaults
quick_search = "Ctrl+S"
bookmark_add = "Ctrl+D"
bookmark_goto = "Ctrl+B"

[file_operations]
copy_buffer_size = 65536  # 64KB
verify_checksums = false
preserve_timestamps = true

[search]
max_results = 1000
search_timeout_seconds = 30

[plugins]
enabled = true
plugin_directory = "~/.config/modern-commander/plugins"
```

---

## Testing Strategy

### Testing Pyramid

```
        ┌─────────────┐
        │   E2E (5%)  │  ← Full application workflows
        ├─────────────┤
        │Integration  │  ← Component interaction
        │    (25%)    │
        ├─────────────┤
        │   Unit      │  ← Individual functions/methods
        │   (70%)     │
        └─────────────┘
```

### Unit Testing

**Goal**: Test individual components in isolation

**Framework**: `pytest` with `pytest-asyncio`

**Location**: `tests/unit/`

**Example Test**:
```python
# tests/unit/test_file_operations.py

import pytest
from pathlib import Path
from modern_commander.operations.file_operations import FileOperations
from modern_commander.core.exceptions import OperationError

@pytest.fixture
def mock_filesystem(mocker):
    """Mock filesystem interface"""
    return mocker.Mock(spec=FileSystemInterface)

@pytest.fixture
def file_operations(mock_filesystem):
    """FileOperations instance with mocked dependencies"""
    event_bus = Mock(spec=EventBusInterface)
    return FileOperations(
        file_system=mock_filesystem,
        event_bus=event_bus,
    )

@pytest.mark.asyncio
async def test_copy_single_file(file_operations, mock_filesystem, tmp_path):
    """Test copying a single file"""
    source = tmp_path / "source.txt"
    destination = tmp_path / "dest.txt"

    # Setup mock
    mock_filesystem.copy = AsyncMock()

    # Execute
    result = await file_operations.copy_files(
        sources=[source],
        destination=destination.parent,
    )

    # Verify
    assert result.success
    mock_filesystem.copy.assert_called_once_with(source, destination)

@pytest.mark.asyncio
async def test_copy_with_permission_error(file_operations, mock_filesystem):
    """Test handling of permission errors during copy"""
    source = Path("/protected/file.txt")
    destination = Path("/dest/")

    # Setup mock to raise permission error
    mock_filesystem.copy = AsyncMock(
        side_effect=PermissionError("Access denied")
    )

    # Execute and verify exception
    with pytest.raises(OperationError, match="Access denied"):
        await file_operations.copy_files([source], destination)
```

### Integration Testing

**Goal**: Test component interactions

**Location**: `tests/integration/`

**Example Test**:
```python
# tests/integration/test_file_panel_integration.py

import pytest
from textual.pilot import Pilot
from modern_commander.app import ModernCommanderApp

@pytest.mark.asyncio
async def test_navigate_between_panels(tmp_path):
    """Test navigation between left and right panels"""
    app = ModernCommanderApp()

    async with app.run_test() as pilot:
        # Initial state
        left_panel = app.query_one("#left-panel")
        right_panel = app.query_one("#right-panel")

        assert left_panel.is_active
        assert not right_panel.is_active

        # Press Tab to switch panels
        await pilot.press("tab")

        # Verify panel switch
        assert not left_panel.is_active
        assert right_panel.is_active

@pytest.mark.asyncio
async def test_file_copy_operation(tmp_path):
    """Test complete file copy workflow"""
    # Create test files
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()
    dest_dir.mkdir()

    test_file = source_dir / "test.txt"
    test_file.write_text("test content")

    app = ModernCommanderApp()

    async with app.run_test() as pilot:
        # Navigate to source directory
        left_panel = app.query_one("#left-panel")
        await left_panel.navigate_to(source_dir)

        # Navigate right panel to destination
        right_panel = app.query_one("#right-panel")
        await right_panel.navigate_to(dest_dir)

        # Select file
        await pilot.press("insert")  # Select file

        # Trigger copy
        await pilot.press("f5")  # F5 = Copy

        # Confirm dialog
        await pilot.press("enter")

        # Wait for operation
        await pilot.pause(0.5)

        # Verify file copied
        copied_file = dest_dir / "test.txt"
        assert copied_file.exists()
        assert copied_file.read_text() == "test content"
```

### End-to-End Testing

**Goal**: Test complete user workflows

**Location**: `tests/e2e/`

**Example Test**:
```python
# tests/e2e/test_basic_workflow.py

import pytest
from pathlib import Path
from modern_commander.app import ModernCommanderApp

@pytest.mark.asyncio
async def test_complete_file_management_workflow(tmp_path):
    """Test complete user workflow: navigate, copy, edit, delete"""

    # Setup test environment
    work_dir = tmp_path / "workspace"
    work_dir.mkdir()

    test_file = work_dir / "document.txt"
    test_file.write_text("Original content")

    app = ModernCommanderApp()

    async with app.run_test() as pilot:
        # 1. Navigate to directory
        panel = app.query_one("#left-panel")
        await panel.navigate_to(work_dir)

        # 2. View file (F3)
        await pilot.press("down")  # Select file
        await pilot.press("f3")    # View

        viewer = app.query_one("FileViewer")
        assert "Original content" in viewer.content

        await pilot.press("escape")  # Close viewer

        # 3. Edit file (F4)
        await pilot.press("f4")  # Edit

        editor = app.query_one("FileEditor")
        await editor.append_text("\nNew line")
        await pilot.press("f2")  # Save

        # 4. Create directory (F7)
        await pilot.press("f7")
        await pilot.press(*"new_folder")
        await pilot.press("enter")

        # 5. Copy file to new directory
        await pilot.press("insert")  # Select file
        await pilot.press("down")    # Navigate to folder
        await pilot.press("enter")   # Enter folder
        await pilot.press("f5")      # Copy

        # Verify results
        new_folder = work_dir / "new_folder"
        assert new_folder.exists()
        assert new_folder.is_dir()

        copied_file = new_folder / "document.txt"
        assert copied_file.exists()
        assert "New line" in copied_file.read_text()
```

### Test Coverage Goals

- **Overall**: >80% code coverage
- **Core Business Logic**: >90% coverage
- **UI Components**: >70% coverage (UI testing is complex)
- **Platform-Specific**: 100% coverage with platform-specific test runners

### Continuous Integration

**GitHub Actions Workflow**: `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.11', '3.12']

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run unit tests
        run: pytest tests/unit --cov=modern_commander --cov-report=xml

      - name: Run integration tests
        run: pytest tests/integration

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## Deployment Architecture

### Package Distribution

**Format**: Python wheel via PyPI

**Installation**:
```bash
pip install modern-commander
```

**Dependencies** (from `pyproject.toml`):
```toml
[project]
name = "modern-commander"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.40.0",
    "aiofiles>=23.0.0",
    "rich>=13.0.0",
    "py7zr>=0.20.0",  # Optional: 7z support
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]
```

### Entry Point

**Location**: `src/modern_commander/app.py`

```python
def main():
    """Main entry point for application"""
    from modern_commander.app import ModernCommanderApp

    app = ModernCommanderApp()
    app.run()

if __name__ == "__main__":
    main()
```

**Console Script** (in `pyproject.toml`):
```toml
[project.scripts]
mc = "modern_commander.app:main"
modern-commander = "modern_commander.app:main"
```

### Configuration Directory

**Linux/macOS**: `~/.config/modern-commander/`
**Windows**: `%APPDATA%\modern-commander\`

**Configuration Files**:
- `config.toml`: User settings
- `keybindings.toml`: Custom key bindings
- `themes/`: Custom theme files
- `plugins/`: User plugins
- `bookmarks.json`: Saved directory bookmarks

### Platform-Specific Installers

**Windows**: Optional `.msi` installer using `cx_Freeze`
**macOS**: Optional `.dmg` bundle using `py2app`
**Linux**: Available via PyPI, optional snap/flatpak packaging

---

## Appendix: Data Models

### Core Data Models

**Location**: `src/modern_commander/core/models.py`

```python
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Optional

@dataclass(frozen=True)
class FileEntry:
    """Represents a file or directory entry"""
    path: Path
    name: str
    size: int
    modified: datetime
    is_directory: bool
    is_hidden: bool
    is_symlink: bool
    permissions: str
    owner: Optional[str] = None
    group: Optional[str] = None

    @property
    def extension(self) -> str:
        """Get file extension"""
        return self.path.suffix.lower()

    @property
    def display_size(self) -> str:
        """Human-readable size"""
        if self.is_directory:
            return "<DIR>"
        return format_size(self.size)


@dataclass
class OperationResult:
    """Result of file operation"""
    success: bool
    message: str
    files_processed: int = 0
    files_failed: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class CopyOptions:
    """Options for copy operation"""
    overwrite: bool = False
    preserve_timestamps: bool = True
    verify_checksum: bool = False
    follow_symlinks: bool = False


@dataclass
class SearchResult:
    """Search result entry"""
    file_entry: FileEntry
    match_type: str  # "name", "content", "size", "date"
    match_context: Optional[str] = None  # Line content for content matches
    line_number: Optional[int] = None


class PlatformType(Enum):
    """Supported platforms"""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


@dataclass
class DriveInfo:
    """Drive/volume information"""
    path: Path
    label: str
    total_space: int
    free_space: int
    filesystem_type: str
```

---

## Summary of Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Architecture Pattern** | Layered (Presentation, Business, Infrastructure) | Clear separation of concerns, testability |
| **UI Framework** | Textual | Modern, async-first TUI with reactive patterns |
| **Language** | Python 3.11+ | Cross-platform, rich ecosystem, async support |
| **Dependency Injection** | Constructor injection | Testability, flexibility |
| **Async Strategy** | asyncio + aiofiles | Non-blocking I/O, responsive UI |
| **Platform Abstraction** | Adapter pattern | Isolated platform-specific code |
| **Configuration** | TOML files | Human-readable, standard format |
| **Plugin System** | Interface-based plugins | Extensibility without core modification |
| **State Management** | Textual reactive properties | Automatic UI updates, consistency |
| **Error Handling** | Custom exceptions + user dialogs | Clear error communication |
| **Testing** | pytest with 80%+ coverage | Quality assurance, regression prevention |
| **Security** | Path validation, permission checks | Protect against common vulnerabilities |

---

## Implementation Roadmap

### Phase 1: Core Infrastructure (Weeks 1-2)
- Project setup and dependency configuration
- Platform abstraction layer implementation
- Core data models and interfaces
- Basic filesystem operations

### Phase 2: UI Foundation (Weeks 3-4)
- FilPanel component with file listing
- CommandBar and StatusBar components
- Keyboard handler and event system
- Basic navigation and selection

### Phase 3: File Operations (Weeks 5-6)
- Copy, move, delete operations
- Progress dialogs and error handling
- DialogSystem implementation
- Operation queue management

### Phase 4: Advanced Features (Weeks 7-8)
- FileViewer and FileEditor
- SearchEngine implementation
- ArchiveHandler for ZIP files
- Configuration system

### Phase 5: Polish & Testing (Weeks 9-10)
- Comprehensive test suite
- Performance optimization
- Documentation completion
- Cross-platform testing

### Phase 6: Extension & Release (Weeks 11-12)
- Plugin system implementation
- Theme system completion
- Packaging and distribution
- User documentation

---

**End of Architecture Documentation**

*Version 1.0.0 - 2025-10-05*
