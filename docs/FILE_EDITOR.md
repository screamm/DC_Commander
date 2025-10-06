# File Editor (F4) - Documentation

## Overview

The File Editor provides comprehensive text editing capabilities with syntax highlighting, undo/redo, search/replace, and auto-save functionality. It's a full-featured text editor integrated into Modern Commander.

## Features

### Text Editing
- **Full Text Editing**: Complete text manipulation capabilities
- **Syntax Highlighting**: Language-aware highlighting for:
  - Python (.py)
  - JavaScript/TypeScript (.js, .ts, .jsx, .tsx)
  - HTML/CSS (.html, .css)
  - JSON/YAML (.json, .yaml, .yml)
  - Markdown (.md)
  - Shell scripts (.sh)
  - SQL (.sql)
  - TOML/INI (.toml, .ini)
  - Plain text (.txt)

- **Encoding Support**: Multi-encoding support with detection:
  - UTF-8 (primary)
  - Latin-1
  - CP1252
  - ISO-8859-1

### File Operations
- **Save**: Manual save with Ctrl+S
- **Auto-Save**: Automatic save every 30 seconds
- **Save Confirmation**: Prompts before closing with unsaved changes
- **Create New Files**: Supports creating files that don't exist

### Editing Features

#### Undo/Redo
- **Undo**: `Ctrl+Z` - Undo last change
- **Redo**: `Ctrl+Y` or `Ctrl+Shift+Z` - Redo undone change
- **Unlimited History**: Full edit history maintained

#### Cut/Copy/Paste
- **Cut**: `Ctrl+X` - Cut selected text
- **Copy**: `Ctrl+C` - Copy selected text
- **Paste**: `Ctrl+V` - Paste from clipboard
- **Select All**: `Ctrl+A` - Select entire document

### Search and Replace

#### Find
- **Find**: `Ctrl+F` - Search for text
- **Find Next**: `F3` or `n` - Jump to next match
- **Find Previous**: `Shift+F3` or `Shift+N` - Jump to previous match
- **Case-Insensitive**: Search ignores case by default

#### Replace
- **Replace**: `Ctrl+H` - Replace text
- **Replace All**: Replaces all occurrences at once
- **Count Matches**: Shows number of replacements made

### Navigation
| Key | Action | Description |
|-----|--------|-------------|
| `Ctrl+G` | Go to Line | Jump to specific line number |
| `Arrow Keys` | Move Cursor | Standard cursor movement |
| `Home` | Line Start | Jump to beginning of line |
| `End` | Line End | Jump to end of line |
| `Ctrl+Home` | File Start | Jump to beginning of file |
| `Ctrl+End` | File End | Jump to end of file |

### Exit Controls
| Key | Action | Description |
|-----|--------|-------------|
| `Escape` / `Ctrl+Q` / `F4` | Quit | Close editor (checks for unsaved changes) |
| `Ctrl+S` | Save | Save current file |

## Status Bar

The status bar displays:
- **File Name**: Current file name
- **File Size**: Human-readable size of current content
- **Line Position**: Current line / total lines
- **Column Position**: Current column number
- **Encoding**: Character encoding (UTF-8, etc.)
- **Last Saved**: Timestamp of last save
- **Modified Status**: `[modified]` or `[saved]` indicator

### Modified Indicator
- **[modified]**: File has unsaved changes (yellow)
- **[saved]**: File is saved (green)

## Usage Examples

### Basic Usage

```python
from pathlib import Path
from features import FileEditor

# Edit existing file
file_path = Path("example.py")
editor = FileEditor(file_path)
app.push_screen(editor)

# Create new file
new_file = Path("new_script.py")
editor = FileEditor(new_file, create_new=True)
app.push_screen(editor)
```

### Integration with Modern Commander

```python
class CommanderApp(App):
    def action_edit_file(self) -> None:
        """Edit selected file (F4)."""
        current_item = self.get_current_file()
        if current_item:
            if current_item.is_file():
                # Edit existing file
                self.push_screen(FileEditor(current_item.path))
            else:
                # Create new file
                file_name = self.prompt_filename()
                if file_name:
                    new_path = current_item.path / file_name
                    self.push_screen(FileEditor(new_path, create_new=True))

    BINDINGS = [
        Binding("f4", "edit_file", "Edit"),
    ]
```

## Auto-Save Feature

### Configuration
- **Interval**: 30 seconds (configurable)
- **Enabled by Default**: Yes
- **Notification**: Shows brief "Auto-saved" message
- **Background Thread**: Non-blocking operation

