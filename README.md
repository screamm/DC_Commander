# DC Commander

![DC Commander Screenshot](assets/dccommanderscreenshot.png)

A modern, cross-platform Norton Commander-style file manager built with Python and Textual.

## Features

- **Dual-Panel Interface** - Norton Commander-style two-panel layout for efficient file management
- **Cross-Platform** - Native support for Windows 11, Linux, and macOS
- **Keyboard-Driven** - Complete keyboard navigation with F-key shortcuts
- **File Operations** - Copy, move, delete with progress tracking
- **Archive Support** - Browse and manage ZIP/TAR archives
- **Built-in Viewer/Editor** - View (F3) and edit (F4) text files
- **Search Engine** - Search by name, content, size, or date
- **Extensible** - Plugin system for custom functionality
- **Themeable** - Classic and modern themes with customization

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py
```

## Technology Stack

- **Python 3.11+** - Modern Python with async/await support
- **Textual 0.40+** - Modern TUI framework with reactive UI
- **aiofiles** - Async file I/O operations
- **Rich** - Beautiful terminal formatting

## Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| F1 | Help | Show help screen |
| F3 | View | View file contents |
| F4 | Edit | Edit file |
| F5 | Copy | Copy selected files |
| F6 | Move | Move selected files |
| F7 | MkDir | Create directory |
| F8 | Delete | Delete selected files |
| F10 | Quit | Exit application |
| Tab | Switch Panel | Toggle between panels |
| Insert | Select | Select/deselect file |

## Project Structure

```
DC Commander/
├── src/modern_commander/    # Application source code
│   ├── core/                # Core models and interfaces
│   ├── components/          # UI components
│   ├── operations/          # Business logic
│   └── platform/            # Platform abstraction
├── tests/                   # Test suite
├── docs/                    # Documentation
└── examples/                # Example configurations
```

## Documentation

- [Architecture Overview](architecture.md) - System architecture and design
- [Component Diagrams](component-diagrams.md) - Visual architecture reference
- [Implementation Roadmap](implementation-roadmap.md) - Development plan
- [Design Decisions](design-decisions.md) - Architectural decisions

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src

# Development mode
python -m modern_commander
```

## License

MIT License - See LICENSE file for details

## Acknowledgments

Inspired by Norton Commander (1986) and built with the excellent Textual framework by Textualize.
