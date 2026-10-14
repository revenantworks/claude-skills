# Audit evidence and controls

Read on an audit only, and only when the target holds a hook, a controls file or fixture, a pattern list that gates a hook, or a usage figure that a keep-or-remove call rests on, and when the enforceability dimension backtests a prose rule against session history. A plain `CLAUDE.md` or Project-block audit never opens this file. These rules decide whether the evidence behind a finding can be believed; the five dimensions and the user-install boundary stay in SKILL.md.

## Contents

- Usage evidence: name the instrument, then use three buckets (#0024, #0039)
- A pattern list that gates a hook (#0016)
- An `InstructionsLoaded` hook does not see an `AGENTS.md` loaded by setting
- A stateful hook's controls are side-effect-free (#0047)
- A fixture is literal in its shape, never in its paths (#0063)
- A fixture that depends on live state declares it (#0062)
- State the extent you parsed (#0041)
- A check you just wrote is an untested claim (#0042)
- A step that makes a file is verified by the file (#0162)
- Rule backtest against session history

---

## Usage evidence

**Usage evidence — name the instrument, then use three buckets** (observations #0024 and #0039). Where a keep/remove call rests on how often something was used:

- **Say which counter was read and what it counts.** A per-skill invocation counter and a per-plugin activation counter answer different questions over the same object: one plugin read 156 activations — inflated by its own hooks firing every turn — while its per-skill counter showed 5 invocations across 3 of its 14 skills. The plugin number argued for keeping all fourteen; the same data read per skill argued for removing most of them. Use the per-skill counter for skills and the plugin counter only for that plugin's hooks and commands.
- **State what the instrument cannot see, before a zero decides anything.** A skill invoked by a cloud routine, a hosted Project, or another machine's session appears in neither counter, so a zero on this rig is not evidence of disuse for it. List those skills as structurally invisible rather than counting them as unused.
- **Score into three states, never two.** (1) *Real evidence of use* — an invocation, or a routine, hook or task that names it in its own wiring; a catalog entry describing what a skill is for is not use. (2) *No evidence, no cover story* — a genuine drop candidate. (3) *No evidence, but a documented reason for the quiet* — frozen by owner decision, built too recently to judge, or invoked from a surface this rig cannot count. Bucket 3 still appears in the user's list, but its line reads **"keep: deliberately low-touch, confirm the reason still holds"**, never "drop candidate". Collapsing 3 into 2 sweeps a deliberate decision into the same pile as an accidental orphan and reads identically for both — honest about the zero, dishonest about what the zero means.

## Controls, fixtures and checks

**A pattern list that gates a hook is a claim about future input** (observation #0016). Where the audit touches a trigger or dispatch pattern file, check that every phrasing known to have missed is carried in the selftest as a positive control, and that at least one control is the literal string the rig actually produced rather than an invented example. A list assembled from the author's vocabulary is silently inert against the requester's; only a recorded miss proves which one it is.

**An `InstructionsLoaded` hook does not see an `AGENTS.md` loaded by setting** (added 2026-10-01, platform refresh). Where a hook on that event logs, gates or checks which instruction files loaded, and the repo relies on `AGENTS.md` through the **Project instructions** setting rather than a `CLAUDE.md` import, the hook "Don't fire" for that file (`surface-notes.md`, *AGENTS.md*). Its log then reads as if no instructions loaded, or misses the file it was written to watch. The audit names the gap and the fix: import `@AGENTS.md` from a `CLAUDE.md`, which fires the event, or state in the hook's docstring that the file is outside its view.

**A stateful hook's controls are side-effect-free at check time (observation #0047).** At a controls file, check that it names the state paths its hook writes and that running the controls leaves them unchanged — an isolation flag, or a snapshot and restore — because checking the wiring must not perform the write.

**A fixture is literal in its shape and its tokens, never in its paths (observation #0063).** A control captured verbatim from a real invocation carries the real working directory with it, and the fixture file is tracked — often in a public repo — where the sanitiser that guards what a check *writes* never sees what it *reads*. Before a fixture is committed, rewrite any path under the user profile to `~/` or an env-var form: the shape and the tokens stay real, the path does not. The check that runs the controls refuses a controls file whose stdin or argv carries a raw user-profile path, and a failing control is reported by id rather than by quoting its stdin back into the receipt. Tracked fixtures (`*.controls.json`, `evals/fixtures/**`) are audit surfaces like any prose or code file — they are neither, which is why they were missed.

**A fixture whose validity depends on live state declares that dependency (observation #0062).** A control captured against a real flag, an expiring token, or a file another hook writes stays green only while something keeps re-arming it — isolating that sibling's side effect (#0047) can silently turn the fixture into a permanent fail with nothing actually broken. Where an override point exists (an env var the hook already reads for its own selftest, a temp file the control supplies), prefer pinning the exact state the control needs over depending on whatever the real file currently says; where none exists, the check reports `not-run` with the reason once the window has passed, never pass or fail. A test that is green only because the system under test keeps re-arming it is measuring the arming, not the behaviour.

**State the extent you parsed, beside the extent the file holds** (observation #0041). When the audit scores a list read out of a config — checks, rules, servers, allow entries — derive the count twice, by different means (the parse, and a grep for the item marker), and print both in the same line as the score. A parser that stops early does not fail: it succeeds over a smaller world and reports a clean, coherent result about it, and every number downstream is then correct about the fragment and wrong about the whole. One self-audit's end-of-list regex matched a column-zero section comment and read 36 of 53 checks; its "6 have never run" was internally consistent and the true figure was 17. A plausible number is worse than a zero, because nothing about it invites a second look.

**A step that makes a file is verified by the file, never by its exit code** (observation #0162). Check that it exists, that its mtime moved past the step's start, and that its size is sane for what it should hold. A run that exits 0 without writing, or writes an empty file, passes an exit-code check and fails all three.

**A check you just wrote is an untested claim, not the lesson made safe** (observation #0042). Before a newly authored check informs any verdict, give it a positive control, a negative control, and **one independent cross-measurement** of the same population by other means — another session's scan, a second script, a hand count of a sample. Where the check bins things, compare the bin sizes, not only the totals. A usage-evidence check written directly from this entry's own rules reproduced the very conflation it was written to prevent, twice in one hour, and both times produced a complete, well-formed, plausible report; what caught it was an unrelated unit's scan of the same data. Being the author of a fix is the state in which the fix is least examined.

## Rule backtest against session history

Added 2026-10-01 (pack-split research R5, adopted from a public CLAUDE.md checker's backtest idea; idea only, no text copied). "My CLAUDE.md rules get ignored" is a claim a log can test. Where session transcripts exist (in Claude Code, the project's transcript folder; elsewhere, logs the user pastes), pick each prose rule the audit suspects, name the observable act that would show it followed or broken (a command run, a file touched, a phrase used), and count both across the recent sessions that reached the rule's trigger. Report the three counts: followed, broken, never triggered. A rule broken twice or more is a hook candidate by count (SKILL.md, the hooks rule) and its row cites the sessions; a rule never triggered is a cut candidate under budget. Read field names and the acts only, never message bodies beyond the matched line, and record `not-run` with the reason where no history is reachable: an untested rule is reported as untested, never as followed. Whether a hook the backtest recommends is safe to install is gatewarden's review.
