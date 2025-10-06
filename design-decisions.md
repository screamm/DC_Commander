# Modern Commander - Design Decisions and Rationale

**Version**: 1.0.0
**Date**: 2025-10-05

This document records all significant architectural and design decisions made for the Modern Commander project, including the rationale, alternatives considered, and trade-offs.

---

## Table of Contents

1. [Technology Stack Decisions](#technology-stack-decisions)
2. [Architectural Pattern Decisions](#architectural-pattern-decisions)
3. [Component Design Decisions](#component-design-decisions)
4. [Cross-Platform Strategy Decisions](#cross-platform-strategy-decisions)
5. [Performance Optimization Decisions](#performance-optimization-decisions)
6. [Security Design Decisions](#security-design-decisions)
7. [Testing Strategy Decisions](#testing-strategy-decisions)
8. [User Experience Decisions](#user-experience-decisions)

---

## Technology Stack Decisions

### Decision 1: Python as Primary Language

**Decision**: Use Python 3.11+ as the primary implementation language

**Rationale**:
- **Cross-platform**: Python runs natively on Linux, Windows, and macOS without compilation
- **Rich Ecosystem**: Excellent libraries for filesystem operations, async I/O, and TUI development
- **Async Support**: Native asyncio for non-blocking file operations
- **Rapid Development**: High productivity for application development
- **Maintainability**: Clean, readable code that's easy to maintain

**Alternatives Considered**:
1. **Rust**: Better performance, but steeper learning curve and longer development time
2. **Go**: Good performance and concurrency, but less mature TUI frameworks
3. **C++**: Maximum performance, but complex cross-platform compilation and longer development

**Trade-offs**:
- **Performance**: Slower than compiled languages, mitigated by async I/O and optimized libraries
- **Distribution**: Requires Python runtime, but acceptable for a TUI application
- **Startup Time**: Slightly slower than compiled binaries, optimized with lazy imports

**Impact**: Medium - affects development speed, runtime performance, and distribution complexity

---

### Decision 2: Textual Framework for TUI

**Decision**: Use Textual as the TUI framework

**Rationale**:
- **Modern Architecture**: Built on asyncio, reactive programming, and CSS-like styling
- **Rich Features**: Advanced widgets, modal dialogs, layout management
- **Active Development**: Well-maintained with regular updates and community support
- **Pythonic**: Clean API that feels natural for Python developers
- **Cross-platform**: Consistent rendering on all platforms

**Alternatives Considered**:
1. **Curses/npyscreen**: Low-level, more control, but requires more boilerplate code
2. **urwid**: Mature library, but older API design and less active development
3. **Rich + Manual Layout**: More control, but would require building entire UI system

**Trade-offs**:
- **Learning Curve**: Requires learning Textual's component model and reactive system
- **Dependency**: Adds framework dependency, but provides significant value
- **Flexibility**: Some UI patterns require framework-specific approaches

**Impact**: High - determines UI development approach, code organization, and user experience

---

### Decision 3: Async-First I/O Strategy

**Decision**: Use asyncio and aiofiles for all file I/O operations

**Rationale**:
- **Responsiveness**: UI remains responsive during long file operations
- **Concurrency**: Natural support for concurrent file operations
- **Textual Integration**: Textual is built on asyncio, making integration seamless
- **Scalability**: Can handle multiple operations without blocking

**Alternatives Considered**:
1. **Threading**: Could use ThreadPoolExecutor, but more complex state management
2. **Multiprocessing**: Overkill for I/O-bound operations, high overhead
3. **Synchronous**: Simpler code, but blocks UI during operations

**Trade-offs**:
- **Complexity**: Async code requires understanding of event loops and coroutines
- **Debugging**: Async debugging is more challenging than synchronous code
- **Testing**: Requires async testing frameworks like pytest-asyncio

**Impact**: High - affects responsiveness, concurrency model, and code complexity

---

## Architectural Pattern Decisions

### Decision 4: Layered Architecture

**Decision**: Implement a three-layer architecture: Presentation, Application, Infrastructure

**Rationale**:
- **Separation of Concerns**: Clear boundaries between UI, business logic, and platform code
- **Testability**: Each layer can be tested independently with mocks
- **Maintainability**: Changes in one layer don't affect others
- **Scalability**: Easy to add new features within appropriate layer

**Layer Responsibilities**:
```
Presentation:    UI components, user interaction, display
Application:     Business logic, file operations, coordination
Infrastructure:  Filesystem access, platform-specific code
```

**Alternatives Considered**:
1. **MVC Pattern**: Too rigid for TUI application, presentation and controller often overlap
2. **Hexagonal Architecture**: More complex than needed for this project scope
3. **Flat Structure**: Simpler, but becomes unmaintainable as project grows

**Trade-offs**:
- **Boilerplate**: More interfaces and abstractions than flat structure
- **Indirection**: More layers mean more navigation through code
- **Learning Curve**: Developers need to understand layer boundaries

**Impact**: High - affects entire codebase organization and development approach

---

### Decision 5: Dependency Injection via Constructor

**Decision**: Use constructor-based dependency injection for component dependencies

**Rationale**:
- **Testability**: Easy to inject mocks for testing
- **Explicit Dependencies**: Dependencies are clear from constructor signature
- **Simple Implementation**: No need for complex DI framework
- **Type Safety**: Can use type hints for compile-time checking

**Example**:
```python
class FilPanel:
    def __init__(
        self,
        file_system: FileSystemInterface,
        event_bus: EventBusInterface,
        config: ConfigInterface,
    ):
        self.fs = file_system
        self.events = event_bus
        self.config = config
```

**Alternatives Considered**:
1. **DI Framework**: (e.g., dependency-injector) - More features, but adds complexity
2. **Service Locator**: Global registry, but hides dependencies
3. **Global Instances**: Simplest, but makes testing difficult

**Trade-offs**:
- **Verbosity**: Constructors can become long with many dependencies
- **Manual Wiring**: Need to manually wire dependencies at app startup
- **No Lifecycle Management**: Must manually manage component lifecycles

**Impact**: Medium - affects component design, testing approach, and code clarity

---

### Decision 6: Event-Driven Component Communication

**Decision**: Use event bus pattern for inter-component communication

**Rationale**:
- **Loose Coupling**: Components don't need direct references to each other
- **Extensibility**: New components can subscribe to events without modifying existing code
- **Textual Integration**: Textual has built-in message system that aligns with this pattern
- **Auditability**: All events flow through central bus, making debugging easier

**Event Flow**:
```
FileOperations → CopyStartedEvent → EventBus → [ProgressDialog, StatusBar, FilPanel]
```

**Alternatives Considered**:
1. **Direct Method Calls**: Simpler, but creates tight coupling
2. **Observer Pattern**: Similar benefits, but more boilerplate code
3. **Callback Functions**: Flexible, but can lead to callback hell

**Trade-offs**:
- **Indirection**: Harder to trace event flow through codebase
- **Type Safety**: Events are less type-safe than direct method calls
- **Debugging**: Event timing issues can be subtle

**Impact**: Medium - affects component communication and system observability

---

## Component Design Decisions

### Decision 7: Reactive Properties for UI State

**Decision**: Use Textual's reactive properties for UI state management

**Rationale**:
- **Automatic Updates**: UI updates automatically when reactive properties change
- **Consistency**: Ensures UI always reflects current state
- **Framework Integration**: Leverages Textual's built-in reactivity system
- **Declarative**: State changes are declarative rather than imperative

**Example**:
```python
class FilPanel(Container):
    current_path: Reactive[Path] = Reactive(Path.home())
    selected_files: Reactive[List[FileEntry]] = Reactive([])

    def watch_current_path(self, new_path: Path) -> None:
        """Called automatically when current_path changes"""
        self.refresh_file_list()
```

**Alternatives Considered**:
1. **Manual Updates**: Call update methods explicitly, more control but error-prone
2. **State Management Library**: (e.g., Redux-like) - Overkill for this project
3. **Property Observers**: Similar pattern, but Textual provides this built-in

**Trade-offs**:
- **Framework Lock-in**: Tied to Textual's reactivity system
- **Learning Curve**: Requires understanding reactive programming model
- **Performance**: Small overhead for reactivity tracking

**Impact**: Medium - affects UI state management and update mechanisms

---

### Decision 8: Virtual Filesystem for Archive Browsing

**Decision**: Implement virtual filesystem abstraction to browse archives like directories

**Rationale**:
- **User Experience**: Users can navigate archives just like directories
- **Consistency**: Same UI and operations work for both real and virtual filesystems
- **Extensibility**: Can extend to other virtual filesystems (FTP, cloud storage)

**Implementation**:
```python
class VirtualFileSystem(FileSystemInterface):
    """Base for virtual filesystems (archives, remote, etc.)"""
    pass

class ArchiveFileSystem(VirtualFileSystem):
    """Treat archive contents as virtual directory structure"""
    pass
```

**Alternatives Considered**:
1. **Separate Archive Browser**: Dedicated UI for archives, more features but inconsistent
2. **Extract to Temp**: Extract to temporary directory, simpler but slower
3. **Read-Only View**: Just list contents, can't navigate, limited functionality

**Trade-offs**:
- **Complexity**: More complex than simple archive listing
- **Performance**: Need to cache archive metadata for performance
- **Memory**: Larger archives consume more memory for virtual structure

**Impact**: Medium - affects archive handling and extensibility to other virtual filesystems

---

### Decision 9: Plugin Architecture with Interface Pattern

**Decision**: Use abstract base classes (ABC) for plugin interfaces

**Rationale**:
- **Type Safety**: Type checking ensures plugins implement required methods
- **Documentation**: Interface serves as documentation for plugin developers
- **Validation**: Can validate plugins at load time
- **Python Native**: Uses Python's built-in ABC mechanism

**Plugin Interface**:
```python
class PluginInterface(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def initialize(self, app: ModernCommanderApp) -> None: ...
```

**Alternatives Considered**:
1. **Protocol (PEP 544)**: Structural typing, more flexible but less explicit
2. **Duck Typing**: No enforcement, simpler but error-prone
3. **Plugin Framework**: (e.g., pluggy) - More features, but heavy dependency

**Trade-offs**:
- **Strictness**: Plugins must implement all methods, less flexible
- **Boilerplate**: Plugin authors need to write more code
- **Runtime Checks**: ABC enforcement happens at instantiation, not import

**Impact**: Low - affects plugin system design and developer experience

---

## Cross-Platform Strategy Decisions

### Decision 10: Adapter Pattern for Platform Abstraction

**Decision**: Use Adapter pattern with platform-specific implementations

**Rationale**:
- **Clean Separation**: Platform-specific code isolated in dedicated modules
- **Testability**: Can test with mock adapters on any platform
- **Maintainability**: Platform bugs are isolated to specific adapters
- **Extensibility**: Easy to add support for new platforms

**Architecture**:
```
FileSystemInterface (abstract)
    ├── WindowsFileSystem (Windows-specific)
    ├── LinuxFileSystem (Linux-specific)
    └── MacOSFileSystem (macOS-specific)
```

**Alternatives Considered**:
1. **If/Else Conditionals**: Check platform in each method, messy and hard to maintain
2. **Separate Implementations**: Different codebases per platform, code duplication
3. **Lowest Common Denominator**: Only platform-agnostic features, limits functionality

**Trade-offs**:
- **Code Duplication**: Some code duplicated across platform adapters
- **Abstraction Overhead**: Interface adds layer of indirection
- **Platform Testing**: Need to test on all platforms

**Impact**: High - critical for cross-platform support and code maintainability

---

### Decision 11: Path Handling with pathlib

**Decision**: Use pathlib.Path for all path operations

**Rationale**:
- **Cross-platform**: Automatically handles path separators and platform differences
- **Type Safety**: Path is a distinct type from str, catches errors
- **Rich API**: Object-oriented API for path manipulation
- **Standard Library**: No external dependencies

**Example**:
```python
from pathlib import Path

# Works on all platforms
path = Path.home() / "documents" / "file.txt"
```

**Alternatives Considered**:
1. **os.path Module**: Functional API, requires more manual handling
2. **String Concatenation**: Error-prone, platform-specific issues
3. **Custom Path Class**: Reinventing the wheel

**Trade-offs**:
- **Learning Curve**: Developers need to learn pathlib API
- **Legacy Code**: Some libraries still use string paths
- **Performance**: Slight overhead vs string operations

**Impact**: Medium - affects all path handling throughout application

---

## Performance Optimization Decisions

### Decision 12: Lazy Loading for Large Directories

**Decision**: Implement virtual scrolling with chunked directory loading

**Rationale**:
- **Responsiveness**: Instant display even for directories with thousands of files
- **Memory Efficiency**: Don't load entire directory into memory at once
- **Scalability**: Handles directories of any size
- **User Experience**: Progressive display gives feedback immediately

**Implementation**:
```python
async def load_directory(self, path: Path) -> None:
    """Load directory in chunks for responsiveness"""
    chunk_size = 100
    entries = []

    async for entry in self.fs.list_directory(path):
        entries.append(entry)
        if len(entries) >= chunk_size:
            self.add_entries(entries)
            entries = []
            await asyncio.sleep(0)  # Yield to event loop
```

**Alternatives Considered**:
1. **Load All Upfront**: Simpler, but blocks for large directories
2. **Background Thread**: Complexity of thread synchronization
3. **Pagination**: Traditional pagination, but less intuitive for file browsing

**Trade-offs**:
- **Complexity**: More complex than simple loading
- **State Management**: Must track loading state
- **Sorting**: Harder to sort incomplete directory listing

**Impact**: Medium - critical for handling large directories performantly

---

### Decision 13: Caching Strategy with TTL

**Decision**: Implement TTL (Time To Live) cache for directory listings and file metadata

**Rationale**:
- **Performance**: Avoid redundant filesystem calls for recently accessed data
- **Freshness**: TTL ensures data doesn't become too stale
- **Memory Efficiency**: LRU eviction prevents unbounded memory growth
- **Invalidation**: Explicit invalidation for operations that modify filesystem

**Implementation**:
```python
class FileSystemCache:
    def __init__(self, ttl: int = 60):
        self.cache = TTLCache(maxsize=1000, ttl=ttl)

    def invalidate(self, path: Path) -> None:
        """Invalidate cache entry explicitly"""
        self.cache.pop(str(path), None)
```

**Alternatives Considered**:
1. **No Caching**: Simplest, but poor performance for repeated operations
2. **Permanent Cache**: Best performance, but stale data issues
3. **Manual Invalidation Only**: Too easy to forget, leads to bugs

**Trade-offs**:
- **Stale Data**: Cache may show outdated information within TTL window
- **Memory Usage**: Cache consumes memory for stored entries
- **Complexity**: Need to manage cache lifecycle and invalidation

**Impact**: Medium - improves performance but adds complexity

---

### Decision 14: Parallel File Operations with Semaphore

**Decision**: Use asyncio.Semaphore to limit concurrent file operations

**Rationale**:
- **Performance**: Parallel operations maximize throughput
- **Resource Control**: Semaphore prevents overwhelming system
- **Responsiveness**: Async keeps UI responsive during operations
- **Configurable**: Users can adjust concurrency level

**Implementation**:
```python
async def copy_files(self, sources: List[Path], dest: Path) -> None:
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

    async def copy_with_limit(source: Path) -> None:
        async with semaphore:
            await self._copy_single_file(source, dest)

    await asyncio.gather(*[copy_with_limit(s) for s in sources])
```

**Alternatives Considered**:
1. **Sequential Operations**: Simpler, but slower for many files
2. **Thread Pool**: Traditional approach, but more complex state management
3. **Process Pool**: Maximum parallelism, but high overhead for I/O

**Trade-offs**:
- **Complexity**: Async coordination is more complex than sequential
- **Ordering**: Results may complete out of order
- **Error Handling**: Need to handle partial failures

**Impact**: High - significantly affects file operation performance

---

## Security Design Decisions

### Decision 15: Path Traversal Protection

**Decision**: Implement strict path validation to prevent path traversal attacks

**Rationale**:
- **Security**: Prevents malicious paths from accessing sensitive files
- **Safety**: Protects against accidental navigation to system directories
- **Archive Safety**: Critical for extracting untrusted archives

**Implementation**:
```python
def is_safe_path(path: Path, base: Path) -> bool:
    """Ensure path doesn't escape base directory"""
    try:
        resolved = path.resolve()
        base_resolved = base.resolve()
        return resolved.is_relative_to(base_resolved)
    except (OSError, ValueError):
        return False
```

**Alternatives Considered**:
1. **No Validation**: Simplest, but unsafe
2. **String Checking**: Fragile, easy to bypass with edge cases
3. **Whitelist Approach**: Too restrictive for file manager

**Trade-offs**:
- **User Experience**: Some legitimate operations may be blocked
- **Performance**: Validation adds overhead to path operations
- **Complexity**: Need to handle edge cases across platforms

**Impact**: High - critical security measure

---

### Decision 16: Archive Bomb Protection

**Decision**: Implement compression ratio and size checks for archive extraction

**Rationale**:
- **Security**: Prevents denial-of-service via malicious archives
- **Stability**: Avoids system crashes from memory exhaustion
- **User Safety**: Protects users from accidentally extracting dangerous archives

**Implementation**:
```python
MAX_EXTRACTION_RATIO = 100  # Max 100:1 compression
MAX_EXTRACTION_SIZE = 10 * 1024 * 1024 * 1024  # 10GB

async def validate_archive(self, archive_path: Path) -> None:
    compressed_size = archive_path.stat().st_size
    uncompressed_size = sum(entry.size for entry in self.list_archive(archive_path))

    if uncompressed_size / compressed_size > MAX_EXTRACTION_RATIO:
        raise SecurityError("Suspicious compression ratio")

    if uncompressed_size > MAX_EXTRACTION_SIZE:
        raise SecurityError("Archive too large")
```

**Alternatives Considered**:
1. **No Validation**: Simple, but dangerous
2. **File Count Limit**: Helps, but doesn't protect against large files
3. **Time Limit**: Unreliable, depends on system performance

**Trade-offs**:
- **False Positives**: May block legitimate highly-compressed archives
- **Performance**: Need to scan entire archive before extraction
- **Usability**: Users may not understand why extraction is blocked

**Impact**: High - critical security feature for archive handling

---

### Decision 17: Filename Sanitization

**Decision**: Sanitize filenames to remove dangerous characters

**Rationale**:
- **Cross-platform**: Prevents invalid filenames on different platforms
- **Security**: Removes path separators and special characters
- **Reliability**: Prevents filesystem errors from invalid names

**Implementation**:
```python
def sanitize_filename(filename: str) -> str:
    """Remove dangerous characters from filename"""
    dangerous_chars = '\0/\\:<>"|?*'
    sanitized = ''.join(
        c for c in filename
        if c not in dangerous_chars and ord(c) >= 32
    )

    # Prevent Windows reserved names
    reserved = {'CON', 'PRN', 'AUX', 'NUL'}
    if sanitized.upper() in reserved:
        sanitized = f"_{sanitized}"

    return sanitized
```

**Alternatives Considered**:
1. **No Sanitization**: Simple, but causes errors
2. **Reject Invalid**: Safer, but poor user experience
3. **Platform-Specific**: Most correct, but complex

**Trade-offs**:
- **Data Loss**: Sanitization may change filenames unexpectedly
- **User Confusion**: Users may not understand why names changed
- **Compatibility**: Sanitized names may not match original

**Impact**: Medium - affects file creation and archive extraction

---

## Testing Strategy Decisions

### Decision 18: Pytest with Async Support

**Decision**: Use pytest with pytest-asyncio for testing

**Rationale**:
- **Async Support**: Native support for async test functions
- **Fixtures**: Powerful fixture system for test setup
- **Plugins**: Rich ecosystem of pytest plugins
- **Industry Standard**: Widely used and well-documented

**Example**:
```python
@pytest.mark.asyncio
async def test_copy_file(file_ops):
    result = await file_ops.copy_files([source], dest)
    assert result.success
```

**Alternatives Considered**:
1. **unittest**: Standard library, but less features and boilerplate
2. **nose2**: Less active development than pytest
3. **Custom Test Runner**: Reinventing the wheel

**Trade-offs**:
- **Learning Curve**: Developers need to learn pytest conventions
- **Dependency**: Adds test framework dependency
- **Magic**: Some pytest features use implicit behavior

**Impact**: Medium - affects testing approach and developer experience

---

### Decision 19: Dependency Injection for Testability

**Decision**: Design components with dependency injection to enable mock testing

**Rationale**:
- **Isolation**: Components can be tested in isolation with mocks
- **Speed**: Fast tests without real filesystem operations
- **Reliability**: Tests don't depend on filesystem state
- **Coverage**: Can test error conditions easily

**Example**:
```python
@pytest.fixture
def mock_filesystem():
    fs = Mock(spec=FileSystemInterface)
    fs.list_directory = AsyncMock(return_value=[...])
    return fs

def test_panel_navigation(mock_filesystem):
    panel = FilPanel(file_system=mock_filesystem)
    # Test panel with mocked filesystem
```

**Alternatives Considered**:
1. **Integration Tests Only**: More realistic, but slower and fragile
2. **Monkey Patching**: Flexible, but brittle and hard to maintain
3. **Test Doubles**: Manual mock objects, more boilerplate

**Trade-offs**:
- **Realism**: Mocks may not accurately reflect real behavior
- **Maintenance**: Need to keep mocks in sync with interfaces
- **Complexity**: More setup code for tests

**Impact**: High - fundamental to testing strategy

---

### Decision 20: Test Coverage Goals

**Decision**: Target >80% overall coverage, >90% for business logic

**Rationale**:
- **Quality**: High coverage catches more bugs
- **Confidence**: Developers can refactor safely
- **Documentation**: Tests serve as usage examples
- **Regression Prevention**: Changes less likely to break existing functionality

**Coverage Targets**:
```
Overall:          >80%
Business Logic:   >90%
UI Components:    >70% (UI testing is harder)
Platform Code:    100% (critical for cross-platform)
```

**Alternatives Considered**:
1. **100% Coverage**: Goal, but diminishing returns and impractical
2. **No Target**: Simple, but no quality baseline
3. **Lower Target**: Faster development, but less confidence

**Trade-offs**:
- **Development Time**: Writing tests takes time
- **Maintenance**: Tests need to be maintained
- **False Security**: High coverage doesn't guarantee quality

**Impact**: Medium - affects development process and code quality

---

## User Experience Decisions

### Decision 21: Norton Commander Compatible Keybindings

**Decision**: Use Norton Commander F-key bindings as defaults

**Rationale**:
- **Familiarity**: Users familiar with Norton Commander feel at home
- **Muscle Memory**: Experienced users can use without learning new shortcuts
- **Consistency**: Follows established file manager conventions
- **Customizable**: Users can remap if desired

**Default Bindings**:
```
F1  = Help
F3  = View
F4  = Edit
F5  = Copy
F6  = Move
F7  = MkDir
F8  = Delete
F10 = Quit
```

**Alternatives Considered**:
1. **Modern Shortcuts**: (Ctrl+C for copy) More familiar to general users
2. **Custom Scheme**: Unique bindings, but requires learning
3. **No Defaults**: Let users configure, but poor initial experience

**Trade-offs**:
- **Conflict**: F-keys may conflict with terminal emulators
- **Modern Users**: Younger users may not know Norton Commander
- **Customization**: Some users will want different bindings

**Impact**: Medium - affects initial user experience and muscle memory

---

### Decision 22: Progressive Feedback for Long Operations

**Decision**: Show progress dialogs for operations taking >500ms

**Rationale**:
- **User Confidence**: Users know operation is progressing
- **Cancellation**: Provides opportunity to cancel long operations
- **Context**: Shows what's happening (current file being copied)
- **Time Estimation**: Can show estimated completion time

**Implementation**:
```python
async def copy_files(self, sources, dest):
    if estimated_time > 0.5:  # >500ms
        dialog = await self.show_progress_dialog()

    for source in sources:
        await self._copy_file(source, dest)
        dialog.update(progress=...)
```

**Alternatives Considered**:
1. **Always Show**: Clutters UI for fast operations
2. **Never Show**: Poor experience for long operations
3. **Fixed Threshold**: Our choice, could be configurable

**Trade-offs**:
- **Complexity**: Need to estimate operation time
- **Flickering**: Dialog may flash for operations near threshold
- **Interruption**: Modal dialogs interrupt user flow

**Impact**: Medium - affects perceived performance and user experience

---

### Decision 23: Dual-Panel Layout

**Decision**: Implement traditional dual-panel layout like Norton Commander

**Rationale**:
- **Efficiency**: Source and destination visible simultaneously
- **Familiarity**: File manager users expect this layout
- **Comparison**: Easy to compare directories side-by-side
- **Operations**: Natural source→destination workflow

**Layout**:
```
┌──────────────────┬──────────────────┐
│   Left Panel     │   Right Panel    │
│   /home/user     │   /tmp           │
│                  │                  │
│   file1.txt      │   docs/          │
│   file2.py       │   images/        │
│   folder/        │   backup.zip     │
└──────────────────┴──────────────────┘
│ F1=Help F5=Copy F8=Delete F10=Quit │
└─────────────────────────────────────┘
```

**Alternatives Considered**:
1. **Single Panel**: Simpler, but less efficient for operations
2. **Miller Columns**: (like Finder) Modern, but less space-efficient
3. **Tree + Panel**: Hybrid approach, but complex UI

**Trade-offs**:
- **Screen Space**: Each panel has half width, limiting long filenames
- **Complexity**: More complex than single panel
- **Mobile**: Doesn't translate well to mobile interfaces (out of scope)

**Impact**: High - defines core user experience

---

### Decision 24: Configuration Hierarchy

**Decision**: Support multiple configuration sources with clear precedence

**Rationale**:
- **Flexibility**: Users can configure at different levels
- **Defaults**: Ship with sensible defaults
- **Override**: System admins can set policies
- **Portability**: Users can include configs in version control

**Precedence** (highest to lowest):
```
1. Command-line arguments     (--flag=value)
2. User config file            (~/.config/mc/config.toml)
3. System config file          (/etc/mc/config.toml)
4. Built-in defaults           (config/default_config.toml)
```

**Alternatives Considered**:
1. **Single Source**: Simpler, but inflexible
2. **Environment Variables**: Additional source, but complex precedence
3. **GUI Settings**: User-friendly, but not scriptable

**Trade-offs**:
- **Complexity**: Users must understand precedence rules
- **Debugging**: Harder to determine which config is active
- **Conflicts**: Multiple sources can specify conflicting values

**Impact**: Low - affects configuration management and deployment

---

## Summary of Critical Decisions

| Decision | Impact | Risk | Reversibility |
|----------|--------|------|---------------|
| Python as Language | High | Low | Low (rewrites required) |
| Textual Framework | High | Low | Medium (UI rewrite) |
| Async-First I/O | High | Medium | Medium (significant refactor) |
| Layered Architecture | High | Low | Low (fundamental structure) |
| Dependency Injection | Medium | Low | High (refactoring possible) |
| Event-Driven Communication | Medium | Low | High (can change pattern) |
| Adapter Pattern for Platforms | High | Low | Medium (affects platform code) |
| Virtual Filesystem | Medium | Medium | High (additional feature) |
| Lazy Loading | Medium | Low | High (performance optimization) |
| Path Traversal Protection | High | Low | Low (security critical) |
| Archive Bomb Protection | High | Low | Low (security critical) |
| Pytest Testing | Medium | Low | High (testing framework) |
| NC Keybindings | Low | Low | High (configuration change) |
| Dual-Panel Layout | High | Low | Low (core UX) |

---

**End of Design Decisions Document**

*Version 1.0.0 - 2025-10-05*
