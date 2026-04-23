# DC Commander — User Manual

Welcome to DC Commander, a dual-pane terminal file manager inspired by Norton
Commander. This manual covers everything you need to use it day to day:
navigating the panels, running file operations, searching, configuring the
app, and recovering when something goes wrong.

![Main interface](screenshots/main.png)

---

## Table of contents

- [Welcome to DC Commander](#welcome-to-dc-commander)
- [Quick start](#quick-start)
- [The interface](#the-interface)
- [Keyboard reference](#keyboard-reference)
- [File operations — detailed](#file-operations--detailed)
- [Search and filter](#search-and-filter)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Getting help](#getting-help)

---

## Welcome to DC Commander

DC Commander is a keyboard-driven file manager that runs in your terminal. It
shows two directory panels side by side so you can copy, move, compare, and
browse files without ever leaving the keyboard. The interface, colour scheme,
and F-key layout are deliberately close to the original Norton Commander from
1986, while the engine underneath is modern Python running on the
[Textual](https://textual.textualize.io/) framework.

You do not need to know Norton Commander to use it. If you are comfortable
with the arrow keys, Tab, and the function keys on the top row of your
keyboard, you already know enough to start.

---

## Quick start

### Launch the app

```bash
python run.py
```

On first launch you will see:

- **Two panels** side by side, each showing a directory listing.
- A **top menu bar** with the labels *Left · Files · Commands · Options · Right*.
- A **status bar** showing information about the currently highlighted file.
- A **command bar** at the bottom listing the F1–F10 shortcuts.

One panel is **active** (highlighted). Keyboard actions apply to the active
panel.

### Navigate

| Key               | What it does                                        |
| ----------------- | --------------------------------------------------- |
| `↑` `↓`           | Move the cursor up/down in the active panel         |
| `Enter`           | Enter a directory, or open a file                   |
| `Backspace`       | Go up one directory                                 |
| `Home` / `End`    | Jump to the first / last entry                      |
| `PgUp` / `PgDn`   | Page up / down                                      |
| `Tab`             | Switch which panel is active                        |
| `Escape`          | Clear selection / close dialog                      |

That is enough to wander around the filesystem. When you are ready to do
something with a file, look up the right F-key in the section below.

---

## The interface

### Panel anatomy

Each of the two panels shows:

- A **header** with the current path and the panel label (`Left` or `Right`).
- A **file list** with three columns by default: name, size, and
  modification date. Directories appear first and are marked `<DIR>`.
- A **footer** with summary information — number of files, total size,
  selection count and size.

The active panel has a brighter border; the inactive panel is dimmed.

### Menu bar

Along the top: `Left · Files · Commands · Options · Right`. Open the menu
system with `F2`. Use the arrow keys to move between categories and items,
and press `Enter` to activate.

- **Left / Right** — change the view mode or sort order of that panel.
- **Files** — file operations (copy, move, delete, etc.) and group selection.
- **Commands** — find file, quick view, compare directories, swap panels.
- **Options** — configuration and theme selection.

### Status bar

Shows details for the file under the cursor: full path, size, modification
time, and permissions where the platform supports it.

### Command bar (F-key hints)

The bottom row labels the primary F1–F10 commands so you always have a
cheat sheet in view:

```
1 Help   2 Menu   3 View   4 Edit   5 Copy
6 Move   7 Mkdir  8 Delete 9 Config 10 Quit
```

---

## Keyboard reference

The tables below list the bindings registered in the current build. Keys are
written using Textual's binding syntax (`ctrl+f`, `kp_plus`, and so on).

### Global — main application

| Key              | Action              | Description                                           |
| ---------------- | ------------------- | ----------------------------------------------------- |
| `F1`             | Help                | Show the help screen                                  |
| `F2`             | Menu                | Open the interactive menu bar                         |
| `F3`             | View                | View the highlighted file in the built-in viewer      |
| `F4`             | Edit                | Edit the highlighted file in the built-in editor      |
| `F5`             | Copy                | Copy the selected file(s) to the opposite panel       |
| `F6`             | Move                | Move the selected file(s) to the opposite panel       |
| `F7`             | New directory       | Create a new directory in the active panel            |
| `F8`             | Delete              | Delete the selected file(s)                           |
| `F9`             | Config              | Open the configuration screen                         |
| `F10` / `Q`      | Quit                | Exit the application                                  |
| `Tab`            | Switch panel        | Toggle the active panel between left and right        |
| `Ctrl+R`         | Refresh             | Reload both panels from disk                          |
| `Ctrl+H`         | Toggle hidden       | Show / hide dotfiles and hidden files                 |
| `Ctrl+F`         | Find file           | Open the recursive find-file dialog                   |
| `Ctrl+Q`         | Quick view          | Preview the highlighted file in the opposite panel    |
| `Escape`         | Clear selection     | Deselect files in the active panel                    |
| `T`              | Cycle theme         | Switch to the next built-in theme                     |
| `Ctrl+T`         | Cycle theme         | Same as `T`; available when `T` conflicts             |

### Panel-local — file list

These bindings act on the active panel.

| Key              | Action                | Description                                          |
| ---------------- | --------------------- | ---------------------------------------------------- |
| `Backspace`      | Parent directory      | Navigate to the parent directory                     |
| `Insert`         | Toggle selection      | Select/deselect the current file, move cursor down   |
| `Ctrl+R`         | Refresh               | Reload the current directory listing                 |
| `Ctrl+S`         | Cycle sort            | Cycle the sort column (name → size → date → …)       |
| `Ctrl+D`         | Reverse sort          | Toggle ascending / descending sort                   |
| `Ctrl+V`         | View mode             | Cycle Full / Brief / Info panel view                 |
| `NumPad +`       | Select group          | Select files matching a wildcard pattern             |
| `NumPad -`       | Deselect group        | Deselect files matching a wildcard pattern           |
| `NumPad *`       | Invert selection      | Flip selection state for every file in the panel     |

> If your terminal does not forward the numpad keys (common on laptops
> without a physical NumPad or when NumLock is off), use the **Files** menu
> (`F2 → Files`) which has equivalent entries.

### File viewer (`F3`)

| Key                | Action                                                  |
| ------------------ | ------------------------------------------------------- |
| `Escape` / `Q` / `F3` | Close the viewer                                     |
| `↑` / `K`          | Scroll up one line                                      |
| `↓` / `J`          | Scroll down one line                                    |
| `PgUp`             | Page up                                                 |
| `PgDn` / `Space`   | Page down                                               |
| `Home` / `G`       | Jump to the start                                       |
| `End`              | Jump to the end                                         |
| `Ctrl+G`           | Go to line                                              |
| `/` / `Ctrl+F`     | Search                                                  |
| `N`                | Next match                                              |
| `Shift+N`          | Previous match                                          |
| `H`                | Toggle hex view (for binary files)                      |
| `W`                | Toggle line wrapping                                    |

### File editor (`F4`)

| Key                    | Action                                          |
| ---------------------- | ----------------------------------------------- |
| `Ctrl+S`               | Save                                            |
| `Escape` / `Ctrl+Q` / `F4` | Quit (prompts if there are unsaved changes) |
| `Ctrl+Z`               | Undo                                            |
| `Ctrl+Y` / `Ctrl+Shift+Z` | Redo                                         |
| `Ctrl+F`               | Find                                            |
| `Ctrl+H`               | Replace                                         |
| `Ctrl+G`               | Go to line                                      |
| `Ctrl+A`               | Select all                                      |
| `F3`                   | Find next                                       |
| `Shift+F3`             | Find previous                                   |

### Find-file dialog (`Ctrl+F`)

| Key      | Action                                                 |
| -------- | ------------------------------------------------------ |
| `Enter`  | Jump to the highlighted result                         |
| `F5`     | Start / restart the search                             |
| `Escape` | Cancel                                                 |

### F2 menu

| Key                | Action                                          |
| ------------------ | ----------------------------------------------- |
| `←` / `→`          | Move between categories                         |
| `↑` / `↓`          | Move between items in a category                |
| `Enter`            | Activate the highlighted item                   |
| `Escape`           | Close the menu                                  |

---

## File operations — detailed

Every multi-file operation in the table below respects the current
**selection**. If no files are explicitly selected, the operation acts on
the single file under the cursor.

### Copy (F5)

1. Select one or more files in the active panel (`Insert` to toggle, or
   `NumPad +` for a wildcard pattern).
2. Press `F5`.
3. A dialog prompts for the destination. The default destination is the path
   shown in the opposite panel.
4. Confirm with `Enter`.
5. A progress dialog shows bytes copied and percentage. For short operations
   it may flash and disappear; that is normal.
6. When the operation finishes, both panels refresh and the selection is
   cleared.

If a destination file already exists, the app prompts for overwrite. Errors
(permission denied, disk full, source disappeared) open an **Error dialog**
with a short user-facing message and an expandable technical details section.
A `Retry` button is shown when the failure is likely transient; a second
failure dismisses the retry option to avoid infinite loops.

### Move (F6)

Same workflow as Copy, but the source file is removed once the copy
succeeds. On the same filesystem this is implemented as a rename and is
near-instantaneous. Across filesystems it is a copy-then-delete and shows a
progress dialog.

### Delete (F8)

1. Select the files you want to remove.
2. Press `F8`.
3. A confirmation dialog shows the count. Confirm with `Enter`.

**There is no recycle bin.** Files are removed directly. Be careful with
wildcard selections.

### Create directory (F7)

1. Press `F7` in the panel where you want the directory created.
2. Type a name.
3. `Enter` to create.

Invalid names are rejected with a user-friendly message. Path traversal
(`..`), null bytes, reserved Windows device names (`CON`, `NUL`, `PRN`,
`COM1`, …) and characters that are illegal on the current filesystem are all
blocked. Your entry is preserved on validation errors so you can fix it.

### Rename

Not available as a dedicated key binding in v1.0. Planned for a later
release. In the meantime you can rename a file by editing it in a shell or
by using `F6` Move with the same destination directory and a new filename.

### View (F3)

Opens a read-only viewer. Text encoding is auto-detected (UTF-8, UTF-16 with
BOM, Latin-1, and a few common code pages). For binary files, `H` toggles a
hex view with offset, bytes, and ASCII columns. `W` toggles line wrapping
for long lines.

### Edit (F4)

Opens the built-in editor with the highlighted file. Save with `Ctrl+S`,
quit with `Escape` or `Ctrl+Q` (prompts on unsaved changes). If you press
`F4` on a name that does not exist yet, the editor opens with an empty
buffer and creates the file when you save.

---

## Search and filter

### Quick filter (type-to-filter)

Start typing while a panel has focus. The panel filters its visible entries
in real time to names matching what you typed. `Escape` clears the filter.
This is the fastest way to jump to a file when you know the first few
letters of its name.

### Find file (`Ctrl+F`)

Opens the **Find File** dialog. It searches recursively from the current
directory of the active panel.

- **Pattern:** glob wildcards by default (`*.py`, `report-2024*.pdf`).
- **Regex:** enable the `Regex` checkbox to switch to a regular expression
  match against the filename.
- **Press `F5`** to start the search. Results stream into the list as they
  are found.
- **Press `Enter`** on a result to jump the active panel to that file's
  parent directory and select the file.
- **Press `Escape`** to close the dialog without jumping.

### Quick view (`Ctrl+Q`)

Toggles a file preview in the **opposite** panel. Move the cursor around in
the source panel and Quick View updates to show the file under the cursor.
Press `Ctrl+Q` again to hide the preview and restore the normal file list.

---

## Configuration

### Config file location

- **Windows:** `%APPDATA%\ModernCommander\config.json`
- **Linux / macOS:** `~/.config/modern-commander/config.json`
  (overridable with `XDG_CONFIG_HOME`).

The file is created on first launch. Deleting it restores the defaults.

### Configuration screen (`F9`)

`F9` opens the configuration screen with tabs for:

- **General** — default start paths and global toggles.
- **Left panel / Right panel** — independent settings for each panel,
  including sort column, sort direction, and which columns are visible.
- **Cache** — directory cache size and TTL.
- **Themes** — choose a built-in theme or create a custom one.

Changes apply immediately and are written to the config file on save.

### Themes

DC Commander ships with four built-in themes:

- **Norton Commander** (default) — the classic cyan/yellow/blue palette.
- **Modern Dark** — a neutral dark theme.
- **Solarized** — the Solarized Dark palette.
- **Midnight Blue** — a deep blue professional theme.

You can also create up to three custom themes via `F9 → Themes`. Press `T`
in the main view to cycle through themes without opening the config screen.

### Panel view modes

Each panel has three view modes, toggled with `Ctrl+V` or via `F2 → Left/Right`:

- **Full** — name, size, and modification date.
- **Brief** — multiple columns of names only, for dense directory listings.
- **Info** — name plus extended file metadata (permissions, owner, group on
  Unix). The Info view has reduced content on Windows because Windows does
  not expose the same permission model.

---

## Troubleshooting

### Windows SmartScreen warning on the installer

The DC Commander installer in v1.0 is not yet signed with a code-signing
certificate, so Windows SmartScreen may show a *Windows protected your PC*
dialog. To proceed:

1. Click **More info**.
2. Click **Run anyway**.
3. Verify the installer against the SHA-256 checksum published in the GitHub
   release notes. If they do not match, do not install — open an issue.

A signed installer is tracked as a post-1.0 improvement.

### The app will not start

- Run `python --version`. DC Commander requires Python 3.10 or newer.
- If you installed from source, make sure your virtual environment is
  activated and dependencies are installed: `pip install -e ".[dev]"`.
- Check the launcher log under `~/.modern_commander/logs/` — startup
  failures are logged there even if the TUI never appears on screen.

### NumPad `+` / `-` / `*` do nothing

Some terminals do not forward the dedicated numpad keys, or remap them when
NumLock is off. Workarounds:

- Make sure NumLock is on and try again.
- Use the **Files** category of the `F2` menu, which has entries for
  *Select group*, *Deselect group*, and *Invert selection*.
- On some terminal emulators, enabling *Application keypad mode* in the
  terminal preferences fixes it.

### Colours look wrong or the theme did not change

Textual stores CSS variables at mount time, which can leave stale values in
some widgets right after a theme switch. The current workaround is to press
`Tab` to switch panels, which forces a refresh. This is a known issue and is
tracked for a later release.

### The app crashed

Uncaught exceptions are captured by the global crash handler. A dump is
written to:

```
~/.modern_commander/crashes/YYYY-MM-DD_HHMMSS.txt
```

The file contains the exception, a full traceback, environment information,
and the last 100 lines of the log. Attach it to a bug report.

### Reading logs

Regular logs live in:

```
~/.modern_commander/logs/dc_commander_YYYYMMDD.log
~/.modern_commander/logs/dc_commander_errors_YYYYMMDD.log
```

Each daily log file rotates at 10 MB with five backups. The error log
contains only `WARNING` and above, which makes it small enough to attach
in its entirety.

### Resetting the configuration

If the app refuses to start due to a malformed config file, or you simply
want defaults back, delete:

- **Windows:** `%APPDATA%\ModernCommander\config.json`
- **Linux / macOS:** `~/.config/modern-commander/config.json`

The next launch will recreate it with defaults.

---

## FAQ

**Can I use the mouse?**
DC Commander is primarily a keyboard application. Textual supports mouse
events and clicks on the panels will move the cursor, but none of the file
operations are wired to mouse clicks in v1.0. Treat mouse support as a
convenience, not a complete input method.

**How do I change the colour scheme?**
Press `T` in the main view to cycle through built-in themes, or open
`F9 → Themes` for the full selector and custom-theme editor.

**Can I bind custom keys?**
Not in v1.0. The binding table is defined in the source. Custom bindings
are tracked as a possible enhancement for a future release.

**Does it work over SSH?**
Yes. DC Commander is a terminal application, so it runs anywhere you have
a decent terminal and a working Python 3.10+ environment, including over
SSH. Performance depends on the latency of the connection. Resize the
terminal, switch fonts, or reduce the theme colour depth if rendering
feels sluggish.

**How does it compare to Far Manager or Midnight Commander?**
DC Commander is smaller in scope than either. Far Manager is a mature
Windows-native file manager with a large plugin ecosystem; Midnight
Commander has decades of polish and a rich toolchain around it. DC
Commander focuses on a clean, modern Python codebase, the core Norton
Commander workflow, and ergonomic error handling. If you need an advanced
plugin system, FTP/SFTP panels, a built-in archive browser that rivals
`mc`'s, or shell-level integration, those tools remain the better choice
today. If you want a small, hackable, keyboard-first dual-pane manager on
any platform where Python 3.10 runs, DC Commander is a reasonable fit.

---

## Getting help

- **Bugs:** open a GitHub issue using the bug-report template.
  Please attach a log excerpt and, if it crashed, the crash-report file.
- **Feature requests:** open a GitHub issue with the `enhancement` label.
- **Questions:** GitHub Discussions if enabled on the repository; otherwise
  open an issue with the `question` label.

Thanks for using DC Commander.
