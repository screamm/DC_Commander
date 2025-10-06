# Modern Commander - Component Diagrams

**Version**: 1.0.0
**Date**: 2025-10-05

This document provides detailed visual diagrams of the Modern Commander architecture, showing component relationships, data flow, and interaction patterns.

---

## System Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   ModernCommanderApp                         │  │
│  │                   (Main Textual App)                         │  │
│  └────────┬──────────────────────┬──────────────────────────────┘  │
│           │                      │                                  │
│  ┌────────▼────────┐    ┌───────▼────────┐    ┌──────────────┐   │
│  │  FilPanel       │    │  FilPanel      │    │ CommandBar   │   │
│  │  (Left Panel)   │    │  (Right Panel) │    │              │   │
│  │                 │    │                │    │  F1...F10    │   │
│  │ ┌─────────────┐ │    │ ┌────────────┐│    └──────────────┘   │
│  │ │ Breadcrumb  │ │    │ │ Breadcrumb ││                        │
│  │ └─────────────┘ │    │ └────────────┘│    ┌──────────────┐   │
│  │ ┌─────────────┐ │    │ ┌────────────┐│    │  StatusBar   │   │
│  │ │  FileList   │ │    │ │  FileList  ││    │              │   │
│  │ │             │ │    │ │            ││    └──────────────┘   │
│  │ │  file1.txt  │ │    │ │  docs/     ││                        │
│  │ │  file2.py   │ │    │ │  images/   ││                        │
│  │ │  folder/    │ │    │ │  README.md ││                        │
│  │ └─────────────┘ │    │ └────────────┘│                        │
│  └─────────────────┘    └────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                                │
│                                                                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │
│  │ KeyboardHandler│  │ ActionHandler  │  │  DialogSystem  │        │
│  │                │  │                │  │                │        │
│  │ - F1...F10     │  │ - Dispatch     │  │ - Confirm      │        │
│  │ - Ctrl+X       │  │ - Validate     │  │ - Prompt       │        │
│  │ - Alt+X        │  │ - Execute      │  │ - Alert        │        │
│  └────────┬───────┘  └────────┬───────┘  │ - Progress     │        │
│           │                   │           └────────────────┘        │
│           ▼                   ▼                                      │
│  ┌────────────────────────────────────────────────────────┐        │
│  │              Business Logic Services                    │        │
│  │                                                          │        │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │        │
│  │  │FileOperations│  │ SearchEngine │  │ FileViewer   │ │        │
│  │  │              │  │              │  │              │ │        │
│  │  │ - copy()     │  │ - byName()   │  │ - display()  │ │        │
│  │  │ - move()     │  │ - byContent()│  │ - search()   │ │        │
│  │  │ - delete()   │  │ - bySize()   │  │ - navigate() │ │        │
│  │  │ - create()   │  │ - byDate()   │  └──────────────┘ │        │
│  │  └──────────────┘  └──────────────┘                    │        │
│  │                                                          │        │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │        │
│  │  │ArchiveHandler│  │  FileEditor  │  │  Clipboard   │ │        │
│  │  │              │  │              │  │              │ │        │
│  │  │ - create()   │  │ - load()     │  │ - copy()     │ │        │
│  │  │ - extract()  │  │ - save()     │  │ - paste()    │ │        │
│  │  │ - list()     │  │ - edit()     │  │ - clear()    │ │        │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │        │
│  └────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                              │
│                                                                       │
│  ┌────────────────────────────────────────────────────────┐         │
│  │           FileSystemAdapter (Factory)                  │         │
│  │                                                          │         │
│  │    Creates platform-specific implementation             │         │
│  └────────────┬──────────────┬──────────────┬─────────────┘         │
│               │              │              │                        │
│       ┌───────▼──────┐ ┌────▼─────┐ ┌──────▼────────┐             │
│       │   Windows    │ │  Linux   │ │    macOS      │             │
│       │  FileSystem  │ │FileSystem│ │  FileSystem   │             │
│       │              │ │          │ │               │             │
│       │ - Drives     │ │ - Mounts │ │ - Volumes     │             │
│       │ - UNC paths  │ │ - Perms  │ │ - App bundles │             │
│       │ - Long paths │ │ - Symlinks│ │ - .DS_Store  │             │
│       └──────────────┘ └──────────┘ └───────────────┘             │
│                                                                       │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐       │
│  │  SystemInfo    │  │ ProcessUtils   │  │ Platform Utils │       │
│  │                │  │                │  │                │       │
│  │ - getPlatform()│  │ - execute()    │  │ - normalize()  │       │
│  │ - getDrives()  │  │ - shell()      │  │ - validate()   │       │
│  │ - getDiskUsage│  │ - async_run()  │  │ - format()     │       │
│  └────────────────┘  └────────────────┘  └────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Dependency Graph

