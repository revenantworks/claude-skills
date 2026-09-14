# Changelog — revenantworks-foundation-dispatchwright

## [1.2.9] — 2026-09-14

**Self-containment, owner ruling** (observation #0073). dispatchwright's Tier section (§4) called
promptwright's Entry — Model live for every unit's tier row — a real, load-bearing dependency the
skill's own `Dependencies (standalone profile)` section didn't disclose. Asked whether any
model-using foundation skill leverages a sibling for its own recurring job, the owner ruled that
this one, and tokenwright's parallel case, should carry the logic themselves instead — one source
of truth that can drift from the skills that call it, traded deliberately for N self-contained
copies that can drift from each other.

- New `references/tier-routing.md`: a Claude-only tier table (S/A/B/C, one model name per tier),
  the effort-before-tier rule, and the three role-based overrides §7 already restated from
  promptwright — now this skill's own doctrine, not a citation. Stated explicitly as a one-time
  copy of promptwright's `model-snapshot.md`, not a live mirror.
- `description`, the intro paragraph, §1's seams list, §4 (rewritten), §7's two citations, and
  Behavior notes — Scope all updated to read from the new file instead of calling promptwright.
- New **`dispatchwright refresh`** entry point, since the skill now owns a calendar-volatile file;
  `metadata.volatile` gains the corresponding entry.
- `evals/trigger-evals.md`: #14's boundary note corrected (dispatchwright tiers its own units now,
  not "what promptwright tiered"). 22 rows, 10/10 unchanged — the trigger conditions didn't move,
  only the internal mechanism. Cold re-judge owed since the `description` moved, not yet performed.

## [1.2.8] — 2026-09-13

