# DC Commander - Development Roadmap

**Last Updated:** 2025-10-10
**Status:** Planning Document

> **Note:** This document describes PLANNED features and future architecture improvements. For current implementation, see [ACTUAL_ARCHITECTURE.md](ACTUAL_ARCHITECTURE.md).

---

## Vision Statement

Transform DC Commander from a functional Norton Commander clone into a production-ready, high-performance, cross-platform file manager with excellent security, accessibility, and user experience.

---

## Current State Assessment

### Strengths ✅
- Clean layered architecture
- Good design pattern usage (Command, Strategy)
- Excellent security module (not yet integrated)
- Authentic Norton Commander UI/UX
- Solid Textual framework integration

### Weaknesses 🔴
- Synchronous I/O blocks UI
- Security module not used
- Test coverage only ~35%
- No platform-specific handling
- Missing progress indicators
- Type hints incomplete (60%)

### Technical Debt Score

**Total: ~6-8 weeks of effort**
- Critical: 2-3 weeks (async operations, security integration, documentation)
- High: 2-3 weeks (type hints, testing, CI/CD)
- Medium: 1-2 weeks (performance, refactoring, platform adapters)
- Low: 1 week (UI enhancements, minor cleanups)

---

## Roadmap Phases

## Phase 1: Foundation Fixes (Weeks 1-2)

**Goal:** Fix critical issues and establish quality gates

**Status:** 🔴 Not Started

### 1.1 Documentation Accuracy ✅ COMPLETED
**Priority:** CRITICAL
**Effort:** 3 days
**Status:** ✅ Done

- [x] Create ACTUAL_ARCHITECTURE.md reflecting reality
- [x] Create ROADMAP.md for future plans
- [x] Move aspirational content from architecture.md to roadmap
- [x] Fix Python version requirements (3.10 vs 3.11 mismatch)
- [x] Update requirements.txt

### 1.2 Security Integration
**Priority:** CRITICAL
**Effort:** 3 days

- [ ] Integrate `src/core/security.py` validation into `services/file_service.py`
- [ ] Add path validation to all file operations
- [ ] Add filename sanitization to all user inputs
- [ ] Add input validation in UI layer (directory creation, rename, etc.)
- [ ] Add security logging for validation failures
- [ ] Test security integration thoroughly

**Files to Modify:**
- `services/file_service.py` - Add security validation
- `modern_commander.py` - Validate all user inputs
- `components/dialogs.py` - Add input sanitization

**Acceptance Criteria:**
- [ ] All file operations use `validate_path()`
- [ ] All filenames use `sanitize_filename()`
- [ ] Security tests pass
- [ ] No path traversal vulnerabilities

### 1.3 Type Hints Completion
**Priority:** HIGH
**Effort:** 4 days

- [ ] Install and configure mypy
- [ ] Add type hints to all functions (currently ~60%)
- [ ] Fix all mypy errors in strict mode
- [ ] Add pre-commit hooks for type checking
- [ ] Document type hint standards

**Files to Modify:** All `.py` files

**Acceptance Criteria:**
- [ ] 100% type hint coverage
- [ ] `mypy --strict` passes with no errors
- [ ] Pre-commit hook configured

### 1.4 Python Version Clarification
**Priority:** HIGH
**Effort:** 1 day

- [ ] Update `requirements.txt` to `python>=3.10` (current reality)
- [ ] OR add Python 3.11+ features to justify 3.11 requirement
- [ ] Document Python version decision in README.md

**Decision:** Keep Python 3.10+ (no 3.11+ features currently needed)

**Acceptance Criteria:**
- [ ] Requirements match reality
- [ ] CI tests on Python 3.10, 3.11, 3.12

---

## Phase 2: Critical Infrastructure (Weeks 3-4)

**Goal:** Implement async operations and testing infrastructure

**Status:** 🔴 Not Started

### 2.1 Async File Operations
**Priority:** CRITICAL
**Effort:** 2 weeks

- [ ] Convert file service methods to async
- [ ] Implement async copy with `aiofiles`
- [ ] Implement async move operations
- [ ] Implement async delete operations
- [ ] Add progress callbacks for long operations
- [ ] Update UI to use async properly (Textual supports this)
- [ ] Test with large files and directories

**Files to Modify:**
- `services/file_service.py` - Convert to async
- `modern_commander.py` - Update to use async
- `components/file_panel.py` - Support async refresh

