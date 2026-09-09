# Grill — relentless interview before the build

Loaded only on `promptwright grill`, "grill me", "stress-test this before you build it",
or when Phase 4 is escalated to a grill by name. Never a standard-build load.

The grill exists because a question round is not an interview. Phase 4 asks 1–3 questions
and takes "just build it" for an answer — right for a request that is nearly clear. A grill
is the opposite trade: it keeps asking until no **essential freedom of choice** is left for
the build to guess at. Use it when the cost of building the wrong thing exceeds the cost of
the interview.

Ported from the `ase-task-grill` pattern (rse/ase, Apache-2.0) and re-aimed from code plans
at prompt and task requests. Credit in `SOURCES.md`.

## Focus areas — outside-in, descending importance

| # | Area | What it covers | Severity | Question form |
|---|---|---|---|---|
| 1 | **JOB** | What the prompt must make happen: the deliverable, who consumes it, what "done" means | MUST | `Shall…?` |
| 2 | **CONTRACT** | Externally observable behavior: output shape, format, length, refusal and edge-case behavior, what the caller depends on | MUST | `Shall…?` |
| 3 | **STRUCTURE** | Framework, context placement, tool and retrieval wiring, chaining, model tier | SHOULD | `Should…?` |
| 4 | **WORDING** | Phrasing, tone, ordering, and every other inner detail | MAY | `May…?` |

Severity is read off the area, not judged per question. A MUST area is not left open at the
end of a round; a MAY area may be closed with an assumption stated in the build.

## Indicators — how a question gets found

- **Fuzzy language** — a vague or overloaded term where a precise one exists ("good", "clean", "handle").
- **Conflicting terminology** — a term that collides with the target domain's or the existing prompt's own vocabulary.
- **Conflicting source** — the request states how something currently works; check the actual prompt, file, or data and see whether it agrees.
- **Non-concrete scenarios** — invent a realistic input that probes the boundary and force a decision on it, rather than discussing the relationship in the abstract.
- **Unspecified structure** — more than one decent framework fits the job and none was named.
- **Unspecified dependencies** — the job normally needs tools, retrieval, or a particular tier, and none was mentioned.

## Procedure

1. **Announce the round.** `── Grilling ──`, or `── Grilling round M/N ──` when more than one was asked for.
2. **Find the aspects.** Each gets a one- or two-word identifier (`Audience`, `Refusal-Path`) and one very brief, precise question in its area's form. Encode every literal — paths, identifiers, flags, config keys, values — in backticks.
3. **Sort.** Primarily by focus area (all JOB, then CONTRACT, then STRUCTURE, then WORDING); secondarily by dependency, so a question is asked after the ones it depends on. Renumber from 1 each round. **Truncate at 10 questions.**
4. **Ask one at a time.** For each, offer between two and four grounded answers — the first being what the current request or draft already implies, marked `⚑` — each with a 1–3 word label and a description of at most 10 words. Ground the alternatives in the codebase, the existing prompt, or real practice; never invent a plausible-sounding option to pad the list. Render the choice per Turn shape rule 2 (the tool-list test): a tappable single-select where the surface has one, the plain-text fallback otherwise. Always include `SKIP GRILLING` as the last option.
5. **Honor the exits.** `SKIP GRILLING` ends the questions, folds in the answers gathered so far, and drops any remaining rounds. A cancel leaves the request untouched and stops — nothing is built from a half-grill without saying so.
6. **Fold in.** Update the working request from the round's answers. Each further round restarts from the *updated* request and forgets the previous round's questions, so a second round finds what the first round's answers newly exposed.

## After the grill

The build resumes at **Phase 5** — the grill replaces Phase 4, it does not add a phase, and
the ladder still shows `── Phase 4 / 7 — Clarify (grilled — N aspects, N rounds) ──`.
Phase 7's footer carries `grilled: N aspects` so a prompt's provenance is visible later.

A grill that ends with a MUST area still open is reported as such, never quietly built over.

## Restraint

Do not grill a request that is already unambiguous — say it is clear, name the one or two
assumptions you would make, and offer the ordinary build. A grill over a settled request is
the interview equivalent of padding, and it burns the user's patience for the times it matters.
