# Changelog — revenantworks-warden-gatewarden

## [1.0.0] — 2026-10-01

First public release. What Claude and its agents may do with the tools already installed, and what
they actually reach, read from evidence. (The reach entries came from the retired filewarden and the
`layout` entry was added on 2026-10-08, inside the 1.0.0 private test phase.)

Description cut to about 600 characters, main use case first (2026-10-08).

### What it does

- Hooks install in watch mode: they log what they would stop and let the work run. Hard rules
  (a force or delete push, a push the gate cannot read, a Hyper-V destroy, an OBS go-live, Python
  reading stdin) refuse in every mode; no modes entry, snooze or `GATEWARDEN_MODE` relaxes them. A
  weekly session-start line counts suggestions; `warden_review.py` shows them, and the owner's
  `set <rule> nudge|guard` is the only thing that moves a soft rule (a watch or nudge entry expires
  after 30 days by default; `set` refuses a hard rule). No `ask` mode.
- Warden audit fixes, 2026-10-08 (K7-4): disguised force pushes (inline alias, `send-pack`,
  run-time subcommand, redirected git dir) are hard refusals; a hook entry no longer relaxes a hard
  rule; a script too large or locked to read fails closed for hard rules; a mirror or `+`/`:` push
  refspec in git config is refused; `python -` is caught in PowerShell too; echoed CI logs and
  push-error text mask token shapes. Hook tests now run at the install default as well as in guard.
- Verifier fixes, 2026-10-09 (V-K8w): line continuations are joined before any match; abbreviated
  force, delete, mirror, prune and tag flags are refused; a run-time program name, Start-Process or
  xargs feeding git, an alias chain past five levels, a config change on a push line and a script
  written and run on a push line are hard shape refusals; aliases are read once per run and each hard
  hook has a 20 s time budget that fails closed; quoted prose that names `git push` (`echo`, `grep`,
  `git commit -m`, `gh`) passes; an interpreter's large file no longer trips push_gate and files up to
  8 MB are read; the stdin rule covers more Python names, wrappers, `/dev/fd/0` and an interactive
  start with no input, and fails closed on bad input; `snooze` checks its days before saving; the
  go-live block follows a `cd` into an OBS profile. A script decoded, downloaded or copied on the line
  and then run (`… | base64 -d | bash`, `cp x run.sh && bash run.sh`) is unread, so every hard hook
  refuses it (K8w2).
- Second verifier round, 2026-10-09 (V-K8w2), narrowed to daily-work false positives and plain
  commands: a notes heredoc that `cat` or `tee` only writes to a file, and quoted prose written to a
  data or notes file (`>> todo.txt`, `Set-Content notes.md`, `Out-File`), no longer count as a push;
  a run-time program name in an earlier `&&` or `;` step (`$PYTHON x.py && git push`) no longer
  blocks a plain push; `gh api` DELETE or force PATCH on `git/refs/…` and `gh repo sync --force` are
  hard refusals; OBS's `--startstreaming` / `--startvirtualcam` flags and `obs-cmd` / `obs-cli`
  stream and virtual-camera verbs are blocked; hyperv_lock refuses writing, emptying or moving a disk
  file and a `*.vh*` wildcard fed to a delete verb; the stdin rule also covers bare `node`, a bare
  shell, `bash -s`, `pwsh -Command -`, `ipython`, `python -m code` and `winpty python`. Encoded and
  decoded payload forms beyond the piped one are a known open area under review.
- M14 shape round, 2026-10-09 (V-K8w2 B3, B4, B9): a push argument filled in at run time (`$x`,
  `${x}`, `$(…)`, backticks, `"$@"`, `$*`, `$1`..`$9`, `%x%`) and a glob in the command word that may
  name git on a push segment (`gi[t] push`) are hard shape refusals; plain pushes, redirections and
  globs in arguments pass. The in-repo regression battery `scripts/test_hooks_shapes.py` holds one
  test class per finding, each with an allow control.
- M14b, 2026-10-09 (V-K8w2 B5): a config include (`-c include.path`, `-c includeIf.*`,
  `--config-env` naming an include, a `GIT_CONFIG_KEY_n` or `GIT_CONFIG_PARAMETERS` include, or a
  config key set at run time) on a line whose git subcommand is not a builtin is a hard shape
  refusal: an alias from an included config file cannot be read. A builtin with an include passes;
  on a push an include counts as a redirected config and is refused.
- M14c1, 2026-10-09 (V-K8w2 B8): inline interpreter code (`python -c`, `node -e`, `pwsh -c`) whose
  text names both a decode call and a run call counts as code the hooks cannot read, so every
  hard-rule hook refuses it. Matching is on the call names as plain substrings; nothing is decoded.
  Decode alone, or a run call alone, passes.
