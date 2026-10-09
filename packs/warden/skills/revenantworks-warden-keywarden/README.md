# revenantworks-warden-keywarden

Knows where every credential on a Windows dev machine lives, what each one may do, and how to
replace it, and it never shows a value. Reports carry a fingerprint: a salted hash, the length
and a class name such as `github-fine-grained-pat`.

## Why it exists

Vaults, secret scanners and redaction hooks already exist. keywarden drives them and fills
three gaps:

- **What a command prints when it fails.** A script that verifies a key can print that key in a
  401 message or a traceback; `curl -v` prints the `Authorization` header on success and on
  failure; output it captures is data, not instructions. keywarden checks the command before it runs (`preflight.py check`) and, when the
  failure output is unknown, runs it through a masking wrapper (`preflight.py run`).
- **Where the credentials are.** No tool lists the stores on a Windows dev machine together:
  Credential Manager, Git Credential Manager, gh, `.env` files, the `env` blocks in Claude Code
  settings and the `env` and `headers` of MCP servers in `.mcp.json`. The last two are where
  plaintext keys keep turning up.
- **Who uses each one.** Rows that share a fingerprint are linked, so a rotation has a checklist
  of every place the old value must leave.

## What it will not do

- Print, log, write or commit a value; read a secret file into the conversation.
- Ask you to paste a secret into chat. Sign-ins happen in your own terminal.
- Issue or revoke a credential. You get one command or one page per step.
- Write a filled `.env`. It writes a references-only `.env.tpl` or injects at run time.
- Scan history or rewrite it (shieldwarden), write permission rules or hooks (gatewarden), or
  design a routine's credentials (agentwright).

## Package

```
revenantworks-warden-keywarden/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE
├── references/
│   ├── dangerous-shapes.md     # commands that print a credential, and the safe rewrite
│   ├── stores-windows.md       # every store, how it is read, when it is a plaintext risk
│   ├── scope-recipes.md        # least grant per job; classic vs fine-grained; two accounts
│   ├── rotation-runbooks.md    # PAT, OAuth, API key, SSH key, routine, Credential Manager
│   ├── tool-surface.md         # dated facts: Claude Code, gh, GCM, vault CLIs (stamped)
│   ├── install-walkthrough.md  # owner-run optional installs, a check and a way back each
│   └── pack.md                 # warden roster, generated
├── scripts/
│   ├── kw_common.py            # fingerprint, prefix classes, masking, crash reporting
│   ├── cred_inventory.py       # stores → JSON rows, fingerprints only
│   ├── preflight.py            # check a command; run one with masked output
│   ├── scope_check.py          # GitHub token scopes from headers only
│   └── test_keywarden.py
└── evals/                      # hand-run suites + native claude plugin eval cases
```

## Entry points

| Say | Does |
|---|---|
| `keywarden inventory [roots]` | Fingerprint rows for every store, plaintext first, NOT-RUN stores named. Changes nothing |
| `keywarden scope` | What the GitHub token may do, and the least grant to cut it to; which gh account is active |
| `keywarden rotate <credential>` | Consumer checklist, new value, swap, verify, one revoke command for you, re-inventory |
| `keywarden leak` | Rotation first; the history half goes to shieldwarden |
| `keywarden preflight "<cmd>"` | What the command prints on success, failure and crash; a safe rewrite |
| `keywarden refresh` | Re-read the dated facts and restamp `tool-surface.md` |

Plain requests work too: "where are my API keys stored on this PC", "is my gh token too broad",
"I pasted my key into the chat, what now", "check this curl before I run it with my token".

## Requirements

Python 3 (stdlib). Optional: git, gh, 1Password `op`, Bitwarden `bws` or `bw`, Windows
`cmdkey`; a Docker credential helper (`list` only, opt-in). No admin rights. No network except `gh api` in `scope_check.py`. Without a shell the
store list is walked by hand and every store is NOT-RUN.

## Tests

`python -m unittest discover -s scripts -p "test_*.py"` — 36 cases. Canaries are built at run
time; every case asserts that no canary byte reaches stdout, stderr or JSON, on the success
path, on a failing command, on a traceback and on a crash.

## Staying current

`references/tool-surface.md` and `SOURCES.md` carry a `Last verified` stamp and a 90-day
cadence. `keywarden refresh` re-reads them; the pack's upkeep sweep flags them when due. One
rule is pending a re-test: cloud environment variables stay on one line until a scratch
environment shows a quoted multi-line value survives. History is in `CHANGELOG.md`.

## Install one or the other

This skill ships in the warden pack and may also ship as its own featured one-skill plugin. Install one or the other, not both: the two carry the same skill name, so the listing pays for the description twice, and an update to one side only leaves two different bodies under one name.
