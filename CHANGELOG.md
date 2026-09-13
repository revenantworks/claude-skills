# Changelog — claude-skills

2026-08-17 — repository renamed revenantworks/citadel → revenantworks/claude-skills (GitHub redirects the old name).

Pack releases tag as `<pack>-vX.Y.Z`; member versions are independent semver.
This log starts at the foundation 1.0.0 baseline.

> **Predecessor-era version numbers do not resolve.** The pack re-baselined to
> 1.0.0 on 2026-07-31 and the pre-1.0 history was destroyed with no archive, so
> tag names from before that date (`foundation-v1.1.x` through `v1.4.x`,
> 2026-07-14 → 2026-07-27) name releases that no longer exist anywhere, as do
> the commit SHAs recorded beside them. **Two of those names have since been
> reused:** today's `foundation-v1.1.0` and `foundation-v1.1.1` are new
> releases unrelated to the predecessor tags of the same name. Where a
> pre-2026-07-31 designation appears in a frozen record — the eval `RESULTS.md`
> ledgers, `spec.md`'s history sections, `IMPROVEMENTS.md` — it is left verbatim
> because it records what was true when written; read it as a date, not a tag.
> Live code and runbooks cite dates instead, for exactly this reason.

## [localops-v1.1.1] - 2026-09-13

