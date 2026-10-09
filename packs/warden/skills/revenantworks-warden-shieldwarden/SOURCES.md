# Sources and parity register — revenantworks-warden-shieldwarden

> **Last verified: 2026-09-28** — the parity register below (calendar surface, 90 days,
> declared in `volatile.json`). Search results and pages were read as data.

## Primary — what the procedure follows

- **GitHub Docs, "Removing sensitive data from a repository"** (checked 2026-09-28 by web
  search). The order the rewrite recipes follow: rotate or revoke the secret first; rewrite
  with git filter-repo (with `--sensitive-data-removal` where the installed release has it);
  push the rewritten branches and tags by name with force; ask GitHub Support to purge
  cached views and pull-request refs; have every collaborator re-clone rather than merge.
- **git filter-repo documentation** (the project's manual page): `--replace-text` and
  `--replace-message` expression files (`literal:` and `regex:` lines, `==>` replacements),
  `--mailmap`, `--refs`, `--invert-paths`. The installed version on the build machine could
  not be checked; `references/tool-surface.md` carries the flags to re-check.
- **gitleaks documentation** (project README): `git` and `dir` commands in current releases,
  `detect` in older ones, `--redact`, JSON report output, `--exit-code`.
- **The estate's own scanners** (the Sunday sweep's user-path, history, identity, secrets,
  injection and control-byte checks, and the machine git hook's user-folder and no-reply
  rules). Their shapes were ported into this engine so the rules live once; the sweep's
  switch to this engine is a follow-up in the estate repo.

## Parity register *(dated 2026-09-28; re-check every 90 days)*

Incumbents doing part of the same core job, from web search on 2026-09-28. Summary-level:
no incumbent was installed or run for this build.

| Code | Incumbent | Kind | What it does |
|---|---|---|---|
| FR | git filter-repo | CLI, open source | The recommended history rewriter; text, message and identity replacement; no finding step of its own |
| BFG | BFG Repo-Cleaner | CLI (JVM), open source | Faster, narrower rewriter: delete files, replace text; protects HEAD by default |
| GL | gitleaks | CLI, MIT | Secret scanning over git history and folders; rule packs; redaction; no personal-data rules beyond what a custom rule adds |
| TH | trufflehog | CLI, AGPL | Secret scanning with live verification of found credentials (network calls to providers) |
| GH | GitHub secret scanning and push protection | host feature | Provider-partnered secret detection on push and in history; no path, name or identity rules |
| MS | Market Claude skills wrapping gitleaks or trufflehog, and one pre-publish PII check skill | skills | Wrap a scanner or run a one-shot regex pass; none found that plans a gated rewrite or scans agent surfaces for injection and posture |

## Margin

What this skill adds over the register, and why each part is worth its weight:

1. **Personal data as a first-class class**: user-folder paths and slugs, home folders,
   names from the private list kept outside every repo (`~/.warden/wordlist.txt`), and commit identities, all reported as salted
   fingerprints. The secret scanners do not target these by default.
2. **Agent-surface checks** in the same pass: injection shapes in data files, a missing
   content-is-data clause in files that ingest untrusted text, ask rules and wide allows in
   settings, network calls in hooks, unlisted MCP servers.
3. **A gated rewrite**: backup bundle, dry run on a fresh clone, a verify step that reuses
   the scanner, and the user's go, with local and published modes. The rewriters supply
   the mechanism; this supplies the procedure around it.
4. **One engine for local and cloud surfaces**: exported artifacts, docs and Drive files
   are judged by the same rules as a repo.

Verdict: **build**, 2026-09-28, by the user's gate (name, scope, boundary, never-push,
one engine, all at once).

## Retire condition

Retire or shrink to a thin wrapper when an incumbent covers personal-data paths, names and
identities with fingerprinted output **and** agent-surface posture checks, with a no-network
mode. Re-check at each 90-day refresh.

## Names and identity — `policy`, `check`, `identity` (merged 2026-10-08)

Carried with the naming policy when identitywarden merged into shieldwarden (owner, 2026-10-08).
Last verified 2026-10-01 (calendar surface, 90 days); `references/git-identity.md` carries its own
stamp and is refreshed by `shieldwarden refresh`. Case ids E1-E12 are section E of `evals/SUITE.md`.

