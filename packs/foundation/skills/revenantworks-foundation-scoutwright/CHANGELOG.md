# Changelog — revenantworks-foundation-scoutwright

## [1.0.0] — 2026-10-01

2026-10-08 (K8 fix round): trigger row 26 names a current feature (`/dash`); row 31 and a fourth edge note pair `fit` with pacewright's `baseline` (audit K7-2-10, -27).

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

### Entry points

- `sweep` (every source since the ledger), `since <date or version>`, `watch <area>`, `adopt`,
  `fit <model or feature>` (how best to use it here), `sources` (probes every source), `refresh` (re-verifies the source map).

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
- An outside research topic is researchscribe's; applying an adopt row skillwright's; a config change
  rigwright's; a tier pick promptwright's.
