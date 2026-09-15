# Changelog — revenantworks-foundation-promptwright

> Renamed from `revenant-foundation-promptwright` on 2026-08-07 (pack 2.0.0 — the `revenant` → `revenantworks` marketplace migration). Name-only change: directory, frontmatter `name:`, and every cross-reference moved; the version history below is continuous across the rename.

## [1.5.12] — 2026-09-14

**Repairs the `description` that 1.5.9–1.5.11 left failing the build gate.** The handoff clause
added across those three versions took the field to 1294 characters, over the 1024 house ceiling,
and its unquoted `Entry: Model` made the whole frontmatter fail YAML parse; `build.py --check`
failed on both.

- `description`: the bold two-sentence tail becomes one boundary sentence, "A handoff or task
  brief is resumewright's to write." 1294 → 990 characters, no `: ` in the value; everything before
  it is byte-identical to 1.5.8's released text. The service-call detail — resumewright calls
  Entry — Model for a brief's tier line, and dispatchwright does not call it at all (#0073) — stays
  in the body, where 1.5.11 already put it.
- `evals/test-cases.md` re-anchored to v1.5.12 (1.5.9–1.5.11 never re-anchored it);
  `evals/trigger-evals.md` re-anchored. No row, case, or count moved; the cold re-judge owed since
  1.5.9 is still owed, now against the 1.5.12 text.

## [1.5.11] — 2026-09-14

**Corrects a claim 1.5.10 made that dispatchwright 1.2.9 (same day) made untrue** (observation
#0073). 1.5.10 said Entry — Model is "called as a service by resumewright (or a dispatchwright
plan)"; dispatchwright's own per-unit tiering became self-contained in the same session
(`references/tier-routing.md`, no sibling call) and never actually called this entry to begin
with — the phrase described an aspiration for dispatchwright's *plan* output, not its real Tier
mechanism, and would have gone stale the moment either changed.

- `description` and `Entry — Model` both corrected: dispatchwright does not call this entry;
  resumewright still does, for a task brief's tier line, per #0072.
- No eval case named dispatchwright directly, so `evals/trigger-evals.md` needed no case change —
  provenance note added for the description move regardless.


## [1.5.10] — 2026-09-14

**Owner ruling on 1.5.9's split, same day** (observation #0072). 1.5.9 gave promptwright a direct
trigger on handoff/task-brief requests, so it and resumewright could both fire on the same
request and negotiate who does what. The owner reviewed that shape and ruled it wrong: resumewright
owns every handoff, backward or forward; promptwright answers a tier question when asked, or when
resumewright asks it internally — it should not itself be a live candidate for "give me something
to hand off."

- `description` drops the 1.5.9 handoff clause; a handoff request no longer fires this skill
  directly. Adds one line naming resumewright/dispatchwright as the actual owners and Entry —
  Model as the service they call.
- `Entry — Model` reframed: called by resumewright (or a dispatchwright plan) for a brief's tier
  line, reached directly only on its own named ask or when neither sibling is assembling the
  brief.
- `evals/trigger-evals.md` **#39 flips should → shouldn't** (it was 1.5.9's own worked example of
  the trigger this version removes). 40 stays 40, split moves 20/20 → **19/21**. Cold re-judge
  still owed, now against the 1.5.10 text.

## [1.5.9] — 2026-09-14

**A real routing miss, caught by the owner asking directly** (observation #0071). Asked for "a
prompt to hand off to do the work later" (a multi-step Claude Code task brief, not a single-shot
prompt), the acting session invoked neither promptwright nor resumewright — the brief shipped
with no tier or model recommendation, which is Entry — Model's job by dispatchwright's own stated
rule ("the tier table is promptwright's... it never picks a model itself"). The gap wasn't that
Entry — Model was the wrong call; it's that the request didn't read as "building a prompt" at a
glance, so the entry was never reached.

- `description` and `Entry — Model` both gain a clause: a handoff, task brief, or unit brief
  written for a future session or agent to execute owes this entry's tier pick even when no
  single-shot prompt is being built. The trigger is "something is being handed to a future
  executor," not "a prompt is being built." Writing the handoff's own content is named as not
  this skill's job (resumewright for session state, plain writing or dispatchwright's unit-brief
  template otherwise).
