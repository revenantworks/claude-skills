# Changelog — revenantworks-scribe-researchscribe

## [1.0.0] — 2026-10-01

First public release. Research that ends in something usable, from any route, with every claim
graded by kind of fact.

Description cut to about 600 characters, main use case first (2026-10-08).

K8c fix round (2026-10-08): the description names rigwright as the owner of config-file checks
(K7-3-15).

### What it does

- Tags every claim [documented], [vendor-reported], [estimate] or [unverified], and keeps every
  unchecked claim visible (blocked pages, budget cuts, rate-limited checks); nothing is dropped
  silently.
- Ends in one of three products: a verdict (one recommendation with a flip condition), a versioned
  playbook, or a graded research report.
- Verdicts on measured systems follow their own measurement rules.
- Routes deep research three ways: (a) a claude.ai Research hand-off, (b) a Claude Code workflow or
  subagent fan-out, (c) a single pass. It states the size and cost of any fan-out and waits for a yes
  before spending.
- Report intake: a handed-in report is re-graded live into a verdict, playbook or graded report.
- Verify: a fact and form drift catalog for an existing doc or report. `verify official` checks
  each claim against the vendor's own docs for the version in use.
- In a repo, a research report lands as a cited file (on the owner's yes) that later runs extend.
- Walled sources (Reddit, YouTube, X and other sites that block bots or need a login): a route table,
  a capture request to the owner, and a documented owner-run API route.

### Entries

- `verdict` (with a "quick" switch for deciding cells only), `playbook`, `research`, `verify`,
  `sources`, `refresh` (re-verifies the dated platform and hard-source files). A bare
  `researchscribe` states its capability and asks what to decide, document or check.

### Workflow and scripts

- `workflows/research.js`: an optional saved workflow for Claude Code (owner opt-in); shipped by the
  pack, it runs as `/scribe:research`. Before each launch the skill checks the workflow format stamp
  and re-reads the workflow docs when it is stale.
- `scripts/workflow_lint.py` (optional, stdlib only): lints the workflow file;
  `scripts/test_workflow_lint.py` tests it.

### Safety rules

- Never spends on a fan-out without a yes; "just write it" skips the criteria or template gate,
  never that yes.
- Without web search and fetch, every product ships provisional and [unverified].
- No package to install, no MCP server, no key.

### Integrations

- Writes in a named voice or brand when asked; tags and figures do not change.
- Optional pointers, never required: lorescribe, commscribe, a brand's `VOICE.md`, whisperrunner,
  duckrunner, lmstudiorunner.
- Dated references: platform facts and hard sources (30 days), parity register (90 days).
