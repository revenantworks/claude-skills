# Changelog — revenantworks-warden-keywarden

## [1.0.0] — 2026-10-01

First public release. Knows where every credential on a Windows dev machine lives, what each one
may do, and how to replace it, and never shows a value.

Description cut to about 600 characters, main use case first (2026-10-08).

### What it does

- Inventory: Windows Credential Manager, Git Credential Manager, gh, `.env` files, the `env` blocks
  in Claude Code settings, the `env` and `headers` of MCP servers in `.mcp.json`, and cloud
  environments, as fingerprint rows (salted hash, length, class name), plaintext risks first.
- Rows that share a fingerprint are linked, so a rotation has a checklist of every consumer.
- Scope: what a GitHub token may do, read from headers only, and the least grant to cut it to;
  which gh account is active, and switching between two accounts.
- Rotate: consumer checklist, new value, swap, verify, one revoke command for the owner,
  re-inventory. Runbooks for a PAT, OAuth, an API key, an SSH key, a routine and Credential Manager.
- Leak: rotation first; the history half goes to shieldwarden.
- Preflight: what a command prints on success, failure and crash, with a safe rewrite; a masking
  wrapper runs a command whose failure output is unknown.
- Drives 1Password `op` and Bitwarden `bw` or `bws` when present.

### Entry points

- `inventory [roots]` (changes nothing), `scope`, `rotate <credential>`, `leak`,
  `preflight "<cmd>"`, `refresh` (re-reads the dated tool facts).

### Scripts

- `cred_inventory.py`, `preflight.py` (`check` and `run`), `scope_check.py`, with `kw_common.py`
  for fingerprints, prefix classes, masking and crash reporting (Python 3 stdlib; run, never read).
- `test_keywarden.py`: 36 cases; canaries built at run time, asserted absent from stdout, stderr and
  JSON on the success path, a failing command, a traceback and a crash.

### Safety rules

- Never prints, logs, writes or commits a value, and never reads a secret file into the
  conversation.
- Never asks for a secret in chat; sign-ins happen in the owner's own terminal.
- Never issues or revokes a credential; one command or one page per step.
- Never writes a filled `.env`: a references-only `.env.tpl`, or injection at run time.
- No admin rights; no network except `gh api` in `scope_check.py`. Optional tools are never
  installed by the skill (`references/install-walkthrough.md`).

### Integrations

- Scanning files or history is shieldwarden's; allow, deny and hook rules gatewarden's; a routine's
  credential design agentwright's; a vault's MCP server is vetted by trustwarden first; which email a
  commit uses is shieldwarden's.