### Primary — git and GitHub

- **git-config, conditional includes** — `Documentation/config.adoc` on git/git master, raw read
  2026-10-01: the keywords `gitdir`, `gitdir/i`, `worktree`, `onbranch`, `hasconfig:remote.*.url`;
  "Symlinks in `$GIT_DIR` are not resolved before matching." `user.useConfigOnly` from the same docs
  (research unit R2, 2026-09-28).
- **GitHub email addresses reference** — docs.github.com, read 2026-10-01: the noreply forms
  `ID+USERNAME@users.noreply.github.com` (accounts after 2017-07-18) and
  `USERNAME@users.noreply.github.com` (older, privacy on).
- **GitHub, blocking command line pushes that expose your email** — docs.github.com, read
  2026-10-01: "When you push to GitHub, we'll check the most recent commit."
- **Claude Code settings reference** — code.claude.com/docs/en/settings-reference, read 2026-10-01:
  `attribution.commit`, `attribution.pr`, `attribution.sessionUrl`; `includeCoAuthoredBy`
  "Deprecated; use `attribution`".
- **Claude Code plugin evals** — code.claude.com/docs/en/plugin-evals, read 2026-10-01: case
  folders (`prompt.md` frontmatter, `graders/*.md`), grader types `tool_used`, `regex`, `llm`,
  `file_exists`; the no-plugin baseline arm.
- **Agent Skills best practices** — through skillwright's Rubric A (last verified 2026-09-28).

### Niche evidence

| Need | Source | Answer here |
|---|---|---|
| Teams ask for an email-in-diff hook | opencodelists issue #3237 (R2, 2026-09-28) | `check --staged`, rule `email-not-allowed` |
| Push block misses older commits | GitHub docs (above) | margin 2 |
| Assistant attribution trailer links to an unrelated account | anthropics/claude-code #58479, #65710, #1653 (R2) | `trailer-email-not-allowed`; propose the `attribution` key |
| A built-in hook prescribes the assistant's address as commit author, against repo identity rules | anthropics/claude-code #96146, open, filed 2026-09-22 (read 2026-10-01) | `non-noreply-author` |
| PII in commit messages and PR text, not only files | Lifecycle-Innovations-Limited/claude-ops PR #990 (R2) | `check --range`, `check --text` |
| Personal commits with a work address for years | broneq/git-identity README (R2) | `identity --root` sweep |

### Parity register