- `references/unit-brief-template.md` gains a second Boundaries clause (#0062): isolating one
  hook's side effect can silently starve a sibling fixture that was only staying valid because
  the isolated write kept re-arming a flag or timestamp the sibling reads. A unit reports what
  live state (besides the path it directly touches) a control's pass/fail depends on, and pins
  against that dependency — via the hook's own test-override where one exists — rather than
  hoping the real file stays put. Reference-only; no entry-point contract moved.

## [1.2.7] — 2026-09-13

Nine task-observer observations from the weekly review staged 2026-09-13, drafted in autonomous
mode and applied on a review branch by a single writer. Body and reference only; the
`description` is byte-identical, so the routing surface is unchanged.

- **§2 Shape check names a fork only the requester can settle (observation #0049).** When the
  asked-for outcome has exactly one technically real path and that path crosses a boundary the
  owner owns — which platform an unattended agent runs on, which account, which credential model
  — the boundary is the decision, not an implementation detail; Shape check answers whether this
  is a fan-out, never whether the approach was authorised. The creation-type judgment itself
  stays agentwright's, as that observation assigns it.
- **§5 Durability contract gains the scripted-edit rule (#0058).** A scripted multi-file edit
  proves each edit landed with an asserted match count, not an exit code: a replace on a string
  that does not occur returns the original bytes and exits zero, and line endings are a per-file
  property — five files in one directory carried three. Write bytes, detect each file's own
  ending, assert the count.
- **§6 Wave execution gains two rules (#0043, #0044, #0051).** The `isolation: "worktree"` bullet
  now states that a review or polish skill a unit invokes is itself a writer — helpers told to
  report only have edited and pushed on their own, and one spawned a sub-agent that ran the
  unit's own release step — so the helper runs inside the worktree, the tree is diffed after each
  exchange, and the agents are re-listed to stop anything it started. A second bullet: cancelling
  a unit mid-flight stops the agent first and its processes second, and the evidence is the work's
  absence a minute later, never the kill command's success.
- **§8 Reconcile gains a reversal check and tightens the test-total rule (#0045, #0057).** A
  landed row whose surface is not a git commit is unverified until its `reversal` field is
  non-empty. The existing test-total check now says where the expectation comes from — a baseline
  run of the unchanged suite, not the last number someone wrote down — and an actual above it is
  recorded as the new expectation rather than passed quietly; the shortfall half of #0057 was
  already carried since 1.2.2 and is unchanged.
- **`references/ledger-schema.md` gains the `reversal` field (#0045).** How the unit's change is
  undone — the exact command, or the path of the file holding the prior state — written at the
  same time as `commit_sha`, by the unit that made the change. A git commit reverses itself; a
  setting, a plugin, a routine, a remote, a junction or a repo description does not, and the one
  rollback line that came out exact was the one whose undo file was written as it happened.
- **`references/unit-brief-template.md` gains six rules (#0043, #0044, #0045, #0047, #0053,
  #0057, #0058).** A review or polish skill you invoke inherits none of this brief — record `HEAD`
  and `git status`, isolate, diff after, and re-run `ListAgents` after each exchange with a
  backgrounded helper. Record the prior value before changing anything that is not a git commit
  and put the undo in the row's `reversal` field. A control or fixture written for a stateful hook
  performs that hook's real side effect, so the unit names every state path it touches and the
  mechanism that keeps the check side-effect-free. Read the regenerating function before cutting
  from a generated collection — a cut inside an idempotency guard's "already handled" set is a
  tombstone, not a delete. The Expected test total field is derived from a baseline run and
  reports its slack. Every scripted edit asserts its occurrence count, with the two-line per-file
  line-ending detector beside it.
- Registry body budget raise owed, 5700 → 6000 (`references/pack-registry.md`, skillwright): the
  six body additions are decision rules a fan-out run must not open a file to know — an
  authorisation fork at Shape check, the proof an edit landed, what a helper counts as, how a
  cancellation is verified, and the two Reconcile checks — body-resident for the same reason the
  other caps are. Estimated ≈5940 against a 5547 baseline; the writer confirms with
  `build.py --footprint` before landing and adjusts the ceiling if the measurement differs.
  `.claude/hooks/` untouched: nothing here changes what `dispatch_gate.py` or
  `dispatch_ledger_guard.py` parses, and the new `reversal` field is read by Reconcile, not by the
  guard.

## [1.2.6] — 2026-09-11

Applied by unit L1b (dispatch run `2026-09-10-estate-audit`) from the task-observer weekly
review staged 2026-09-11. Body and reference only; the `description` is byte-identical, so the
routing surface is unchanged.

- **§2 Shape check counts surfaces, not verbs (observation #0016).** A request naming four or
  more distinct surfaces is a fan-out whatever verbs carry it; every phrasing that should have
  fired and did not is kept as a positive control in the enforcing gate.
- **§3 Decompose gains three rules.** A unit's surface is its tool list, and a deferred or
  session-authenticated tool does not reach a subagent (#0033). A finding whose recommendation
  crosses a repo boundary is split before dispatch, not resolved by the acting unit (#0020). A
  packet's finding-id list and its prose brief are joined — every id must resolve to that unit's
  own surface — before it is dispatched (#0028).
- **`references/ledger-schema.md` gains "Closing a row" (#0023).** `done` joins the status
  vocabulary as the closing state for a unit that produces no commit; a table gives every way a
  unit can end its closing status and the moment it is written; the wave cap counts only rows in
  `dispatched` or `committed`.
- **`references/unit-brief-template.md` gains a tools line, a boundaries section and an
  observations section.** Tools beyond files and a shell are named at dispatch (#0033). An apply
  command that ends in an install is split into `repo_apply` and `owner_install` halves (#0026).
  A pasted tool invocation is a claim about the environment and is calibrated in the brief or
  marked unverified (#0035, #0036). A dispatched unit inherits the parent's observation-log
  activation and returns candidate observations plus the decisions the brief did not cover,
  rather than writing to a log outside its scope (#0019). The durability contract also states
  that a unit's gate runs against the **staged** tree — a guard built on `git grep` is blind to
  a file written but not yet added, and write → test → commit puts every new file through that
  gap (#0034).

## [1.2.5] — 2026-09-11

Reference and body-only pass; the `description` is byte-identical, so the routing surface is
unchanged.

- **`references/ledger-schema.md` documents the agent-count token (task-observer observation
  #0022).** The `surface` field's row now states that a Workflow/Task row fanning out to more
  than one agent carries an `x<N>` token (`subagent (workflow) x245`) instead of one row per
  agent, and that `dispatch_ledger_guard.py`'s `open_unit_count()` weighs the row by N against
  the 6-unit wave cap. The guard fix itself lives in `.claude/hooks/dispatch_ledger_guard.py`
  (rig infrastructure, not part of this package — see SKILL.md's Load budget); this bump covers
  only the schema doc that now matches the guard's real behavior.
- **§1 Scope and seams gains a fourth bullet, and the `dispatchwright resume` entry gains a
  pointer.** The new sibling `revenantworks-foundation-resumewright` (built this pass) writes a
  committed, general-purpose session handoff — the shape `RESUME.md`/`HANDOFF-PROMPT.md` already
  used by hand. Inside an active fan-out, this skill's own ledger and `dispatchwright resume`
  still own the resume state; resumewright covers the session-level handoff outside that —
  before a fan-out starts, between fan-outs, or in a session that never dispatches at all. No
  entry point, gate, or threshold moved; no eval re-anchor is owed.

## [1.2.4] — 2026-09-10

**Two task-observer observations from the second review pass, #0022 and #0032.**

§5 Durability contract: the "ledger row at three points" bullet gains a sentence — the
ledger file itself, and any `RESUME.md`/`OWNER-STEPS.md` beside it, is committed at every
one of the three writes, not held untracked to a final snapshot; the durability contract
covers the run's own record, not only the units'. The Resume bullet gains a sentence — if
the ledger path is missing or the tree reads unexpectedly clean, run `git stash list`
before concluding the run has no state, since a handover or worktree switch can stash the
whole run directory silently (#0032, `session-teleport-stashed-the-untracked-run-ledger`).

§6 Wave execution gains a bullet: count agents, not ledger rows, against the wave cap and
the usage-window check. A single Workflow/Task call that fans out to N agents costs N
units of both, whatever number of ledger rows records the call — three rows once hid 245
agents from both checks, and a wave costing more than the finding wave it verifies is the
same failure the estate audit's own Phase 2 hit the same day (#0022,
`a-workflow-row-hid-245-agents-from-the-wave-cap`).

`references/ledger-schema.md`: "Where it lives" reversed from gitignored to committed
(same reasoning as #0032 above, stated in full there — untracked state is one stash away
from gone); a new "Resuming a run" section carries the `git stash list`/`git reflog`
check; "Writing the ledger" names the commit-at-every-write requirement.

All three are decision rules a unit must not open a file to know, body-resident for the
same reason the other eight sections' caps are. Registry body budget raised 4500 → 4700
(`references/pack-registry.md`, skillwright 1.3.7) — landed at ≈4638/4700. `.claude/hooks/`
untouched here: `dispatch_gate.py` matches prompt text before a fan-out is even decomposed,
not agent counts inside an already-dispatched call, so no pattern change applies there; the
real enforcement point is `dispatch_ledger_guard.py`'s `open_unit_count()`, which counts
ledger ROWS the same way the incident did — flagged as a follow-up needing its own fix and
test coverage, not attempted in this pass. **The live installed copy in `~/.claude/hooks/`
is owner-installed and untouched by this repo change; the owner re-installs to pick up
`ledger-schema.md`'s doctrine change** (no hook code moved, so there is nothing to
re-install for the two SKILL.md/reference edits themselves — noted per house convention).

## [1.2.3] — 2026-09-10

**Three estate-audit findings, one patch** (`dispatchwright-packmd-orphan`,
`dispatchwright-push-without-invocation-control`, `dispatchwright-trigger-evals-header-format`).
Load budget gains the sibling-standard closing line — `references/pack.md`, boundary doubt about
a sibling's territory only — closing the one member whose Load budget never named the manifest
it ships. Behavior notes gains an **Invocation control** paragraph: this member is
model-invocable on purpose (recognizing and dispatching a fan-out is the job), carries no
`disable-model-invocation` flag (a Claude Code-only key that hard-errors on claude.ai and the
Skills API, surfaces this skill also ships to), and names what already bounds its pushes — §5's
identity check, `origin`-only pushes, §7's stop-and-ask on any unnamed irreversible action.
`evals/trigger-evals.md`'s header restated as `# Trigger evals — 22 queries (10 should / 10
shouldn't / 2 injection probes)`, matching the sibling header form; the row count and split were
already correct, only the header text was uninformative. No entry point, section numbering, or
scoring anchor moved; `evals/test-cases.md` and `evals/trigger-evals.md` re-anchor accordingly.

## [1.2.2] — 2026-09-10

**Three additions from the estate's first task-observer weekly review** (observations
#0006, #0007, #0008). §6 Wave execution gains a bullet: an
interrupt or rejected tool call in the parent session ends every unit running under it, and
nothing announces the stop — after any such event, re-read the ledger and each unit's own
journal before assuming a wave is still running; absence of output is unknown state, never
progress. §8 Reconcile gains two bullets: a reported gate figure (a frame rate, a test
count, any number a decision hangs on) is re-derived from the raw counts and stated
conditions the unit reports, not read off its summary line; a reported test total is
checked against the total the unit's brief stated before the run, not merely against
pass/fail colour — a runner that silently drops an unparseable file still reports green on
what it did run. `references/unit-brief-template.md` gains an "Expected test total" field
beside Expected artifacts to carry that number. No entry point, section numbering, or
scoring anchor moved; `evals/test-cases.md` re-anchors accordingly.

## [1.2.1] — 2026-09-09

**Identity check before push, and provenance on the shared fetch cache** (estate finding
`dispatchwright-pushes-to-main-with-no-identity-check-and-caches-fetches-without-provenance`,
VER-01 rubric S3/S4). §5's durability contract now requires a unit to check the expected push
account before pushing (`gh auth status` where available; structurally satisfied by pushing only
to `origin` where it is not) — the same rule longshot's own hard rules state for themselves, on
a skill whose whole job is fanning pushes out across repositories. The shared fetched-document
cache is now named in the Load budget's data list alongside plans, ledgers and status reports,
and every cache entry must carry a provenance record (source URL, fetch time) or it is refetched
rather than trusted by a later unit. Description byte-identical.

## [1.2.0] — 2026-08-21

Earned the standalone profile back by removing what disqualified it, not by
relabelling. 1.1.0 flipped this member to `standard` because it shipped
executable code and read as hard-depending on `git` and the surface's
Task/Agent/Workflow tools. Both findings were correct. This release removes the
first and corrects the second, and the profile follows as a result.

- **The two forcing hooks left the package.** `dispatch_gate.py`,
  `dispatch_ledger_guard.py` and `dispatch_patterns.txt` moved out of
  `references/hooks/` and into the `claude-skills` repo's own `.claude/hooks/`,
  beside the brand firewall and the pack-bump check. They are rig
  infrastructure keyed to `~/.claude/dispatch-mode.json`, not skill payload,
  and a marketplace installer of this pack has no business receiving
  auto-installed `PreToolUse` hooks. The files moved with `git mv`, so history
  follows them; no line of either script changed, and both `--selftest` runs
  pass byte-identical from the new location. The live hooks a session actually
  executes still live under `~/.claude/hooks/` and are untouched by this move.
- **This member now ships no executable code.** That was the one hard bar the
  standalone profile sets, and it is the change that clears it. `references/`
  holds three Markdown files and nothing else.
- **`git` and subagent tools restated as optional, with the degradation
  named.** Neither was ever required to finish a plan; the old wording implied
  they were. Without `git`, a run still plans, tiers, dispatches and records —
  a row it cannot check against origin is reported unverified rather than done,
  which is section 8's existing rule, not a new one. Without subagent or Task
  tools, a run ends at the tiered plan and the ledger, handed back for a human
  or a later session to launch. This follows skillwright's own precedent: an
  optional dependency with stated degradation does not break standalone, a hard
  one does.
- **`profile: standalone` restored as a consequence.** The declaration is true
  because the package changed, not because the label did. Load budget was
  already inside the standalone ceiling — a plan opens one reference, a
  dispatch two, an audit one — and dropping the hooks costs a run no load,
  since executables were never read into context.
- **Stale claim removed.** SKILL.md and README both pointed a reader at "that
  folder's own README" for the hook install block. No such README has ever
  existed in `references/hooks/`; the sentence is gone rather than repointed.
- No behavior change anywhere else. The workflow, the wave caps, the durability
  contract, the ledger schema, the anti-patterns and the three seams are
  unchanged, and the description did not move.

## [1.1.0] — 2026-08-20

Pack-wide skillwright audit findings, P1-1 and P1-2. Both were self-inflicted
gaps between what this member claimed and what it enforced.

- **P1-1 — the declared profile was wrong.** Frontmatter said
  `profile: standalone`, but the package ships two executable Python hook
  scripts and hard-depends on `git` and the surface's Task/Agent/Workflow
  tools; the standalone profile bars shipped executable code outright, and
  this member does not behave identically on chat/API (where it degrades to
  plan-and-tier) as standalone requires. Now `profile: standard`, with the
  dependency paragraph naming the hooks and stating that the skill runs
  identically without them, just without the automatic forcing behavior.
- **P1-2 (S-3) — the wave caps were prose nobody enforced.** SKILL.md §6
  states a 6-unit concurrency cap and a one-writer-per-repo rule; the
  `PreToolUse` guard only ever proved *a* tiered row existed, so a run could
  fan out past either cap with a plausible ledger and nothing would stop it.
  `dispatch_ledger_guard.py` gains `open_unit_count()` and `repo_collision()`,
  both reading the ledger as it stands and blocking (exit 2) when it already
  shows a cap violated. A row counts as open from `dispatched` until it
  reaches a terminal status; an unlabeled status counts as open, since an
  unlabeled row is what a cap exists to catch. Four new exit-code selftest
  cases, 17 total, all passing.

## [1.0.1] — 2026-08-18

Fail-open audit of the two shipped hooks (D1-D4). A sibling session repaired four fail-open
defects in the LIVE hooks at `~/.claude/hooks/`; this release brings the version-controlled
copies under `references/hooks/` into line with them — the shipped copies had drifted to the
broken originals, which is exactly the gap this member's own package exists to prevent.

- **D1 — no session id was a total no-op.** `flag_is_live` returned `False` (allow) whenever the
  PreToolUse payload carried no session id, so any Task/Agent/Workflow call without one passed
  the guard outright. `flag_state()` now returns one of absent / stale / other-session /
  uncorrelated / live, and an uncorrelatable session id on either side enforces the ledger check
  rather than skipping it.
- **D2 — exit 1 on any exception, not 2.** Claude Code blocks a PreToolUse call only on exit code
  2; only `json.load` was wrapped, so a fault anywhere else failed open. The whole hook body is
  now wrapped; every path returns 0 or 2, never 1.
- **D3 — a stale ledger disarmed the guard forever.** `find_ledger` took the newest ledger by
  mtime with no age limit, so one old populated ledger passed every dispatch in that directory
  for good. A ledger now counts only inside the same staleness window that keeps the flag live,
  or by naming the current session outright.
- **D4 — junk cells counted as tiered.** The populated-row check rejected only `""`, `-`, and the
  em dash, so a row of `TBD` / `?` / `x` read as a real model/effort/surface. Each cell is now
  validated per field against a placeholder list and an effort vocabulary.
- Both files carry a `--selftest` exercising all four defects at the real exit-code level
  (verified: `python dispatch_gate.py --selftest` and `python dispatch_ledger_guard.py
  --selftest`, both OK against the copies now shipped here).
- No behavior change to anything else in this member — SKILL.md, the anti-patterns, the ledger
  schema, and the three seams are unchanged.
- The pack registry's seam table (`pack-registry.md`, shipped inside skillwright — see that
  member's own CHANGELOG for its version) now carries the three rows this member's README named
  as owed at 1.0.0: dispatchwright ↔ promptwright, ↔ rigwright, ↔ agentwright, each declared as
  an uncontested, one-sided edge. README's "What did not land" section updated to match.

## [1.0.0] — 2026-08-18

Baseline release. The tenth foundation member, built to close the gap the 2026-08-17 estate
rebuild's lessons page named directly: a session-scale fan-out with no standing doctrine for
tiering, durability, or reconciling against reality rather than an agent's own report.

- **Shape check first.** Every plan is tested against the cheaper alternatives — the main
  conversation, a single subagent, a skill — before any unit, tier, or ledger row exists.
- **Decompose, then tier through promptwright.** Explicit unit boundaries and stop conditions,
  one writer per repo; the finished unit list is handed to promptwright's Entry — Model plan
  grain and its target table is copied verbatim. dispatchwright never invents a tier.
- **The durability contract.** Atomic commit+push, pushed after every finished piece of work and
  before any report, a ledger row at dispatch/commit/push, and `git log --oneline origin/main -5`
  plus the ledger read as resume's first action.
- **Wave execution caps.** Six concurrent units, two nesting levels, a named split above twelve
  units, staggered launch, `isolation: "worktree"` for every writer, and a usage-window check
  before a top-tier wave.
- **Escalation on signal only.** Effort raised before tier, one escalation per unit, a reviewer
  that changes model family rather than resampling, and an owner ask before any top-tier
  escalation, irreversible action, or 2x budget overrun.
- **Reconcile against origin, not report.** Every ledger row checked against
  `git rev-parse origin/main`; unclaimed commits, unpushed worktrees, duplicated work, and actual
  vs. estimated spend reported per run.
- **Thirteen named anti-patterns** (`references/anti-patterns.md`), several with the 2026-08-17
  rebuild's own instance recorded beside the reason.
- Two forcing hooks shipped as version-controlled copies under `references/hooks/`
  (`dispatch_gate.py`, `dispatch_ledger_guard.py`); the installed copies a session actually runs
  live under `~/.claude/hooks/` — see that folder's own README for the settings.json block.
- Trigger evals only at this release: 10 should-fire, 10 should-not (including the promptwright,
  agentwright, and rigwright boundary pairs), and 2 injection probes. Authored, not yet run
  (`evals/RESULTS.md`). No assertion suite yet, and no routing-seam row in the pack registry —
  both named as owed in this member's own README.
