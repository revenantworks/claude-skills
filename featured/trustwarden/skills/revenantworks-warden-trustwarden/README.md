# revenantworks-warden-trustwarden

Vets third-party code before it is installed: skills, plugins, MCP servers and GitHub Actions. It
ends with a verdict and the terms to install under, never a bare score.

## Why it exists

Good scanners for agent skills and workflows already exist, and trustwarden drives them rather than
rebuilding them. Two gaps remain:

- **Scanners skip files without saying so.** Files over 1 MB, `.pyc` bytecode, archives and binaries
  pass through unread, and "clean" is reported anyway (skillspector #363, skill-scanner #220,
  agent-scan #421 and #462). trustwarden lists **every** file with the readers that read it. An
  unread executable, bytecode, archive or oversized file means the verdict cannot be PASS.
- **A score does not say how to install.** A Claude Code plugin runs hooks and MCP servers outside
  the sandbox with your user permissions, and auto-update can change the files you reviewed.
  trustwarden's verdict is a set of terms tied to Claude Code's own controls: the commit SHA to pin,
  auto-update off, a read-only copy for skills, and the exact rules gatewarden should add
  (`deniedMcpServers`, `disableSkillShellExecution`, deny rules for `bin/` tools).

It also reads what scanners do not look for: a skill line that runs a shell command at load time,
what an installer writes (a global `CLAUDE.md` block, hooks, git hooks), whether a claimed feature is
released or only an open pull request, the licence before any idea is folded in, and the terms of a
data route before it is adopted.

## What it will not do

- Install, enable or run the candidate, start its MCP servers or run its hooks.
- Install a scanner. A missing one is reported NOT-RUN; your steps are in
  `references/install-walkthrough.md`.
- Send candidate content to a remote scanner or an LLM analyzer without your yes.
- Write a settings file, a marketplace file or a hook. It names the rules; gatewarden writes them.
- Run an unknown author's binary on the host. That goes to a sandbox (hypervrunner).

## Package

```
revenantworks-warden-trustwarden/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE
├── references/
│   ├── red-flags.md            # the vet list, read on every vet
│   ├── scanner-matrix.md       # which tool reads which kind, flags, known skips (stamped)
│   ├── install-terms.md        # terms and the Claude Code control behind each (stamped)
│   ├── install-walkthrough.md  # owner-run scanner installs, a check and a way back each
│   └── pack.md                 # warden roster, generated
├── scripts/
│   ├── trust_vet.py            # stdlib; vet and revet; JSON verdict
│   └── test_trust_vet.py
└── evals/                      # hand-run suites + native claude plugin eval cases
```

## Entry points

| Say | Does |
|---|---|
| `trustwarden vet <url, path or plugin@marketplace>` | Clone to scratch at one SHA, inventory, script and scanners, the vet list, verdict, terms, report |
| `trustwarden revet <path> --from <SHA> --to <SHA>` | Drift since the pin: every changed file, which need a fresh vet, both tree hashes. Changes nothing |
| `trustwarden terms` | The terms and the gatewarden rule list for a vet already done |
| `trustwarden refresh` | Re-read the tool flags and Claude Code controls, then restamp the two dated references |

Plain requests work too: "is this skill safe to install", "vet this MCP server before I add it",
"check this GitHub Action", "what does this installer write".

## Verdicts

| Verdict | Means |
|---|---|
| PASS | Every file read by two readers (trust_vet plus a second scanner that agrees; skillspector is one option), no finding left. Carries the SHA pin and auto-update off |
| CONDITIONAL | Safe on stated terms, one per finding, plus a rule list for gatewarden. The ceiling when no second scanner agrees, or when code makes a network call: external hosts and localhost/loopback calls (internal, vet further for onward leakage) are separate classes |
| HOLD | Not decidable yet: unread executable content, no SHA, unread scanner hits, an installer that writes config, hidden text, a link inside the tree |
| FAIL | Do not install: a hook or load-time command that reaches the network, a download piped into a shell, a shipped safety bypass |

## Requirements

Python 3 (stdlib) and git. Optional scanners: skillspector, zizmor, pinact, OpenSSF Scorecard (Docker
image, on demand), cisco skill-scanner. snyk agent-scan is opt-in only: it needs a token, sends data
out and starts MCP servers. Without a shell the vet list is walked by hand and the verdict cannot be
PASS.

## Tests

`python -m unittest discover -s scripts -p "test_*.py"` — 34 cases over invented fixtures; no scanner
is installed or run by the tests.

## Staying current

`references/scanner-matrix.md`, `references/install-terms.md` and `SOURCES.md` carry a
`Last verified` stamp and a 90-day cadence. `trustwarden refresh` re-reads them; the pack's upkeep
sweep flags them when due. History is in `CHANGELOG.md`.

## Install one or the other

This skill ships in the warden pack and may also ship as its own featured one-skill plugin. Install one or the other, not both: the two carry the same skill name, so the listing pays for the description twice, and an update to one side only leaves two different bodies under one name.
