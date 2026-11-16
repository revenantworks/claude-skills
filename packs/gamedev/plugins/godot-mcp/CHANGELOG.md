# Changelog — godot-mcp

## [1.0.1] — 2026-11-16

2026-11-16 (the owner's editor output filled with `WASAPI: GetBufferSize error` and `Current
output_device invalidated, closing output_device`, over and over, after the Windows sound device
changed; Godot does not handle that case quietly, godotengine/godot#104837):

- Games played through `godot_run_scene` run with Godot's Dummy audio driver, so a run Claude
  starts never opens the PC's sound device. `audio: true` on the call, or
  `GODOT_MCP_RUN_AUDIO=1` for every run, plays with sound. The plugin adds
  `--audio-driver Dummy` to `editor/run/main_run_args` in memory, waits two frames for the Run
  Instances dialog to copy it, presses Play and sets the old value back; project.godot is never
  written. Run arguments that already pick an audio driver win. The owner's own Play button is
  untouched. The reply's `audio` field says which way the run went.
- Output is tidied before Claude reads it, on both halves: a message repeated back to back is
  kept once with a count (`[repeated N times]` in the game log, `repeat` on an editor entry),
  and a run of the WASAPI pair (input-device twin included) becomes one note, "audio device
  changed, harmless". The editor's 1,000-entry buffer folds as it records, so a flood can no
  longer push real errors out of it; the server folds too, for an older addon copy still in a
  project. Real errors are left as they are. Game logs report `folded`, the lines removed.
- Tests: 45 unit tests (15 new: the pasted flood, the older two-line form, repeats, untouched
  real errors, old and new addon entries, the audio argument and its environment default) and
  48 end-to-end checks (7 new: the Dummy driver on the game's real command line, run arguments
  restored and project.godot unchanged, `audio: true`, and the folding on real Godot 4.7.2 output
  from a @tool autoload that prints the pair in the editor and the game). The e2e plays games
  with the headless display driver instead of `--headless`, which forces the Dummy driver and
  would hide the change.

## [1.0.0] — 2026-10-22

2026-10-22 (own Godot MCP server, built step by step with the owner on a game project, then
hardened from a survey of nine community Godot MCP servers and the MCP spec): first release.
An opt-in plugin beside the gamedev pack.

- `addon/claude_mcp/` (Godot 4.5+ editor plugin): listens on 127.0.0.1 (6010, nine fallbacks,
  `GODOT_MCP_PORT`), a random token per editor session in `res://.godot/claude_mcp/session.json`,
  compared in constant time; one client at a time; an 8 KiB limit before the token is accepted
  and a dropped connection on a wrong token. Eight commands, edits through the editor's undo
  history, `claude_mcp/read_only` in Editor Settings refuses every edit. Finds the game's user
  folder from `override.cfg` itself (the editor ignores it; the game obeys it).
- `scripts/godot_mcp_server.py` (stdlib stdio MCP server): eight tools with titles, annotations,
  closed input schemas and output schemas; results as `structuredContent` plus text; tool errors
  carry a stable code (`NO_EDITOR`, `BAD_ARGS`, `READ_ONLY`, `TIMEOUT`, ...); `--read-only`
  hides and refuses the edit tools; game and editor logs come wrapped as untrusted data; a log
  older than the last run returns no lines; repeatable `--project-dir`.
- Tests: `scripts/test_godot_mcp_server.py` (fake editor), `scripts/e2e_godot.py` (a real
  headless editor on a throwaway project, 22 checks).

2026-10-24 (security fixes from an adversarial review, still 1.0.0 under the repo's version
rule): `value_godot` may use only Godot's value types, checked before parsing (`str_to_var` built
objects and ran a tool script's `_init`), parsed values are walked for objects, and
resource-typed properties are refused; a headless editor opens no port and the session file is
removed only by its owner; scenes under `addons/` and `tests/` are not played; node paths stay
inside the open scene (no `/`, `..`, `:`, instanced sub-scenes or editor nodes); runs count as
writes in read-only mode; one bad number or `params` shape no longer stops the server
(argument types and ranges are checked, a catch-all returns -32603); a client must send its token
within 3 s and is dropped after 30 s idle; every result is wrapped as untrusted project text;
replies name `~` for the home folder; only the log's last 2 MB is read, lines cut at 2,000
characters; `GODOT_MCP_PORT` must be 1024-65526. Tests: 30 unit, 41 end-to-end checks, each
review probe included; the earlier plugin fails them.
