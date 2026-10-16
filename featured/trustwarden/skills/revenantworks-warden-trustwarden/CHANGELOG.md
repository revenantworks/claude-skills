# Changelog — revenantworks-warden-trustwarden

## [1.0.0] — 2026-10-01

First public release. Vets third-party skills, plugins, MCP servers and GitHub Actions before they
are installed, and ends with a verdict and the terms to install under, never a bare score.

Description cut to about 600 characters, main use case first (2026-10-08).

2026-10-16 (observation 0428): a model-weights kind. Pickle and torch files are parsed opcode by
opcode, never loaded, and every import is named against a tensor, numpy and collections
allow-list (FAIL for `os`, `subprocess`, `eval` and the like; HOLD for the unknown, the
unresolved, TorchScript code and trailing bytes); safetensors and GGUF read as non-executable
after a header check. fickling, modelscan or picklescan, run by hand, is the second reader for
weights. In a git checkout each row says whether it is tracked, and an untracked `.pyc` compiled
from a tracked source is GENERATED, out of the verdict. A new `licence` mode reads the Civitai and
Hugging Face fields and the upstream text for one weight and holds when they disagree.
New `references/model-weights.md`. 28 tests.

2026-10-16 (observation 0445): scanner discovery looks on PATH, then in the Python user Scripts
folder (`pip install --user`), and names that folder when the scanner was found there; the
install walkthrough gives the pip form, the PATH line, and says `python -m zizmor` is not a check.
One test.

### What it does

- Clones the candidate to scratch at one commit SHA and inventories every file with the readers that
  read it; an unread executable, bytecode, archive or oversized file means the verdict cannot be
  PASS. A scanner that takes the path runs from an empty temp folder, never from the clone or the
  folder beside it (2026-10-09).
- Drives skillspector, zizmor, pinact, OpenSSF Scorecard (Docker, on demand) and cisco
  skill-scanner when present; snyk agent-scan is opt-in only.
- Reads what scanners do not look for: a skill line that runs a shell command at load time, what an
  installer writes (a global `CLAUDE.md` block, hooks, git hooks), whether a claimed feature is
  released or only an open pull request, the licence before any idea is folded in, and the terms of
  a data route before it is adopted.
- Lockfile checks: dependencies with no lockfile, entries resolved outside the registry, missing
  integrity hashes, unpinned requirements. A look-alike of a popular skill whose install count
  outruns its history is HOLD. Sentry's skill-scanner counts as an optional second reader for skills.
- Network calls in code are two separate finding classes: external hosts, and localhost or loopback
  calls (internal, vet further for onward leakage).
- Verdicts: PASS (every file read by two readers that agree, no finding left), CONDITIONAL (safe on
  stated terms, one per finding; the ceiling when no second scanner agrees or code makes a network
  call), HOLD (not decidable yet), FAIL (do not install).
- Terms tied to Claude Code's own controls: the SHA pin, auto-update off, a read-only copy for
  skills, and the exact rules gatewarden should add (`deniedMcpServers`,
  `disableSkillShellExecution`, deny rules for `bin/` tools).

### Entry points

- `vet <url, path or plugin@marketplace>`, `revet <path> --from <SHA> --to <SHA>` (drift since the
  pin; changes nothing), `terms`, `refresh` (restamps the scanner matrix and install terms).

### Scripts

- `scripts/trust_vet.py` (Python 3 stdlib): vet and revet, JSON verdict.
- `scripts/test_trust_vet.py`: 56 cases over invented fixtures; no scanner is installed or run by
  the tests.

### Safety rules

- Never installs, enables or runs the candidate, starts its MCP servers or runs its hooks.
- Never installs a scanner; a missing one is reported NOT-RUN (`references/install-walkthrough.md`
  holds the owner's steps).
- Never sends candidate content to a remote scanner or an LLM analyzer without a yes.
- Never writes a settings file, a marketplace file or a hook; it names the rules and gatewarden
  writes them. An unknown author's binary goes to a sandbox (hypervrunner), never the host.
- Network only to clone the candidate and read its GitHub metadata.

### Integrations

- Runtime permissions are gatewarden's, secrets in the code shieldwarden's, building or auditing
  your own skills skillwright's.
- Also ships as a featured one-skill plugin; install the pack or the featured plugin, not both.
