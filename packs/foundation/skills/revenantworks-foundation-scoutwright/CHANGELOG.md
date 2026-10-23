# Changelog — revenantworks-foundation-scoutwright

## [1.0.0] — 2026-10-01

2026-10-16 (owner eval run, U38): `output-format.md` keeps the eight change-report headings word for word; a plain-language reply had renamed section 5 and dropped the word "undocumented" (case `docs-page-diff`).

2026-10-08 (K8 fix round): trigger row 26 names a current feature (`/rw-vigil`); row 31 and a fourth edge note pair `fit` with pacewright's `baseline` (audit K7-2-10, -27).

2026-10-08: description cut to about 600 characters, main use case first; trigger phrases and seams kept (routing proof: K9 evals).

First public release. Watches the Claude platform for change and turns each change into work for
this setup.

### What it does

- Reads Claude Code (hooks, settings, plugins, evals, subagents, workflows), claude.ai (Projects,
  Research, artifacts, design systems, Docs, connectors), Cowork, the API and models, docs,
  changelogs and community sources.
- Every relevant change lands as "affects X, change file Y, owning skill Z" in a dated change report.
- Catches what no changelog says: a docs page that vanished, a page whose outline moved, a tracker
  issue about a silent removal.
- Flags skills whose dated model or tier table has gone stale.
- Writes adopt rows for a skill currency sweep, with a read-back before every write.
- Judges how best to use a new model or feature in your own work: a fit card per item with use for,
  not for and unknown per job class (read from your tier tables, agent definitions, routines and run
  ledgers), the places a feature would replace a workaround, remove a manual step or cut cost, and
  a replay trial proposed with its cost for every unknown.
- Reads walled community sites only through lawful routes, with a capture queue for the owner.
- Benchmarks your skill roster once a month against public skill and plugin repos: the official
  listings, the most-starred repos and a long-tail sample chosen by need, so good ideas in small
  repos are found too. It reads your roster at run time, compares capability by capability, and
  gives each find one verdict: build (fold the idea into a named skill), adopt (rely on it as is,
  after a vet) or skip (with one reason).

### Entry points

- `sweep` (every source since the ledger), `since <date or version>`, `watch <area>`, `adopt`,
  `fit <model or feature>` (how best to use it here), `bench` (the monthly skill and plugin
  benchmark), `sources` (probes every source), `refresh` (re-verifies the source map).

### Safety rules

- Never installs, schedules itself or holds a key; writes only its change report, adopt rows and
  ledger. Without web fetch it says what it could not read and stops.
- `fit` changes nothing: it never edits a tier table or a setting, and runs a model trial only on
  the user's yes in the session (a scheduled run proposes, never runs). Trial figures go to
  pacewright's baseline as data.
- The report and ledger go to `.scout/` in the calling repo: committed in a private repo, kept out of
  git in a public one.

### Integrations

- A weekly sweep routine (designed by agentwright) calls `scoutwright sweep` as one step,
  then `scoutwright fit` on each new model or feature within a stated token budget.
- Optional: the gh CLI, a shell for exact page hashes, researchscribe for sites that block bots.
- A bench build row goes to skillwright; a bench adopt row to trustwarden for a vet before any
  install.
- An outside research topic is researchscribe's; applying an adopt row skillwright's; a config change
  rigwright's; a tier pick promptwright's.
