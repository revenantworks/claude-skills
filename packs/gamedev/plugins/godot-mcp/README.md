# godot-mcp

**A small, security-first Godot MCP server for Claude Code.** Claude runs your scenes, reads their
output and errors, lists the open scene's nodes, and adds or edits nodes through the editor's own
undo history. Eight tools, a token lock, nothing destructive. An opt-in plugin beside the gamedev
pack, like `gdscript-lsp`. Version 1.0.0.

It has two halves:

- `addon/claude_mcp/` is a Godot 4.5+ editor plugin. Copy it into a project. It listens on
  `127.0.0.1` only and answers one JSON request per line.
- `scripts/godot_mcp_server.py` is the MCP server Claude Code starts over stdio. It forwards each
  tool call to the editor plugin. Python standard library only, nothing to install.

```
Claude Code --stdio--> godot_mcp_server.py --127.0.0.1 + token--> claude_mcp plugin --> Godot editor
```

## The tools

| Tool | What it does | Changes the project? |
|---|---|---|
| `godot_status` | Godot version, project, main scene, open scene, playing or not, game log path, read-only flag | No |
| `godot_run_scene` | Plays `main`, `current` or a `res://` scene outside `addons/` and `tests/`, waits `capture_seconds` (default 3), returns the run's log and new editor errors | Runs the game; the editor saves open scenes first |
| `godot_stop_scene` | Stops the playing scene | No |
| `godot_read_output` | The game's log and the editor's messages; `errors_only` keeps errors and warnings with the lines under them | No |
| `godot_scene_tree` | The open scene's nodes: name, type, path, script | No |
| `godot_add_node` | Adds a built-in Node class under a parent, with a name and JSON properties | Yes, undoable |
| `godot_set_property` | Sets one inspector property: `value` (JSON) or `value_godot` (`Vector2(1, 2)`) | Yes, undoable |
| `godot_save_scene` | Saves the open scene to its own file (Ctrl+S) | Writes that one file |

**Left out on purpose:** deleting or renaming nodes, writing or deleting files, running GDScript
sent over the socket, setting `script` or `owner`, and adding editor classes. Many community
servers ship a "run any GDScript" tool; this one never will.

Every result comes back twice, as `structuredContent` and as text. A failed call says why with a
stable code Claude can act on: `NO_PROJECT`, `NO_EDITOR`, `BAD_ARGS`, `BAD_TOKEN`, `REFUSED`,
`READ_ONLY`, `TIMEOUT`, `VERSION`, `BAD_REPLY`.

## Safety

- **Loopback only.** The plugin binds `127.0.0.1`; the server connects only there.
- **A token per editor session.** The plugin makes 16 random bytes at start and writes them, with
  the port, to `res://.godot/claude_mcp/session.json`. `.godot/` is Godot's cache and git ignores
  it; the file is deleted when the plugin stops. The token is compared in constant time.
- **Guards before the token.** One client at a time (others wait). The first line must carry the
  right token within 3 seconds; a line over 8 KiB, a wrong token or anything else closes the
  connection. A client idle for 30 seconds is dropped.
- **Headless editors stay idle.** `godot --headless --import` and CI load editor plugins too; the
  plugin opens no port there, so it never replaces the session file of an editor you have open.
  It removes the session file only while the file still holds its own token.
- **No objects from text.** `value_godot` may name only Godot's value types (`Vector2`, `Color`,
  `Transform2D`, packed arrays and the like), checked word by word before parsing, because
  `str_to_var` would otherwise build `Object(...)` and `Resource(...)` while it parses and run a
  tool script's `_init`. Parsed values are walked for objects at any depth, and resource-typed
  properties are refused.
- **The open scene only.** Node paths are relative to the scene root, with no leading `/`, no `..`
  and no `:`; a node inside an instanced sub-scene or the editor's own tree is refused. Classes are
  built-in Node subclasses only (`ClassDB`, no `Editor*`).
- **Safe scenes to run.** Scene paths must start `res://`, end `.tscn` or `.scn`, hold no `..`,
  exist, and sit outside `addons/` and `tests/` (test runners played from the editor skip test
  isolation).
- **Read-only, on both sides.** `--read-only` (or `GODOT_MCP_READ_ONLY=1`) hides and refuses the
  four tools that can write in the server, runs included, since the editor saves before it plays;
  **Editor Settings > claude_mcp/read_only** makes the plugin refuse them too. The MCP spec says
  clients must not trust tool annotations, so enforcement lives in code.
- **Project text is untrusted data.** Node names, property values and log lines are text the
  project wrote, so every result's text comes in a per-call nonce envelope marked as data, not
  instructions, and `structuredContent` carries an `untrusted` note.