- `evals/trigger-evals.md` gains **#39** (should: a handoff request that needs the tier pick) and
  **#40** (should-not: a session-state handoff that's resumewright's whole job). 38 → **40**,
  19/19 → **20/20**. The `description` moved, so a full cold re-judge is owed and not yet
  performed — recorded rather than skipped.

## [1.5.8] — 2026-09-11

Applied by unit L1b (dispatch run `2026-09-10-estate-audit`) from the task-observer weekly
review staged 2026-09-11. Body only; the `description` is byte-identical.

- **Phase 5 Tier routing, role-based overrides (#0022).** A verifier that only re-derives
  evidence already on disk defaults to balanced or fast tier at low or medium effort; the top of
  the ladder is for the judge weighing votes, not the voters fetching them. Stated with its
  budget form: verification costs less than the discovery it verifies.
- **Entry — Model, plan grain (#0022).** A target-table row that fans out states its agent count
  and the effort each agent inherits — one row for N agents understates the plan's cost by N,
  and the effort is this table's call, not a session default.

## [1.5.7] — 2026-09-10

**U2b/promptwright-zero-headroom-both-budgets.** Description sat at 1002/1024 chars (22 left)
and the body at its full 9470-token registry budget (0 left) — both ceiling-riding with no
room for the next doctrine addition. Slimmed with tokenwright's lossless ladder only
(dedupe, tighten, prune-to-contrastive-minimum — rungs 1-6; no rung-9 semantic compression,
no rule, threshold, number, or exact-reply string touched): description → 938/1024 chars
(**86 headroom, 8.4%**), body → ≈9319/9470 tokens (**151 headroom, 1.6%**).

The description slim: deduped the repeated `promptwright` prefix inside the subcommand
parenthetical (`promptwright model` → `model`, etc. — `promptwright` is already stated
immediately before the parenthesis), dropped "task" and "product" as non-differentiating
modifiers, "and" → "/" twice. No trigger word, verb, or boundary clause removed.

The body slim: cut the Phase 3 framework menu's decorative asides ("(the shape)"/"(the
feel)" etc.) while keeping every framework's acronym, use-case, and its named comparative
differentiator; pruned one of three illustrative examples in the Hostile-read "Letter beats
spirit" shape and its paired repair example (contrastive minimum — the shape is fully
carried by the remaining two); cut two small redundant restatements (Turn shape rule 1's
"Nothing else collapses it.", rule 2's "so nothing *can* follow") that repeated the same
sentence's own prior clause; tightened four short connective phrases (Phase 1 cross-ref,
quiet-build clause, knowledge-vacuum clause, sibling-handoff clause, restraint clause).

