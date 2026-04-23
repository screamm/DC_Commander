# Contributing to DC Commander

Thanks for your interest in DC Commander. This document explains how to set up
a development environment, what the project layout looks like, and how to land
a change — whether that is a small bug fix or a new feature.

The project is written in Python 3.10+ on top of [Textual](https://textual.textualize.io/).
It is a TUI (terminal user interface) application inspired by Norton Commander.

By participating you agree to behave according to the
[Contributor Covenant](https://www.contributor-covenant.org/) code of conduct:
be respectful, assume good intent, and keep discussions on-topic.

---

## Table of contents

- [Development setup](#development-setup)
- [Project structure](#project-structure)
- [Code style](#code-style)
- [Branching and commits](#branching-and-commits)
- [Pull requests](#pull-requests)
- [Testing](#testing)
- [Running specific checks](#running-specific-checks)
- [Reporting bugs](#reporting-bugs)
- [Questions and discussion](#questions-and-discussion)

---

## Development setup

### Prerequisites

- **Python 3.10 or newer** (3.10, 3.11, 3.12 are all supported and tested)
- **Git**
- A terminal that renders a modern TUI reasonably well — Windows Terminal,
  iTerm2, Kitty, Alacritty, WezTerm, or a recent GNOME Terminal all work.
  Plain `cmd.exe` works but has limited colour and Unicode support.

### Clone and create a virtual environment

```bash
git clone https://github.com/yourusername/dc-commander.git
cd dc-commander

python -m venv .venv

# Activate the venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Windows (cmd)
.venv\Scripts\activate.bat
# macOS / Linux
source .venv/bin/activate
```

### Install the project with development extras

The project declares its dev dependencies under the `dev` extra in
`pyproject.toml`, so a single editable install is enough:

```bash
pip install -e ".[dev]"
```

This pulls in `pytest`, `pytest-cov`, `pytest-asyncio`, `mypy`, `ruff`,
`pre-commit`, `bandit`, and everything else needed for the full test and
quality pipeline.

If the `dev` extra is unavailable for some reason (e.g. a stripped-down
environment), you can install the minimum manually:

```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio mypy ruff pre-commit
```

### Install the pre-commit hooks

```bash
pre-commit install
pre-commit install --hook-type commit-msg  # enables Conventional Commits check
```

From now on, `ruff`, `mypy`, `bandit`, and a set of general hygiene hooks run
automatically on every `git commit`, and the commit message is checked against
the Conventional Commits convention.

### Run the test suite

```bash
pytest
```

The default configuration produces HTML coverage at `htmlcov/index.html` and
enforces an 80% coverage floor.

### Run the application

```bash
python run.py
```

The launcher initialises the central logger and global crash handler before
starting the Textual app.

### Where things get written at runtime

- **Logs:** `~/.modern_commander/logs/dc_commander_YYYYMMDD.log`
  (plus a separate `dc_commander_errors_YYYYMMDD.log` for WARNING and above).
  On Windows, `~` resolves to `%USERPROFILE%`.
- **Crash reports:** `~/.modern_commander/crashes/YYYY-MM-DD_HHMMSS.txt`
- **User configuration:**
  - Windows: `%APPDATA%\ModernCommander\config.json`
  - Linux/macOS: `~/.config/modern-commander/config.json`

Attach the relevant log excerpt and/or crash report when you file a bug.

---

## Project structure

```
dc-commander/
├── modern_commander.py          # Main application (being refactored in Sprint 2)
├── run.py                       # Launcher: logging + crash handler + app.run()
├── pyproject.toml               # Build, dependencies, tool config
├── pytest.ini                   # Pytest configuration
├── .pre-commit-config.yaml      # Pre-commit hooks
│
├── components/                  # UI widgets and dialogs (Textual)
│   ├── file_panel.py           # Dual-pane file list widget
│   ├── dialogs.py              # ErrorDialog, ProgressDialog, confirm dialogs
│   ├── find_file_dialog.py     # Ctrl+F search dialog
│   ├── menu_screen.py          # F2 menu system
│   └── ...
│
├── services/                    # File-operation services
│   ├── file_service.py         # Synchronous copy/move/delete
│   └── file_service_async.py   # Async equivalents with progress
│
├── src/core/                    # Core primitives
│   ├── security.py             # Path safety / traversal checks
│   ├── ui_security.py          # User-input validation helpers
│   ├── error_boundary.py       # Central error capture
│   ├── error_messages.py       # Exception → user-facing message mapping
│   ├── file_scanner.py         # Directory traversal
│   └── archive_handler.py      # Archive extraction with safety limits
│
├── src/utils/                   # Cross-cutting utilities
│   ├── logging_config.py       # Central rotating-file logging setup
│   ├── crash_reporter.py       # Global excepthook + crash dumps
│   ├── async_file_ops.py       # Async I/O helpers
│   ├── formatters.py           # Display formatting
│   └── directory_cache.py      # LRU directory cache
│
├── features/                    # User-facing features
│   ├── theme_manager.py        # Theme registry and CSS generation
│   ├── config_manager.py       # JSON-backed configuration
│   ├── file_viewer.py          # F3 viewer
│   └── file_editor.py          # F4 editor
│
├── repositories/                # Filesystem abstraction
│   └── file_repository.py
│
├── tests/                       # Pytest suite
│   ├── characterization/       # Snapshot-style tests of current behaviour
│   ├── conftest.py             # Shared fixtures
│   └── test_*.py
│
├── docs/                        # User-facing documentation
│   └── user-manual.md
│
└── claudedocs/sprints/          # Sprint planning notes (local, gitignored)
```

A few notes:

- `modern_commander.py` is the single biggest file and is being decomposed as
  part of Sprint 2. Prefer adding new logic in `services/`, `src/core/`, or a
  dedicated module rather than growing the main file further.
- `claudedocs/` is gitignored and used for local planning. Do not rely on
  anything there being present in CI or for other contributors.
- `tests/characterization/` pins down the current behaviour of the app so the
  Sprint 2 refactor cannot change it accidentally. See the
  [Testing](#testing) section for the rules around that directory.

---

## Code style

The project uses **Ruff** for both linting and formatting, and **Mypy** for
type checking. Both are configured in `pyproject.toml`.

- **Line length:** 100 characters.
- **Quote style:** double quotes.
- **Type hints:** required on all new public functions and methods.
  The codebase is migrating toward `mypy --strict`; the Sprint 3 goal is to
  enable `disallow_untyped_defs`. Please do not add new untyped code.
- **Docstrings:** Google style. Document parameters, return values, and raised
  exceptions. Keep the one-line summary short and imperative.
- **Naming:**
  - `snake_case` for modules, functions, variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants
  - Leading underscore for private/internal names
- **Imports:** sorted by Ruff (`I` rules). Standard library, third party,
  first party, relative — separated by blank lines.
- **Errors:** raise specific exception classes. When catching, prefer the
  narrowest type that makes sense. Bare `except:` is forbidden by the linter.

### Example function

```python
def copy_file(source: Path, destination: Path, *, overwrite: bool = False) -> None:
    """Copy a single file to a new location.

    Args:
        source: Absolute path to the file being copied.
        destination: Target path. Must not exist unless ``overwrite`` is True.
        overwrite: If True, replace an existing destination file.

    Raises:
        FileNotFoundError: If ``source`` does not exist.
        FileExistsError: If ``destination`` exists and ``overwrite`` is False.
    """
    ...
```

---

## Branching and commits

### Branches

- Branch off `main`.
- Use a short, descriptive prefix:
  - `feature/short-description` for new functionality
  - `fix/issue-123` or `fix/short-description` for bug fixes
  - `refactor/short-description`, `docs/short-description`, `chore/...` for
    supporting work
- Keep branches focused on one change. Rebase onto `main` before opening the
  PR if `main` has moved.

### Commit messages

The project follows [Conventional Commits](https://www.conventionalcommits.org/).
A `conventional-pre-commit` hook enforces this on the commit message itself,
so non-conforming messages are rejected locally.

Allowed types:

| Type       | When to use                                                    |
| ---------- | -------------------------------------------------------------- |
| `feat`     | New user-visible functionality                                 |
| `fix`      | Bug fix                                                        |
| `refactor` | Internal restructuring with no behaviour change                |
| `test`     | Adding or fixing tests only                                    |
| `docs`     | Documentation only                                             |
| `chore`    | Tooling, deps, repo maintenance                                |
| `build`    | Build system or packaging                                      |
| `ci`       | CI configuration                                               |
| `perf`     | Performance improvement                                        |
| `style`    | Formatting with no semantic change                             |

Scope is optional but encouraged when it clarifies which area is affected:

```
feat(dialogs): add retry button to ErrorDialog
fix(file-panel): restore cursor after refresh
docs: add keyboard reference to user manual
```

The message body should explain **why** the change is being made, not what the
diff shows. The diff shows the what. Keep lines under 72 characters.

If an AI assistant or pair-programming partner helped with the change, add a
`Co-Authored-By:` footer so authorship is accurate:

```
Co-Authored-By: Name <email@example.com>
```

---

## Pull requests

1. Open the PR against `main`.
2. **Title:** short and imperative. Match the primary commit if it is a
   single-commit PR.
3. **Description:** briefly state
   - the problem being solved,
   - the approach chosen (and alternatives considered, if relevant),
   - what you tested and how.
4. **Link issues.** If the PR closes an issue, use `Closes #123`.
5. **CI must be green.** The pipeline runs Ruff, Mypy, Pytest, Bandit, and
   checks that coverage does not drop below the configured floor.
6. **Reviewer.** Request at least one reviewer. On a solo project you can
   self-review, but leave a 24-hour gap between opening the PR and merging it
   so you read your own diff with fresh eyes.
7. Squash-merge by default. Keep the squashed commit message Conventional and
   rewrite the body to summarise the PR if the original commit messages are
   too granular.

Please avoid force-pushing after review has started unless the reviewer asks
for it. Prefer follow-up commits so review comments stay anchored.

---

## Testing

- **Every new function gets tests.** Every bug fix starts with a failing test
  that reproduces the bug.
- **Coverage must not decrease.** The floor is configured at 80% in
  `pyproject.toml`. The goal is to keep trending upward.
- **Use `tmp_path` for filesystem tests.** Never touch the user's real home
  directory or `/tmp` directly — `tmp_path` gives you an isolated directory
  that pytest cleans up automatically.
- **UI tests use Textual's `Pilot`.** See the existing `test_e2e_*.py` files
  for examples of driving the app through simulated keypresses.
- **Async code:** pytest is configured with `asyncio_mode = "auto"`, so
  `async def test_...` works without extra decorators.
- **Property-based tests:** Hypothesis is available and used for things like
  filename validation fuzzing — reach for it when the input space is large.

### Characterization tests are sacred

Files under `tests/characterization/` pin down the current behaviour of the
application so the Sprint 2 refactor cannot change it silently. Rules:

- **Do not modify existing characterization tests** to make a refactor pass.
  If a characterization test fails, the refactor is the problem, not the test.
- If you genuinely need to change documented behaviour (e.g. a bug in the
  characterized behaviour), update the characterization test in a **separate
  commit** from the behaviour change, and explain the intent in the body.
- New characterization tests are welcome when you discover behaviour that
  is not yet pinned down.

### Test layout

- `tests/test_<module>.py` — unit tests for `<module>`
- `tests/test_e2e_*.py` — end-to-end flows driving the full app
- `tests/test_*_integration.py` — integration across components
- `tests/fixtures.py` and `tests/conftest.py` — shared fixtures

---

## Running specific checks

Run these locally before opening a PR; they are also run in CI.

```bash
# Lint
ruff check .

# Format check (fails if files would be reformatted)
ruff format --check .

# Auto-format (use this before the check)
ruff format .

# Type check
mypy .

# Tests with coverage
pytest

# Tests without coverage (faster during iteration)
pytest --no-cov

# A specific file
pytest tests/test_file_service.py

# A specific test, with full output
pytest tests/test_file_service.py::test_copy_file -vv

# Run every pre-commit hook against every file
pre-commit run --all-files
```

For security scanning specifically:

```bash
bandit -c pyproject.toml -r src components services features repositories
```

---

## Reporting bugs

The fastest way to report a bug is the bug-report template at
`.github/ISSUE_TEMPLATE/bug_report.md`, which GitHub surfaces automatically
when you open a new issue.

A good bug report includes:

- **Environment**
  - OS and version
  - DC Commander version
  - Terminal emulator and version
  - Install method (NSIS installer / AppImage / `pip install` / source)
  - Python version (for source installs)
- **Steps to reproduce** — numbered, minimal, deterministic
- **Expected behaviour**
- **Actual behaviour**
- **Logs** — excerpt from
  `~/.modern_commander/logs/dc_commander_YYYYMMDD.log` or the error log in the
  same directory
- **Crash report** if the app crashed — attach the file from
  `~/.modern_commander/crashes/`
- **Screenshots** for UI glitches

Please check existing issues before opening a new one; if there is an open
issue that matches, add your environment and any new reproduction details as
a comment instead of filing a duplicate.

---

## Questions and discussion

- **Feature ideas and open-ended discussion:** GitHub Discussions, if enabled
  on the repository. Otherwise open an issue with the `question` or
  `enhancement` label.
- **Bug reports:** GitHub Issues with the `type:bug` label (the bug-report
  template sets this automatically).
- **Security issues:** do not open a public issue. Contact the maintainers
  privately through the address listed in `SECURITY.md` if present, or via
  direct message on the hosting platform.

Thanks again for contributing. Every issue, review, and PR makes the project
better.