- **No home paths.** Paths in replies name `~`, never the account's own folder.
- **No stale or giant answers.** A game log written before the last run returns no lines, with a
  note; only the log's last 2 MB is read, and a line over 2,000 characters is cut.
- **Limits.** Any program running as your user can read the session file, so the token stops other
  users and stray local clients, not your own programs. Windows offers no isolation between local
  accounts beyond file permissions.

## What it needs

- **Godot 4.5 or later** (it uses `Logger` and `OS.add_logger`). Checked on 4.7.2, Windows.
- **Python 3.9+** on PATH as `python` (`python3` on Linux and macOS: use that name below).
- Godot's file logging on (`debug/file_logging/enable_file_logging`, on by default for desktop),
  so the game's output can be read.

## Install

1. Copy `addon/claude_mcp/` into your project as `addons/claude_mcp/`.
2. In Godot: Project > Project Settings > **Plugins**, tick **Claude MCP**. The Output panel says
   `Claude MCP: listening on 127.0.0.1:6010`.
3. Register the server with Claude Code, from the project folder:

   ```
   claude mcp add --scope local godot -- python <path to this folder>/scripts/godot_mcp_server.py --project-dir <your project folder>
   ```

   `--project-dir` repeats: list several projects and each call drives the first one open in
   Godot. With none, the server searches upward from the folder Claude Code started in.
4. Ask Claude: *"run the main scene for 10 seconds, list any errors, then stop it"*.

The plugin is not in the marketplace yet (the build registry has no table for a plugin that sits
inside a pack, as with `gdscript-lsp`). Its `.mcp.json` is ready for when it is.

## Settings

| Setting | Where | Default |
|---|---|---|
| First port (then the next 9) | `GODOT_MCP_PORT` in the editor's environment, 1024-65526 | `6010` |
| Listen in a headless editor (tests only) | `GODOT_MCP_HEADLESS=1` in the editor's environment | off |
| Projects | `--project-dir` (repeatable), else `CLAUDE_PROJECT_DIR`, else the working directory | — |
| Read-only server | `--read-only` or `GODOT_MCP_READ_ONLY=1` | off |
| Read-only plugin | Editor Settings > `claude_mcp/read_only` | off |

**Worktrees and `override.cfg`.** The game obeys `override.cfg` (for example a custom user folder
per checkout), but the editor does not apply it to its own settings. The plugin reads
`res://override.cfg` itself, so the game log it reports is the one the run actually writes.

## Tests

```
python -m unittest discover -s scripts -p "test_*.py"
python scripts/e2e_godot.py
```

The unit tests use a fake editor on a loopback port; no Godot runs. `e2e_godot.py` builds a
throwaway project in a temp folder (with an `override.cfg`), starts `godot --headless --editor`
with no window, calls every tool through the server, probes the socket guards directly, then
stops the editor and removes the project and its user folders. Games it plays run with
`--headless`. Exit 3 is NOT-RUN (no Godot on PATH).

**Trial, 2026-10-22, Godot 4.7.2 on Windows:** 26 unit tests and 22 of 22 end-to-end checks
passed, including the override.cfg log folder, both socket guards and no unexpected editor errors.
The owner also drove every tool from Claude Code against a live editor on a real game project.

**Security review, 2026-10-24:** an adversarial review of 1.0.0 found one high (`value_godot`
built objects and ran tool-script code), four medium (a headless import took the port and deleted
a live editor's session file; test-runner scenes could be played; node paths reached the editor's
own tree; read-only mode still allowed runs, which save) and six low (one float stopped the
server; a silent client held the slot; unwrapped project text; whole-log reads; home paths in
replies; a bad port variable). All eleven are fixed. 30 unit tests and 41 of 41 end-to-end checks
pass, the new checks include each review probe, and the 1.0.0 plugin fails them (the positive
control).
A headless editor logs `Parameter "t" is null` from the dummy renderer when it saves a scene
thumbnail; the scene still saves, and a normal editor does not do this.

## How it compares

Nine community Godot MCP servers were read before release (READMEs and docs, 2026-10-22). Most
offer 20 to 300 tools, runtime input, screenshots and a "run any GDScript" tool. This one keeps
eight tools and adopts their safest practices instead: a read-only mode (as in
satelliteoflove/godot-mcp and the Godot MCP Toolkit), a per-session token and a pre-auth size limit
(as in godot-ai), and untrusted-output wrapping (as in the Godot MCP Toolkit). Not adopted:
unauthenticated in-game TCP servers, code execution, dynamic tool loading, and one-line installers.

## Licence

Apache-2.0 (`LICENSE`, `NOTICE`). No third-party code. Godot is a separate program the user
installs; none of its code is redistributed.