**Example Implementation:**
```python
# services/file_service.py
import aiofiles
import asyncio

async def copy_file_async(
    source: Path,
    dest: Path,
    progress_callback: Optional[Callable] = None,
    chunk_size: int = 64 * 1024
) -> None:
    async with aiofiles.open(source, 'rb') as src:
        async with aiofiles.open(dest, 'wb') as dst:
            bytes_copied = 0
            while chunk := await src.read(chunk_size):
                await dst.write(chunk)
                bytes_copied += len(chunk)
                if progress_callback:
                    await progress_callback(bytes_copied)
                await asyncio.sleep(0)  # Yield to event loop
```

**Acceptance Criteria:**
- [ ] UI remains responsive during file operations
- [ ] Progress updates work correctly
- [ ] Can cancel long operations
- [ ] No blocking I/O in main thread

### 2.2 Test Coverage Improvement
**Priority:** HIGH
**Effort:** 1 week

- [ ] Install pytest-cov and coverage tools
- [ ] Write missing unit tests
- [ ] Add UI interaction tests (Textual Pilot)
- [ ] Add end-to-end workflow tests
- [ ] Add performance tests
- [ ] Target >80% coverage

**Test Categories to Add:**
- [ ] Performance tests (`tests/performance/`)
- [ ] E2E tests (`tests/e2e/`)
- [ ] Property-based tests (`tests/property/`)
- [ ] UI tests with Textual Pilot

**Acceptance Criteria:**
- [ ] Test coverage >80%
- [ ] All critical paths tested
- [ ] Performance benchmarks established

### 2.3 CI/CD Pipeline
**Priority:** HIGH
**Effort:** 3 days

- [ ] Create GitHub Actions workflow
- [ ] Multi-platform testing (Windows, Linux, macOS)
- [ ] Multi-version testing (Python 3.10, 3.11, 3.12)
- [ ] Coverage reporting with codecov
- [ ] Type checking with mypy
- [ ] Linting with ruff
- [ ] Auto-release on tag

**Files to Create:**
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`

**Acceptance Criteria:**
- [ ] CI runs on all platforms
- [ ] Coverage reports visible
- [ ] Type checking enforced
- [ ] Auto-deploy on release

---

## Phase 3: Performance & Quality (Weeks 5-6)

**Goal:** Optimize performance and improve code quality

**Status:** 🔴 Not Started

### 3.1 Performance Optimizations
**Priority:** MEDIUM
**Effort:** 1 week

- [ ] Implement directory caching (LRU cache with 60s TTL)
- [ ] Add lazy loading for large directories
- [ ] Optimize string operations (pre-compute constants)
- [ ] Profile and measure all improvements
- [ ] Add performance tests

**Implementations:**

**Directory Caching:**
```python
from cachetools import TTLCache

class FilePanel:
    def __init__(self):
        self._dir_cache = TTLCache(maxsize=100, ttl=60)

    def _load_directory(self) -> List[FileItem]:
        cache_key = str(self.current_path)
        if cache_key in self._dir_cache:
            return self._dir_cache[cache_key]

        items = self._scan_directory()
        self._dir_cache[cache_key] = items
        return items
```

**Lazy Loading:**
```python
def _load_directory_lazy(self, chunk_size=100):
    """Load directory contents in chunks for better responsiveness"""
    items = []
    for i, entry in enumerate(self.current_path.iterdir()):
        items.append(FileItem.from_path(entry))
        if i % chunk_size == 0 and i > 0:
            yield items  # Yield to UI for update
            items = []
    if items:
        yield items
```

**Acceptance Criteria:**
- [ ] Directory loading <100ms for 1000 files
- [ ] UI never blocks >100ms
- [ ] Memory usage stays reasonable
- [ ] Performance benchmarks pass

### 3.2 Code Refactoring
**Priority:** MEDIUM
**Effort:** 1 week

- [ ] Extract duplicate code from file_service.py (copy/move ~80% duplicate)
- [ ] Break long methods (>50 lines) into smaller functions
- [ ] Extract magic numbers to constants
- [ ] Standardize exception handling approach
- [ ] Improve naming consistency

**Refactorings:**

**Extract Common Operation Logic:**
```python
def _execute_file_operation(
    items: List[Path],
    dest_path: Path,
    operation: Callable[[Path, Path], None],
    operation_name: str
) -> OperationSummary:
    """Common logic for file operations (copy, move, delete)"""
    success_count = 0
    error_count = 0
    errors = []

    for item in items:
        try:
            dest_file = dest_path / item.name
            operation(item, dest_file)
            success_count += 1
        except Exception as e:
            errors.append((item.name, str(e)))
            error_count += 1

    return OperationSummary(
        self._determine_result(success_count, error_count),
        success_count,
        error_count,
        errors
    )
