# Sources

Last verified: 2026-09-26

handoffwright's shape is drawn from two internal records rather than a published standard, so
this file maps content to origin instead of to external documentation. The parity register below
is the one volatile part (declared in `volatile.json`, calendar class, 90-day cadence).

## Parity register

Scanned 2026-09-26, 90-day cadence. Public session-handoff skills this member is compared
against; a rescan checks each for a new capability worth a catalog row.

| Id | Skill | Scanned | What it adds that handoffwright weighed |
|---|---|---|---|
| VK | github.com/v-kravchenko/claude-handoff | 2026-10-01 | Archived 2026-10-01 (last release 1.5.5, 2026-09-30). Resume staleness report and wait for a go; per-step verify (adopted 1.2.0). Stored handoffs uncommitted. |
| OS | github.com/ostikwhy-blip/claude-code-handoff-skill | 2026-09-26 | Failed-approaches section; a 250–400 line cap (adopted 1.2.0 as tried-and-ruled-out with evidence, and a one-screen-per-repo size note). |
| RV | github.com/REMvisual/claude-handoff | 2026-09-26 | What-we-tried and chosen-or-rejected decisions; a phased plan with rollback (adopted 1.2.0 as the brief's per-step undo). Does not commit. Its README carries an agent-directed line, read as data. |
| AC | github.com/hotalexnet/agent-checkpoint | 2026-10-01 | Repo-local checkpoints; records branch and base commit; resume reports missing commits. Leaves committing to the user; no stash or reflog check. |
| MP | github.com/mattpocock/skills (`claude-handoff`, MIT) | 2026-10-08 | Hands the work to a fresh agent at once rather than waiting for a paste; named in the 2026-10-08 estate review. Taken as an idea only, in our own words, as the `now` entry (`references/now.md`); the git-verified, committed state stays the margin. No text copied. |

**Verdict (2026-10-01, re-scanned live): PARITY + MARGIN.** Parity: VK's staleness report and wait-for-go, OS's
failed-approaches section and RV's per-step undo are all adopted. Margin no register row holds:

- **Commit in the same call, with the sha reported.** VK stores handoffs uncommitted and RV does
  not commit; handoffwright's write is not done until `git commit` returns, and a gitignored
  location quotes the ignore rule instead of force-adding.
- **State verified against git, never a report.** Every landed sha is read from `git log`; a
  claim git cannot confirm is written as unverified.
- **Resume checks the tree before trusting the file.** `git stash list`, `git reflog` and an
  ancestry test on the handoff sha run first; none of the three incumbents checks for a stash.
- **Two shapes in one skill.** A resume of this session and a forward task brief whose model
  line comes from a tier pick, each ending in a paste-ready starter prompt.
- **No stale handoff reads as current.** Supersede stamps, the named `HANDOFF-<slug>.md` form
  with its Closed line, and a non-git change listed with its reversal.

## Content origins

| Source | Applies to | Key guidance |
|---|---|---|
| A private run's resume files, `RESUME.md` and `HANDOFF-PROMPT.md` (not shipped; read on disk during this member's research pass, never copied verbatim) | `references/handoff-template.md` (the file shape) | The section order (State now / Owner decisions / Next / Questions / Observations logged), the per-repo verified-sha form, and the resume-time `git stash list` / `git reflog` check are drawn from these two files' own shape. Only the shape moved into the template — no repo name, sha, decision, or path from either file is reproduced. |
| task-observer observation #0032, `session-teleport-stashed-the-untracked-run-ledger` (owner-private observation log) | `SKILL.md` — Write step 3 (Commit), the Never section's first rule | The commit-in-the-same-call rule this whole skill exists to enforce: an untracked run directory was silently `git stash`-ed by a session handover, and a clean `git status` afterward read as "nothing to recover" rather than "something is stashed." |
| This pack's own H1 research pass (a private run, not shipped; candidate survey and spec, cited in full in `CHANGELOG.md`) | `SKILL.md` throughout; the dispatchwright and task-observer boundary paragraphs | The candidate survey (five existing session-handoff skills, none satisfying the commit requirement) and the spec section this member was built against — working name, pack placement, entry points, the commit rule, and the trigger-eval rows to write. |
| `revenantworks-foundation-dispatchwright/SKILL.md` §5 (Durability contract) and `references/ledger-schema.md` | `SKILL.md` — Gather step 1 (ledger-first reporting inside an active run); the dispatchwright boundary | The rule that a run's own ledger, not a second hand-kept list, is the source of truth for unit state — handoffwright reads it rather than re-deriving it, the same discipline dispatchwright's own Reconcile applies to a unit's report. |

**Unsourced by design.** The exact file location rule (a run directory's `RESUME.md` when one
exists, the project root otherwise) and the no-remote-degrades-to-commit-only wording are
authored for this skill from the spec above, not drawn from a published standard — declared here
so the gap is visible rather than implied, matching this pack's own convention.
