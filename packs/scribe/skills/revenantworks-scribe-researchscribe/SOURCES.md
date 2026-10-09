# Sources

Last verified: 2026-10-01 (the parity register below; upkeep reads this stamp).

Calendar surface, 90-day cadence (`volatile.json`). Platform facts (commands, limits, aliases,
the workflow file format) are not kept here: they live in `references/platform-facts.md`, stamped
on its own 30-day clock. Site routes for hard sources live in `references/hard-sources.md`.

## Doctrine sources

| Source | Read | Guidance drawn |
|---|---|---|
| Anthropic, Agent Skills best practices (platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | 2026-09-26 (pack baseline) | Lean body, mutually exclusive reference files, contents lists past 100 lines, feedback loops |
| Claude Code, dynamic workflows (code.claude.com/docs/en/workflows) | 2026-10-01 | The fan-out route, the saved-workflow file rules, sizes, limits, approval per permission mode, the bundled deep-research workflow |
| Claude Code, plugin manifest reference (code.claude.com/docs/en/plugins/manifest-reference) | 2026-10-01 | A plugin's `workflows/` folder or `workflows` manifest path |
| Claude Code, model configuration (code.claude.com/docs/en/model-config) | 2026-10-01 | Role-to-alias table |
| claude.ai Research help article (support.claude.com, article 11088861, page dated 2026-06-02) | 2026-10-01 | Route (a): plans, surfaces, web search prerequisite, connected sources |
| Anthropic engineering, "How we built our multi-agent research system" (2025-06-13) | 2026-10-01 (pack research unit) | Scale effort to the query (1 agent for a fact, 2–4 for a comparison), start broad then narrow, a separate citation pass |
| Hard-sources route research (pack research unit, 2026-10-01): Reddit, YouTube, X, Hacker News, GitHub, Discord terms and APIs | 2026-10-01 | `hard-sources.md` route table; Reddit's own pages were unreadable to the fetch tool, so Reddit terms are quoted through two secondary sources and marked |
| The predecessor skill's evidence doctrine (four tags, kind-of-fact test, verdict and playbook contracts), carried with its eval history | at the base commit | Every rule in `verification.md`, `verdict-mode.md`, `verdict-measurement.md`, `playbook-mode.md` |

## Parity register

Scanned 2026-10-01. Re-check every 90 days.

**Incumbents**

| ID | Incumbent | Link | Checked | What it does on this job |
|---|---|---|---|---|
| R1 | Claude Code bundled deep-research workflow | code.claude.com/docs/en/workflows | 2026-10-01 | Fans out searches, fetches and cross-checks sources, votes per claim, returns a cited report; unverifiable claims listed as unverified; runs only when the user invokes it |
| R2 | claude.ai Research | support.claude.com article 11088861 | 2026-10-01 | Agentic multi-search with citations on paid plans, plus connected workspace data; not reachable from Claude Code |
| R3 | 199-biotechnologies/claude-deep-research-skill | github.com/199-biotechnologies/claude-deep-research-skill | 2026-10-01 | Report engine with depth modes and credibility scripts; about 1.1k stars; no licence; open bugs on strict-mode holes, Windows encoding, subagent search access |
| R4 | mr-ubik/deeper-research | github.com/mr-ubik/deeper-research | 2026-10-01 | Verbatim source archive, decoy-calibrated verification, mechanical citation gates; Apache-2.0; little adoption |

**Parity table** (researchscribe 0.1.0)

| Line | vs R1 | vs R2 | vs R3 | Reason · case |
|---|---|---|---|---|
| Breadth: parallel search angles | met | met | met | the saved workflow or R1 itself; R2 by hand-off · C7, C8 |
| Claim cross-check | met | beaten | beaten | skeptic re-read per page, plus the data and summariser rules on every worker · C16, C18 |
| Evidence grade by kind of fact | **beaten** | beaten | beaten | vendor-set versus vendor-measured · C13 |
| Blocked sources visible | **beaten** | unknown | met | attempts list on every route · C14 |
| Budget-cut and rate-limited claims visible | **beaten** | unknown | met | kept as [unverified] with cause · C15 |
| "Qualifies" is not "contradicts" | **beaten** | unknown | unknown | qualified status keeps the qualifier · C16 |
| Ends in a decision (pick, flip condition, confidence) | beaten | beaten | beaten | verdict mode · C2 |
| Living, versioned reference doc | beaten | beaten | beaten | playbook mode · C4, C5 |
| Cost control before a fan-out | beaten | out of scope | met | route, size and role stated, owner yes first · C7 |
| Instructions inside sources | beaten | unknown | unknown | finding, never acted on · C17 |
| Walled sources (Reddit, YouTube, X) | beaten | out of scope | out of scope | access order, capture requests, no bypass · C10, C11 |
| Long HTML or PDF report | out of scope | met | met | a report is data to grade, or a graded Markdown report |
| Connected workspace data | out of scope | met | out of scope | reached only through R2 |

**Named margins** (each tested by the cases named):
1. **Graded, decision-ready output from any route.** Whatever searched, the product carries
   kind-of-fact tags, a coverage or attempts line, a flip condition (verdicts) and a confidence
   line from the deciding cells. C2, C13, C21.
2. **Nothing disappears silently.** Blocked sources, budget-cut claims, rate-limited verifiers
   and summariser absences are listed with cause and date. C14, C15, C18.
3. **Route picker with a cost statement.** Route (a), (b) or (c) per question, agents sized by
   query class, model role per stage, and the user's yes before any fan-out. C6, C7, C9.

**Iterate proposals.** Adopt R4's decoy calibration as a build-time eval (a planted false figure
the verifier must refute). Offer an optional verbatim archive of fetched pages in Claude Code
(R4). Add a with/without run on C13 and C14 in the pack's eval pass.

**Retire condition.** Retire the fan-out half of `research` mode when R1 grades by kind of fact,
keeps blocked and budget-cut claims visible, and can end in a decision with a flip condition.
Keep verdict, playbook, verify and sources then, taking R1's report as input.

**Verdict: PARITY + MARGIN** (margins 1–3). Risk: R1 improves quickly; margin 2 depends on its
open issues staying open (listed in `platform-facts.md`).

**Name collision** (2026-10-01): three unrelated repositories named ResearchScribe with no
adoption; npm and PyPI free. SOFT; the full name `revenantworks-scribe-researchscribe` is unique.

## Ideas adopted (2026-10-08)

Taken as ideas from a review of popular public skills and written in this skill's own words; no
text or code copied, nothing installed.

| Idea | Source credited | Where it landed |
|---|---|---|
| Research findings written into the repo as a cited file the next session reads | Matt Pocock's `research` skill | `research-mode.md` §7, "A cited file in the repo" |
| Check claims against the vendor's official docs for the version in use, never a blog | Addy Osmani's source-driven development skill | `playbook-mode.md` §3, `verify official` |

## Adapted material

No text is copied from R1–R4. The verification ideas credited above (decoy calibration, verbatim
archive) are proposals, not shipped code.