```
                      ┌─────────────────────┐
                      │ModernCommanderApp   │
                      │  (Application Root) │
                      └──────────┬──────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
         ┌──────────▼──────┐    │    ┌───────▼────────┐
         │ FilPanel (Left) │    │    │FilPanel (Right)│
         └────────┬─────────┘    │    └───────┬────────┘
                  │              │            │
                  └──────────────┼────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   KeyboardHandler       │
                    │   (Event Coordinator)   │
                    └────────┬─────────────┬──┘
                             │             │
           ┌─────────────────┼─────────────┼─────────────┐
           │                 │             │             │
    ┌──────▼──────┐  ┌───────▼──────┐  ┌──▼──────┐  ┌──▼──────┐
    │FileOperations│  │ SearchEngine │  │FileViewer│  │FileEditor│
    └──────┬───────┘  └───────┬──────┘  └──┬──────┘  └──┬──────┘
           │                  │            │            │
           └──────────┬───────┴────────────┴────────────┘
                      │
           ┌──────────▼──────────┐
           │ FileSystemInterface │
           │    (Abstract)       │
           └──────────┬──────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────▼──────┐ ┌───▼─────┐ ┌─────▼────┐
   │ Windows   │ │ Linux   │ │  macOS   │
   │FileSystem │ │FileSystem│ │FileSystem│
   └───────────┘ └─────────┘ └──────────┘
```

---

## FilPanel Component Detail

```
┌─────────────────────────────────────────────────────┐
│                    FilPanel                         │
│                                                     │
│  Properties (Reactive):                            │
│  ├─ current_path: Path                             │
│  ├─ selected_files: List[FileEntry]                │
│  ├─ is_active: bool                                │
│  └─ sort_order: SortOrder                          │
│                                                     │
│  ┌───────────────────────────────────────────────┐│
│  │         Breadcrumb Component                  ││
│  │  /home/user/documents/projects               ││
│  └───────────────────────────────────────────────┘│
│                                                     │
│  ┌───────────────────────────────────────────────┐│
│  │          FileList Component                   ││
│  │                                               ││
│  │  Name          Size      Modified      Perms ││
│  │  ────────────────────────────────────────────││
│  │  [..]          <UP>                          ││
│  │  > file1.txt   1.2 KB    2025-10-05   rw-   ││
│  │    file2.py    3.4 KB    2025-10-04   rw-   ││
│  │  * folder/     <DIR>     2025-10-03   rwx   ││
│  │    image.png   245 KB    2025-10-02   rw-   ││
│  │                                               ││
│  │  Legend: > = cursor, * = selected            ││
│  └───────────────────────────────────────────────┘│
│                                                     │
│  ┌───────────────────────────────────────────────┐│
│  │        StatusLine Component                   ││
│  │  3 files, 1 selected (245 KB)                ││
│  └───────────────────────────────────────────────┘│
│                                                     │
│  Dependencies:                                      │
│  ├─ FileSystemInterface (injected)                 │
│  ├─ EventBus (injected)                            │
│  └─ Configuration (injected)                       │
│                                                     │
│  Events Emitted:                                    │
│  ├─ PanelNavigationEvent                           │
│  ├─ FileSelectionEvent                             │
│  └─ FileActivatedEvent                             │
│                                                     │
│  Events Consumed:                                   │
│  ├─ RefreshRequestEvent                            │
│  ├─ PathChangeEvent                                │
│  └─ ThemeChangedEvent                              │
└─────────────────────────────────────────────────────┘
```

