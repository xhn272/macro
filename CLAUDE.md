# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A Windows keyboard macro manager GUI built with Python/tkinter. Users create macros (sequences of key presses, mouse actions, and waits) triggered by hotkeys. Requires administrator privileges for input simulation in certain applications.

## Commands

```bash
# Run the app
python macro.py

# The app requires admin for full functionality
# If run without admin, a warning is printed but the app still launches
```

No build steps, test suite, or linting configuration exists.

## Architecture

Single-file GUI application (`macro.py`, ~1350 lines) with a small data module (`about_text.py`). Config persisted as `macros.json` in the working directory.

**Data model** — `macros` is a global list of dicts. Each macro has: `name`, `selected` (bool, historically named `enabled` in JSON), `trigger` (hotkey string like `"ctrl+f2"`), `repeat` (int), `steps` (list of step dicts), and optional `locked` (list of strings). Step types:
- `{"type": "key", "value": "ctrl+c", "delay": 0.1}` — keyboard shortcut
- `{"type": "mouse", "action": "click"|"move"|"scroll", ...}` — mouse operation
- `{"type": "wait", "value": 0.5}` — sleep in seconds
- `{"type": "STOPALL"}` — immediately unregisters all hotkeys and stops execution (only via JSON, not creatable in UI)

**`locked` field** — optional list of strings; empty or absent means no restrictions. Valid values: `"name"`, `"trigger"`, `"steps"`, `"delete"`, `"selected"`, `"repeat"`. Enforced in EditMacroDialog (disables controls) and main windows (blocks delete/select toggle). Copied macros drop the `locked` field. Invalid values are silently ignored.

**Two window modes** switchable via View menu, implemented as separate classes:
- `ClassicMainWindow` — full table view (name, trigger, step count, enabled status) with edit buttons, bulk selection, and create/copy/delete operations
- `SimpleMainWindow` — list of macro names + info panel with individual enable/disable per macro

**Hotkey registration** — `register_hotkeys()` iterates enabled macros, detects trigger-key conflicts, and calls `keyboard.add_hotkey()` for each. `unregister_all()` clears them. The `hotkeys` dict maps trigger strings to `keyboard` library handler IDs.

**Step execution** — `execute_steps(steps, repeat)` iterates step lists, dispatching to `keyboard.send()`, `mouse.click/move/wheel()`, or `time.sleep()`. Supports a per-step post-delay.

**Dependencies**: `keyboard`, `mouse`, and the `about_text` module (just an `ABOUT_TEXT` string). Only standard library otherwise.

## Key constraints

- Editing, deleting, copying, or creating macros is blocked while any hotkeys are registered (must "停用所有" first). This avoids race conditions with the `macros` list while hotkeys reference it by index.
- `macros` is a global list; hotkey callbacks close over the current steps/repeat by copy, not by reference.
- Trigger key conflicts are checked at registration time; duplicates in the same batch show a warning and prevent registration.
- A STOPALL macro (trigger `ctrl+delete`, locked except for trigger) is auto-created in `load()` if no macro with a STOPALL step exists. It calls `unregister_all()` and immediately halts execution.