### How It Works
1. Editor checks for modifications every 30 seconds
2. If file is modified, auto-save is triggered
3. Background thread handles save operation
4. User receives brief notification on successful save
5. Status bar updates to show save time

### Disabling Auto-Save

```python
editor = FileEditor(file_path)
editor.auto_save_enabled = False  # Disable auto-save
```

## Search and Replace Workflow

### Find Workflow
1. Press `Ctrl+F` to open find dialog
2. Enter search term
3. Press Enter to find first match
4. Use `F3` or `n` for next match
5. Use `Shift+F3` or `Shift+N` for previous match
6. Search wraps around at file boundaries

### Replace Workflow
1. Press `Ctrl+H` to open replace dialog
2. Enter find term, press Enter
3. Enter replace term, press Enter
4. All occurrences are replaced immediately
5. Notification shows count of replacements
6. Undo (Ctrl+Z) if needed

## Technical Details

### Performance
- **Efficient Rendering**: Only visible text is rendered
- **Fast Search**: Optimized string matching
- **Responsive Editing**: Smooth typing and cursor movement
- **Auto-Save Thread**: Background save doesn't block UI

### Memory Management
- **Efficient Storage**: Text stored as single string
- **Undo Stack**: Maintained by TextArea widget
- **Auto-Save Thread**: Properly cleaned up on exit

### File Safety
- **Unsaved Changes Check**: Prompts before closing
- **Encoding Preservation**: Maintains original encoding
- **Parent Directory Creation**: Creates directories if needed
- **Atomic Writes**: Safe file writing operation

### Error Handling
- **File Not Found**: Allows creation of new files
- **Permission Denied**: Clear error message
- **Encoding Errors**: Automatic fallback to safe encodings
- **Save Failures**: Non-destructive, preserves content

## Accessibility

- **Keyboard Navigation**: All features keyboard-accessible
- **Clear Visual Feedback**: Status bar with comprehensive info
- **Error Messages**: Descriptive error notifications
- **No Mouse Required**: Complete keyboard-only operation
- **WCAG 2.1 AA Compliant**: Accessible keyboard controls

## Limitations

### Current Limitations
- **Text Files Only**: Cannot edit binary files
- **In-Memory Editing**: Entire file loaded into memory
- **Single File**: Cannot edit multiple files simultaneously
- **Simple Search**: No regular expressions
- **Case-Insensitive Only**: Search doesn't support case-sensitive mode

### File Size Recommendations
- **Optimal**: < 1 MB for best performance
- **Good**: 1-10 MB acceptable performance
- **Slow**: > 10 MB may have performance issues
- **Maximum**: Limited by available RAM

## Future Enhancements

### Planned Features
- Multiple file tabs
- Regular expression search
- Case-sensitive search option
- Block selection mode
- Code folding
- Bracket matching
- Auto-completion
- Snippet support
- Customizable key bindings
- Theme customization

### Advanced Features
- Diff view for file comparison
- Git integration
- Spell checking
- Find in files (project-wide search)
- Multi-cursor editing
- Column mode editing

## Code Quality

### Design Principles
- **User-First Design**: Prioritizes usability and clarity
- **WCAG 2.1 AA Compliance**: Accessible to all users
- **Performance Optimized**: Efficient memory and CPU usage
- **Error Resilient**: Comprehensive error handling
- **Data Safety**: Auto-save and unsaved changes protection

### Testing Recommendations
- Test with various file encodings
- Test with different file sizes
- Test auto-save functionality
- Test search and replace
- Test undo/redo operations
- Test unsaved changes prompts
- Test file creation workflow

## Integration Guide

### Custom Editor Configuration

```python
class CustomEditor(FileEditor):
    def __init__(self, file_path: Path, **kwargs):
        super().__init__(file_path, **kwargs)
        # Customize auto-save interval
        self.auto_save_interval = 60  # 60 seconds

    def _save_file(self) -> bool:
        """Custom save logic."""
        # Add custom save handling
        result = super()._save_file()
        if result:
            # Custom post-save actions
            self.notify("Custom save completed!")
        return result
```

### Event Handling

```python
def on_text_area_changed(self, event: TextArea.Changed) -> None:
    """Handle text changes."""
    # Custom change handling
    super().on_text_area_changed(event)
    # Add your custom logic
```

## See Also

- [File Viewer (F3)](FILE_VIEWER.md) - For viewing files
- [Modern Commander](README.md) - Main application documentation
- [Keyboard Shortcuts](KEYBOARD_SHORTCUTS.md) - Complete shortcut reference
- [Configuration Guide](CONFIGURATION.md) - Customization options