---

## File Operations Flow

```
User Presses F5 (Copy)
         │
         ▼
┌────────────────────┐
│ KeyboardHandler    │  ─────→  Check if files selected
│ .handle_key("F5") │           ├─ Yes: Continue
└──────────┬─────────┘           └─ No: Show error
           │
           ▼
┌────────────────────┐
│ DialogSystem       │  ─────→  Show confirmation dialog
│ .confirm()         │           "Copy 3 files to /dest?"
└──────────┬─────────┘           ├─ Yes: Continue
           │                     └─ No: Cancel
           ▼
┌────────────────────┐
│ FileOperations     │
│ .copy_files()      │
└──────────┬─────────┘
           │
           ├─────────────────────────────────┐
           │                                 │
           ▼                                 ▼
┌──────────────────┐              ┌──────────────────┐
│ Show Progress    │              │ For each file:   │
│ Dialog           │              │                  │
│                  │◄─────────────┤ 1. Emit event    │
│ [████████░░] 80% │              │ 2. Copy file     │
│                  │              │ 3. Update progress│
└──────────────────┘              └──────────┬───────┘
           │                                 │
           │                                 │
           └─────────────┬───────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │ Operation Result │
              │                  │
              │ Success: true    │
              │ Processed: 3     │
              │ Failed: 0        │
              └──────────┬───────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
            ▼            ▼            ▼
    ┌─────────────┐ ┌────────┐ ┌──────────┐
    │ Refresh     │ │ Close  │ │ Update   │
    │ Panels      │ │ Dialog │ │ Status   │
    └─────────────┘ └────────┘ └──────────┘
```

---

## Search Engine Component

```
┌─────────────────────────────────────────────────────────┐
│                    SearchEngine                         │
│                                                         │
│  Search Types:                                          │
│  ┌───────────────────────────────────────────────────┐│
│  │ 1. Name Search (Pattern Matching)                ││
│  │    - Glob patterns: *.txt, test*.py              ││
│  │    - Regex support: ^file[0-9]+\.txt$            ││
│  │    - Case sensitive/insensitive                   ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  ┌───────────────────────────────────────────────────┐│
│  │ 2. Content Search (Full-Text)                    ││
│  │    - Search within file contents                 ││
│  │    - Returns matching lines with context         ││
│  │    - Optional file pattern filter                ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  ┌───────────────────────────────────────────────────┐│
│  │ 3. Attribute Search                              ││
│  │    - Size range: 1MB - 10MB                      ││
│  │    - Date range: Last 7 days                     ││
│  │    - Permissions: rwx pattern                    ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  Implementation:                                        │
│  ┌───────────────────────────────────────────────────┐│
│  │ async def search_by_name(                        ││
│  │     root: Path,                                  ││
│  │     pattern: str,                                ││
│  │     recursive: bool = True                       ││
│  │ ) -> AsyncIterator[FileEntry]:                  ││
│  │                                                   ││
│  │     # Stream results as found                    ││
│  │     async for entry in scan_directory(root):    ││
│  │         if matches_pattern(entry.name, pattern):││
│  │             yield entry                          ││
│  │             await asyncio.sleep(0)  # Yield loop││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  Performance Features:                                  │
│  ├─ Async iteration for responsiveness                 │
│  ├─ Cancellation support                               │
│  ├─ Result streaming (no memory buildup)               │
│  └─ Optional indexing for large directories            │
└─────────────────────────────────────────────────────────┘

Search Flow:
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│User Input│────▶│Build Query│────▶│Execute   │────▶│Stream    │
│"*.py"    │     │Pattern    │     │Search    │     │Results   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                         │
                                         ▼
                                  ┌──────────────┐
                                  │Update UI with│
                                  │each result   │
                                  │(No blocking) │
                                  └──────────────┘
```