**Honest shortfall, not silently crossed (tokenwright's own Budget rule):** the body did
not reach the 5% (≈473-token) target. This member's body is dense, previously slimmed at
several past releases, and carries exact-reply-text (`Bare invocation`) and heavily
eval-anchored passages (Turn shape, Phase 3/5/6, the four Entry points, Keep going
rendering) this pass could not safely cut further without the full `test-cases.md`
assertion suite run to verify — the pack's own doctrine treats that as required before a
larger structural or de-specify pass on rule-bearing text, not something to gamble past
without it. Reaching 5% from here needs either a dedicated tokenwright Slim pass run
against the live suite, or a small declared-budget adjustment (this member's registry row
already records several such raises for genuine content additions); flagged for the owner.

**Blind trigger re-judge performed** against the slimmed description, all 38
`evals/trigger-evals.md` queries via `tools/blind_queries.py`: **38/38 hold their recorded
direction**, no row flipped. Before: 38 queries, 19/19 split, last full re-judge at 1.5.0
returned 36/38 with #29/#34/#37 as standing watch rows (unremediated, pre-existing). After
this slim: same 38/38 match against the established key; the three standing watch rows are
unaffected (none of the removed text touched the red-team/grill object wording those rows
turn on). `evals/trigger-evals.md` and `evals/test-cases.md` re-anchored to 1.5.7 below.

## [1.5.6] — 2026-09-10

**Two estate-audit findings.** `eval-ledgers-underreport-executed-probes`: Cases 40-42's
headings still read "authored, not run" though `evals/RESULTS.md`'s 2026-09-08 entry had
already recorded all three executed and passing — corrected the three headings to name the
result; no case content, input, assert, or count changed.
`promptwright-model-snapshot-stale-frontier-string`: `references/model-snapshot.md`'s
S-frontier Claude slot read "Fable 5" on five lines while this session's own lineup is
Claude Fable 5.1 — a lineup move inside the 60-day calendar window, which a pure calendar
cadence cannot catch. Spot-verified live against
`platform.claude.com/docs/en/about-claude/models/overview` (Claude column only — the other
four vendor columns were not re-verified and keep their 2026-08-17 stamp): Fable 5.1 is
unchanged in price ($10/$50), context (1M), and output (128K) from Fable 5, so this is a
naming correction, not a pricing or capability change. Added a launch-triggered refresh cue
beside the calendar one. Evals re-anchor accordingly.

## [1.5.5] - 2026-09-10

Closes the doctrine finding 1.5.4 filed, same day. No case, count, or
`description` moved outside what's named below.

- **`frameworks.md`'s Confirm-shared-understanding note now names three
  forms** and the test for picking one: **Hold** (a person answers in real
  time), **Assume** (nobody's there now, but a reader acts on it later — say
  the assumption and proceed), **State, then proceed** (no synchronous
  party and no later reader positioned to intervene before the effect
  lands — make the read visible, since there's nothing to hold for). A
  short paragraph names the failure of picking the wrong one in either
  direction: Hold on an unattended agent blocks forever; State-then-proceed
  on an interactive one lets a wrong read commit unseen.
- `SKILL.md`'s Phase 5 pointer line now names the three forms in passing,
  trimmed to land exactly at the registry's 9470-token body budget (`tools/build.py --footprint`) rather than raising the ceiling for it.
- **Case 44 gained a seventh assert** (`evals/test-cases.md`), under T1:
  the checkpoint must pick State-then-proceed for a ticket-driven pipeline
  agent and never phrase itself as a Hold that isn't happening.
- **Graded against the retained T1 transcript from 1.5.4's execution, not
  a new blind build** — the doctrine changed, the artifact didn't, and the
  same evidence answers the new assert directly. Pass, recorded in
  `evals/RESULTS.md`. Case 44 now stands at 7/7.
- `evals/trigger-evals.md` re-anchored, provenance-only.

## [1.5.4] - 2026-09-10

Run-record patch. No `SKILL.md` rule, `frameworks.md` content, phase, entry
point, or `description` moved; the routing surface is untouched.

- **Case 44 executed, T1 and T2, 6/6** (`evals/RESULTS.md`) — a harder split
  than any prior execution here: T1 and T2 were each built by an
  independent agent given only `SKILL.md`, `frameworks.md`, and the bare
  request, with no visibility into the case or its asserts; grading against
  the six asserts happened afterward, cold, against the two transcripts.
  1.5.3 shipped it `(authored, not run)`; that is now closed.
- **One doctrine finding, filed not patched.** `frameworks.md`'s
  Confirm-shared-understanding row says the built agent "holds for a
  correction (or proceeds under a named assumption)". The blind T1 build
  did neither by name: it stated its read of the ticket and proceeded
  immediately, reasoning (correctly, for an unattended pipeline agent with
  no synchronous party to hold for) that the checkpoint's job is visibility,
  not permission. That is a third, legitimate form the doctrine sentence
  doesn't name, and no assert in Case 44 currently distinguishes it from
  the other two — the case tests that the checkpoint exists, not which form
  it takes, the same shape as the grill `⚑` gap filed at 1.5.1.
- `evals/test-cases.md` and `evals/trigger-evals.md` re-anchored to 1.5.4,
  provenance-only.

## [1.5.3] - 2026-09-10

Pays the debt 1.5.2 filed. No phase, entry point, or `description` moved.

- **Case 44** (`evals/test-cases.md`): a two-turn case asserting the
  Confirm-shared-understanding checkpoint in both directions — present,
  one or two lines, distinct from act-vs-ask, for a multi-file refactor
  build; correctly absent for a single-tool, fully-specified log-append
  build. Not executed this pass (authored, not run — `evals/RESULTS.md`
  carries no row for it).
- `evals/test-cases.md` and `evals/trigger-evals.md` re-anchored to
  1.5.3; both provenance-only, since the `description` did not move.

## [1.5.2] - 2026-09-10

Adopted a convergence: four independent lineages (ase-code-edit's pre-build
"grill", addyosmani/agent-skills' interview mode, mattpocock/skills' grilling
primitive, Superpowers' brainstorming skill) landed on the same fix for the
same failure — an implementation agent guesses intent and gets corrected
after the fact. The fix belongs in the doctrine this skill writes into
*built* prompts, not as an imported framework: four builders converging
independently is a signal the pattern is right, not a reason to import any
one of their frameworks for it.

- **New Agent/System component: Confirm shared understanding**
  (`frameworks.md`). Sits beside Act vs. ask: before a non-trivial or
  hard-to-undo change, the built agent states its plan or read of the task
  in one or two lines and holds for a correction (or proceeds under a named
  assumption); a single-file fix or fully-specified task skips it. Distinct
  from Phase 4 and `grill.md`, both of which clarify the request *this
  skill* is building from — this is a rule written into the artifact so the
  agent it drives does the same before it acts.
- `SKILL.md` Phase 5's Agentic/system-prompt line now names the component
  alongside act-vs-ask, tool discipline, parallel calls, stop conditions,
  and the output contract, so it surfaces without opening `frameworks.md`.
- No phase, entry point, or `description` moved; routing is untouched.
  `evals/` re-anchored provenance-only — none of the 43 cases exercise a
  full Agent/System build, so none moved. **A case is owed**, not shipped
  here: a built coding/agent prompt should assert the checkpoint appears
  before a non-trivial change and is correctly absent from a single-file,
  fully-specified task.

## [1.5.1] - 2026-09-09

Run-record patch. No rule, phase, entry point, reference or `description`
moved; the routing surface is untouched and no re-judge is owed.

- **Case 43 executed**, T1 and T2, **9 / 9** - traced against the written
  procedure, disclosed as traced rather than as a live product-surface run.
  1.5.0 shipped it `(authored, not run)`; that is now closed.
- **One doctrine gap found and filed, not patched.** `grill.md` step 4 requires
  the first offered answer to be the one the request already implies, marked
  `⚑`. When the request implies nothing - and for two of the five traced
  aspects it implied nothing at all - the procedure does not say what `⚑`
  does, and the readings available differ materially: marking a house default
  would present an invented choice as the user's own, which is the exact
  failure the convention exists to prevent. No assert covers the case, which
  is itself the finding: the suite tests that `⚑` is applied, never what
  happens when it cannot be.
- **Why this is a version at all.** Editing `evals/` changes a shipped file, and
  a shipped file that moves at the same member version is the bookkeeping debt
  skillwright 1.3.4 was cut to pay - three passes deep by then. The run record
  itself correctly touched no version, because a record must never edit the
  thing it grades; the bump is paid here instead, in the same pass rather than
  one later, which is the whole point of having learned it.

## [1.5.0] — 2026-09-09

**Added — Entry — Grill.** A relentless interview that runs before the build,
until no essential freedom of choice is left for it to guess at. Ported from the
`ase-task-grill` pattern (rse/ase, Apache-2.0) and re-aimed from code plans at
prompt and task requests; the framework it ships in was not adopted, only the
pattern. Credit in `SOURCES.md`.

- **`references/grill.md`** (new) — four focus areas outside-in with severity
  fixed by area (JOB/CONTRACT MUST · STRUCTURE SHOULD · WORDING MAY), six
  indicators for finding questions, and the round procedure: sort by area then
  dependency, truncate at 10, ask one at a time with two to four grounded
  answers (the implied one marked `⚑`) plus a `SKIP GRILLING` exit; further
  rounds restart from the updated request. Explicitly **outside the standard
  load budget** — it loads on the grill and nowhere else.
- **SKILL.md — Entry — Grill** (new section) with both shapes: inside a build it
  replaces Phase 4 and resumes at Phase 5 (`Clarify (grilled — N aspects, N
  rounds)`, footer `grilled: N aspects`); standalone it reports settled
  decisions and any open MUST area and produces no prompt. The agentwright seam
  is stated — grilling a running agent's guardrails is not this entry.
- **SKILL.md — Phase 4** gained the escalation paragraph, with the restraint
  that matters: never escalate unasked, because interrogating a clear request is
  padding.
- **Description** gained `promptwright grill` in the subcommand parenthetical,
  and the clause was then scoped to `interview a **prompt request**` — see the
  re-judge below, which is what motivated the scoping. 918 → 1002 chars by
  `build.py`'s measure, under the 1024 ceiling. **The routing surface moved**,
  so a full cold re-judge of the trigger suite was owed.
  - **Correction, same pass:** this line first read `918 → 1002` for a text that
    measured **995**. The figure was wrong when written and is stated here
    rather than quietly left correct by the later +7. The seven characters the
    scoping cost are what closed the gap.
  - **Cost, stated:** at 1002 the member now trips `build.py`'s ceiling-riding
    advisory (≥ 1000, zero edit headroom). Paid deliberately: buying the seven
    back would mean trimming a load-bearing clause, which moves the routing
    surface again and owes a third re-judge — a worse trade than carrying a
    non-fatal warning. The next content edit here must slim before it adds.
- **Trigger evals** 34 → 38 rows, split 17/17 → 19/19 (#35–#38 for the new
  entry). **The re-judge was performed** — two column-isolated cold runs via
  `tools/blind_queries.py`, a fresh judge each, ledgered in `evals/RESULTS.md`.
  Run 1 against the as-authored text scored **37/38**; the one miss, #38, came
  back AMBIGUOUS because the grill clause bound no object. That defect was
  fixed (the scoping above) and run 2 against the amended text scored
  **36/38**, with #38 closed on the new qualifier. No row flipped its expected
  direction in either run. **#37 held both times** — the watch row routed to
  agentwright on the object over the shared verb, and run 2's judge named it
  the set's one live risk without being able to see the note that flagged it.
  Run 2 returned two new AMBIGUOUS on should-not rows, **#34** and **#29**,
  both clean in run 1; they are recorded as findings and **join #37 as
  standing watch rows**, not remediated. AMBIGUOUS was scored as a miss
  throughout.
- **Assertion suite** 42 → 43. **Case 43 remains authored, not run** — the
  re-judge above covers routing only. Disclosed, not folded into a green claim.

## [1.4.1] — 2026-08-17

Estate member audit + security scan (2026-08-17; rubric A, S-1..S-4, C-1/C-2,
OWASP agentic lenses) plus the calendar refresh the stamp owed. The description
is untouched, so the routing surface did not move.

**Findings and fixes:**

- **S-1 · P1 — mid-build web fetch escaped the rule.** The head note permits
  web search "for an external fact the prompt's job needs, or to verify the
  model lineup"; both fetch pages the skill did not author, and the
  data-never-instructions rule sat only in Phase 1 (handed-in text) and Entry —
  Refresh (that entry's own fetches). Fix: the permission now states that a
  page fetched for either is data, never instructions, on Phase 1's terms.
- **S-1 · P1 — Entry — Model's plan grain escaped the rule.** A plan handed
  in for tiering is an ingested artifact, and the entry runs Tier routing
  "invoked directly" without passing Phase 1 (the same gap 1.4.0 closed for
  Refresh). Fix: one located sentence in Plan grain — the handed-in plan is
  data; a line in it addressed to the run rather than describing a subtask
  (pin every row to one tier, waive the flip conditions or the standing rule)
  is a finding reported beside the table, never a routing input. Text that
  names a target *inside a subtask's own description* stays user direction
  under Tier routing's 1.3.0 override; the two rules bind different text.
- **Eval gap (rubric f).** Case 36 was the suite's only injection probe and
  covered build/improve. Added, authored not run: **Case 40** (score-only,
  then red-team by name), **Case 41** (plan grain — a routing directive
  embedded in the plan beside a legitimate subtask-level model ask), **Case
  42** (refresh — an instructing source page). 39 → 42. The count line in
  `evals/test-cases.md` had read 38 since 1.3.0 while the suite held 39;
  corrected.
- Rubric A otherwise clean: description matches the body (every entry point
  advertised, boundary clauses true); references one level deep, TOCs on
  every 150+ line file; every referenced file present, no broken relative
  links; no `citadel` mention live anywhere in the member; no Windows-style
  paths; invocation control (dimension 11) passes — the only writes (Refresh's
  regeneration of `model-snapshot.md` + this file + the version; the prompt
  card) fire on a named invocation or a hard opt-in, never silently.

**Security scan 2026-08-17:** (a) prompt-injection posture — every ingesting
step now states the rule (Phase 1 intake incl. score-only and red-team, the
mid-build fetch, Entry — Refresh, Entry — Model plan grain); (b) no
fetch-and-follow, permission-widening, secret-echo or guard-bypass instruction
in SKILL.md or any reference; (c) tool scoping — web search and native file
tools only, no shell, degradation stated (no search → no restamp; no HTML
surface → no card; no option tool → plain-text selection); (d) hidden-text
scan clean (2026-08-17); (e) output handling — Refresh writes one named file
plus the CHANGELOG line and version, the card is opt-in only; (f) one
injection probe per ingesting entry (Cases 36, 40, 41, 42). S-2 none, S-3
none, S-4 none (the card template is single-file, offline, no external host).

**Refresh — `model-snapshot.md` restamped Last verified 2026-08-17.** All five
vendor model docs fetched live (Anthropic models overview + pricing + effort
pages; OpenAI models, model pages and pricing; Gemini models + pricing;
docs.x.ai models; api-docs.deepseek.com pricing), OpenRouter registry as
cross-check; LiteLLM not fetched this pass. Changes: Claude A-tier Opus 4.8 →
**Opus 5** (4.8 now legacy, same price); Sonnet 5's $2/$10 is now standard
(the 2026-09-01 rise cancelled); 128K output on Fable 5, Opus 5 and Sonnet 5;
`effort` levels are low/medium/high/xhigh/max (no `minimal`/`none`; xhigh and
max coverage restated; Haiku 4.5 has no effort control); Opus 4.7+ tokenizer
note added. OpenAI: 5.4 nano/mini no longer undercut Luna — dropped from the C
slot; long-context premium (>272K) attributed to the whole 5.x line; cache
1.25×/0.1×/1,024-token minimum/30-minute life verified. Gemini B-tier 3.6
Flash → **3.7 Flash** (Aug 2026, GA); 3.6/3.7 Flash promo price to
2026-12-31 recorded; 3.5 Pro still absent (Aug 13 press confirms delay); 3.1
Pro corrected to its `-preview` id. Grok A-tier 4.5 → **4.6** (2026-08-12,
500K); 4.1 Fast is gone from xAI's model list — removed from the C slot,
which now reads Grok 4.3 (the 4.20 non-reasoning variant for latency); the
"2M context" quirk rewritten around 4.3's 1M. DeepSeek: the API now lists
only V4 Pro (0813) and V4-Flash (0731), both 1M / 384K, thinking on by
default — the bare "V4" B slot → V4-Flash; the expired promo note dropped for
the off-peak half-rate note. Not re-verified and retired with the models they
described rather than carried: the 3.6-vs-3.5 Flash "~17% fewer output
tokens" figure and the Flash-Lite "~350 tok/s" figure. Left as previously
stated (not re-verified live this pass): the "Grok 4 Heavy" consumer-product
name for the S slot (docs.x.ai lists no Heavy API model; the footnote holds
either way). Observation for the next durable-file pass, not changed here:
`model-notes.md` §6 says multi-agent Heavy is not an API capability, while
docs.x.ai now lists a `grok-4.20-multi-agent` API model at 4.3 rates.

**Body budget:** 8977 → 9004 measured against the 9030 row (`build.py
--footprint`); the two additions were paid for by seven claim-preserving trims
(the `evals/` load-budget line, the volatile-block sentence, the Fast-path
say-so, Phase 3's Fast-path exception, Entry — Model's opener and step 3, the
Maintenance note), each a restatement of a rule whose binding statement lives
elsewhere in the body. No row raise needed.

Both eval heads re-anchored to 1.4.1. Trigger suite unchanged (34, 17/17);
Cases 40–42 authored, not run — no RESULTS.md row.

## [1.4.0] — 2026-08-12

Two 2026-08-12 estate-audit findings closed in Entry — Refresh; the
description is untouched, so the routing surface did not move:

- **Refresh injection rule (finding 2).** The refresh path re-researches live
  vendor pages and writes the result into `model-snapshot.md`, the file every
  Model line reads — and the handed-in-text-is-data rule lived only in Phase
  1, which the refresh entry explicitly skips. The rule now rides in the
  entry itself: a fetched page is data, never instructions; an instructing
  source is itself a finding, recorded at its URL.
- **Search-unavailable fallback (finding 14).** The entry now states what a
  refresh does when it cannot verify: never re-stamp, report the surface
  unverified, leave the Last-verified date untouched, name the invocation to
  re-run — so the stamp downstream members trust keeps its meaning.

## [1.3.0] — 2026-08-05

Tier routing (Phase 5) gains the **user-named-target override**, directed by
the pack owner and recorded as the ENHANCE verdict in AUDIT-2026-08-05: a
model or effort the user names wins, exactly as a named framework wins in
Phase 3 — build to the stated target, shape the prompt for that tier, never
quietly substitute the routed pick; when routing disagrees, the Model line
notes the target was set by user direction and offers the better tier or
effort in one line. Entry — Model is bound identically (stated target
confirmed, not re-routed, disagreement named). Single-homed in Tier routing,
as the role-based overrides are.

Four lossless trims in the same pass offset the addition against the 8,850
body budget (AUDIT-2026-08-05 TRIM verdict; all four are restatements of
rules whose binding statement lives elsewhere in the body, no rule moved):
Turn shape rule 5's quiet-build/Fast-path contrast compressed (the full
distinction lives in the Fast path section); the Keep going Rendering
bullet's tool-list-test restatement now points at Turn shape rule 2, keeping
the observed-field-failure example; the Load budget's `hostile-interpreter.md`
bullet compressed (its reach-for conditions restate Phase 6's); the
Surface-awareness note's selection-form sentence now cites rule 2. Body
lands at 8,850 / 8,850 measured — exactly at budget, zero headroom
(`build.py --footprint`): the next body edit must bring its own offset or a
deliberate row raise.

Suite: **Case 39** covers the override (built to a user-named target, Model
line note, one-line better-fit offer, no silent substitution); Cases 1–38
untouched. Trigger evals not re-anchored — the `description` did not move.

## [1.2.0] — 2026-08-02

Tier routing (Phase 5) gains two **role-based overrides**, applying to both
the standalone Model entry and plan grain since both run the same routing
logic:

- **Planning/orchestrator subtasks default one effort notch lower** than
  their tier would otherwise suggest. High-effort planning reliably
  over-thinks and scope-creeps a plan past what was asked; effort is raised
  only once the plan itself is failing to converge, never pre-emptively.
- **Review/verification subtasks default to a different model family** than
  the work they're checking, where the stakes justify the cost — not a
  resampled instance of the same model, which tends to miss what that model
  already rationalized away.

Closes a gap identified in a skillwright niche-verdict + gap scan run against
a candidate 10th foundation member (an orchestration skill). The scan found
plan grain (1.1.0) already covers the candidate's stated job end-to-end
except for these two rules, so a new pack member wasn't justified — this is
the "smaller fix" half of that verdict, landing directly in Tier routing
rather than a new file.

Evals: **Case 38** added (`evals/test-cases.md`) — a four-role project
exercising both overrides in one table. Cases 1–37 untouched: the override is
additive to existing Tier routing logic, and no prior case's plan depended on
a planning or review role's specific effort/model. Trigger evals not
re-anchored — the `description` field did not move.

## [1.1.1] — 2026-08-01

Prose/register pass over this skill's own files (SKILL.md, README.md,
`references/hostile-interpreter.md`): dash-chained run-on sentences split
into plain sentences, the README's crammed differentiator sentence converted
to a short bulleted list, and the hostile-read catalog's four failure-shape
entries trimmed to keep only the added instances, pointing back to SKILL.md
Phase 6 for the definition instead of re-stating it.

Also fixed: `references/model-snapshot.md`'s tier-map footnotes skipped ²
entirely (¹, then ³, then ⁴, with no ² anywhere in the file) — a table-
formatting defect, not a claim change. Renumbered sequentially (¹ ² ³) since
no source in the pack recorded what a footnote 2 would have claimed; the
facts each footnote carries are unchanged, only their markers moved.

No rule, gate, count, or entry point moved. No eval re-anchor is owed.

## [1.1.0] — 2026-08-01

Entry — Model gains **plan grain**: handed a task list or project plan with a
targets ask, steps 1–3 run per subtask and delivery becomes one target table —
`subtask · tier + model · effort/depth · run inline or as a subagent · one-line
why` — in place of the single-recommendation line. Two contracts ride with
every table: the **living table** (a subtask created mid-session gets a row
through the same steps *before* dispatch, so emergent work adheres to the same
tier logic as the plan it joins) and the **standing rule** (one paste-ready
rule line emitted beneath the table so the contract survives the session;
layer placement stays rigwright's, named not made). Decomposition stays the
caller's — promptwright targets the subtasks it is handed and never re-plans
the project.

- `description` gains the plan clause ("a prompt, a live task, or each subtask
  of a plan"), the mid-session binding, and the target-table mention in the
  `promptwright model` parenthetical.
- **Body budget raised 8500 → 8800** in skillwright's registry: the plan-grain
  delivery shape and both contracts are decision rules, body-resident like the
  rest of Entry — Model — the content reason this raise owes per the
  registry's own budget notes.
- Trigger rows #31–#34 (two should, two shouldn't — the rigwright standing-
  config boundary and the no-targets decomposition boundary) and assertion
  Case 37 (target table + living table + standing rule, two turns) added;
  both suites re-anchored. All 34 trigger rows judged cold against the new
  description this pass; Case 37 is authored, not executed — see
  `evals/RESULTS.md`.

## [1.0.0] — 2026-07-31

Baseline release. The 1.0 feature set:

- Seven-phase build pipeline — Intake → Analyze & score → Pick structure →
  Clarify → Build → Re-score & self-check → Output — with a five-dimension
  1–10 scoring rubric (clarity, specificity, context, completeness,
  structure) delivered as a before→after delta.
- Framework menu with named-origin doctrine: CO-STAR, RISEN, TIDD-EC, BAB,
  RTF/APE, chain-of-thought, and agent/system shapes; a user-named framework
  always wins and is never silently substituted.
- Fast path: a fixed five-condition gate collapsing Phases 1–6 into one trace
  line for small RTF/APE-shape prompts, with published exit conditions.
- Hostile read: a bad-faith-literal pass over every binding line — four
  failure shapes, each with a named repair — plus collision and
  instruction-boundary cross-checks; the knowledge-vacuum check flags factual
  tasks lacking reference material before scoring.
- Model-tier routing (S/A/B/C: frontier / flagship / balanced / fast) feeding
  a mandatory Model line on every delivered prompt, and the standalone
  `promptwright model` entry for live-task tier picks without a build.
- Output contract: TL;DR, Model line, Score, Structure, an optional
  self-contained HTML prompt card, and the fixed four-option "Keep going"
  close.
- One calendar surface: `model-snapshot.md` (60-day), re-verified by
  `promptwright refresh`, with tier-name fallback when the stamp is stale.