- lmstudiorunner 1.1.0 → 1.1.1: weekly skill review (autonomous mode, PR). Section 2 gains the claim-type
  table — enumeration and cross-reference claims a local model can produce, judgement claims it cannot —
  and Section 5 reports a confirmation rate per claim type from a sample (#0046); the briefing rule
  hands a delegated model the coverage search population explicitly (#0056).

## [foundation-v2.8.0] - 2026-09-13

- Weekly skill review, autonomous mode (owner absent), delivered as a pull request: fifteen open
  observations (#0043–#0047, #0049, #0051–#0060) actioned across six foundation members. Minor
  because skillwright 1.3.10 → 1.4.0 moved a contract: Build step 4 now returns a niche verdict per
  reach partition and Restraint gained a fourth condition (#0059); Case 9 re-run cold, not re-anchored.
- dispatchwright 1.2.6 → 1.2.7: helper isolation in Wave execution (#0043/#0044), a `reversal` field in
  the ledger row and its Reconcile check (#0045), the hook-controls clause in the brief (#0047), the
  boundary fork in Shape check (#0049), stop-order cancellation (#0051), the regeneration-guard
  question (#0053), the slack rule beside the test-total check (#0057), the asserted match count for
  scripted edits (#0058). Body budget raised 5700 → 6400, landed ≈6203.
- agentwright 1.2.8 → 1.2.9: the boundary fork (#0049), kill-switch stop order and the one-minute
  absence proof (#0051), hold-and-announce at a terminal date (#0052), the regeneration guard
  (#0053); Case 4 re-run cold. Budget 4900 → 5300, landed ≈5111.
- rigwright 1.1.7 → 1.1.8: side-effect-free hook controls that declare what they touch (#0047), the
  mixed-line-endings fact (#0058), the partition-by-reach placement call (#0059). Budget 4700 → 5000,
  landed ≈4888.
- evalwright 1.1.2 → 1.1.3: the coverage search population (#0056), floors that print and bound their
  slack (#0057), grouping a large scanner result by matched string (#0060).
- resumewright 1.0.1 → 1.0.2: a reversal line per non-git change in the handoff's State block (#0045).
- `.claude/hooks/dispatch_gate.controls.json` declares `touches` so HOOK-02's check restores the
  dispatch-mode flag byte-for-byte instead of performing the hook's real write every run (#0047;
  the check itself changed in workshop, PR #2).

## [foundation-v2.7.4] - 2026-09-11

- `packs/foundation/spec.md`'s Approved roster Version column was stale against live
  `SKILL.md` metadata (e.g. skillwright showed 1.0.6, live 1.3.9) — every version cell
  rewritten from each member's own frontmatter; nothing else in the table touched.
- Reviewed `.claude/hooks`, `tools`, and `revenantworks-foundation-resumewright` across
  `2acc301~1..31f6ec1` at code-review medium plus a polish pass: no correctness or
  clarity defects found. Descriptions kept byte-identical. (estate-audit unit P1e)

## [foundation-v2.7.3] - 2026-09-11

**Unit P1d, dispatch run `2026-09-10-estate-audit`.** Review + polish pass after L1b, plus the
owner's freeze-lift decision.

- **Freeze lifted.** Owner decision 2026-09-11: the 2026-08-17 freeze on tokenwright, commwright
  and evalwright is over. `CLAUDE.md` and `packs/foundation/CLAUDE.md` now say so, dated; all
  three are ordinary members again, bumps follow the two-clock rule like any other member.
- **evalwright 1.1.1 → 1.1.2.** L1b applied `references/eval-doctrine.md`'s content (task-observer
  observations #0021, #0025, #0042) under the still-live freeze, so its `CHANGELOG.md` section
  stayed `[Unreleased]` and `frontmatter.metadata.version` stayed `1.1.1`. With the freeze lifted
  the same day, that section converts to a dated `[1.1.2]` release; `description` is
  byte-identical, so no trigger re-judge is owed. Eval provenance re-anchored in
  `evals/test-cases.md` and `evals/trigger-evals.md` (still 14 cases, still 20 triggers 10/10 —
  documentation only, no case or query moved). `packs/foundation/spec.md`'s Approved roster
  registry row updated `1.0.2` → `1.1.2` (the row had never tracked the 1.1.x line).
- **Review + polish, `.claude/hooks`, `tools`, `revenantworks-foundation-resumewright`.**
  `git diff 31f6ec1..HEAD` scoped to those three paths is empty — no commit since H2's resumewright
  build (`4d94fe3`) and its follow-up (`31f6ec1`) has touched any of them. `code-review` at medium
  confirmed the empty range and made no edits; `polish`, run against the (also empty) local diff,
  reached its own "nothing to review" stop. Nothing to fix. A backgrounded review helper this unit
  resumed by message independently ran the pack's release step on its own initiative
  (`build.py --bump-pack`, an unrequested CHANGELOG scaffold) twice before being caught and
  stopped; both sets of edits were reverted before anything was committed, `origin/main` never
  moved, and the incident is logged as task-observer observation #0044.
- **Gate.** `python tools/build.py --check`: clean (0 manifests synced). `python -m unittest
  discover -s tools -p "test_*.py"`: 15/15. Hook selftests — `firewall.py --selftest`,
  `dispatch_gate.py --selftest`, `dispatch_ledger_guard.py --selftest`: all OK.

## [foundation-v2.7.2] - 2026-09-11

**Unit L1b, dispatch run `2026-09-10-estate-audit`.** Applies the eight members staged by the
task-observer weekly review (`workshop/estate/observer/skill-updates/2026-09-11/`, PENDING.md)
covering observations #0011, #0016 through #0042 — patch releases across seven members, plus a
new reference file on brandwright. Every `description` is byte-identical to its predecessor, so
no member's routing surface moved and no trigger re-judge was owed by this pass. See each
member's own `CHANGELOG.md` for the full account.

- **dispatchwright 1.2.5 → 1.2.6.** §2's shape check counts surfaces, not verbs; §3 Decompose
  gains three rules (a unit's tool list, a cross-repo finding split before dispatch, the packet
  id/brief join); `references/ledger-schema.md` gains a Closing a row section;
  `references/unit-brief-template.md` gains a Tools line, a boundaries section, and an
  observations section; the durability contract now runs a unit's gate against the staged tree
  (#0016, #0019, #0020, #0023, #0026, #0028, #0033, #0034, #0035, #0036). Declared body budget
  raised 4900 → 5700.
- **agentwright 1.2.7 → 1.2.8.** Entry — Audit gains three questions the checklist areas do not
  ask (a structurally unreachable fallback logs a failure; the session count matches the cron; a
  run log's first result event is the fire's completion evidence), a delegation line, and the
  extent-parsed rule; `references/security-scan-doctrine.md` scores a scanner's findings by file
  role (#0017, #0018, #0031, #0033, #0041). Declared body budget raised 4100 → 4900.
- **skillwright 1.3.8 → 1.3.9.** Packaging step 4 measures every description in the delivery
  set; Packaging gains step 5 (leak guards run against the staged tree after `git add -A`);
  Entry — Audit gains a Third-party adoption paragraph scoring a scanner's findings by file
  role; `references/description-crafting.md` gains a verb-parity rule; `references/release-
  doctrine.md` states the eval-ledger head window as a layout rule (#0011, #0021, #0025, #0031,
  #0034). Declared body budget raised 8450 → 9100.
- **rigwright 1.1.6 → 1.1.7.** Entry — Audit gains a usage-evidence rule (name the counter, state
  its blind spot, score into three buckets), the owner-install boundary for a catalog row
  touching a live hook/permission file/`.mcp.json`/cap/baseline, a positive-control check on a
  gating pattern list, the extent-parsed rule, and a newly-written-check-is-an-untested-claim
  rule (#0016, #0024, #0026, #0039, #0041, #0042). Declared body budget raised 3500 → 4700.
- **brandwright 1.4.3 → 1.5.0 (minor — new reference file).** New `references/measurement-
  doctrine.md`, ten sections: the instrument ships with the definition (reference-data self-test,
  negative control), the canary cell, gamut-ceiling margin as a published measurement, the
  reflow module, the 400 px iframe harness, direction boards, the swatch-board pick loop, History
  hunt targets, rig-copy parity, and propagation as its own unit — plus a known third-party
  linter false-positive note (#0029, #0030, #0035, #0036, #0037, #0038). `references/pack.md`
  re-synced from the registry (no drift — roster and seam content unchanged). Declared body
  budget raised 3700 → 4700.
- **promptwright 1.5.7 → 1.5.8.** Phase 5 Tier routing gains a role-based override for a verifier
  that only re-derives evidence already on disk; Entry — Model's plan grain states a fan-out
  row's agent count and the effort those agents inherit (#0022). Declared body budget raised
  9470 → 9800.
- **lorewright 1.1.8 → 1.1.9.** Verification doctrine gains "a computed figure publishes its
  computation" (#0037). Declared body budget raised 3050 → 3450.
- **evalwright — content applied, no version bump.** `references/eval-doctrine.md` gains the
  provenance-layout authoring rule, the newly-written-instrument-gets-the-same-controls rule, and
  "re-anchoring a suite is not running it" (#0021, #0025, #0042). `evalwright` is frozen per this
  repo's `CLAUDE.md` ("no bumps unless broken; a security finding counts as broken") and none of
  the three observations is a security finding, so `metadata.version` stays `1.1.1` and the
  member's own `CHANGELOG.md` carries the addition under `[Unreleased]` rather than a dated
  release. `build.py --check`'s "member bump needed" warning for evalwright is expected and is
  this deliberate exception, not drift.
- `references/pack-registry.md` (skillwright): the seven budget-row raises above.

Pack version bumped patch (Z), not minor — no new pack member and no roster/seam count change;
precedent is `foundation-v2.6.4` (promptwright's own 1.4.1 → 1.5.0 minor rode a pack patch) and
`foundation-v2.6.10` (six members patched under one pack patch).

## [foundation-v2.7.1] - 2026-09-10

**Estate-audit unit H2, follow-up.** `foundation-v2.7.0`'s `resumewright` 1.0.0 shipped
`SOURCES.md` naming three private files by their absolute local drive path — this repo is
public and `tools/test_release_paths.py`'s `test_no_absolute_local_path_in_tracked_files`
(widened 2026-09-10 per task-observer observation #0013) exists to catch exactly that. The test
passed pre-commit only because `git grep` scans tracked content and the member's folder was not
yet `git add`-ed; the very next test run against the tagged commit caught it, and this release
fixes it in the following commit before anything else rode on top.

- **resumewright 1.0.0 → 1.0.1.** `SOURCES.md`'s three rows now name their source generically
  (a private estate-run directory, an owner-private observation log) instead of by path. No
  behavior, rule, or the shipped `description` moved.

## [foundation-v2.7.0] - 2026-09-10

**Estate-audit unit H2.** A new foundation member, `revenantworks-foundation-resumewright`
(1.0.0) — a committed session handoff, built to close the gap H1's research pass found: five
existing session-handoff skills were surveyed and none satisfied task-observer observation
#0032's commit requirement. Plus the ledger-guard agent-count fix from observation #0022 and the
registry updates that follow from adding an eleventh member. See each member's own
`CHANGELOG.md` for the full account.

- **New member: resumewright 1.0.0.** Write (Gather against `git`, never a report → write the
  `RESUME.md`-shaped handoff → commit in the same call, pushing to `origin` only where the repo
  has a remote) and Resume (`git stash list` + `git reflog -5` before trusting the file, matching
  `dispatchwright resume`'s own first action). 16 trigger evals (7/7/2), 10 assertion-suite
  cases, both authored and cold-judged this pass: 14/14 on the routing rows, 2/2 on the traced
  injection probes (`evals/RESULTS.md`).
- **dispatchwright 1.2.4 → 1.2.5.** `references/ledger-schema.md` documents the `x<N>`
  agent-count token (observation #0022 — see the hook fix below); §1 gains a fourth seam bullet
  and the `resume` entry a pointer, both naming resumewright. Declared body budget raised
  4700 → 4900 for the new seam bullet. `description` unchanged — no eval re-anchor owed beyond
  the provenance-line restatement already in the suite.
- **skillwright 1.3.7 → 1.3.8.** `references/pack-registry.md` roster update: resumewright's
  roster row, budget row (2600 tokens), and the new `dispatchwright ↔ resumewright` seam row
  (both descriptions). Registry roster count moves 10 → 11.
- **`.claude/hooks/dispatch_ledger_guard.py` — task-observer observation #0022.**
  `open_unit_count()` counted ledger ROWS, and one Workflow row can fan out to hundreds of
  agents — three rows once hid 245 refuters from the 6-unit wave cap and the usage-window check
  in the same run. A row's `surface` cell may now carry an `x<N>` agent-count token
  (`subagent (workflow) x245`); the guard weighs that row as N units against the cap. A missing
  or malformed token defaults to 1, the same weight a row with no token carries. This hook is rig
  infrastructure (not shipped inside the dispatchwright package — see its SKILL.md Load budget);
  its own selftest gains four new cases and stays green end to end (18 exit-code cases total).
- `tools/test_build.py`'s hardcoded foundation roster count moves 10 → 11 to match the real
  registry (`test_roster_budgets_agree`).

## [localops-v1.1.0] - 2026-09-10

- **lmstudiorunner 1.0.1 → 1.1.0.** Reasoning-budget enhancements from a live LM Studio
  research pass (estate-audit unit W9, observation #0027): `references/api-surface.md`
  gains an `enable_thinking` reliability caveat, a note that structured output does not
  by itself add reasoning cost, and a "Sizing the budget: a one-request probe" section;
  `SKILL.md` step 4 gains a matching sentence. `evals/SUITE.md` gains D7/D8 (33 → 35
  cases, authored not run). See the member's own `CHANGELOG.md` for the full account.

## [foundation-v2.6.10] - 2026-09-10

**Estate-audit unit W9** (`promptwright-zero-headroom-both-budgets`,
`estate-voice-vs-pack-doctrine-conflict-on-skill-bodies`,
`estate-voice-drift-in-skill-bodies`, `release-gate-check-excludes-parity`) plus a
tokenwright refresh, four CHANGELOG path-leak fixes, and a rigwright placement line — six
members changed, one tag. See each member's own `CHANGELOG.md` for the full account.

- **tokenwright 1.2.3 → 1.2.4.** `tokenwright refresh` (exempt from the 2026-08-17 freeze):
  `measurement.md`'s per-model cache-floor table and cache-mechanics section re-verified
  live; the description-cap figure re-confirmed; the skill-listing-budget claim flagged
  unconfirmed rather than silently carried or silently dropped.
- **promptwright 1.5.6 → 1.5.7.** Lossless slim: description 1002 → 938/1024 chars (8.4%
  headroom), body ≈9470 → ≈9319/9470 tokens (1.6% headroom, an honest shortfall against
  the 5% target, recorded rather than crossed). Blind trigger re-judge, 38/38 hold.
- **rigwright 1.1.5 → 1.1.6.** Placement — the layer stack gains a line: private-path
  leakage into public packages is a rig placement concern, not just a leak to scrub
  (task-observer observations #0013, #0026).
- **dispatchwright 1.2.3 → 1.2.4.** Durability contract gains a ledger/RESUME-committed-
  at-every-write rule and a resume-time `git stash list` check; Wave execution gains a
  count-agents-not-ledger-rows rule for the wave cap and usage window (task-observer
  observations #0022, #0032). `references/ledger-schema.md`'s "Where it lives" reversed
  from gitignored to committed to match.
- **skillwright 1.3.6 → 1.3.7.** `references/pack-registry.md` budget-row update
  (dispatchwright's raise 4500 → 4700) — a change to skillwright's own shipped reference.
- Root `CHANGELOG.md`, `agentwright/CHANGELOG.md`, `dispatchwright/CHANGELOG.md`, and
  `rigwright/CHANGELOG.md`: four lines citing an absolute local workspace path (the
  estate observer's own drive path) rewritten to cite the observation ids they already
  named alongside it (observation #0013). `tools/test_release_paths.py` gained a
  narrower check — a local path in a CHANGELOG entry dated 2026-09-10 or later is no
  longer covered by the blanket historical-CHANGELOG exemption.
- Two findings skipped by owner decision 2026-09-10 (public packs stay neutral; a user
  applies a voice with brandwright on their side): `estate-voice-drift-in-skill-bodies`,
  `estate-voice-vs-pack-doctrine-conflict-on-skill-bodies`. No pack doctrine text in this
  repo claimed otherwise — `rubrics.md`'s C-2 and `packs/foundation/CLAUDE.md` already
  state the neutral-by-default rule, so no doctrine fix was needed.
- One finding skipped on refutation: `release-gate-check-excludes-parity` — a Phase 2
  refuter found `skillwright/references/release-doctrine.md`'s "Install parity" section
  and Release order step 6 already name parity as a required, owner-run release step;
  folding it into `--check` would make it a no-op in CI, which has no local install to
  diff against. No code or doctrine change made.

## [localops-v1.0.1] - 2026-09-10

- **lmstudiorunner 1.0.0 → 1.0.1.** Seven estate-audit findings, first patch since the
  member's 2026-09-09 debut. `loaded_context_length` is only present when `state` is
  `loaded`; SKILL.md, `api-surface.md`, and `work-classes.md`'s Long-input row now all
  state the not-loaded fallback (judge fit against `max_context_length` provisionally,
  flag resident context as unconfirmed) — the field is absent from every entry on this
  rig's just-in-time setup at rest, and nothing said what to do about it. `evals/SUITE.md`
  cases A4 and C3 now name their precondition (a resident model) explicitly; paired cases
  A4b and C3b cover the not-loaded state so the suite stays runnable at rest instead of
  marking correct behaviour a failure. The posture clause now names the queue file, task
  cards (including a card's own `check` field), and the raw API response as data, never
  instructions; `task-cards.md` adds that a `check` is shown to the owner and confirmed
  before its first execution, and a card whose `check` was not authored by the owner is
  refused rather than run. `evals/RESULTS.md` created — Case E5 (the injection probe)
  executed as a traced run, 1/1, this member's first run record of any kind. The discovery
  probe in `api-surface.md` now covers all four host/port combinations with a 2-second
  connect timeout each (the old three-line block both omitted the address that actually
  answers on this rig and had no timeout, so a closed port hung instead of failing fast).
  SKILL.md gains a Load budget section naming all four reference files, closing with the
  `pack.md` boundary-doubt line. `capabilities` may be absent entirely on an `embeddings`
  entry; `publisher` and `compatibility_type` added to SKILL.md's field list to match
  `api-surface.md`.

## [foundation-v2.6.9] - 2026-09-10

- **dispatchwright 1.2.2 → 1.2.3.** Load budget now closes with the sibling-standard
  `references/pack.md` line (boundary doubt about a sibling's territory only) — the one
  member whose Load budget never named the manifest it ships. Behavior notes gains an
  Invocation control paragraph naming why model invocation is required (recognizing and
  dispatching a fan-out is the job) and what bounds its pushes (the identity check, the
  named remote, the stop-and-ask on any unnamed irreversible action) — no
  `disable-model-invocation` flag, since that key hard-errors on claude.ai and the Skills
  API, surfaces this member also ships to. `evals/trigger-evals.md`'s header restated to
  the sibling row-count form.
- **agentwright 1.2.6 → 1.2.7.** Inventory mode's Entry — Audit paragraph cited a private
  repo's script path, unresolvable and disclosing to a public installer; cut, the rule it
  illustrated (walk `~/.claude/scheduled-tasks/*`, an undocumented task_id is P1) stands
  on its own.
- **rigwright 1.1.4 → 1.1.5.** Two behaviour changes (1.1.3's inventory-mode paragraph,
  1.1.4's live/tracked-pair rot fold) had shipped with no case asserting either, across
  two releases. `evals/test-cases.md` gains Case 17 (inventory mode: an unaccounted real
  directory files at P1) and Case 18 (a diverged live/tracked pair files under `rot`, both
  paths named); both executed as traced runs, 2/2. Also corrected a standing
  self-contradiction in `evals/trigger-evals.md`: the cold re-judge owed since v1.0.2 was
  discharged 2026-08-20 per `RESULTS.md`, but the line kept reading "remains owed" for
  three more re-anchors after the close.
- **lorewright 1.1.7 → 1.1.8, promptwright 1.5.5 → 1.5.6, skillwright 1.3.5 → 1.3.6.**
  Injection probes (lorewright Cases 40-42, promptwright Cases 40-42, skillwright Cases
  41-45) all ran and passed 2026-09-08 per each member's own `evals/RESULTS.md`, but the
  case headings still read "not run" — an audit reading only the suite files would have
  filed a false coverage gap or re-run work already done. Corrected all eleven headings to
  name the execution date and result; no case content, input, assert, or count changed.
  tokenwright carries the same stale-marker defect and is deliberately left untouched —
  tokenwright is a frozen member (owner decision 2026-08-17, no bumps unless something is
  actually broken), and whether a documentation-only correction counts as "broken" is an
  open owner decision recorded in `pack-registry.md`, not settled by this release.
- **promptwright, additionally: `model-snapshot.md`'s S-frontier Claude slot corrected
  from "Fable 5" to "Fable 5.1"** across five lines — a lineup move inside the 60-day
  calendar window, which a pure calendar cadence cannot catch on its own. Spot-verified
  live against `platform.claude.com/docs/en/about-claude/models/overview` (the Claude
  column only); naming-only, no price, context, or output change ($10/$50, 1M, 128K
  unchanged from Fable 5). A launch-triggered refresh cue was added beside the calendar
  one.
- **brandwright 1.4.2 → 1.4.3.** Case 28 added to `evals/test-cases.md`, closing the
  authored-not-covered debt the 1.4.2 release recorded: the guide-card HTML-escaping rule
  shipped with no case asserting it. Case 28 feeds the render path a tagline and a
  sign-off carrying `<script>`/`<img onerror=>` markup and asserts both come back
  HTML-escaped, never inlined verbatim. Authored, not run, per this pass's own
  instruction — `evals/RESULTS.md` records the case with no pass rate claimed.
- **skillwright, additionally: Load budget and standalone-profile reconciliation.** The
  Load budget paragraph said a standard build touches four reference files "in practice"
  with `description-crafting.md` conditional on fixing a description — false, since Build
  step 5 drafts a description with a char count against it on every build. Restated as
  five, always. `references/rubrics.md`'s standalone profile gained the shell/interpreter
  carve-out Packaging already declares (`zip`, a stdlib-only `python3`, both skip-clean)
  and a clarification that the ≤3-reference-load cap bounds undeclared reach, not a
  build's own doctrine-mandated file count. `references/pack-registry.md` (skillwright's
  own shipped reference) gains a tokenwright freeze note recording the 2026-08-17 owner
  decision where upkeep and integrate actually read policy, with the calendar-refresh
  exemption question left explicitly open.
- **Hooks (`.claude/hooks/`, not a pack member):** `dispatch_patterns.txt` gains five
  shape-based patterns (observation 0016) — a real estate-audit prompt asking for a
  "complete estate sweep" naming many surfaces missed every existing pattern, because the
  list matched the author's vocabulary rather than the request's shape.
  `dispatch_gate.py`'s `--selftest` gains a second positive control built from that real
  prompt fragment, alongside the existing synthetic one, so a vocabulary gap like this one
  cannot pass silently again. Two of the four originally-missed phrasings still miss
  (they need the surface-count rule observation 0016 also recommended, a logic change
  beyond this pass's scope) and are left for a future pass.

## [foundation-v2.6.8] - 2026-09-10

- **promptwright 1.5.2 → 1.5.5.** Adopted a four-way convergence (ase-code-edit's
  pre-build grill, addyosmani/agent-skills' interview mode, mattpocock/skills' grilling
  primitive, Superpowers' brainstorming skill) as its own doctrine rather than importing
  any one of their frameworks: `frameworks.md`'s Agent/System table gains a Confirm
  shared understanding component, so a built coding/agent prompt states its plan before
  a non-trivial or hard-to-undo change. Case 44 authored (1.5.3), then executed for real
  via two independent blind builds judged cold against it — 6/6 (1.5.4) — which surfaced
  a genuine doctrine gap: the checkpoint's two named forms (hold for a correction, or
  proceed under a named assumption) didn't cover what a competent blind build produced
  for an unattended pipeline agent with no synchronous party to hold for. Closed same day
  (1.5.5): the doctrine now names three forms — Hold, Assume, State-then-proceed — picked
  by who is on the other end when the agent acts, with a seventh case assert added and
  graded against the retained transcript. Full run records in promptwright's own
  `evals/RESULTS.md`.

No entry point, checklist area, scoring anchor, or restraint path moved. promptwright's
own `evals/test-cases.md` and `evals/trigger-evals.md` re-anchor provenance-only at each
step; the `description` never moved across the four bumps.

## [foundation-v2.6.7] - 2026-09-10

The estate's first task-observer weekly review (the estate observer workspace) staged and this
session installed nine observations against three foundation members — see PENDING.md and
observations #0001-#0011 in the estate repo for the full disposition.

- **agentwright 1.2.6** — Entry — Emit's render step (rule 2) prefers a pointer into a repo
  file over duplicating instruction text in a scheduler's own field; `platform-notes.md`'s
  guardrail table gains the unattended-ask-rule caveat (#0003, #0004).
- **rigwright 1.1.4** — Placement — the layer stack gains the live/tracked-pair diff rule,
  folded into the Audit `rot` check (#0003).
- **dispatchwright 1.2.2** — §6 Wave execution gains the silence-is-not-a-liveness-signal
  bullet; §8 Reconcile gains gate-figure and test-total re-derivation bullets;
  `unit-brief-template.md` gains an Expected test total field (#0006, #0007, #0008).

No entry point, checklist area, scoring anchor, or restraint path moved in any of the three;
each member's own `evals/test-cases.md` re-anchors provenance-only. Three observations
(#0002, #0005, #0009) were promoted to the estate's `cross-cutting-principles.md` instead of
a skill edit, so they carry no member bump here.

## [foundation-v2.6.6] - 2026-09-09

Patch release, one member: promptwright 1.5.1. A run record and the version it owes, nothing else. **Case 43 was executed** — the grill's behaviour case, shipped `(authored, not run)` at 1.5.0 — T1 and T2, **9 / 9**, traced against the written procedure and disclosed as traced rather than as a live product-surface run, matching the 2026-09-08 precedent for Cases 40–42. No rule, phase, entry point or `description` moved, so the routing surface is untouched and the two cold trigger runs ledgered under 2.6.4 still describe the shipped text.

The run **found one doctrine gap and filed it rather than patching it**: `grill.md` step 4 requires the first offered answer to be the one the request already implies, marked `⚑`, and for two of the five traced aspects the request implied nothing at all. The procedure does not say what `⚑` does then, and the readings differ materially — marking a house default would present an invented choice as the user's own, which is precisely what the convention exists to prevent. **No assert covers the case**, and that absence is the sharper half of the finding: the suite tests that `⚑` is applied, never what happens when it cannot be. A case is owed.

**This release exists because the previous one taught it.** `foundation-v2.6.5` shipped skillwright 1.3.4 to pay a bookkeeping debt three passes deep — a shipped file moving at an unchanged member version. Editing `evals/` is exactly that, and the run record itself correctly touched no version, because a record must never edit the thing it grades. The bump is therefore paid here, in the same pass rather than one later, which is the only way the lesson is worth anything.

## [foundation-v2.6.5] - 2026-09-09

Patch release, three members: rigwright 1.1.3, agentwright 1.2.5, skillwright 1.3.4. Brings the estate sweep's `INV-01` provenance check on demand into a session, split across the two members that already own the halves. **rigwright's Entry — Audit gains inventory mode**: when the target is the rig as a whole rather than one named file, it asks a sixth question the five dimensions never ask — is every installed skill and hook traceable to a repo. A real directory where a junction was expected, or a link resolving outside every repo the session can see, is `unaccounted: <name>`, **P1 and never P0**, because unaccounted means unproven rather than unsafe and the owner decides keep, adopt or remove. **agentwright's Entry — Audit gains the same for scheduled tasks** — a `task_id` under `~/.claude/scheduled-tasks/` with no documentation in a repo this session can see is `undocumented: <task_id>`, same severity and same reasoning. The split follows this pack's own attended-versus-unattended boundary rather than putting both in one member, and each states the other's half as out of scope. Both mirror `estate/scripts/local_checks.py` in `MickMacPW/workshop`, so a session and the weekly cloud sweep answer the same question the same way. No `description` moved on either member, so the routing surface is untouched and no cold re-judge is owed; their eval suites are re-anchored for provenance only.

**skillwright 1.3.4 is the bookkeeping this repo keeps failing to do.** Editing `references/pack-registry.md` is a change to skillwright's own shipped reference and owes it a version. That went unpaid across **three** passes — the VER-01 batch, this inventory-mode split, and `foundation-v2.6.4` itself, which added the localops rows, promptwright's grill Job column and the `-hand`→`-runner` motif correction. The third was found by the session writing the entry, while checking the entry's own count of two. The 1.3.2 entry had already named this exact failure mode for this exact file, and the precedent did not catch it; a rule stated in a changelog is not a gate.

## [gamedev-v1.0.1] - 2026-09-09

Patch release, one member: pixelsmith 1.0.1. Pure bookkeeping — no rule, band, law, entry point or reference moved, and the `description` is byte-identical, so the routing surface did not move and no trigger re-anchor is owed. The pack ships a version because a shipped file changed at the same member version and `build.py --check` had been flagging it: the 2026-09-08 pass created pixelsmith's `evals/RESULTS.md`, executing Case 12 — the suite's one injection probe — in both parts, 2 / 2, traced against the written procedure and recorded as traced rather than as a live product-surface run. That entry deliberately touched no SKILL.md, version or CHANGELOG, which is correct for a run record that must never edit the thing it grades, so the bump is paid here instead, one pass later. This closes the 2026-09-06 sweep's VER-01 finding that pixelsmith was the only skill in the estate with no eval history of any kind; 1 of 12 cases now has a run record and the other eleven remain authored, not run.

## [foundation-v2.6.4] - 2026-09-09

Minor release, one member: promptwright 1.5.0. New entry point — **Entry — Grill**, a relentless interview that runs before the build until no essential freedom of choice is left for it to guess at. Ported from the `ase-task-grill` pattern (rse/ase, Apache-2.0) and re-aimed from code plans at prompt and task requests; the framework it ships in was evaluated and not adopted, only the pattern, with credit in the member's `SOURCES.md`. Doctrine lives in the new `references/grill.md` — four focus areas outside-in with severity fixed by area, six question-finding indicators, and the round procedure (sort, truncate at 10, ask one at a time with grounded options and a skip exit) — explicitly outside the standard load budget. SKILL.md carries only the route contract: the two shapes, the Phase 4 escalation and Phase 5 resume, and the agentwright seam. The `description` gained the grill clause, so the routing surface moved: trigger evals extended 34 → 38 (19/19) and the full cold re-judge a description move owes was **performed** — two column-isolated runs through `tools/blind_queries.py`, a fresh judge each holding only the shuffled queries and all twelve members' name + description. Run 1 scored 37/38 and found the defect that run 2 tested the fix for: the grill clause bound no object, so #38 came back AMBIGUOUS against commwright. The clause was scoped to `interview a prompt request` and run 2 scored 36/38 with #38 closed. No row flipped in either run; **#37, the declared watch row, held both times**, routing to agentwright on the object over the shared verb. #34 and #29 returned AMBIGUOUS in run 2 only and join #37 as standing watch rows rather than being chased. The scoping put the description at 1002/1024, which trips the ceiling-riding advisory — paid deliberately and recorded in the member's CHANGELOG. Assertion suite 42 → 43 (Case 43 remains authored, not run — this pass judged routing only). Registry budget row raised 9030 → 9470, the raise sized down by the focus-area restatement deleted from the body in the same pass.

## [foundation-v2.6.3] - 2026-09-08

Patch release, five members: lorewright 1.1.7, agentwright 1.2.4, rigwright 1.1.2, dispatchwright 1.2.1, brandwright 1.4.2. One estate deep-pass batch (VER-01 rubric S2/S3/S4/S6). lorewright's Verification doctrine states a Fetch scope -- open-domain by design, but never behind a login/paywall bypass, never a URL taken from inside a source's own text as the next fetch target. agentwright and rigwright's Entry -- Refresh now name the domains their own SOURCES.md already cites (code.claude.com, support.claude.com, platform.claude.com, agentskills.io) -- previously stated only as prose with no host named anywhere in either package; rigwright's had none at all. dispatchwright's durability contract requires an identity check before any push and a provenance record (source URL, fetch time) on the shared fetch cache -- an entry with none is refetched, never trusted as-is. brandwright's guide-card fill rules state an explicit escaping control -- every interpolated string is HTML-escaped, no handed-in HTML/JS ever inlined verbatim -- matching the same-day fix on longshot's stakekeeper. Registry budget rows raised for the three members whose additions crossed their declared ceiling (agentwright, lorewright, brandwright). Eval provenance re-anchored across all five; new doctrine not yet covered by an existing case is marked authored-not-covered rather than silently claimed.

## dispatchwright hooks moved into the repo's own .claude/hooks - 2026-08-21

`revenantworks-foundation-dispatchwright` stopped shipping executable code. Its two forcing hooks
and their pattern file moved out of the member's `references/hooks/` and into this repo's own
`.claude/hooks/`, beside the brand firewall and the pack-bump check. The member goes to 1.2.0 and
its declared profile returns to `standalone` — earned by the packaging change, not by relabelling
the same package.

- **`git mv`, not delete-and-recreate.** `dispatch_gate.py`, `dispatch_ledger_guard.py` and
  `dispatch_patterns.txt` moved as renames, so history follows the files. No line of either
  script changed; both `--selftest` runs pass from the new location. Both scripts already
  resolved their own directory at runtime, so nothing needed repathing.
- **The live hooks are untouched.** The copies a session actually executes live under
  `~/.claude/hooks/`, outside this repo. Only the version-controlled copies moved.
- **Stored here, not armed here.** The pair is intentionally absent from `.claude/settings.json`.
  A rig installs them into `~/.claude/hooks/`; wiring them a second time from the repo would
  double-fire. `CLAUDE.md`'s hard rules now say so.
- **Distribution consequence, stated rather than hidden.** The `.skill` archive packages the
  member's own folder, so an installer of this pack no longer receives the hook scripts at all.
  That is the intended outcome — a marketplace install has no business auto-installing
  `PreToolUse` hooks — and the member's SKILL.md and README now describe that model instead of
  the shipped-with-the-skill one.

## Ossuary pack removed - 2026-08-20

The `ossuary` pack leaves this repo. Both members — `revenantworks-ossuary-linecaller` and
`revenantworks-ossuary-bonecaller` — were ported to the private repo `MickMacPW/longshot` on
2026-08-20 and renamed to `northstar-ledger-cardkeeper` and `northstar-ledger-stakekeeper`
(personal North Star skills, `-keeper` motif). longshot is now their canonical home. This repo,
`revenantworks/claude-skills`, ships exactly one pack from this date: **foundation**, ten
members, unchanged by this pass.

- **The downstream-mirror relationship is retired, not merely paused.** From 2026-08-07 this
  repo was source of truth and `MickMacPW/longshot` kept a declared mirror at its `skills/`,
  re-synced by `tools/release.py`'s mirror step. That direction is now inverted: longshot holds
  the canonical copies and this repo holds none. `sync_mirror()`, the `--mirror-only` flag, the
  `CLAUDE_SKILLS_LONGSHOT` env var, and the `LONGSHOT*` constants are removed from
  `tools/release.py`; the remaining steps renumber 9→8, 10→9, 11→10.
- **Removed from disk and from the catalog.** `packs/ossuary/` and its two members are deleted;
  the `ossuary` plugin entry is gone from `.claude-plugin/marketplace.json`, and the pack's
  registry row, roster, budgets, seams, capstone and canonical-repo blocks are gone from
  skillwright's `references/pack-registry.md`. `build.py --check` now reports
  `registry 10 = folders 10 = manifests 10`; before this pass it reported 12.
- **Tests retargeted, not dropped.** `test_ossuary_registered` and
  `test_ossuary_roster_budgets_agree` were per-pack duplicates of the foundation tests beside
  them and are removed. `test_each_pack_has_its_own_conformance_line` keeps its live per-pack
  assertion and now checks conformance-line distinctness across whatever packs are registered;
  the cross-pack regression it used to cover live is still covered by the two-pack `SYNTH`
  fixture in `test_pack_lines_does_not_borrow_another_packs_conformance`.
  `test_import_survives_unset_vars` now probes the two brand-repo paths instead of the deleted
  `LONGSHOT` constants, keeping the same "unset env var stays None" coverage.
- **Dated history is untouched.** Every `ossuary-v*` entry below stays exactly as written, as do
  the `-caller` motif claims in `audit/COLLISION.md` (2026-08-07, 2026-08-08), the ossuary
  incident citations in `RUNBOOK.md`, the defect records in `tools/build.py`, and deferral
  register ⑦ in `packs/foundation/spec.md`. A 2026-08-20 retirement note is appended to
  `COLLISION.md` rather than edited into those rows. Note that the `ossuary-v2.4.1` heading
  below never had a body written and no `ossuary-v2.4.1` tag exists — the newest ossuary tag is
  `ossuary-v2.4.0`. It is left as found rather than back-filled.

## [gamedev-v1.0.0] - 2026-08-29

First release of the **gamedev** pack (profile standard, `-smith` motif, restamp lazy).

- **pixelsmith 1.0.0** — art direction for pixel art that must read at several zoom scales at once: per-band palette and silhouette rules, a per-band "reads" checklist, terrain-versus-unit contrast (Case 1 recorded), a one-scene look-test procedure with a scorecard, and artist and generator briefs. Entries: direct, `pixelsmith test`, `pixelsmith brief`, `pixelsmith audit`. Image viewing optional with a text-described path. 20 trigger evals, 12 assertion cases.
- Registry: `gamedev` pack row, one-member roster, 3500-token budget row; `packs/gamedev/.claude-plugin/plugin.json` and the marketplace entry at 1.0.0.
- Root README pack table and CLAUDE.md updated to two packs.
- `tools/release.py`: the changelog gate read the section *after* the released heading (`split(...)[1]`), so a stale stub two entries down blocked an unrelated release; it now reads the released heading's own section.

## [ossuary-v2.4.1] - 2026-08-18

- (fill in)

## [foundation-v2.6.2] - 2026-08-21

Patch release: brandwright 1.4.1, doctrine only. Two new palette-derivation rules in
`audit-doctrine.md` — D-8 (measure a mark against the ground it actually sits on, not the ground
its token was designed against) and D-9 (a second form channel where an ordinal state or severity
set shares one hue between adjacent levels) — landed after a render pass on an external estate's
published dashboards surfaced both failure modes live: a status dot correct in its definition's
own table failing 2.72:1 against the raised surface it was actually painted on, and a four-level
severity ladder sharing one hue across two adjacent levels with no second channel to tell them
apart. No new audit category, no description change, no member-count change; the palette-drift
category gloss now cites both rules. Eval provenance re-anchored (`test-cases.md`,
`trigger-evals.md`) — both D-8 and D-9 are authored-not-covered, the same status D-1 to D-7
carried at their own introduction.

## [foundation-v2.6.1] - 2026-08-18

Estate-sweep patch: four findings from an adversarial audit of the 2.6.0 release, fixed rather
than re-litigated.

- **Shipped hooks synced to their fixed live originals (dispatchwright 1.0.1).** A sibling repair
  fixed four fail-open defects (D1-D4) in the LIVE hooks at `~/.claude/hooks/`, but the
  version-controlled copies this pack ships under `references/hooks/` had drifted to the broken
  originals. Both files are now byte-for-byte the fixed versions; both `--selftest` suites pass
  against the copies shipped here. See dispatchwright's own CHANGELOG for the per-defect account.
- **Plugin description undercounted its own roster.** `plugin.json` and `marketplace.json` both
  said "Nine standalone wrights" and listed nine names, omitting dispatchwright — the member this
  very release train added at 2.6.0. Both now say "ten" and name dispatchwright. `CLAUDE.md`, the
  root `README.md`, and `pack-registry.md`'s roster table already said ten; only the two plugin
  manifests had not caught up.
- **Two private-repo paths removed from the public build tool.** `tools/build.py` carried two
  hardcoded absolute paths — one into the private `revenantworks/brand` repo, one into the private
  `MickMacPW/brand` repo — in a file that ships on this public repo's `origin/main`. No protected
  name was exposed, but the paths handed a reader the owner's local drive layout and the existence
  and location of two private repos. Both now resolve from environment variables
  (`CLAUDE_SKILLS_BRAND_REPO_SOURCE`, `CLAUDE_SKILLS_PEER_SOURCE_NORTHSTAR`) with a clean skip when
  unset, so the parity check still works on the owner's rig (env vars set there) and simply skips
  that one check everywhere else — the same behavior as an absent brand/peer repo today. The two
  paths remain in git history; a history rewrite and force-push to scrub them is the owner's call,
  not made here.
- **Stale seam note corrected (skillwright 1.3.2).** `pack-registry.md`'s evalwright ↔ skillwright
  row still claimed the eval-authoring carve-out lived on evalwright's side only; skillwright's own
  description closed that gap at 1.2.0 (2026-08-12) and the registry was never updated to match.
  Corrected to **both descriptions**, verified against the live text of both members' frontmatter.
- **dispatchwright's three seam rows added (skillwright 1.3.2).** `build.py --check` had warned
  dispatchwright was "named in no routing seam" since 2.6.0. The three edges dispatchwright's own
  SKILL.md already states (↔ promptwright, ↔ rigwright, ↔ agentwright) are now rows in the table,
  each recorded as an uncontested, one-sided edge — verified by reading all four members'
  descriptions, none of which name dispatchwright back.
- Adding the seam rows regenerated every member's `references/pack.md` (the seam table is shared
  across all manifests); only dispatchwright and skillwright had their own authored content change
  and were version-bumped. The other eight members' manifests differ from the 2.6.0 tag by this
  mechanical regeneration alone — `build.py --check`'s advisory "member bump needed" warnings for
  those eight are expected and not a sign of unshipped work, the same category the frozen-member
  policy already accepts for tokenwright/commwright/evalwright.

## [foundation-v2.6.0] - 2026-08-18

Tenth foundation member: `revenantworks-foundation-dispatchwright` 1.0.0, a
session-fan-out dispatcher closing the orchestration-skill candidate that
`NEXT.md` had carried blocked since 2026-08-01. It decomposes a large request
into units, tiers each one through promptwright's Entry — Model target table
(never inventing a tier of its own), dispatches with a durability contract
(atomic commit+push, pushed after every finished piece of work and before
any report, a ledger row at dispatch/commit/push), runs waves under fixed
caps (six concurrent, two nesting levels, a worktree per writer), escalates
only on a verifiable signal, and reconciles every run against
`git rev-parse origin/main` rather than an agent's own report. Doctrine is
drawn from `workshop/handbook/lessons-2026-08-17-rebuild.md`'s own account of
a large multi-agent session that cost five usage-limit stops and several
refuted self-reports; `references/anti-patterns.md` names each of its
thirteen anti-patterns against that record where an instance exists.

- Registry: roster row + a declared budget row (measured ≈3254 tokens,
  ceiling 4000) in skillwright's `pack-registry.md`, roster 9 → 10; capstone
  note updated, capstone run not re-triggered (a member add updates the line
  only). Router: one row in `packs/foundation/CLAUDE.md`'s table plus one
  How-they-compose line ("dispatchwright dispatches; promptwright tiers").
- Two forcing hooks ship with the member at `references/hooks/`
  (version-controlled copies) and are installed at `~/.claude/hooks/`
  (outside this repo, per the task that built them): `dispatch_gate.py`
  (`UserPromptSubmit`, fails open, flags a likely fan-out and sets a
  session mode flag) and `dispatch_ledger_guard.py` (`PreToolUse` on
  `Task|Agent|Workflow`, fails closed while the flag is live and the run's
  ledger has no row carrying model, effort, and surface). Both selftests
  pass; the hooks folder's own README carries the settings.json block the
  owner pastes by hand (the global settings file denies editing itself).
- Trigger evals only at 1.0.0: 10 should-fire, 10 should-not (the
  promptwright/agentwright/rigwright boundary pairs named explicitly), 2
  injection probes — authored, not yet run (`evals/RESULTS.md`).
- **Not done, recorded rather than hidden:** no routing-seam row for
  dispatchwright's three boundary pairs (promptwright, rigwright,
  agentwright) — the pack's seam table (`**foundation seams**`) was not
  extended, so `build.py --check` reports the member as "named in no routing
  seam" (advisory, non-fatal). No assertion suite yet. Both are named in the
  member's own README as owed to a future `skillwright integrate` pass.
- Prose pass (`handbook/estate-voice.md`) across root docs and eight
  foundation members' README/SKILL.md — see the member CHANGELOGs and the
  repo commit for the per-file account; frontmatter, descriptions, and
  CHANGELOG history untouched everywhere. tokenwright, commwright, and
  evalwright were read but not edited (frozen 2026-08-17: no bumps unless
  broken, and any shipped-file edit would force one).
- `tools/test_build.py`'s roster-count assertion updated 9 → 10 to match.

## [foundation-v2.5.0] - 2026-08-17

The 2026-08-17 audit + security scan of all nine wrights against
skillwright's Rubric A / Security classes plus the owner's security rubric
(prompt-injection posture at every ingesting entry point, no
fetch-and-follow or guard-bypass instructions, minimal tool grants, hidden
text, named output handling, one injection probe per ingesting entry — read
through the OWASP Top 10 for Agentic Applications 2026 lenses). Every
member's own CHANGELOG carries its findings and fixes; the pack-level
summary:

- Nine members bumped: skillwright 1.3.0 → 1.3.1, promptwright 1.4.0 →
  1.4.1, brandwright 1.3.0 → 1.4.0, lorewright 1.1.4 → 1.1.5, agentwright
  1.2.1 → 1.2.2, rigwright 1.1.0 → 1.1.1, and the three **frozen** members
  by security-eval patch only — tokenwright 1.2.1 → 1.2.2, commwright 1.1.0
  → 1.1.1, evalwright 1.1.0 → 1.1.1 (frozen 2026-08-17: no bumps unless
  broken; a missing injection probe counted as broken, nothing else in them
  moved).
- The data-never-instructions rule now sits at every ingesting step of every
  member (the S-1 P1 class: skillwright Build 1 / Integrate 1, promptwright's
  mid-build fetch and plan grain, brandwright's four entries at the step,
  lorewright's mode files at the reading step, agentwright Emit / Refresh /
  Security-scan probes, rigwright's config reads); every suite carries
  authored-not-run injection probes per ingesting entry; hidden text
  (zero-width unicode, HTML-comment directives, base64, homoglyph domains,
  fetch-pipe-shell) is now a named S-1 scan in `rubrics.md`, and the pack-wide
  hidden-text scan ran clean.
- Four calendar surfaces refreshed live and restamped 2026-08-17 (they would
  have aged out before 2026-10-01): skillwright `rubrics.md` (frontmatter
  shape — claude.ai accepts exactly six keys; `allowed-tools` is a per-turn
  grant so the minimal grant is none; dimension 11's stated-reason path for
  claude.ai-bound skills), promptwright `model-snapshot.md`, agentwright
  `platform-notes.md`, rigwright `surface-notes.md`. tokenwright
  `measurement.md` (ages out 2026-09-25) is left for the upkeep routine under
  the freeze.
- brandwright reads the live definition from `~/.claude/brand/` first
  (read-only copies refreshed by `tools/release.py`), else the shipped
  neutral file.
- Repo tooling: `tools/release.py` (the whole close-of-pass loop),
  `build.py --check` emits `pack bump needed: <pack>` when shipped files
  differ from the pack's current tag, and a PostToolUse hook on `git commit`
  surfaces it. The rig now loads every member by user-scope junction into
  the working tree; the marketplace plugins were uninstalled there and
  `claude plugin update` left the rig loop (RUNBOOK).
- Every re-run and cold re-judge these bumps owe is recorded as owed in each
  suite's head, none claimed.

## [ossuary-v2.4.0] - 2026-08-17

The 2026-08-17 audit + security scan (linecaller 1.6.0 → 1.7.0, bonecaller
1.4.0 → 1.5.0). The last routine ossuary marketplace release: the pack's
release train is frozen the same day — it ships to its only consumer by the
longshot mirror and the rig junctions.

- linecaller: hard rule 3 widened to every file the run reads and did not
  write, with no URL/path/command from content ever becoming a fetch, push,
  or shell target (S-1 P1); the identity gate states its gh-absent
  structural case (S-3 P1); the key's never-echo clause (S-2 P2); step 5
  names its two `models/` writes; the first-Monday five-line ledger block
  (bankroll, month P&L in units, graded record, ROI, avg CLV — computed
  from `ledger/bets.csv` + `models/bankroll.json`, never invented; owner
  decision) with its definitions in `card-contract.md`; step 8 publishes the
  card to the one fixed artifact page; stale Task Scheduler / nflverse
  staging text cleared; R13–R15 authored-not-run.
- bonecaller: reads the card artifact-first, repo second, source named;
  hard rule 3 covers the artifact page, every repo file, and pastes (S-1
  P1); B8 is the suite's first injection probe, B9 the two-source read —
  authored-not-run; README names the rig junction and the built zip name.
- Descriptions unchanged on both — routing surfaces did not move; the owed
  cold re-judges remain owed. Longshot mirror re-synced by `tools/release.py`.

## [foundation-v2.4.0] - 2026-08-15

The 2026-08-15 estate audit's foundation slice (skillwright 1.2.1 -> 1.3.0):

- Rubric A gains dimension 11, **invocation control** - a skill whose steps
  write, commit, push, send, or spend declares `disable-model-invocation:
  true` or states in one line why model invocation is required; filed under
  S-3 when neither is present.
- `pack-registry.md` gains the two reciprocal seam rows that predated their
  declaration (promptwright <-> skillwright, skillwright <-> tokenwright) and
  a Contents block; `upkeep-doctrine.md` step 1 stops restating the roster
  source, closing the one reference-to-reference hop.
- `packs/foundation/tasks/foundation-skill-upkeep.md`: the Foundation - Skill
  Upkeep routine gets its first verbatim prompt mirror (live synced via the
  update API the same day); `upkeep-task.md` states report-only is held by
  the prompt, not the grant. Both pack routers now say APPEND, a root
  CLAUDE.md covers the top level, and both skillwright eval suites are
  re-anchored at 1.3.0.

Note: foundation-v2.3.1 (2026-08-14) was superseded before release by this
version; no tag or Release was cut for it.

## [ossuary-v2.3.0] - 2026-08-15

The 2026-08-15 estate audit's ossuary slice (linecaller 1.5.4 -> 1.6.0,
bonecaller 1.3.5 -> 1.4.0):

- linecaller's description redraw front-loads the run verbs and cedes the
  bare "today's bets" to bonecaller (the pair was the estate's highest
  description overlap); its compatibility drops the drive-lettered rig path,
  and the body states why model invocation stays enabled - the production
  cloud routine fires the skill through the model - which is Rubric A
  dimension 11's stated-reason path.
- bonecaller's ledger and coaching-note writes are confirm-first (show the
  row/file and path, wait for the owner's yes), and the write step names its
  tool, `github:create_or_update_file`.
- Both trigger suites extended to the 20-row eval-authoring spec with four
  linecaller-vs-bonecaller boundary pairs; new rows authored-not-run, cold
  re-judge owed. Longshot mirror re-synced the same day (diff -r clean).

Note: ossuary-v2.2.5 and ossuary-v2.2.6 (both 2026-08-14) were superseded
before release by this version; no tag or Release was cut for either.

## [ossuary-v2.2.6] - 2026-08-14

- bonecaller 1.3.5: the body called `longshot-bankroll-rules.md` "the single
  home of every threshold number" while that file's own header — amended the
  same day by longshot's single-homing fix — says every threshold lives in
  `longshot/bankroll.py` `GUARDRAILS` and that it is a convenience copy. Two
  files each naming the other as canonical is the defect single-homing exists
  to prevent; it survived because they live in different repos and no single
  sweep pass owns that boundary. Pointer corrected on both halves.

## [ossuary-v2.2.5] - 2026-08-14

A 2026-08-14 estate-audit finding: bonecaller implements a fifth job the
description never named, so nothing routed to it.

- bonecaller 1.3.4: `description` gains the Pause/resume job in its
  capability clause and "pause the betting" in its trigger list, 791 → 890
  chars. The body has carried the job since 1.0.0 and `test-cases.md`
  asserts it at B5; the pack router lists it too, but that router ships as a
  Claude Code `CLAUDE.md` and bonecaller's declared surface is claude.ai,
  which never loads it — so the description was the only routing text and it
  was silent on pause. Trigger suite 8 rows → 9 (row 9 authored, not run);
  the cold re-judge of all 9 is owed, not claimed.
- **The longshot `skills/revenantworks-ossuary-bonecaller` mirror is owed a
  re-sync** (separate session, per the downstream-mirror rule). It is still
  at 1.3.0 — three releases behind before this one — and that copy carries
  the 533-char `compatibility` the live upload form is confirmed to reject.

## [foundation-v2.3.1] - 2026-08-14

Six 2026-08-14 estate-audit findings closed across four members. No
description moved, so no routing surface changed and every trigger suite
keeps its counts; three of the six extend the same
data-never-instructions rule to entry points that were ingesting without it.

- **agentwright 1.2.0 → 1.2.1** — Entry — Emit carries the rule. It ingests a
  handed-in ops spec and renders it into a scheduler's fields, which makes it
  the highest-consequence ingest in that member; 1.2.0 closed Refresh and
  left it open.
- **skillwright 1.2.0 → 1.2.1** — Entry — Upkeep step 1 carries the rule. It
  reads other skills' frontmatter and stamp headers, from a registered
  canonical repo where no workspace copy exists, and step 4 acts on what it
  read. `upkeep-doctrine.md` points at that single home instead of copying
  it. Body budget raised 8080 → 8180 with the reason on the registry row.
- **tokenwright 1.2.0 → 1.2.1** — the rule is promoted from Entry — Slim to a
  fifth Turn shape item, so Audit and Budget are bound by it too; they ingest
  the same instruction-shaped artifacts. Two single-homing repairs ride along:
  the audit inventory's length threshold now lives only in
  `waste-taxonomy.md`, and the refresh sync sweep names `SOURCES.md`, the
  third site of a platform figure it was not reaching.
- **lorewright 1.1.3 → 1.1.4** — eval provenance only: the 1.1.3 re-anchor
  clause was inserted mid-paragraph rather than appended, so the chain
  terminated at the older v1.1.2 anchor. Moved to the end, wording unchanged.

Each member's eval provenance is re-anchored in this commit, and the suites
record what is now asserted nowhere: no case covers an injected directive on
agentwright's Emit, skillwright's Upkeep, or tokenwright's Audit and Budget.
Those cases are owed, not claimed.

## [ossuary-v2.2.4] - 2026-08-14

Caught during the 2026-08-14 hygiene sweep's mirror re-sync: citadel's copy
of `references/card-contract.md` (linecaller) had drifted stale against two
real fixes that landed only on the longshot production mirror and were
never ported back — `2713461` (weather driver, today's-risk KPI, bets-first
game ordering) and `e7e43e6` (corrected spread-pick sign, unambiguous bet
instructions). A routine full-directory mirror sync would have silently
clobbered both; caught before it shipped.

- linecaller 1.5.4: `references/card-contract.md` re-synced from the
  longshot mirror — citadel is the canonical source again, both copies
  byte-identical. No trigger token, `name`, `description`, or
  `compatibility` field touched; cold re-judge held 10/10. R1 and R9 in the
  assertion suite sit nearest the changed ground and are owed a live
  re-run before the next release claims full coverage.

## [ossuary-v2.2.3] - 2026-08-14 (correction)

The 2.2.1 fix assumed `description`'s 500-char rejection shared
`compatibility`'s cause. It never did: two real upload attempts at the
trimmed description length never errored on `description`, only on
`compatibility` (2.2.2). skillwright's own rubric caps `description` at
1024 chars and Anthropic's help-center page separately states 200 — neither
number is confirmed live by this product, so guessing further wasn't the
right move. Reverted `description` to its full pre-trim text on both
members.

- bonecaller 1.3.3: description reverted 496 → 791 chars (original text,
  byte-identical to the version already cold-judged 8/8).
- linecaller 1.5.3: description reverted 495 → 742 chars (original text,
  byte-identical to the version already cold-judged 10/10).
- `compatibility` stays at its 2.2.2 trimmed length on both — that field's
  500-char rejection is the one actually confirmed live.

## [ossuary-v2.2.2] - 2026-08-14

> **Never tagged, never released — recorded 2026-08-14, by decision.** This
> version reached main (`537eb13`) and was superseded by 2.2.3 four and a half
> minutes later, so no `ossuary-v2.2.2` tag or Release was ever cut and the tag
> sequence jumps 2.2.1 → 2.2.3. Backfilling the tag now would fire the release
> workflow and publish zips built today that were never actually shipped, which
> is worse than a gap; the gap is recorded here instead. Clone-based plugin
> installs read `marketplace.json` from the repo and never needed the assets,
> and this version's content is fully superseded by 2.2.4.

The 500-char claude.ai upload ceiling turned out to apply to more than
`description` — the owner's actual upload attempt on ossuary-v2.2.1 was
rejected on `compatibility` (bonecaller 533 chars, linecaller 667 chars).

- bonecaller 1.3.2: `compatibility` trimmed 533 → 312 chars, every
  dependency and degradation fact preserved.
- linecaller 1.5.2: `compatibility` trimmed 667 → 463 chars, every
  dependency and degradation fact preserved.
- Pack bump only — no trigger token, hard rule, or reference file changed;
  cold re-judge not owed (compatibility carries no routing).

## [ossuary-v2.2.1] - 2026-08-13

Both members' claude.ai skill upload was failing: the live upload form
rejects a `description` over 500 characters, a stricter ceiling than the
1024-char spec limit this pack's `rubrics.md` baseline carries (flagged there
for the next `skillwright refresh`).

- bonecaller 1.3.1: description trimmed 791 → 496 chars, every trigger token
  and both boundary clauses preserved; cold re-judge 8/8, unchanged.
- linecaller 1.5.1: description trimmed 742 → 495 chars, every trigger token
  and both boundary clauses preserved; cold re-judge 10/10, unchanged.
- Pack bump only — no member body, hard rule, or reference file changed.
  Longshot `skills/revenantworks-ossuary-linecaller` mirror re-synced
  byte-identical.

## [ossuary-v2.2.0] - 2026-08-12

The 2026-08-12 estate-audit remediation pass, ossuary half (findings 3, 6, 7,
11, 12, 19, 20 of `estate-audit/findings/audit-2026-08-12.json`):

- linecaller 1.5.0: coaching notes bounded to model guidance (never the Hard
  rules, the identity gate, the staging list, or any command); step 7 gains
  the delivery proof (fetch, confirm origin/main holds HEAD, retry once, else
  DELIVERY FAILED — ported from the live routine prompt so the skill is the
  procedure's single home); `compatibility` declares step 3's web-search and
  network dependency and drops the Windows-only path and interpreter forms
  for per-surface ones.
- bonecaller 1.3.0: the graded-bet ROI threshold is re-homed to a pointer at
  `longshot-bankroll-rules.md` (one number, one home); the connector
  dependency names the fully-qualified tools (`github:get_file_contents`,
  `github:create_or_update_file`); hard rule 3 extends to the verbatim-HTML
  render path.
- **The longshot `skills/` mirror is owed a re-sync** for both members
  (separate session, per the downstream-mirror rule), and the live Longshot
  routine prompt is owed its thinning to point at the skill (finding 6's
  other half).

## [foundation-v2.3.0] - 2026-08-12

The 2026-08-12 estate-audit remediation pass, foundation half (findings 2, 5,
8, 9, 10, 13, 14, 15, 16, 17 of the same audit):

- All five refresh-carrying members (agentwright 1.2.0, promptwright 1.4.0,
  tokenwright 1.2.0, rigwright 1.1.0, skillwright 1.2.0) carry the
  fetched-page injection rule on their fetch-and-stamp steps, and the four
  without one gain the search-unavailable no-restamp fallback.
- The handed-in-material injection rule is promoted to a file-level Turn
  shape rule in commwright 1.1.0, brandwright 1.3.0, evalwright 1.1.0, and
  rigwright 1.1.0 — single-homed, binding every entry.
- Boundary closes: rigwright ↔ tokenwright shut from both sides (both
  descriptions moved; seam row updated); skillwright's description gains the
  tokenwright and evalwright negative triggers.
- skillwright: packaging caps re-homed to Rubric A; shell/python3 packaging
  dependency declared; rubrics.md records the ~150-line TOC threshold as a
  deliberate house variance from Anthropic's ~100.
- TOCs: lorewright 1.1.3 (verdict-mode.md) and commwright (humanize.md) gain
  Contents blocks.
- agentwright gains its missing dependency declaration.
- upkeep-task.md scope item 2 now derives member surfaces from
  `metadata.volatile` and fails loud; the live routine's STEP 2 is owed the
  matching edit by hand.
- Registry budget rows raised for the audit additions (promptwright 9030,
  skillwright 8080, linecaller 1560), reasons per row.

## [ossuary-v2.1.0] - 2026-08-08

- linecaller 1.4.0: the daily run stages **by path**
  (`reports ledger models docs data/intel data/odds`) instead of `git add -A`,
  with `data/nflverse/` excluded by name. Closes the two remaining open
  findings against this member from the 2026-08-08 assessment: the
  unbounded-history risk (a 37 MB depth-chart CSV plus games.csv were
  recommitted on every refresh — in-season churn would have ballooned the
  repo, which is what the LFS question was really about) and the observation
  that `-A` ships any stray working-tree file unreviewed. Chosen over Git LFS
  deliberately: LFS would add a binary dependency the daily cloud runner does
  not have, while the CSVs are re-fetchable cache governed by their own
  `.stamp` files. They stay tracked at their current revision so a fresh clone
  still boots warm, so run reliability is unchanged. New assertion case R12
  covers it (11 → 12).

## [foundation-v2.2.4] - 2026-08-08

- skillwright 1.1.1: pack-registry records the ossuary member rename
  (`cardcaller` → `bonecaller`, see ossuary-v2.0.0 below) across the members,
  budgets, and seams tables; the Entry — Pack eval scenario's role moved to
  "a customer-support engineer" (2026-08-08 estate audit, owner judgment —
  the old role was a near-description of a firewalled identity's own
  product).
- commwright 1.0.3: case-04 fixture second-pass re-baseline — the greeting's
  recipient name (never a frozen fact, provenance unrecorded) is neutralized
  like the sender signature was in 2.2.3.
- Forge Run capstone card: rigwright joins the Leg-4 consult roster
  (brandwright + evalwright + rigwright) — the registry's 2026-07-30
  nine-member claim finally reaches the card it claimed to have updated.
- RUNBOOK: member-bump-on-shipped-change rule codified — any change to a
  member's shipped files (evals and fixtures included) bumps that member in
  the same commit, because the claude.ai lazy re-upload is keyed on the
  member zip's version. 2.2.3 shipped three members' eval changes with no
  version signal; for commwright the stranded change was the name scrub.
- build.py: eval-provenance freshness now requires the head to name the
  CURRENT member version (a dated re-anchor to an old version used to pass —
  how linecaller's assertion suite sat at v1.1.0 through two releases);
  parity compares an installed peer brand definition against its declared
  home-repo source instead of skipping it (northstar mapped); clone parity
  lines are labeled per pack.
- NEXT.md refreshed (item 2 → confirm the 2026-08-07 branded `+install` zip
  actually reached claude.ai).

## [ossuary-v2.0.0] - 2026-08-08

- **Member renamed: `revenantworks-ossuary-cardcaller` →
  `revenantworks-ossuary-bonecaller`** (owner-directed, motif conserved —
  the ossuary claims `-caller`, and bones are the oldest dice). Major pack
  bump: a member's invocation name is a breaking surface. Collision-checked
  before the claim (`audit/COLLISION.md`, 2026-08-08 supersession): zero
  GitHub namesakes, unclaimed on npm/PyPI/crates.io; runner-up `shotcaller`
  rejected on the same bar. Directory, frontmatter `name:`, description
  trigger token, router, registry rows, root README, and both manifests
  moved; member history continuous.
- bonecaller 1.2.0: eval coverage completed to the house standard —
  first assertion suite (`evals/test-cases.md`, 7 cases), first
  `SOURCES.md`, and `evals/RESULTS.md` now exists, making the four surfaces
  that already pointed at it true (the 1.1.1 re-judge record previously
  lived only in trigger-evals' provenance note). Post-rename cold re-judge
  of the trigger suite recorded there.
- linecaller 1.3.0: description and compatibility follow the companion's
  new name; step 5 hardened — enrichment bullets are plain text,
  HTML-escaped before landing in the rendered card's drivers list (audit
  finding: a planted "quote" could smuggle markup into the artifact the
  companion renders verbatim); assertion-suite provenance re-anchored (the
  missed 1.2.0 re-anchor the old gate accepted).
- Pack CLAUDE.md: the stale "open asymmetry" seam paragraph replaced with
  the closure the registry and both descriptions have recorded since
  ossuary-v1.1.0 (the router asserted the opposite of the surface it
  governs).

## [foundation-v2.2.3] - 2026-08-08

- brandwright evals: the 1.2.0 roster/peer-selection mechanism finally has
  coverage — trigger suite 22 → 30 (17/13), assertion suite 16 → 23 (Cases
  17–23: named/scoped/ask selection, never-blend, peer-scoped audit with the
  cross-brand P0, absent-roster refusal, build-writes-peers), and a new peer
  fixture `brand-definition-saltmere.md` beside the primary (bumped 2.0.0 →
  2.1.0 with a roster table). Extended AND executed the same day: two
  independent blind judges 27/30 each (identical misses — the known #15/#17
  borderline pair, plus new #27, an authoring defect reworded in-pass with
  its single re-judge owed); Cases 17–23 first execution 7/7 PASS. Full
  record in brandwright `evals/RESULTS.md`.
- Owner-approved personal-identifier scrub on public eval surfaces:
  commwright's `case-04` fixture re-signed with a neutral name (re-baselined,
  not silently edited — frozen facts byte-identical; provenance updated in
  `RESULTS.md`), and local run paths in commwright's and agentwright's
  `RESULTS.md` ledgers redacted to `%TEMP%` (entries otherwise verbatim).
- skillwright pack-registry: the ossuary seam row moves from *one
  description* to *both descriptions* — the owed linecaller boundary clause
  landed (ossuary 1.1.0) and the cold re-judge is executed, so the seam note
  records the closure instead of the debt.

## [ossuary-v1.1.0] - 2026-08-08

- linecaller 1.2.0: the description gains the owed seam-closing clause —
  "not for reading an existing card and ledger/bankroll questions — the
  claude.ai companion revenantworks-ossuary-cardcaller owns those." Full
  10-row cold re-judge executed: 10/10, and row 9's old JUDGE tag retires
  (the exclusion is now stated text). `references/card-contract.md` also
  stops naming live brand palette tokens on this public surface — it points
  at the private repo's `style.py` as the single token source
  (brand-carriage hygiene).
- cardcaller 1.1.1 + linecaller 1.2.0: owner-approved personal-name scrub —
  the owner is no longer named by first name anywhere in either member
  (descriptions, bodies, contracts, README, eval prose). No trigger token
  moved; cardcaller's 8-row suite was re-judged cold anyway: 8/8. Both
  members' provenance re-anchored in the same commit.
- cardcaller README: the cloud routine is named by its full canonical name
  ("Project Longshot - Daily Card"), closing a stale short form.

## [ossuary-v1.0.1] - 2026-08-07

- linecaller evals: discharge the row-3 trigger debt owed since the
  `vault`→`ossuary` / `-picker`→`-caller` rename — re-read cold against the
  shipped `linecaller` token, PASS. R11 (a live idempotency assertion, not a
  cold-trigger read) stays open until a real pipeline run exercises it; noted
  in `RESULTS.md` rather than closed by assertion.

## [foundation-v2.2.2] - 2026-08-07

Ships content that had already landed on 2.2.1 without a bump — and the pack version
is the cache key, so an install could never receive it. That is the gotcha this repo
documents; this release is it happening for real.

- `LICENSE` x10 now read `Copyright (c) 2026 Revenantworks` (brand definition v2.1.14
  made the copyright line a naming class: the house, never a person).
- `pack-registry.md` carries the ossuary pack tables; `spec.md` records register 7 as
  resolved.
- `tools/build.py`: per-pack conformance notes (a latent bug the second pack exposed —
  every pack resolved to the FIRST pack's conformance line), and `--parity` no longer
  reports an installed **peer** brand definition as drift. A peer is installed from a
  private repo by design and absent from HEAD, so flagging it made parity a gate that
  could never pass — the inverse of one that never fails, and no more useful.

## [ossuary-v1.0.0] - 2026-08-07

**Second pack, first release from this repo — the citadel is now the canonical home
for every skill** (owner decision, 2026-08-07). `revenantworks-ossuary-linecaller`
and `revenantworks-ossuary-cardcaller`, both at member version 1.1.0, moved from
`MickMacPW/longshot`'s `skills/` into `packs/ossuary/skills/`. Names unchanged; no
member behavior changed.

New in this repo: `packs/ossuary/.claude-plugin/plugin.json` at 1.0.0, an `ossuary`
marketplace catalog entry, a pack router at `packs/ossuary/CLAUDE.md`, and the pack's
registry section — `ossuary` members, budgets, and seams — so `references/pack.md` is
generated for both members like foundation's nine. Measured bodies: linecaller 1145
tokens against a 1400 ceiling, cardcaller 805 against 1100, both far under the 5k
advisory and declared anyway so the pack starts with one comparable number per member.
The single boundary pair (linecaller ↔ cardcaller) is declared with its cold-listing
signal recorded honestly as **one description**: cardcaller's description excludes
running the pipeline, linecaller's says nothing about reading a card that already
exists, and the cold re-judge that would close it is owed, not claimed. Pack
conformance checks adopted: **O-1 decision-support only · O-2 never fabricate a
number** — both verbatim hard rules in both bodies.

**longshot keeps a working copy, by requirement.** The "Project Longshot - Daily Card"
cloud routine clones only that repo and reads linecaller's `SKILL.md` and two of its
`references/` files out of the fresh clone, and a user-scope junction points into it.
That copy is now a declared **downstream mirror** — same convention the repo already
uses for `docs/routine-prompt.md`: citadel is source of truth, the two must not drift,
and the mirror is byte-identical so `diff -r` is the drift check. Recorded in longshot's
`skills/README.md` and in its `CLAUDE.md` file map.

**Deferral-register item ⑦ is closed** (`packs/foundation/spec.md`) — resolved the
other way round: the pack moved in rather than the registry moving out of skillwright,
which dissolves the cross-repo source-of-truth problem the item was opened against.

**`tools/build.py` — a latent parser bug the second pack exposed.** `pack_lines()` read
conformance checks from the registry row's *Profile* cell, never matched, and fell
through to a whole-document search that returns the **first** pack's line — so ossuary's
generated manifest was stamped with foundation's checks and its 2026-07-13 adoption date,
with `--check` clean throughout. Fixed: new `registry_pack_notes()` reads each pack's own
Notes cell, and the whole-document fallback is gone in favour of a stated default. Two
unit tests added (one on the synthetic fixture, one asserting the live registry's two
packs cannot resolve to the same pair), plus number words 2–6 for the manifest's roster
line. Foundation's nine manifests are byte-unchanged by the fix.

Count integrity now spans two packs: registry 11 = folders 11 = manifests 11.

## [foundation-v2.2.1] - 2026-08-07

brandwright 1.2.1 — the neutral definition's palette storage shape now has slots for
everything 1.1.0's derivation rules produce: the computed neutral ladder, accent
base/ink pairs, per-mode light, shared accents, and the separation floor. Without them
the rules had nowhere to land on a new brand, and the absence read as compliance.

## [foundation-v2.2.0] - 2026-08-07

**brandwright holds several brands now.** It could carry exactly one active
definition, so a personal or social brand could not sit beside a product brand
without overwriting it. brandwright 1.2.0 adds a roster and a selection step.

- `brand-definition.md` carries the **roster** — each brand'"'"'s slug, the surfaces it
  owns, its peers — and peers live in `brand-definition-<slug>.md` siblings that
  open only when selected, so the always-open cost stays one file.
- **Selection is a named workflow step**, resolved before any other work: named in
  the request, else scoped by the target, else **asked** in one line. Topic and tone
  never decide it — a personal-voice request aimed at a product surface is exactly
  the case to ask about rather than infer.
- **Cross-brand law**: never apply one definition to a surface another owns, never
  blend two in one output; they share a surface only where the owning definition
  declares an attribution mark for the peer.
- Build writes peers: a build for an unrostered brand creates its sibling and adds
  the roster row in one pass. Scope and coexistence are asked inside the existing
  firewall-map group — the count of 14 build groups is load-bearing.
- `tools/apply-install-swaps.py` takes `<primary-dir> [<peer-dir> ...]`, overlays
  peers as siblings, and warns when a peer is absent from the primary'"'"'s roster
  (overlaid but unreachable). Single-dir invocation is unchanged.
- brandwright'"'"'s body budget raised 3300 → 3450 with its reason recorded: the
  selection block is always-relevant routing and must be body-resident.

## [foundation-v2.1.0] - 2026-08-07

Additive doctrine release — no rename, no entry point moved, no description
changed on any member. Two members carry the pass; the other seven pick the
fresh manifests up on their own next release (`restamp: lazy`).

- **brandwright 1.0.2 → 1.1.0.** Palette doctrine, which until now was a
  role-token rule and a drift sweep note. `audit-doctrine.md` gains **Build —
  palette derivation** (D-1 to D-7): neutrals computed in OKLCH at the brand's
  own accent hue rather than hand-picked · a ~1.13:1 visibility floor per
  elevation step · the border token split quiet/lit with the lit one clearing
  3:1 on its own surface · lit and glow derived from the accent's own lightness
  with the contrast floor as a `max` second term, carrying the general rule that
  a rule tuned on one hue is re-tested on every hue before it becomes doctrine ·
  colour never carrying state alone (WCAG 1.4.1) · a shared accent set proved by
  a ΔE00 coverage matrix and optimised jointly rather than member-by-member,
  with semantic overrides recorded · CIEDE2000 as the separation metric with a
  regional floor where the wheel is crowded. The **palette drift** sweep note
  now puts the neutrals in scope and requires the ratios recomputed and
  reported. `application-doctrine.md` gains **Palette inheritance — structure,
  light, and marks**: structure may be shared system-wide, light belongs to one
  identity and one mode, a multi-mode brand needs a complete set per mode with a
  stated switch condition, and a parent accent may cross onto a child's surface
  as attribution but never as its light.
- **skillwright 1.0.6 → 1.1.0.** `rubrics.md` gains **Generator classes G-1 to
  G-3** — derive the source's section list or fail loudly rather than
  skip-and-continue, ship a `--check` parity mode as part of the generator, and
  detect stale output in the target directory — plus **Naming-class coverage**,
  the rule that a naming convention binds every class carrying a name, display
  names and artifact titles included, and that ids carry no cadence suffix.
  Wired from the body by two clauses at a cost of 33 tokens; the 7,800 budget row
  is unchanged and the member now sits 17 tokens under it.

Both passes are neutral by the brand-carriage law: the doctrine states
derivations, thresholds, and metrics, and adds no palette value, brand name, or
identity string anywhere.

## [foundation-v2.0.0] - 2026-08-07

The `revenant` → `revenantworks` migration (brand definition v2.1.0, History
rows dated 2026-08-06; owner-adjudicated 2026-08-07). Breaking rename — the
marketplace identity and every member name move; content is otherwise
unchanged, so no member version bumps and no eval re-anchors are owed.

- **Marketplace renamed `revenant` → `revenantworks`** (`marketplace.json`
  `name` + `owner.name` → `Revenantworks`). The platform has **no marketplace
  rename mechanism** (COLLISION.md C3/C4 — kept as record, supersession note
  appended): every `<plugin>@revenant` reference breaks by design. The owner
  adjudicated execute-anyway; the single-consumer estate migrates by local
  remove-and-re-add of the marketplace (`claude plugin marketplace add` under
  the new name, then `claude plugin update foundation@revenantworks`). The
  plugin keeps its name — `foundation` — so no `renames` map applies.
- **All nine members renamed** `revenant-foundation-<member>` →
  `revenantworks-foundation-<member>`: directory names, `name:` frontmatter,
  H1s, eval files, references, and every cross-reference, registry and
  manifests included. Each member CHANGELOG carries a dated rename note;
  version history is continuous across the rename.
- **Brand token** in the registry's Build defaults and each member's
  `metadata.brand` label → `revenantworks`.
- **Tooling follows**: `build.py` (registry path, `--parity` clone/cache
  surfaces now `marketplaces/revenantworks` and `foundation@revenantworks`),
  `test_build.py` fixture, `apply-install-swaps.py`, README/RUNBOOK commands.
- **promptwright budget row 8850 → 8860** — the member name grew 5 chars and
  appears in the body; bookkeeping, no content change.
- **LICENSE** (root + all nine member copies): copyright now carries both
  founding names, QuaziDed · DeD Pixel, per the definition's identity map.
- Frozen records keep the old strings by design: `audit/AUDIT.md`,
  `audit/COLLISION.md` (each with a dated supersession note),
  `AUDIT-2026-08-05.md`, `ledger.md` dated entries, predecessor-era eval
  ledgers, and this file's 1.0.0 entry.
- **Install-parity consequence, recorded not chased**: until the local
  remove-and-re-add lands, `build.py --parity` cannot see the old-name
  install (`marketplaces/revenant`, `foundation@revenant`) and reports
  nothing-installed/skip. The claude.ai copies still carry 1.0.0 bodies under
  the retired names — register ⑨ widened accordingly.

## [foundation-v1.2.0] - 2026-08-05

The AUDIT-2026-08-05 apply pass — every verdict from the adversarial
refinement audit (report at repo root), applied member by member on approval.

- **Registry**: new rigwright ↔ tokenwright seam row (motive-keyed, signal:
  one description) closing the undeclared "trim my CLAUDE.md" / "slim my
  CLAUDE.md" boundary opened by rigwright's 2026-07-30 addition; the stale
  naming note now counts three CLAUDE.md descriptions. Seam note records the
  close. 12 → 13 seams; all nine manifests regenerated.
- **promptwright 1.3.0**: Tier routing gains the user-named-target override
  (a model or effort the user names wins — built to, noted as user-directed,
  better fit offered in one line; Entry — Model bound identically). Four
  lossless trims offset it; body lands exactly at its 8,850 budget. Case 39.
- **tokenwright 1.1.0**: description gains the rigwright boundary clause
  (802 → 894 chars). Trigger evals extended (Y11/N11), 22 rows.
- **agentwright 1.1.0**: description slimmed 992 → 950 chars, every cue
  kept; the ceiling-riding fix `build.py`'s warn text had scheduled.
- **skillwright 1.0.6**: lossless trim at the two audit-named sites (Build
  step 6 registry guard; bare-invocation cap); Case 14/17 anchors intact.
- **rigwright 1.0.2**: description names hooks in the artifact list
  (952 → 959 chars).
- Cold re-judges of the four moved routing surfaces (tokenwright,
  agentwright, rigwright trigger suites; promptwright's did not move) are
  owed and recorded as owed in each suite's provenance line, not claimed.

## [foundation-v1.1.5] - 2026-08-02

lorewright brought current, promptwright gains two tier-routing rules.

- **lorewright 1.0.2 → 1.1.2.** The v1.1.0 doctrine (Selection/Decision class
  split, four-slot Selection recommendation, seeded must-have gate,
  independent-evidence-first, coverage disclosure, purchase link) had been
  authored in a separate session and never installed — repo, marketplace, and
  cache had all silently stayed on 1.0.2 with 23 cases. Installed as built.
  **1.1.1:** Finding G1 applied — §4a's Top overall slot now states the
  must-haves gate explicitly, matching the other three slots; Case 27
  re-confirmed. Cases 30, 32, 34, 36 cold-executed for real with live
  search/fetch (the four whose Asserts need real retrieval) — 4/4 PASS,
  logged in `evals/RESULTS.md`; the remaining 12 of Cases 24–39 are authored,
  not yet cold-run. **1.1.2:** tokenwright slim, no behavior change —
  `SKILL.md` body cut ≈3040 → ≈2717 tokens; registry row raised 2700 → 2750.
- **promptwright 1.1.1 → 1.2.0.** Tier routing (Phase 5) gains two
  role-based overrides, shared by the standalone Model entry and plan grain:
  a planning/orchestrator subtask defaults one effort notch lower (high
  effort over-thinks and scope-creeps a plan); a review subtask checking
  another model's output defaults to a different model family, stakes
  permitting. Closes the gap found by a skillwright niche-verdict + gap scan
  run against a candidate 10th foundation member (an orchestration skill,
  informed by real-world r/ClaudeCode prior art) — plan grain already covers
  the candidate's stated job end-to-end except these two rules, so a new
  pack member wasn't justified. Case 38 added. Registry row raised
  8800 → 8850.
- Roster and seams unchanged (9 members, 12 seams); seven members untouched.

## [foundation-v1.1.4] - 2026-08-01

Parity tells the truth now, and carries the two records files that had no
release to travel on.

- **`--parity` widened from `SKILL.md` frontmatter to every shipped file.**
  The narrow scope reported **clean** twice while the loaded copy was stale:
  the lagging files were `ledger.md` and `spec.md`, which are not frontmatter
  and so were never compared. It now lists each file as missing, differing or
  extra, normalises line endings (a CRLF working tree vs an LF clone is not
  drift), and skips runtime markers. Verified by running it against the real
  stale install, where it named exactly the two files and nothing else.
- **skillwright 1.0.5** — Install parity re-scoped to match, with the lesson
  stated once: a detector narrower than what it certifies produces false
  assurance, which is worse than no detector because it ends the
  investigation.
- **Delivers `ledger.md` and `spec.md`** as of `8fdeeb9`, the post-1.1.3
  docs commit that had no pack bump to ride. Records only — no skill loads
  either at runtime.
- Roster and seams unchanged (9 members, 12 seams); eight members untouched.

## [foundation-v1.1.3] - 2026-08-01

Pack-wide prose pass: every member's own files (SKILL.md, README, SOURCES,
reference docs) and the root/pack-level docs (README, this file, RUNBOOK,
NEXT, the always-on router, decisions.md) were rewritten for register —
connector cleanup (em dash and " - " used to join clauses that read better as
two sentences, matched-pair parenthetical asides left alone), cross-referenced
rule duplication (a rule stated in full in two places now has one home and one
pointer), and a few wording/consistency fixes. No rule, gate, count, or entry
point moved anywhere, so no eval re-anchor is owed pack-wide.

- **commwright → 1.0.2** — its own SKILL.md and README used em dashes in the
  sentences announcing its no-dash H1 rule; the framing prose now matches the
  policy it states. Rule bodies and `humanize.md` were already dash-free.
- **skillwright → 1.0.4** — the shared "foundation seam notes" history in
  `pack-registry.md` (the seam-table's canonical source, read by every
  member's generated `pack.md`) reformatted from one ~700-word paragraph into
  a dated list, same facts; plus SOURCES.md wording and reference-file
  connector fixes.
- **promptwright → 1.1.1** — `model-snapshot.md`'s footnote markers had a gap
  (¹, ³, ⁴ with no ²); renumbered sequentially. `hostile-interpreter.md`
  trimmed to stop re-stating SKILL.md's own failure-shape definitions.
- **tokenwright → 1.0.2** — SKILL.md's Preservation-contract list was missing
  an item (dependency declarations and absence behaviors) that
  `waste-taxonomy.md` and this file both already carried; added, closing a
  real 6-vs-7 gap, not a style choice.
- **agentwright, brandwright, lorewright → 1.0.2 each** — a duplicated
  quarantined-reader rule (agentwright), a triple-duplicated per-element
  exclusion example (brandwright), and one telegraphic line (lorewright) each
  now single-homed or reworded.
- **evalwright → 1.0.2, rigwright → 1.0.1** — SKILL.md rules that restated a
  reference file's rule in full (count-drift/provenance for evalwright,
  the secrets rule for rigwright) now cross-reference their one home.
- **`spec.md`** (the live baton, not itself a member): the Current-status
  block now reflects 1.1.2/1.1.3 instead of stopping at 1.1.1; the frozen
  1.3.2-pass history paragraph gained an inline tag marking it as the
  pre-rebaseline snapshot, since the live deferral register 100+ lines later
  states a different, current register count and the two were easy to
  mistake for a contradiction.
- **`ledger.md` and `IMPROVEMENTS.md`** headers now point at this file's own
  predecessor-era disclaimer instead of independently restating it — three
  copies of the same disclaimer collapsed to one canonical text plus two
  pointers. Neither file's dated historical entries were touched, per their
  own append-only doctrine.
- **`tools/build.py` fix, found by this pass:** the seam-note extractor
  assumed the registry's seam-notes annotation was always one physical line
  and silently returned nothing otherwise. Reformatting it into a dated list
  (above) tripped that assumption and would have shipped all nine `pack.md`
  copies with the section missing; the extractor now captures a multi-line
  block up to the next top-level pack annotation. Caught before commit, not
  after.
- Roster and seams unchanged (9 members, 12 seams); no member's rules,
  counts, or entry points changed except tokenwright's one named content fix
  above.

## [foundation-v1.1.2] - 2026-08-01

Frozen records marked, so no version number anywhere in the pack can be
mistaken for a current one. Delivery release for the 1.1.1 post-tag work.

- **13 `evals/` files across 7 members gained a frozen-record header** naming
  their version numbers as predecessor-era and pointing at the root note. The
  remaining eval files already carried the disclaimer. **Rows, verdicts,
  dates, counts and pass rates are untouched.** The ledgers stay evidence,
  which is why this is a marker and not a rewrite.
- **agentwright, brandwright, commwright, evalwright, lorewright, tokenwright
  → 1.0.1; skillwright → 1.0.3** (its 1.0.2 doc fix rides here too, having
  been undeliverable at member grain).
- Also carries **skillwright 1.0.2** and the `tools/build.py` date-anchoring
  from `3a3b084`, which had no pack bump to travel on.
- **`build.py` now prunes superseded `dist/` zips.** It wrote
  `<member>-<version>.zip` and never removed the old one, so every bump left
  its predecessor sitting beside the current build: 16 zips for 9 members at
  this release. Since release-doctrine treats `dist/` as the upload source of
  truth, a stale neighbour is a mis-upload waiting to happen. `dist/` now
  holds exactly one zip per member.
- Roster and seams unchanged (9 members, 12 seams); promptwright and
  rigwright untouched.

## [foundation-v1.1.1] - 2026-08-01

Install-parity release: the tooling fix from `4800918` reaching the copies
that actually load. Cut for delivery, not for new capability.

- **The pack version is the plugin cache key.** `claude plugin update`
  compares pack versions, so a member-only bump never reaches an installed
  user: the marketplace clone moves, the loaded cache does not, and the
  update reports "already at the latest version". skillwright 1.0.1 rode main
  and stayed unreachable until this bump, which is the whole reason it
  exists. Recorded in `release-doctrine.md` — Install parity and RUNBOOK
  step 5.
- **skillwright 1.0.1** — release-doctrine's Install parity described one
  installed copy where Claude Code has two (the clone an install reads from,
  the cache it loads); now states both surfaces, the two-step order, the
  cache-key rule, and that parity knows nothing about claude.ai.
- **`tools/build.py --parity`** diffs the clone **and** the loaded cache,
  names which surface drifted, and skips each cleanly when absent (CI-safe).
  Verified against a real stale cache, not trusted on a clean run.
- Roster and seams unchanged (9 members, 12 seams); no member behavior moved.

## [foundation-v1.1.0] - 2026-08-01

- **promptwright 1.1.0** — Entry — Model gains plan grain: a handed-in plan
  with a targets ask gets a per-subtask target table (tier + model,
  effort/depth, inline-or-subagent, one-line why) instead of a single
  recommendation. A living-table contract rows an emergent mid-session
  subtask through the same tier logic before it dispatches; a standing-rule
  line rides beneath every table, its layer placement left to rigwright.
  Trigger suite 30 → 34 rows (17/17), assertion suite 36 → 37 cases; see the
  member's own CHANGELOG and `evals/RESULTS.md` for the full account.
- Router `packs/foundation/CLAUDE.md` gains the plan-table route cue and the
  living-table compose bullet.
- Roster and seams unchanged (9 members, 12 seams); no other member touched.

## foundation 1.0.0 — 2026-07-31 — the wright baseline

Nine build-time wrights, one plugin (`foundation@revenant`), each routing on
its own description and standing alone on any Agent Skills surface. Every
member ships with its references, trigger evals, and an assertion suite;
the pack's cold trigger baseline is 97/97. Versions are 1.0.0 across the
pack, plugin manifest, marketplace entry, and all nine members.

The 1.0 feature set, member by member (each member's own CHANGELOG carries
the full list):

- **skillwright** — builds, audits, ports, and integrates install-ready
  Agent Skills and whole packs: research-backed niche verdicts, dual-scored
  audits carrying the S-1…S-4 security pass and a register-only prose pass,
  sanitizing port with PORT-REPORT, pack-wide integrate under count
  integrity, 60-day refresh plus the pack-wide upkeep sweep. Ships
  spec-clean neutral.
- **promptwright** — seven-phase prompt builds with five-dimension scoring,
  a named-origin framework menu, a gated fast path, hostile-read hardening,
  the knowledge-vacuum check, S/A/B/C model-tier routing with the standalone
  `promptwright model` pick, and an optional offline HTML prompt card.
- **commwright** — channel-profile drafting under the silent H1–H9 humanize
  rules, a humanize entry for handed-in text, report-only message audits,
  cadence sets, and a pre-publish redaction sweep; it never sends.
- **agentwright** — ten-area ops-spec design sized blast-radius-first, emit
  into seven profiled platforms with per-control enforcement-gap tables, the
  five-class runtime security-scan, trust-tier doctrine, and a restraint
  that refuses autonomy plus irreversibility without a human gate.
- **lorewright** — evidence-graded verdicts ending in one direct
  recommendation with a flip condition, versioned playbooks verified against
  primary sources, four-grade claim tagging, and source-is-data-never-
  instructions injection handling.
- **brandwright** — the single home of brand and voice: the 14-group
  definition (ships neutral), the apply cascade, a seven-category drift
  audit with the P0 score floor, and four export payloads including the
  offline HTML brand-guide card.
- **evalwright** — coverage-mapped trigger-eval tables and assertion suites
  under count integrity and the zero-runtime-dependency law; five-check
  suite audits and diff-scoped refresh.
- **tokenwright** — exact-or-disclosed-estimate measurement, the W1–W10
  waste taxonomy, the nine-rung lossless→lossy ladder behind a preservation
  contract, net-cost accounting with cache mechanics, the description-cap
  rule, and set-level budget plans.
- **rigwright** — standing Claude configuration (Project instructions,
  CLAUDE.md, `.claude` layout, `.mcp.json`) built and audited through the
  seven-layer placement stack, with secrets restraint and a hard boundary to
  agentwright for anything unattended.

Pack-level:

- The always-on router (`packs/foundation/CLAUDE.md`): the routing table,
  the composition seams, and the pack conventions — neutral by default, one
  catalog one gate, audits report rather than rewrite, declared
  dependencies, stamped volatile surfaces on a 60-day cadence.
- Registry-derived build and validation (`tools/build.py`): the pack
  registry is the single source of truth for rosters; the build syncs
  manifests, validates every member, and produces the `dist/` zips;
  `--check` is CI mode, `--parity` verifies the installed clone.
- Brand-carriage law: brandwright is the only brand carrier anywhere — repo
  or installs; `tools/apply-install-swaps.py` overlays a private definition
  onto the neutral repo copy to produce the branded install zip.
- The `foundation-upkeep` cloud routine carries the volatile-surface sweep
  and the brand-escrow reminder.