---

## Archive Handler Component

```
┌─────────────────────────────────────────────────────────┐
│                   ArchiveHandler                        │
│                                                         │
│  Supported Formats:                                     │
│  ┌──────────┬─────────┬──────────┬────────────────┐   │
│  │ Format   │ Read    │ Write    │ Implementation │   │
│  ├──────────┼─────────┼──────────┼────────────────┤   │
│  │ ZIP      │ ✓       │ ✓        │ zipfile        │   │
│  │ TAR      │ ✓       │ ✓        │ tarfile        │   │
│  │ TAR.GZ   │ ✓       │ ✓        │ tarfile        │   │
│  │ TAR.BZ2  │ ✓       │ ✓        │ tarfile        │   │
│  │ 7Z       │ ✓       │ ✗        │ py7zr (opt)    │   │
│  │ RAR      │ ✓       │ ✗        │ rarfile (opt)  │   │
│  └──────────┴─────────┴──────────┴────────────────┘   │
│                                                         │
│  Operations:                                            │
│  ┌───────────────────────────────────────────────────┐│
│  │ create_archive()                                  ││
│  │  ├─ Select files/directories                      ││
│  │  ├─ Choose format and compression level          ││
│  │  ├─ Create archive with progress updates         ││
│  │  └─ Verify integrity (optional)                  ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  ┌───────────────────────────────────────────────────┐│
│  │ extract_archive()                                 ││
│  │  ├─ List archive contents                         ││
│  │  ├─ Select files to extract (or all)             ││
│  │  ├─ Choose destination                            ││
│  │  ├─ Extract with progress updates                ││
│  │  ├─ Handle conflicts (overwrite/skip/rename)     ││
│  │  └─ Security: Check for path traversal attacks   ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  ┌───────────────────────────────────────────────────┐│
│  │ list_archive()                                    ││
│  │  └─ Browse archive like directory (VFS mode)     ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  Security Checks:                                       │
│  ├─ Path traversal detection (../../etc/passwd)        │
│  ├─ Archive bomb protection (compression ratio)        │
│  ├─ Size limit validation                              │
│  └─ Filename sanitization                              │
└─────────────────────────────────────────────────────────┘

Archive Extraction Flow:
┌───────────┐
│Select .zip│
│ file      │
└─────┬─────┘
      │
      ▼
┌──────────────┐
│List contents │
│              │
│ file1.txt    │
│ file2.py     │
│ docs/        │
└─────┬────────┘
      │
      ▼
┌──────────────┐       ┌──────────────┐
│Select files  │──────▶│Security check│
│to extract    │       │ - Paths      │
│              │       │ - Size       │
└─────┬────────┘       └──────┬───────┘
      │                       │
      ▼                       ▼
┌──────────────┐       ┌──────────────┐
│Choose dest   │       │Extract files │
│directory     │       │with progress │
└─────┬────────┘       └──────┬───────┘
      │                       │
      └───────────┬───────────┘
                  ▼
            ┌──────────┐
            │Complete! │
            └──────────┘
```

---

