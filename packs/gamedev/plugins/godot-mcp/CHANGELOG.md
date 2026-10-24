# Changelog — godot-mcp

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