```

**Acceptance Criteria:**
- [ ] No code duplication >10 lines
- [ ] All methods <50 lines
- [ ] Magic numbers extracted to constants
- [ ] Consistent exception handling

### 3.3 Progress Dialogs
**Priority:** MEDIUM
**Effort:** 3 days

- [ ] Create ProgressDialog component
- [ ] Add to copy operations
- [ ] Add to move operations
- [ ] Add to delete operations
- [ ] Add cancel support
- [ ] Show estimated time remaining

**Implementation:**
```python
class ProgressDialog(ModalScreen):
    def __init__(self, title: str, total: int, cancelable: bool = False):
        super().__init__()
        self.title = title
        self.total = total
        self.current = 0
        self.canceled = False
        self.cancelable = cancelable

    def update(self, current: int, message: str = ""):
        self.current = current
        percent = (current / self.total) * 100
        self.query_one(".progress-bar").update(percent)
        self.query_one(".progress-message").update(message)

    def on_key(self, event):
        if self.cancelable and event.key == "escape":
            self.canceled = True
```

**Acceptance Criteria:**
- [ ] Progress shown for operations >1s
- [ ] Can cancel long operations
- [ ] Accurate progress percentage
- [ ] Estimated time remaining shown

---

## Phase 4: Platform & Architecture (Weeks 7-8)

**Goal:** Platform-specific handling and architectural improvements

**Status:** 🔴 Not Started

### 4.1 Platform-Specific Adapters
**Priority:** MEDIUM
**Effort:** 1 week

- [ ] Create `src/core/protocols.py` with filesystem protocol
- [ ] Implement Windows adapter (long paths, UNC, drive letters)
- [ ] Implement Unix adapter (permissions, symlinks)
- [ ] Implement macOS adapter (bundles, resource forks)
- [ ] Add platform detection and adapter selection
- [ ] Test cross-platform thoroughly

**Protocol Definition:**
```python
from typing import Protocol, List
from pathlib import Path

class FileSystemProtocol(Protocol):
    """Protocol for filesystem operations"""

    def list_directory(self, path: Path) -> List[FileItem]:
        """List directory contents"""
        ...

    def copy_file(self, source: Path, dest: Path) -> None:
        """Copy file with platform-specific handling"""
        ...

    def validate_path(self, path: Path) -> tuple[bool, str]:
        """Validate path with platform-specific rules"""
        ...
```

**Platform Implementations:**
```python
# platform/windows.py
class WindowsFileSystem:
    def copy_file(self, source: Path, dest: Path) -> None:
        # Handle long paths with \\?\ prefix
        # Handle UNC paths
        # Handle drive letters correctly
        ...

# platform/unix.py
class UnixFileSystem:
    def copy_file(self, source: Path, dest: Path) -> None:
        # Preserve permissions
        # Handle symlinks correctly
        # Handle special files
        ...
```

**Acceptance Criteria:**
- [ ] Windows long paths work (>260 chars)
- [ ] Unix permissions preserved
- [ ] Symlinks handled correctly
- [ ] All platforms tested

### 4.2 Dependency Injection
**Priority:** LOW
**Effort:** 3 days

- [ ] Create simple DI container or factory
- [ ] Refactor components to use DI
- [ ] Improve testability with DI
- [ ] Document DI patterns

**Simple DI Implementation:**
```python
class DIContainer:
    def __init__(self):
        self._services = {}

    def register(self, interface: type, implementation: Any):
        self._services[interface] = implementation

    def get(self, interface: type) -> Any:
        return self._services[interface]

# Usage
container = DIContainer()
container.register(ConfigManager, ConfigManager(config_path))
container.register(ThemeManager, ThemeManager())

# In components
def __init__(self, container: DIContainer):
    self.config = container.get(ConfigManager)
    self.theme = container.get(ThemeManager)