## Event System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    EventBus System                      │
│                                                         │
│  Event Types:                                           │
│  ┌───────────────────────────────────────────────────┐│
│  │ Navigation Events                                 ││
│  │  ├─ PanelNavigationEvent                          ││
│  │  ├─ DirectoryChangedEvent                         ││
│  │  └─ BookmarkNavigationEvent                       ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  ┌───────────────────────────────────────────────────┐│
│  │ File Operation Events                             ││
│  │  ├─ CopyStartedEvent                              ││
│  │  ├─ CopyProgressEvent                             ││
│  │  ├─ CopyCompletedEvent                            ││
│  │  ├─ DeleteConfirmationEvent                       ││
│  │  └─ OperationErrorEvent                           ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  ┌───────────────────────────────────────────────────┐│
│  │ Selection Events                                  ││
│  │  ├─ FileSelectedEvent                             ││
│  │  ├─ FileDeselectedEvent                           ││
│  │  └─ SelectionClearedEvent                         ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  ┌───────────────────────────────────────────────────┐│
│  │ UI Events                                         ││
│  │  ├─ ThemeChangedEvent                             ││
│  │  ├─ PanelFocusEvent                               ││
│  │  └─ ConfigurationChangedEvent                     ││
│  └───────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘

Event Flow Example (File Copy):

┌─────────────┐
│FileOperations│
└──────┬───────┘
       │ emit(CopyStartedEvent)
       ├────────────────────┬─────────────────────┐
       │                    │                     │
       ▼                    ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│ProgressDialog│    │  StatusBar   │    │  FilPanel   │
│              │    │              │    │             │
│ Show dialog  │    │ Update text  │    │ Lock input  │
└──────────────┘    └──────────────┘    └─────────────┘

       │ emit(CopyProgressEvent) x N times
       ├────────────────────┐
       │                    │
       ▼                    ▼
┌──────────────┐    ┌──────────────┐
│ProgressDialog│    │  StatusBar   │
│              │    │              │
│ Update bar   │    │ "Copying..." │
└──────────────┘    └──────────────┘

       │ emit(CopyCompletedEvent)
       ├────────────────────┬─────────────────────┐
       │                    │                     │
       ▼                    ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│ProgressDialog│    │  StatusBar   │    │  FilPanel   │
│              │    │              │    │             │
│ Close dialog │    │ "3 files    │    │ Refresh     │
│              │    │  copied"     │    │ Unlock input│
└──────────────┘    └──────────────┘    └─────────────┘
```

---

## Platform Abstraction Architecture

```
┌─────────────────────────────────────────────────────────┐
│           FileSystemInterface (Abstract)                │
│                                                         │
│  Abstract Methods:                                      │
│  ├─ list_directory(path: Path) -> List[FileEntry]      │
│  ├─ get_file_info(path: Path) -> FileInfo              │
│  ├─ read_file(path: Path) -> bytes                     │
│  ├─ write_file(path: Path, content: bytes) -> None     │
│  ├─ copy(source: Path, dest: Path) -> None             │
│  ├─ move(source: Path, dest: Path) -> None             │
│  ├─ delete(path: Path) -> None                         │
│  └─ exists(path: Path) -> bool                         │
└─────────────────────────────────────────────────────────┘
                            △
                            │ implements
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│Windows       │    │Linux         │    │macOS         │
│FileSystem    │    │FileSystem    │    │FileSystem    │
├──────────────┤    ├──────────────┤    ├──────────────┤
│              │    │              │    │              │
│Specific:     │    │Specific:     │    │Specific:     │
│- Drive letters│    │- Mount points│    │- Volumes     │
│- UNC paths   │    │- Symlinks    │    │- App bundles │
│- Long paths  │    │- Permissions │    │- .DS_Store   │
│- Attributes  │    │- Ext attrs   │    │- Metadata    │
│              │    │              │    │              │
│Uses:         │    │Uses:         │    │Uses:         │
│- os.scandir  │    │- os.scandir  │    │- os.scandir  │
│- pathlib     │    │- pathlib     │    │- pathlib     │
│- win32api    │    │- pwd/grp     │    │- Foundation  │
│              │    │              │    │ (optional)   │
└──────────────┘    └──────────────┘    └──────────────┘

