# File Viewer (F3) - Documentation

## Overview

The File Viewer provides comprehensive file viewing capabilities with syntax highlighting, hex viewing, and advanced navigation features. It's designed to handle both text and binary files efficiently.

## Features

### Text File Viewing
- **Syntax Highlighting**: Automatic language detection and syntax highlighting for:
  - Python (.py)
  - JavaScript/TypeScript (.js, .ts, .jsx, .tsx)
  - HTML/CSS (.html, .css)
  - JSON/YAML (.json, .yaml, .yml)
  - Markdown (.md)
  - Shell scripts (.sh)
  - SQL (.sql)
  - C/C++ (.c, .cpp, .h)
  - Java (.java)
  - Rust (.rs)
  - Go (.go)
  - Ruby (.rb)
  - PHP (.php)

- **Encoding Support**: Automatic encoding detection with fallback:
  - UTF-8 (primary)
  - Latin-1
  - CP1252
  - ISO-8859-1

### Binary File Viewing
- **Hex Dump Format**: Professional hex view with:
  - Hexadecimal offset column
  - Hex byte representation
  - ASCII character representation
  - 16 bytes per line display

- **Automatic Binary Detection**: Detects binary files by:
  - Checking for null bytes
  - Testing Unicode decode failures
  - Fallback to hex view for binary content

### Navigation

#### Keyboard Controls
| Key | Action | Description |
|-----|--------|-------------|
| `↑` / `k` | Scroll Up | Move up one line |
| `↓` / `j` | Scroll Down | Move down one line |
| `Page Up` | Page Up | Scroll up one page |
| `Page Down` / `Space` | Page Down | Scroll down one page |
| `Home` / `g` | Go to Start | Jump to beginning of file |
| `End` | Go to End | Jump to end of file |

#### Advanced Navigation
| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+G` | Go to Line | Jump to specific line number |
| `/` / `Ctrl+F` | Search | Search for text in file |
| `n` | Next Match | Jump to next search result |
| `Shift+N` | Previous Match | Jump to previous search result |

### View Controls
| Key | Action | Description |
|-----|--------|-------------|
| `h` | Toggle Hex | Switch between text and hex view |
| `w` | Toggle Wrap | Enable/disable line wrapping |
| `Escape` / `q` / `F3` | Quit | Close viewer and return |

## Status Bar

The status bar displays:
- **File Name**: Current file name
- **File Size**: Human-readable file size (B, KB, MB, GB, TB, PB)
- **Line Position**: Current line / total lines
- **Percentage**: Position in file as percentage
- **View Mode**: Current encoding (UTF-8, etc.) or "HEX" for hex view
- **Wrap Status**: "WRAP" or "NOWRAP"

## Usage Examples

### Basic Usage

```python
from pathlib import Path
from features import FileViewer

# View a text file
file_path = Path("example.py")
viewer = FileViewer(file_path)
app.push_screen(viewer)
```

### Integration with Modern Commander

```python
class CommanderApp(App):
    def action_view_file(self) -> None:
        """View selected file (F3)."""
        current_item = self.get_current_file()
        if current_item and current_item.is_file():
            self.push_screen(FileViewer(current_item.path))

    BINDINGS = [
        Binding("f3", "view_file", "View"),
    ]
```

## Technical Details

### File Size Limits
- **Syntax Highlighting**: Disabled for files > 100,000 characters
- **Memory Efficient**: Loads entire file but displays only visible portion
- **Large Files**: Can handle files of several megabytes efficiently

### Performance
- **Fast Loading**: Optimized file reading with encoding detection
- **Smooth Scrolling**: Efficient viewport rendering
- **Search Performance**: Quick text search with result caching

### Error Handling
- **File Not Found**: Clear error message display
- **Permission Denied**: Graceful error handling
- **Encoding Errors**: Automatic fallback to safe encodings
- **Binary Detection**: Automatic switch to hex view

## Accessibility

- **Keyboard Navigation**: All features accessible via keyboard
- **Clear Visual Feedback**: Status bar with comprehensive information
- **Error Messages**: Descriptive error notifications
- **No Mouse Required**: Complete keyboard-only operation

## Limitations

### Current Limitations
- Cannot edit files (use File Editor F4 for editing)
- No real-time file monitoring
- Search is case-insensitive only
- Regular expressions not supported in search

### Future Enhancements
- Bookmarks for frequently viewed files
- Multiple file tabs
- File comparison mode
- Regular expression search
- Real-time file monitoring
- Customizable color schemes

## Code Quality

### Design Principles
- **WCAG 2.1 AA Compliance**: Accessible keyboard navigation
- **Performance Optimized**: Efficient memory usage
- **Error Resilient**: Comprehensive error handling
- **User-Centric**: Clear feedback and intuitive controls

### Testing
- Test with various file encodings
- Test with different file sizes
- Test binary file detection
- Test search functionality
- Test navigation edge cases

## See Also

- [File Editor (F4)](FILE_EDITOR.md) - For editing files
- [Modern Commander](README.md) - Main application documentation
- [Keyboard Shortcuts](KEYBOARD_SHORTCUTS.md) - Complete shortcut reference
