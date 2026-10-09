# Slim Doctrine — Waste Taxonomy, Technique Ladder, Measuring *(durable doctrine)*

The pack's one full reference for cutting what an LLM-facing artifact costs without changing what it does (moved 2026-10-08 from the retired tokenwright). Read on every `skillwright slim`. promptwright's and rigwright's own `slim` entries state their rules in their own files and may name this one as optional, fuller reading — the foundation pack is standalone, so no member needs it installed. W-codes name the waste; the ladder orders the fixes; the contract names what never gets cut; the formats keep reports uniform.

## Contents

- Who slims what
- W-codes — the waste taxonomy
- Technique ladder — safety-ordered
- Preservation contract
- The legibility floor
- Report formats (slim report · audit catalog · budget sheet)
- Measuring — method, net cost, honesty
- Description caps
- Runtime and output tokens — out of scope

## Who slims what

Each artifact is slimmed by the member that owns it: a skill package (SKILL.md, references) by `skillwright slim`; a prompt, system prompt or agent instructions by `promptwright slim`; CLAUDE.md, Project instructions and other standing config by `rigwright slim`. A slim that would move behavior is not a slim: it is that owner's Audit or Build. Human-facing message length is commscribe's.

---

## W-codes — the waste taxonomy

| Code | Waste | Detection cue | Fix (ladder rung) |
|---|---|---|---|
| W1 | Duplication | The same rule or fact stated twice, anywhere in the set | Dedupe — one owner per rule (2) |
| W2 | Filler & hedging | Throat-clearing, pleasantries, "it's worth noting", restated intent | Tighten (3) |
| W3 | Over-specification | Instructions restating what the model does by default | De-specify, with disclosure (4) |
| W4 | Format overhead | Tables, bold, and headers where structure isn't doing work | Deformat (5) |
| W5 | Example overrun | Examples past the contrastive minimum, or redundant variants | Prune (6) |
| W6 | Inline-what-should-load-on-demand | Heavy material in an always-on or trigger surface that a reference could carry | Offload (7) |
| W7 | Dead weight | Stale, superseded, or unreachable content; commented-out corpses | Cut (1) |
| W8 | Cross-file boilerplate | The same preamble or block repeated across a set | Dedupe to one owner + pointer (2) |
| W9 | Cache-busting placement | Volatile content interleaved into a stable prefix; unstable ordering | Reorder stable-first; isolate volatiles in stamped files (8) |
| W10 | Resident-when-conditional | Always-on cost that only some sessions use (schemas, modes, personas) | Move behind a trigger-loaded surface (7) |

Audit findings cite W-codes; severity (P0/P1/P2) follows the score-only rule below: the code says *what kind* of waste, the P-level says *how much it matters here*.

## Technique ladder — safety-ordered

Rungs apply in order on every slim; each rung logs what it removed. Rungs 1–8 are lossless — the artifact's stated behavior is unchanged. Rung 9 is lossy and always gates.

1. **Cut dead weight** (W7) — stale facts, superseded sections, unreachable branches.
2. **Dedupe** (W1, W8) — one owner per rule; second statements become nothing, not pointers, unless files genuinely load separately.
3. **Tighten** (W2) — meaning-preserving compression: filler out, hedges out, one verb where three stood. The constraint's shortest faithful wording.
4. **De-specify** (W3) — remove instructions that restate model defaults. Lossless in behavior, visible in text — every removed default goes on a disclosure line so the user can veto.
5. **Deformat** (W4) — tables to terse lines where alignment isn't information; emphasis diet; "some things include x, y, z" over three bullets. Structure stays wherever it *is* the information.
6. **Prune examples** (W5) — down to the contrastive minimum, usually one good + one boundary case. Gates like a lossy cut when it would drop below two, or when any pruned example anchors an eval.
7. **Offload** (W6, W10) — progressive disclosure: heavy or conditional material to references loaded on demand, one level deep; the body keeps a one-line pointer. Same content, cheaper residence.
8. **Reorder for cache** (W9) — stable → volatile; volatile facts into stamped single-update-surface files; breakpoint-friendly boundaries. Same content, cheaper reads.
9. **Semantic compression** *(lossy — always gates)* — summarizing, dropping behaviors, collapsing constraints. Each candidate is named with the behavior it drops and the tokens it buys; "just slim it" never pre-approves this rung.

## Preservation contract

Collected before any cut; every item survives the slim or appears as a gated lossy finding — never a silent casualty:

- Safety rules and refusal boundaries
- Output contracts and schemas the artifact promises
- Routing and trigger text (names, descriptions, invocation keywords)
- License, legal, copyright, and ownership lines
- Stamped volatile facts and their stamps
- Eval-anchored behaviors — anything the artifact's suite asserts
- Dependency declarations and absence behaviors

The slim report lists the contract explicitly, so "preserved" is checkable, not claimed.

## The legibility floor

The floor is a procedure, not a judgment call: past rung 5, re-read the artifact cold, and if any step now requires guessing, back up one rung. What the trade actually costs is re-prompting — the tokens a caveman-compressed instruction saves come back as clarifying turns, usually with interest.