Factory Pattern:
┌──────────────────────────────────────┐
│  FileSystemAdapter.create()          │
│                                      │
│  platform = detect_platform()        │
│                                      │
│  if platform == WINDOWS:             │
│      return WindowsFileSystem()      │
│  elif platform == LINUX:             │
│      return LinuxFileSystem()        │
│  elif platform == MACOS:             │
│      return MacOSFileSystem()        │
│  else:                               │
│      return GenericFileSystem()      │
└──────────────────────────────────────┘
```

---

## Keyboard Handler Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 KeyboardHandler System                  │
│                                                         │
│  Key Binding Registry:                                  │
│  ┌───────────────────────────────────────────────────┐│
│  │ Key        Action            Priority  Context    ││
│  ├───────────────────────────────────────────────────┤│
│  │ F1         show_help()           100    global    ││
│  │ F3         view_file()           100    panel     ││
│  │ F4         edit_file()           100    panel     ││
│  │ F5         copy_files()          100    panel     ││
│  │ Tab        switch_panel()        100    global    ││
│  │ Insert     toggle_selection()     90    panel     ││
│  │ Ctrl+R     refresh_panel()        80    panel     ││
│  │ Ctrl+O     toggle_panels()        80    global    ││
│  │ Alt+F7     search_dialog()        80    global    ││
│  │ /          quick_search()         50    panel     ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  Handler Chain (Priority Order):                       │
│  ┌───────────────────────────────────────────────────┐│
│  │                                                   ││
│  │  Key Press Event                                 ││
│  │        │                                          ││
│  │        ▼                                          ││
│  │  ┌──────────────┐                                ││
│  │  │Context Filter│  ──► Check if key applies     ││
│  │  └──────┬───────┘      to current context       ││
│  │         │                                         ││
│  │         ▼                                         ││
│  │  ┌──────────────┐                                ││
│  │  │Priority Sort │  ──► Order by priority        ││
│  │  └──────┬───────┘      (highest first)          ││
│  │         │                                         ││
│  │         ▼                                         ││
│  │  ┌──────────────┐                                ││
│  │  │ Try Handler  │  ──► Execute handler          ││
│  │  └──────┬───────┘      Return if handled        ││
│  │         │                                         ││
│  │         ├──► Handled: Stop chain                ││
│  │         └──► Not handled: Next in chain         ││
│  │                                                   ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  Example: F5 Copy Operation                            │
│  ┌───────────────────────────────────────────────────┐│
│  │ 1. User presses F5                                ││
│  │ 2. KeyboardHandler receives event                 ││
│  │ 3. Check context: "panel" ✓                       ││
│  │ 4. Check files selected: Yes ✓                    ││
│  │ 5. Execute: copy_files()                          ││
│  │    ├─ Get selected files from active panel       ││
│  │    ├─ Get destination from inactive panel        ││
│  │    ├─ Show confirmation dialog                   ││
│  │    └─ Trigger FileOperations.copy_files()        ││
│  │ 6. Return handled=True                            ││
│  └───────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## Configuration System

```
┌─────────────────────────────────────────────────────────┐
│              Configuration Architecture                 │
│                                                         │
│  Configuration Sources (Priority Order):                │
│  ┌───────────────────────────────────────────────────┐│
│  │ 1. Command Line Arguments (--flag=value)          ││
│  │    └─ Highest priority                            ││
│  │                                                    ││
│  │ 2. User Config File (~/.config/mc/config.toml)   ││
│  │    └─ User-specific settings                      ││
│  │                                                    ││
│  │ 3. System Config File (/etc/mc/config.toml)      ││
│  │    └─ System-wide defaults                        ││
│  │                                                    ││
│  │ 4. Built-in Defaults (config/default_config.toml)││
│  │    └─ Fallback values                             ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  Configuration Structure:                               │
│  ┌───────────────────────────────────────────────────┐│
│  │ [general]                                         ││
│  │ startup_directory = "~"                           ││
│  │ show_hidden_files = false                         ││
│  │ confirm_deletions = true                          ││
│  │                                                    ││
│  │ [appearance]                                      ││
│  │ theme = "classic"                                 ││
│  │ date_format = "%Y-%m-%d %H:%M"                    ││
│  │                                                    ││
│  │ [panels]                                          ││
│  │ sync_navigation = false                           ││
│  │ sort_by = "name"                                  ││
│  │                                                    ││
│  │ [keybindings]                                     ││
│  │ quick_search = "Ctrl+S"                           ││
│  │ bookmark_add = "Ctrl+D"                           ││
│  │                                                    ││
│  │ [file_operations]                                 ││
│  │ copy_buffer_size = 65536                          ││
│  │ verify_checksums = false                          ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  Configuration Loading Flow:                            │
│  ┌───────────────────────────────────────────────────┐│
│  │                                                   ││
│  │  App Startup                                      ││
│  │       │                                            ││
│  │       ▼                                            ││
│  │  Load Defaults ───┐                               ││
│  │       │           │                                ││
│  │       ▼           ▼                                ││
│  │  Load System  Load User                           ││
│  │    Config      Config                             ││
│  │       │           │                                ││
│  │       └─────┬─────┘                                ││
│  │             │                                      ││
│  │             ▼                                      ││
│  │      Merge Configs  ◄─── Apply CLI args          ││
│  │             │                                      ││
│  │             ▼                                      ││
│  │      Validate Config                              ││
│  │             │                                      ││
│  │             ▼                                      ││
│  │      Freeze Config (immutable)                    ││
│  │             │                                      ││
│  │             ▼                                      ││
│  │      Inject into components                       ││
│  │                                                   ││
│  └───────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## Plugin System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Plugin Architecture                    │
│                                                         │
│  Plugin Discovery:                                      │
│  ┌───────────────────────────────────────────────────┐│
│  │ ~/.config/modern-commander/plugins/               ││
│  │  ├─ image_viewer.py        (FileViewerPlugin)    ││
│  │  ├─ ftp_upload.py          (OperationPlugin)     ││
│  │  ├─ syntax_highlighter.py  (EditorPlugin)        ││
│  │  └─ custom_theme.py        (ThemePlugin)         ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  Plugin Interface Hierarchy:                            │
│  ┌───────────────────────────────────────────────────┐│
│  │                                                   ││
│  │         PluginInterface (Base)                    ││
│  │                  △                                 ││
│  │                  │                                 ││
│  │     ┌────────────┼────────────┐                   ││
│  │     │            │            │                   ││
│  │     ▼            ▼            ▼                   ││
│  │ FileViewer  Operation    Editor                   ││
│  │  Plugin      Plugin      Plugin                   ││
│  │                                                   ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  Plugin Lifecycle:                                      │
│  ┌───────────────────────────────────────────────────┐│
│  │                                                   ││
│  │  ┌──────────┐                                     ││
│  │  │ Discover │  ──► Scan plugin directory         ││
│  │  └────┬─────┘                                     ││
│  │       │                                            ││
│  │       ▼                                            ││
│  │  ┌──────────┐                                     ││
│  │  │  Load    │  ──► Import plugin modules         ││
│  │  └────┬─────┘                                     ││
│  │       │                                            ││
│  │       ▼                                            ││
│  │  ┌──────────┐                                     ││
│  │  │Validate  │  ──► Check interface compliance    ││
│  │  └────┬─────┘                                     ││
│  │       │                                            ││
│  │       ▼                                            ││
│  │  ┌──────────┐                                     ││
│  │  │Initialize│  ──► Call plugin.initialize()      ││
│  │  └────┬─────┘                                     ││
│  │       │                                            ││
│  │       ▼                                            ││
│  │  ┌──────────┐                                     ││
│  │  │ Register │  ──► Add to plugin registry        ││
│  │  └────┬─────┘                                     ││
│  │       │                                            ││
│  │       ▼                                            ││
│  │  ┌──────────┐                                     ││
│  │  │  Active  │  ◄─► Handle events/requests        ││
│  │  └────┬─────┘                                     ││
│  │       │                                            ││
│  │       ▼                                            ││
│  │  ┌──────────┐                                     ││
│  │  │ Shutdown │  ──► Call plugin.shutdown()        ││
│  │  └──────────┘                                     ││
│  │                                                   ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  Example Plugin (Image Viewer):                         │
│  ┌───────────────────────────────────────────────────┐│
│  │ class ImageViewerPlugin(FileViewerPlugin):        ││
│  │     name = "Image Viewer"                         ││
│  │     version = "1.0.0"                             ││
│  │     supported = ['.png', '.jpg', '.gif']          ││
│  │                                                    ││
│  │     def can_handle(self, path: Path) -> bool:    ││
│  │         return path.suffix in self.supported     ││
│  │                                                    ││
│  │     async def view_file(self, path: Path):       ││
│  │         image = load_image(path)                 ││
│  │         ascii_art = convert_to_ascii(image)      ││
│  │         return ImageWidget(ascii_art)            ││
│  └───────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## State Management