- Audits allow, deny and ask rules across every settings level: dead rules, bypass shapes, and Bash
  denies with no PowerShell twin on Windows, where the sandbox does not run.
- Lints the shapes the docs name: absolute paths, `sh -c`, `git -C`, path rules for tools that are
  never consulted, `Tool(param:value)` on a primary field, an allow inside a deny, a Read deny that
  `grep -r` walks past.
- Flags an `ask` rule in a tracked settings file, which an unattended run has nobody to answer.
- Explains which rule decides a given call.
- Reviews hooks and MCP server scope ("is this hook safe").
- Security-scans an agent's tool grants, credentials and blast radius across five runtime classes.
- Hardens: writes the fixed settings file beside the original as `<name>.hardened.json` with one
  copy command.
- Layout: one read-only map of every settings level, permission rule, added directory and hook
  (gatewarden's, dispatchwright's, the repo's own, installed plugin hooks with Revenantworks mods
  marked), the overlaps, the rules the event log shows interrupting most, and one proposed home per
  rule and hook.
- Drive map: space by folder, largest items, git repos, junctions and symlinks counted once as links,
  checked against the owner's drive layout rules, drawn as a treemap page that stays a local file.
- Claude footprint: every path Claude Code reached, read back from the transcripts it already keeps,
  against what settings grant in both directions, plus orphaned worktrees, scratchpads and transcripts;
  the first live run on a machine is gated and reads field names only.
- Drift: a live config against its tracked copy; `--inventory` names each installed entry's owning
  repo. Loads: skills that load twice, with a complete `skillOverrides` block, never written.

### Entry points

- `audit`, `harden`, `explain`, `scan`, `hooks`, `capreview`, `layout`, `map`, `footprint`, `drift`,
  `loads`, `status`, `refresh` (re-verifies the dated rule-grammar and evidence-source facts against
  the live docs).

### Scripts and hooks

- `perm_audit.py`, `perm_explain.py`, `perm_common.py`, `cap_review.py` and `settings_layout.py`
  (Python 3 stdlib), with tests.
- Reach scripts (stdlib, Python 3.9+): `scan_tree.py`, `footprint.py`, `drive_rules.py`,
  `treemap_page.py`, `drift.py`, `loads.py`, with the pack-shared `warden_fs.py` for redaction and link
  detection; optional WizTree CSV or dust JSON imports, owner-installed
  (`references/scanner-install.md`).
- Six PreToolUse hooks in `scripts/hooks/`, for the owner to install
  (`references/install-walkthrough.md`: install, verify, rollback):
  - push gate: shows the range, refuses a larger one, requires a local-CI pass and a recorded intent
    (`ci_stamp.py` records the pass). Measures the range against the remote's real tip
    (`git ls-remote`), so a recreated remote cannot clear a push as "nothing new"; reads a chained
    push's own arguments only, and not the body of a commit-message heredoc. `ci_stamp.py` takes
    several `--step`s (no `bash -c`, refused where it would start WSL), `--runs N` for a flaky check,
    refuses a passing log that says a check was skipped, and marks an `--excluded` stamp partial,
    which the gate says aloud (observations 0346, 0353-0356; added 2026-10-08 in the test phase);
  - subagent call cap and usage launch throttle;
  - Hyper-V lock: blocks Hyper-V restore and delete commands outside the allowed scripts, pinned by
    content hash;
  - heredoc guard; also refuses, in every mode, Python told to read its program from stdin
    (`python -`, `python /dev/stdin`), with or without a heredoc (observation 0352; 2026-10-08);
  - OBS go-live and stream-key block.
- Optional and never installed: `jsonschema` for a schema check.

### Safety rules

- Never writes a live settings file, a managed file or a hook folder; never installs or runs a hook.
- Never prints an `env` value: settings are parsed and each value shows as a fingerprint.
- Never deletes, moves, renames, re-permits or elevates; every change outside a hardened settings
  file is one command the owner runs. Never follows a junction or symlink, never prints file contents
  or a transcript's command text, and redacts every path.
- Never puts an `ask` rule in a tracked file, and no bypass without a sandbox.
- States what a rule cannot stop: permission rules match command text, so a hook enforces what a
  rule cannot.

### Integrations

- Works in Claude Code (CLI, desktop or IDE); on claude.ai it walks the rules by hand from pasted
  settings.
- Boundaries: whether to install a tool is trustwarden's, tokens keywarden's, leaked secrets in files
  and names that advertise secrets shieldwarden's, where a standing instruction lives rigwright's,
  designing an agent agentwright's, shrinking a Docker or WSL disk dockerrunner's.