**Equivalence probe** (every slim, after the ladder pass): one blind reader answers the artifact's trigger or eval questions from the old text and again from the new text, without being told which is which. Where the surface can start a fresh-context reader (a subagent), use one; otherwise answer each question from the new text alone before looking at the old answers. Any divergence becomes a lossy finding and gates like rung 9, even when the rung that caused it was meant to be lossless. The slim report's `Preserved` line names the probe and its result.

## Report formats

**Resolve the load graph first** (every audit inventory and budget sheet): expand each `@import` and count the imported file where it loads; list every auto-loaded surface in scope (the CLAUDE.md chain, the memory index, the skill listing, MCP tool schemas); then diff them for cross-file duplication (W8). An always-on total that counts only the named file is a defect.

**Slim report** — six lines before the artifact:
`Before → After` (both with method) · `Δ tokens / Δ%` · `Rungs applied` (numbered, with per-rung recovery where notable) · `Preserved` (the contract, listed) · `Disclosures` (defaults removed, examples pruned — or "none") · `Cache impact` (role, re-write cost vs read savings — or "n/a"). Then the rewritten artifact, whole, never a diff the user must apply.

**Audit catalog** — inventory (2–3 lines), then one row per finding:
`ID · W-code · where · finding · est. recoverable · P0/P1/P2`, closing with the efficiency score and the one-line verdict (LEAN / TRIMMABLE ~n% / BLOATED ~n%). No rewritten text anywhere in an audit. **Machine-readable tail (optional):** when asked, or when another tool will read the audit, add one line per finding after the verdict, in catalog order and with no prose: `SL|<ID>|<W-code>|<path>:<line>|<est. tokens>|<P0/P1/P2>`. Two audits of one artifact then diff line by line.

**Budget sheet** — the tier table (always-loaded / trigger-loaded / on-demand; per artifact: current, ceiling, headroom), the set-level always-on total against the tokens-per-task target, load order, and the cache plan. Ceilings cite the platform reference points (Measuring, below) and the set's real turn count.

**Score-only audit** (`slim audit`, or "score the waste, don't change it"): the catalog above, then an efficiency score 1–10 (9–10 lean, cuts would trade capability · 7–8 minor trim · 4–6 real waste, worth a slim · 1–3 bloat is impairing the artifact) and the verdict. **P0** — waste that breaks function (a description past a cap it is bound by, an always-on surface starving the task, cache-busting placement in a cached prefix) · **P1** — clear recoverable waste · **P2** — polish. Applying any row is a slim the user asks for.

## Measuring — method, net cost, honesty

**Method ladder** — highest available wins; the report names which was used.

1. **Exact** — Anthropic's `count_tokens` endpoint against the model that will load the artifact (`exact (count_tokens, <model-id>)`), or a real tokenizer on the surface (`exact (<tool>)`). An exact count is exact for the named tokenizer only.
2. **Estimate** — character arithmetic, with the character count itself taken by a named method (a runtime's length function, a shell count): `estimate (±15%, chars via <tool>)`. Name the target model first: newer tokenizers produce about 30% more tokens for the same text than older ones (Anthropic token-counting docs, read 2026-09-26), so a flat ÷4 can read low. Verify the ratio on that page before quoting it.
3. **Never** — word counts presented as tokens, a count with no method, or an eyeballed or remembered character count dressed as an estimate. With no counting method on the surface, report `unmeasured` and ask for a pasted count.

**Net-cost accounting.**

- **Always-on text bills per turn.** Cost = size × turns in scope. A rule that adds text states this arithmetic; a 300-token rule saving 20 tokens a turn is a loss.
- **Tokens-per-task is the target**, not tokens-per-request: re-prompts a too-aggressive cut causes count against it.
- **Churn, role-qualified.** An always-on artifact is slimmed when `tokens recovered per turn × typical turns in scope` beats the one-time diff and cache-rewrite cost (about the artifact's own size); a one-shot or on-demand artifact under ~500 tokens with under ~10% recoverable is left alone.
- **A cached prefix** is reordered stable-first only when it clears the model's minimum cacheable length (check the prompt-caching docs live); below it no reorder pays and no saving is projected.
- **Count what loads unasked**: hooks that re-fire on compaction, a claude.ai-synced twin of a local skill. A per-session saving is stated against the measured session floor (`/context`), never against zero.

**Honesty rules.** Before → after on every slim, counted with the same tokenizer and model; the method on every count; the ± band on every estimate; a projection (per 1,000 turns) labelled projected, never measured.

## Description caps

Characters, never tokens, counted with a named tool. Three limits bind and none is reported as another: the **platform listing cap** (Claude Code truncates `description` + `when_to_use` combined at 1,536 characters by default), the **listing budget** (the whole skill listing is held to a fraction of the context window and can shorten or drop an entry below the cap), and the **house ceiling** (a repo's own build gate, read from its config — this repo's `tools/build.py` fails a description above 1,024 characters). Each finding names which limit, the measured count, the overage and the unit.

## Runtime and output tokens — out of scope

This doctrine slims the artifacts that feed a session, at build time. Cutting tokens at runtime — terser replies, compressed tool output, a live session's context — is served by external tools such as caveman (an output-style compressor) and rtk (a command-output compressor). Name them as optional; never require one. Placing such a tool as a hook or output style is standing config, so rigwright places it, and its install is vetted by trustwarden when the warden pack is present.