```
┌─────────────────────────────────────────────────────────┐
│              Application State Architecture             │
│                                                         │
│  State Components:                                      │
│  ┌───────────────────────────────────────────────────┐│
│  │ AppState (Global)                                 ││
│  │  ├─ active_panel: "left" | "right"                ││
│  │  ├─ config: Configuration                         ││
│  │  ├─ clipboard: List[Path]                         ││
│  │  ├─ bookmarks: Dict[str, Path]                    ││
│  │  └─ history: List[Path]                           ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  ┌───────────────────────────────────────────────────┐│
│  │ PanelState (Per Panel)                            ││
│  │  ├─ current_path: Path (reactive)                 ││
│  │  ├─ entries: List[FileEntry] (reactive)           ││
│  │  ├─ selected: Set[Path] (reactive)                ││
│  │  ├─ cursor_position: int (reactive)               ││
│  │  ├─ sort_order: SortOrder (reactive)              ││
│  │  └─ filter_pattern: str | None (reactive)         ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  ┌───────────────────────────────────────────────────┐│
│  │ OperationState (During Operations)                ││
│  │  ├─ operation_type: "copy" | "move" | "delete"   ││
│  │  ├─ total_files: int                              ││
│  │  ├─ processed_files: int (reactive)               ││
│  │  ├─ current_file: Path | None (reactive)          ││
│  │  ├─ bytes_total: int                              ││
│  │  ├─ bytes_processed: int (reactive)               ││
│  │  └─ errors: List[str] (reactive)                  ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  Reactive Update Flow:                                  │
│  ┌───────────────────────────────────────────────────┐│
│  │                                                   ││
│  │  State Change (panel.current_path = new_path)    ││
│  │         │                                          ││
│  │         ▼                                          ││
│  │  Textual Reactive System detects change          ││
│  │         │                                          ││
│  │         ▼                                          ││
│  │  Trigger watchers/computed properties            ││
│  │         │                                          ││
│  │         ├──► Update breadcrumb display            ││
│  │         ├──► Reload file list                     ││
│  │         ├──► Clear selection                      ││
│  │         └──► Emit navigation event                ││
│  │                                                   ││
│  └───────────────────────────────────────────────────┘│
│                                                         │
│  State Persistence:                                     │
│  ┌───────────────────────────────────────────────────┐│
│  │ On Shutdown:                                      ││
│  │  ├─ Save current paths                            ││
│  │  ├─ Save bookmarks                                ││
│  │  ├─ Save command history                          ││
│  │  └─ Save window state (if applicable)             ││
│  │                                                    ││
│  │ On Startup:                                       ││
│  │  ├─ Restore last session paths                    ││
│  │  ├─ Restore bookmarks                             ││
│  │  └─ Restore UI preferences                        ││
│  └───────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

**End of Component Diagrams**

*Version 1.0.0 - 2025-10-05*
