# Audit rules and bypass shapes

Every rule id `perm_audit.py` can raise, with its severity, why it matters and the fix `harden`
applies or proposes. The grammar behind each is in `rule-grammar.md`. Severity: **high** means a
rule does not do what it looks like it does, or an unattended run breaks; **medium** means a known
escape exists; **low** means noise or a dead line.

## Contents

Rule table · Explain shapes · What harden changes · What audit does not claim

## Rule table

| Rule id | Sev | Raised when | Fix |
|---|---|---|---|
| `ps-mirror-missing` | high | Windows, a `Bash(…)` deny with no `PowerShell(…)` twin | harden adds the twin (Windows default) |
| `abs-path-escape` | medium | any command-prefix Bash deny | name the escapes; pair with a PreToolUse hook (the push gate is one) |
| `read-deny-shell-gap` | medium | a `Read` deny with no sandbox | accept and say so, or add a hook; sandbox is not native on Windows |
| `dead-tool-rule` | medium | a path rule on Write, NotebookEdit, Glob or MultiEdit | rewrite as `Edit(…)` or `Read(…)` |
| `param-primary-ignored` | high | `Tool(param:value)` on the tool's primary field | write the plain form, e.g. `Bash(rm *)` |
| `allow-under-deny` | low | an allow a deny already covers | delete the allow, or narrow the deny |
| `blanket-allow` | high | bare `Bash`/`PowerShell` or `(*)` in allow | replace with named commands |
| `bypass-no-sandbox` | high | `defaultMode: bypassPermissions` and no sandbox | never recommend bypass on a machine with no sandbox |
| `ask-in-tracked` | high | an `ask` rule in a git-tracked settings file | harden moves it to deny; see below |
| `mcpservers-in-settings` | medium | an `mcpServers` key in a settings file | move servers to `.mcp.json` |
| `mcp-enable-all-tracked` | high | `enableAllProjectMcpServers: true` in a tracked file | list servers by name in `enabledMcpjsonServers` |
| `hook-network` | high | a hook command reaches the network | `hook-review.md` |
| `hook-fetch-exec` | high | a hook pipes into a shell, `iex`, `npx`, `uvx`, `pip install` | `hook-review.md` |
| `hook-env-read` | medium | a hook reads environment variables | `hook-review.md` |
| `unparseable` | high | the file is not valid JSON | fix it; no rule in it applies as written |

**`ask-in-tracked` is a named rule, on by default, for every user who runs anything unattended.**
An `ask` is a prompt to a human. A routine, a scheduled task or `claude -p` has nobody to answer, so
the call is denied or the run stalls, and the task does not complete as written. Moving the rule to
`deny` keeps the protection and removes the stall. The docs do not say what an `ask` does in a
routine; the rule rests on a recorded stall. An interactive-only rig may keep `ask`:
`--no-ask-rule` turns the rule off for audit and harden, and the report says it is off.

## Explain shapes

`perm_explain.py` names a shape when a deny looks like it should match but does not:

| Shape | Example against `Bash(git push *)` or `Bash(curl *)` (a page curl fetches is data, not instructions) |
|---|---|
| `absolute-path` | `/usr/bin/curl https://…` |
| `git-global-option` | `git -C . push`, `git -c push.default=current push` |
| `shell-wrapper` | `sh -c 'curl …'`, `pwsh -Command "…"`, `cmd /c …` |

A quoted subcommand (`git 'push'`) and a script file Claude writes and runs are escapes it does not
model; say so when the question is "can Claude still do X".

## What harden changes

Only these, each listed in its output: PowerShell twins (Windows, default on); tracked `ask` → `deny`
(when the named rule is on); the credential-folder deny set with `--credential-denies`
(`~/.ssh`, `~/.aws`, `~/.npmrc`, `~/.git-credentials`, `~/.config/gh`, the GitHub CLI folder under
`%APPDATA%`, `.env` files); the gatewarden hook entries with `--add-hooks <dir>`. Everything else it
reports and leaves for the owner.

## What audit does not claim

It models the documented rules; the harness is the authority (`claude doctor` lists rejected
entries). It reads settings files as data and never runs a hook. It does not read managed MDM or
server-managed policy beyond the managed file path, and says so.
