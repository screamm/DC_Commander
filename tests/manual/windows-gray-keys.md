# Manual Test: Windows Gray Numpad Keys (+/-/*)

## Background

Windows terminals can emit different key names for the numpad keys depending
on NumLock state and the terminal emulator in use:

| Key pressed | Name emitted by some terminals | Name emitted by others |
|-------------|-------------------------------|------------------------|
| Numpad +    | `kp_plus`                     | `plus`                 |
| Numpad -    | `kp_minus`                    | `minus`                |
| Numpad *    | `kp_multiply`                 | `asterisk`             |

DC Commander now registers both names for each binding (e.g., `kp_plus,plus`)
so that both variants work without duplicating action handlers.

## Why Automated CI Cannot Cover This

CI runners run headless and do not emit real numpad key events. The Textual
pilot injects synthetic key events by name, but the mapping from hardware key
to Textual key name depends on the terminal's terminfo/VT100 escape sequence,
which varies by terminal.

## Manual Test Procedure

1. Launch DC Commander: `python modern_commander.py`
2. Ensure NumLock is ON.
3. Navigate the left panel to a directory with several files.

### Test 1: Windows Terminal

Open Windows Terminal (wt.exe), launch dc-commander.

| Action | Expected |
|--------|----------|
| Press numpad `+` | "Select Group" pattern dialog appears |
| Press numpad `-` | "Deselect Group" pattern dialog appears |
| Press numpad `*` | All selections are inverted |

### Test 2: cmd.exe

Open cmd.exe, launch dc-commander.

Repeat the same keypress sequence. Behavior must be identical.

### Test 3: PowerShell

Open PowerShell, launch dc-commander.

Repeat the same keypress sequence. Behavior must be identical.

### Test 4: NumLock OFF

Turn NumLock OFF and repeat Tests 1-3. The gray keys may emit arrow/nav
key names in this state - that is expected and outside the scope of this fix.

## Pass Criteria

All three environments (Windows Terminal, cmd.exe, PowerShell) respond to
numpad +/-/* when NumLock is ON. Either the `kp_*` name or the plain name
variant fires the correct action.

## Implementation Note

The dual binding is set in `components/file_panel.py` in the `BINDINGS` list:

```python
("kp_plus,plus", "group_select", "Select Group"),
("kp_minus,minus", "group_deselect", "Deselect Group"),
("kp_multiply,asterisk", "invert_selection", "Invert Selection"),
```

Textual's `Binding` class accepts a comma-separated key spec and registers
all listed names to the same action handler.