```

**Acceptance Criteria:**
- [ ] No direct instantiation of services
- [ ] All dependencies injected
- [ ] Tests use mock implementations easily

### 4.3 UI Enhancements
**Priority:** LOW
**Effort:** 3 days

- [ ] Add error recovery dialogs (Retry/Skip/Cancel)
- [ ] Improve confirmation dialogs (custom buttons)
- [ ] Add accessibility documentation
- [ ] Add colorblind-friendly themes
- [ ] Improve keyboard focus indicators

**Acceptance Criteria:**
- [ ] Better error handling UX
- [ ] Documented accessibility limitations
- [ ] Multiple theme options
- [ ] Clear focus indicators

---

## Phase 5: Advanced Features (Weeks 9-12)

**Goal:** Add advanced functionality

**Status:** 🔴 Not Started

### 5.1 Command Pattern Integration
**Priority:** MEDIUM
**Effort:** 2 days

- [ ] Hook up Ctrl+Z for undo
- [ ] Hook up Ctrl+Y for redo
- [ ] Show undo history
- [ ] Add undo depth limit configuration
- [ ] Test undo/redo thoroughly

**Acceptance Criteria:**
- [ ] Ctrl+Z undoes last operation
- [ ] Ctrl+Y redoes undone operation
- [ ] Undo history visible in UI
- [ ] All file operations undoable

### 5.2 Plugin System
**Priority:** LOW
**Effort:** 2 weeks

- [ ] Define plugin API
- [ ] Create plugin loader
- [ ] Add plugin configuration
- [ ] Create example plugins
- [ ] Document plugin development

**Plugin Types:**
- File viewers (custom file types)
- Custom operations (batch rename, etc.)
- Custom themes
- External tool integration

**Acceptance Criteria:**
- [ ] Plugins can be loaded dynamically
- [ ] Plugin API documented
- [ ] Example plugins work
- [ ] Plugin manager in UI

### 5.3 Archive Support
**Priority:** MEDIUM
**Effort:** 1 week

- [ ] ZIP archive viewing (browse inside archives)
- [ ] TAR archive support
- [ ] 7Z archive support
- [ ] Extract with progress
- [ ] Create archives

**Acceptance Criteria:**
- [ ] Can browse archives as directories
- [ ] Can extract with security validation
- [ ] Archive bomb detection works
- [ ] All formats tested

### 5.4 Advanced Features
**Priority:** LOW
**Effort:** 3 weeks

- [ ] Quick View mode (file preview in opposite panel)
- [ ] Hidden files toggle (Ctrl+H)
- [ ] FTP/SFTP support
- [ ] Bookmarks and favorites
- [ ] Tab support (multiple panels)
- [ ] Directory comparison
- [ ] Batch rename with preview
- [ ] File permissions editor (Unix)
- [ ] Syntax highlighting in viewer

---

## Success Metrics

### Before (Current State)

```yaml
Performance:
  Startup: 200-500ms ✅
  Directory load (1000 files): >1s 🔴
  UI responsiveness: Blocks during I/O 🔴

Quality:
  Type hint coverage: 60% 🟡
  Test coverage: 35% 🔴
  Async functions: 1 🔴
  Security integration: 0% 🔴
  Code duplication: High 🔴

User Experience:
  Progress indicators: None 🔴
  Cancellable operations: No 🔴
  Undo/redo: Not integrated 🔴
  Cross-platform support: Basic 🟡
```

### After (Target State)

```yaml
Performance:
  Startup: <500ms ✅
  Directory load (1000 files): <100ms ✅
  UI responsiveness: Never blocks >100ms ✅

Quality:
  Type hint coverage: 100% ✅
  Test coverage: >80% ✅
  Async functions: All I/O operations ✅
  Security integration: 100% ✅
  Code duplication: Minimal ✅

User Experience:
  Progress indicators: All long operations ✅
  Cancellable operations: Yes ✅
  Undo/redo: Fully integrated ✅
  Cross-platform support: Excellent ✅
```

---

## Risk Assessment

### High Risk Items

1. **Async Migration** - May introduce subtle bugs
   - Mitigation: Extensive testing, gradual rollout

2. **Platform Adapters** - Hard to test all platforms
   - Mitigation: CI on Windows, Linux, macOS

3. **Performance Optimizations** - May introduce caching bugs
   - Mitigation: Cache invalidation strategy, thorough testing

### Medium Risk Items

1. **Security Integration** - Breaking changes to file operations
   - Mitigation: Comprehensive security test suite

2. **Test Coverage** - Time-consuming to write tests
   - Mitigation: Focus on critical paths first

### Low Risk Items

1. **Documentation** - No code changes
2. **Type Hints** - Mostly additive
3. **UI Enhancements** - Isolated changes

---

## Timeline Summary

| Phase | Duration | Status | Priority |
|-------|----------|--------|----------|
| Phase 1: Foundation Fixes | 2 weeks | 🟢 Partial | CRITICAL |
| Phase 2: Infrastructure | 2 weeks | 🔴 Not Started | CRITICAL |
| Phase 3: Performance | 2 weeks | 🔴 Not Started | HIGH |
| Phase 4: Platform | 2 weeks | 🔴 Not Started | MEDIUM |
| Phase 5: Advanced | 4 weeks | 🔴 Not Started | LOW |
| **Total** | **12 weeks** | | |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to contribute to this roadmap
- Development setup
- Coding standards
- Pull request process

---

## Questions & Feedback

- **GitHub Issues:** Use for bugs and feature requests
- **GitHub Discussions:** Use for roadmap feedback
- **Pull Requests:** Use for implementation contributions

---

**Roadmap Version:** 1.0
**Last Updated:** 2025-10-10
**Next Review:** 2025-11-10
