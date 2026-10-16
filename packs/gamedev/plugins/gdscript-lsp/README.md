# gdscript-lsp

**GDScript code intelligence for Claude Code, through Godot's own language server.** An opt-in
plugin that ships beside the gamedev pack, in the shape of the official `pyright-lsp` plugin:
an `.lsp.json` that maps `.gd` files to one server. Version 1.0.0.

Claude Code runs every language server over stdio. Godot's GDScript language server listens on
TCP (port 6005) while an editor has the project open. `scripts/gdscript_lsp_bridge.py` joins the
two: it connects to that port and copies the protocol bytes both ways. Claude then gets Godot's
diagnostics after each `.gd` edit, and the LSP tool (definitions, references, hover) on GDScript.

It also ships one check-only hook, `scripts/gdformat_check.py`.

## What it needs

- **Python 3** on PATH as `python` (standard library only). On Linux or macOS, where only
  `python3` exists, set `"command": "python3"` in `.lsp.json` and `hooks/hooks.json`.
- **Godot 4.x**, with the project open in the editor, or set `GODOT_LSP_SPAWN=1` (below).
- Optional: a GDScript formatter for the hook, GDQuest's `gdscript-formatter` or gdtoolkit's
  `gdformat`. Nothing here installs one.

## Install

The plugin is not in the pack itself, so installing `gamedev` never starts a language server.

It is not in the marketplace yet: the build registry has no table for a plugin that sits
inside a pack, so it ships as a trial. From a local clone, load it for one session:
`claude --plugin-dir packs/gamedev/plugins/gdscript-lsp`.

## The bridge

```
python scripts/gdscript_lsp_bridge.py [--host H] [--port N] [--timeout S] [--spawn]
                                      [--godot BIN] [--project-dir DIR]
```

| Setting | Flag | Environment | Default |
|---|---|---|---|
| Host, loopback only | `--host` | `GODOT_LSP_HOST` | `127.0.0.1` |
| Port | `--port` | `GODOT_LSP_PORT` | `6005` (Godot's editor setting `network/language_server/remote_port`) |
| Wait for the port | `--timeout` | `GODOT_LSP_CONNECT_TIMEOUT` | 10 s; 90 s with spawn |
| Start a headless editor when nothing listens | `--spawn` | `GODOT_LSP_SPAWN=1` | off |
| Godot binary | `--godot` | `GODOT_BIN` | `godot` |
| Project folder (searched upward for `project.godot`) | `--project-dir` | `CLAUDE_PROJECT_DIR` | working directory |

- **Loopback only.** A host other than 127.0.0.0/8, `::1` or `localhost` exits 2 before any
  connection. No byte leaves the machine.
- **Spawn** runs `godot --headless --editor --path <project> --lsp-port <port>` with no window
  (`CREATE_NO_WINDOW` on Windows) and stops it, children included, when the session ends. The
  headless editor imports the project and writes its `.godot/` cache, as an open editor does.
  Only one editor can hold a port: with the editor already open, leave spawn off.
- stdout carries protocol bytes only; every message goes to stderr. Exit 0 when the session
  ends, 1 when no server answered (the message says how to start one), 2 on a usage error.

Set an environment value for the server in `.lsp.json` (`"env": {"GODOT_LSP_SPAWN": "1"}`) or
in the shell that starts Claude Code.

## The format hook

`PostToolUse` on `Write|Edit|MultiEdit`. For a `.gd` file it runs one formatter in check mode on
that one file. **It never changes the file.**

| Result | What the hook does |
|---|---|
| Formatted | Nothing, exit 0 |
| Needs formatting | The formatter's output on stderr, exit 2, so Claude reads it; the edit stands |
| No formatter on PATH | One `NOT-RUN` line, exit 0; nothing is installed |
| Crash, timeout, gdformat parse failure | One `NOT-RUN` line with the reason, exit 0 |

Formatter order: `GDSCRIPT_FORMAT_CMD` (a JSON list, `--check` and the file are appended), then
`gdscript-formatter --check`, then `gdformat --check --diff`. `GDSCRIPT_FORMAT_TIMEOUT` sets the
limit in seconds (default 20). gdtoolkit's grammar lags new GDScript syntax; a file it cannot
parse is NOT-RUN, never a format finding.

## Tests

```
python -m unittest discover -s scripts -p "test_*.py"
```

No test starts Godot or a real formatter: a fake TCP server and a fake formatter stand in.

**Trial, 2026-10-16, Godot 4.7.2 on Windows, `--spawn`, a two-script scratch project:** the
headless editor answered `initialize` 5.4 s after launch (22 server capabilities), pushed
`publishDiagnostics` on `didOpen` (a type mismatch, an undeclared identifier and an unused
variable, on the right lines), and answered hover and definition. `shutdown` and `exit` ended
the bridge with exit 0, and no editor process was left. Godot returns URIs with an encoded drive
colon (`file:///V%3A/...`); whether a client maps them to the open file was not checked.

## Licence

Apache-2.0 (`LICENSE`, `NOTICE`). No third-party code. Godot, `gdscript-formatter` and gdtoolkit
are separate tools the user installs; none of their code is redistributed.