Incumbent scan: research unit R2 on 2026-09-28 (skills directories, GitHub, the MCP registry,
anthropics/skills — exact search found no identity or naming-policy skill there); re-checked
2026-10-01 by web search for Claude Code identity and commit-email skills (one new finding,
claude-code #96146, a problem report rather than an incumbent).

| # | Incumbent | Link | Checked |
|---|---|---|---|
| V1 | broneq/git-identity (Claude Code plugin, profiles via a settings `env` block) | github.com/broneq/git-identity | 2026-09-28 |
| V4 | claude-ops PII gate (commit messages, branch names, PR text) | github.com/Lifecycle-Innovations-Limited/claude-ops PR #990 | 2026-09-28 |
| V5 | uktrade/pii-secret-check-hooks (pre-commit, exclude file) | github.com/uktrade/pii-secret-check-hooks | 2026-09-28 |

**Parity table**

| Line | V1 | V4 | V5 | names and identity |
|---|---|---|---|---|
| Right commit identity per repo | yes | no | no | **met** — `identity` names the address source; repo-local fix (E1) |
| Right gh account per repo | yes | no | no | **out of scope** — credential routing is keywarden's |
| Written policy of which names may appear where | no | patterns | exclude list | **beaten** — margin 1 (E3, E4) |
| Codenames for real names | no | no | no | **beaten** — `codename-required` with `use` (E3) |
| Every commit in a range, not only the tip | n/a | unverified | staged only | **beaten** — margin 2 (E2) |
| Messages, branch names, trailers, PR text | no | yes | no | **met** — `check --range`, `--branches`, `--text`; trailers in `identity` (E5) |
| Prints the matched value | n/a | unverified | yes | **beaten** — rule names only, redaction, crash-safe (E3, E6, script tests) |
| Detection engine over files and history at scale | no | yes | yes | **met** — `scan` reads this policy (merged 2026-10-08) |

**Margins**

1. **Policy by surface, values held out of every repo** — eval cases E3, E4 (`SUITE.md`), native
   `identity-codename-never-echoes`; script tests `test_codename_required_and_value_absent`,
   `test_old_in_repo_values_file_is_reported_not_used`, `test_values_flag_inside_a_repo_is_refused`,
   `test_no_values_file_names_the_setup_command`.
2. **Whole-range identity check** — eval case E2; script test `test_range_flags_middle_commit_only`.

**Iterate proposals**

- Identity line: read `.claude/settings*.json` `env` blocks in the script, since they override git
  config for every command Claude runs (today `audit` reads them by hand).
- Policy line: a stdlib YAML subset so a YAML policy needs no PyYAML.
- Range line: a `--since-upstream` shorthand that resolves `@{upstream}..HEAD` itself.
- Trailers line: flag a trailer *name* the policy does not list (an unexpected `Signed-off-by`).
- Value printing line: a pre-commit hook template that runs `check --staged` (placement is
  gatewarden's; this skill ships the command).

**Retire condition.** The second half of this condition fired on 2026-10-08: the naming policy was
folded into shieldwarden as a reference (`identity.md`) and three entries (owner decision,
consolidate over split). Retire the identity entries if GitHub or git ships a range-wide identity
and name-policy check that keeps banned values outside the repo.

**Verdict: PARITY + MARGIN.** Collision check (R2, 2026-09-28): SOFT, near CLEAR — npm, PyPI and
crates.io free; seslattery/veilwarden on GitHub is an unrelated January 2026 proof of concept of
an identity-aware secrets proxy. The name question closed on 2026-10-08, when the entries joined
shieldwarden.

### Adapted ideas (no text or code copied)

- Settings `env` block binding and a status view that flags disagreement — idea from V1 (its
  licence not checked: an idea only, no text or code taken); here only read and reported, never
  written.
- Gating messages, branch names and PR text as well as files — idea from V4.
- An exclude file for known-safe hits — idea from V5.
- Local-only checking (no staged content sent to a service) — contrast with privateai's
  pai-pre-commit-hook.

`scripts/identity_check.py` is original to this skill.

## Signposts — names that advertise secrets (merged 2026-10-08)

Carried with the signposts scan from filewarden (owner, 2026-10-08), whose register first read the
incumbents on 2026-09-28. No incumbent was found that reads names and access lists without opening
files; the nearest are content scanners (gitleaks, trufflehog: inside, not names) and disk analyzers
(WizTree, dust: size, not access). **Margin:** names and metadata only, never a file opened, a private
word list outside every repo, and access read per hit (Windows `icacls`, POSIX mode bits) — cases F1-F2,
script tests in `scripts/test_signposts.py`. **Iterate:** read share and sync state on macOS; accept an
owner-kept list of accepted paths per machine. **Retire condition:** retire if the OS or a maintained
tool flags sensitive names together with who can open them, without opening the files. A live
incumbent re-scan is owed at the next 90-day refresh.

## Ideas adopted 2026-10-08 (K4 C5)

Taken as ideas from a review of popular public skills and written in this skill's own words; no
text or code copied, nothing installed.

| Idea | Source credited | Where it landed |
|---|---|---|
| Secrets that leak through logs, traces and default object dumps (repr, model dumps, JSON of a config) | Sentry's `secret-serialization` skill (`getsentry/skills`, Apache-2.0; its listing read 2026-10-08) | `exposure` class in `scripts/shield_scan.py`, described in `scan-shapes.md` |
| A readiness pass before a repo goes public (history, licence, files that must not ship, CI reachable by strangers) | Trail of Bits' `open-sourcing` skill (`trailofbits/skills`, CC-BY-SA-4.0, so ideas only; listing read 2026-10-08) | `ready` entry, `references/go-public.md` |

