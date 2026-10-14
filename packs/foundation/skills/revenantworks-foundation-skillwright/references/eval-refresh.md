# Eval Refresh — Provenance, Re-anchoring, and Recording Runs

Read on an evals refresh, and wherever a suite's provenance line or a `RESULTS.md` record is written or checked. The every-run core is `eval-doctrine.md`; a refresh that regenerates or adds a case also opens `suite-standards.md`.

## Provenance and refresh

- Every suite opens with one line: target name · target version · derivation date.
- A refresh diffs the target against that line: regenerate touched cases, add rows for new entry points, retire dead rows by name, re-run count integrity, update the provenance line.
- **"Touches" is not limited to the changed entry's own row.** A rename or behavior change also touches any case filed under a *different* entry whose Input or Assert merely **references** the changed name, flag, or vocabulary — not only the case that is that entry. Verbatim is reserved for cases with no reference, direct or incidental, to what changed; a case that survives a rename still quoting the old vocabulary because its row belongs to some other entry is a stale suite the "leave untouched cases verbatim" rule was never meant to protect.

## Provenance discipline

When the target's version bumps, the suite's provenance line updates **in the same commit**: keep the derivation history, append "re-anchored to vX.Y.Z, YYYY-MM-DD". A suite whose head names an older target version with no dated re-anchor is a finding — the exact staleness class this skill audits others for, and the pack's build gate warns on it. Recording a run: a dated `evals/RESULTS.md` section (date · target version · runner · a **run with** line (runner, flags, runs, judge model) · per-row verdicts · pass rate; irreducible-judgment rows tagged `JUDGE`) — a protocol, never an executor.

**Write the provenance history as ONE continuous paragraph** — no hard newlines between versions, or newest re-anchor first (added 2026-09-11, task-observer observation #0025). A freshness gate typically reads a fixed head window (N lines) of each eval file. A history kept as one paragraph is still "line 3" however long it grows; a history authored with one physical line per bump works by coincidence until the newest note's own line number crosses the window, and then the build fails with a message about a missing version on a file that plainly names it. Two consequences: the layout is an authoring rule, not a style preference; and a provenance-freshness failure has **two** candidate causes — the version is genuinely missing, or the line sits past the window — so check the line number before re-anchoring something already anchored. The general form: a validator with a fixed read-window encodes an assumption about layout, not only content, and that assumption stays invisible until a file written in a different but equally valid convention crosses it.

**Re-anchoring a suite is not running it.** Updating the version line proves the file was opened. A suite left "authored, not run" has tested nothing, and it is exactly where a drift between a target's documented behaviour and its routing text survives version bumps undetected — one skill's description omitted a write-op verb its body documented, through two bumps, because no cold judge had ever read the two against each other (#0021). Carry "authored, not run" as a finding, never a footnote.
