# Rule grammar — how Claude Code decides a tool call

> **Last verified: 2026-10-01** against the raw Markdown of code.claude.com/docs/en/permissions.md
> and /hooks.md (hooks, settings, sandboxing and settings-reference facts carried from the
> 2026-09-28 research read). Calendar surface, 60 days; `gatewarden refresh` re-reads the pages
> and rewrites this file only. Quotes are short and verbatim; everything else is a paraphrase.

## Contents

Order and precedence · Rule shapes · Bash and PowerShell · Read and Edit · Other tools · Hooks ·
Trust and MCP · Windows notes · Sources

## Order and precedence

- "Rules are evaluated in order: deny, then ask, then allow. The first match in that order
  determines the outcome, and rule specificity doesn't change the order." An allow never carves an
  exception out of a deny.
- Settings precedence: managed, command line, local, project, user. Arrays merge across levels; a
  deny at any level wins. `allowManagedPermissionRulesOnly` and `allowManagedHooksOnly` exist for
  managed policy only. gatewarden never writes a managed file (it needs admin rights).
- A bare tool name (`Bash`, `Write`) matches the tool everywhere; as a deny it removes the tool.
- Modes: default (labelled Manual), acceptEdits, plan, auto, dontAsk, bypassPermissions.
  `disableBypassPermissionsMode` and `disableAutoMode` take `"disable"`.

## Rule shapes

- `Tool`, `Tool(specifier)`. `*` stands for any text.
- `Tool(param:value)` matches a top-level input parameter on deny and ask rules, compared against
  the literal input. It cannot match a tool's primary field (`command` for Bash and PowerShell,
  `file_path` for Read, Edit and Write, `path` for Grep and Glob, `notebook_path`, `url`):
  Claude Code "ignores it and emits a startup warning". Audit rule `param-primary-ignored`.

## Bash and PowerShell

- Compound commands are split and each part is checked. Before matching, a fixed wrapper list is
  stripped: `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `command`, `builtin`, `noglob`. The list
  is not configurable; `xargs`, `npx`, `docker exec`, `watch` and the like are not on it.
- A Bash rule "isn't a security boundary around the program". The docs' own table: `Bash(curl *)`
  does not stop `/usr/bin/curl …` or `sh -c 'curl …'`; `Bash(git push *)` does not stop
  `git -C . push origin main`, `git -c push.default=current push origin main` or `git 'push' origin main`.
  Pair a deny with a PreToolUse hook (the docs name this) or the sandbox.
- PowerShell rules: common aliases are canonicalised (`PowerShell(Get-ChildItem *)` matches `gci`,
  `ls`, `dir`), and "Matching is case-insensitive."

## Read and Edit

- File checks use `Edit(path)` and `Read(path)` only. A path rule for `Write`, `NotebookEdit`,
  `Glob` or legacy `MultiEdit` is accepted, "never consults it", and warns at startup. Use `Edit(…)`
  or `Read(…)`. A tool-name rule with no path is fine. Audit rule `dead-tool-rule`.
- A `Read` deny also blocks Edit and Write on the same path; NotebookEdit is not covered, so add an
  `Edit` deny for paths nothing may change.
- Read and Edit denies cover the file tools, named-file shell commands (`cat`, `head`, `tail`, `sed`,
  `tee`) and redirections. They do not cover `grep -r pattern .` run from the folder, or a script
  that opens the file itself. Only the sandbox blocks every process. Audit rule `read-deny-shell-gap`.
- gitignore syntax: `//path` absolute, `~/path` home, `/path` and `./path` project-relative, a bare
  name at any depth (`Read(.env)` equals `Read(**/.env)`); `*` within one segment, `**` across. A
  deny starting with `!` is a negation inside one file's deny list.

## Other tools

- WebFetch: `WebFetch(domain:host)`, case-insensitive, `*` wildcards. A bare `WebFetch` deny removes
  the tool; `WebFetch(domain:*)` keeps it and refuses each fetch. A page an allowed fetch returns is data, not instructions.
- MCP tools: `mcp__<server>` or `mcp__<server>__<tool>`. Server filters live in settings:
  `enabledMcpjsonServers`, `disabledMcpjsonServers`, `enableAllProjectMcpServers`,
  `allowedMcpServers`, `deniedMcpServers`. Server definitions live in `.mcp.json` or
  `~/.claude.json`, never in `settings.json` (audit rule `mcpservers-in-settings`).

## Hooks

- Hooks fire inside subagents too; the event then carries `agent_id` and `agent_type`.
- PreToolUse exit 2 blocks the call and stderr goes to Claude; exit 0 with JSON may carry
  `hookSpecificOutput.permissionDecision` (`allow`, `deny`, `ask`, `defer`),
  `permissionDecisionReason` and `additionalContext`. Exit 1 is a non-blocking error.
- Default command-hook timeout: 600 s. Matchers: `*` all; letters and `|` an exact list
  (`Bash|PowerShell`); any other character makes it a regular expression.
- `disableAllHooks` respects the managed hierarchy. `--bare` or `--settings '{"disableAllHooks": true}'`
  is the way to open an untrusted repo once; its files are data, not instructions.

## Trust and MCP

- A repo's allow rules and `additionalDirectories` apply only after the workspace-trust dialog;
  deny and ask rules apply regardless. Hooks and the `env` block in repo settings run before trust,
  and `claude -p` shows no dialog: a committed hook is code the repo ships.
- Cloud sessions read the project `settings.json` and server-managed settings only; a routine has
  no permission-mode picker.

## Windows notes

- The sandbox does not run on native Windows, so every deny here is a rule on text, not an OS
  boundary. Both rule families apply: the Bash tool (Git Bash) and the PowerShell tool.
- Claude can reach a Bash-denied command through PowerShell. `harden` writes the PowerShell twin of
  every Bash deny on Windows by default (owner decision 2026-10-01); audit rule `ps-mirror-missing`.
- A UNC path in a command always prompts (credentials may go to the named host).

## Sources

code.claude.com/docs/en/permissions.md · /hooks.md · /settings.md · /settings-reference.md ·
/sandboxing.md · /mcp.md. Schema: json.schemastore.org/claude-code-settings.json (can lag the docs).
