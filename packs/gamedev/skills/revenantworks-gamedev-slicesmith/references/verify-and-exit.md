# Verify and exit — evidence, commits, review, the milestone gate

Read before a commit and on `exit`.

## Contents

- Evidence for a claim
- The commit
- The run log
- Exit — closing a milestone
- Export gate
- Integration

## Evidence for a claim

| Claim | Evidence it needs |
|---|---|
| "Tests pass" | Script count, test count and failures from this session's run, beside the expected totals |
| "Bug fixed" | The reproduction test failing with the fix reverted and passing with it restored |
| "Builds clean" | The build line with zero warnings |
| "Scene works" | The smoke-load proof line |
| "Export works" | The export gate's assembly or file check, not the exit code |
| "Reachable" | The player path that calls it, named |
| "Feels right" | The user's playtest note; never the agent's word |

Evidence comes from this session. A claim carried from a previous session, or from another
agent's report, is re-run or marked unverified.

## The commit

One verified slice, one commit. Follow the repo's own message convention; with none:

```
<scope>: <imperative summary, at most 72 characters>

Why: <the finding or the spec line this slice serves>
Cause: <root cause, for a fix>
Evidence: <scripts>/<tests> passed (expected <n>/<m>), 0 warnings, [M4] OK
Deviations: <ruling, or none>
```

Stage the slice's named files, never `git add -A` blindly. Never commit a red suite.

## The run log

`RUN-LOG.md` (or the repo's own) is append-only. Each slice adds a dated line: slice id,
evidence, commit sha, deviations. A wrong earlier entry is corrected by a dated note below it,
never edited away. An overstated claim is withdrawn in writing.

## Exit — closing a milestone

1. **Re-derive** every figure the milestone claims from raw counts in this session.
2. **Proof obligation** (S1): run the check the spec named. If it does not hold, the milestone
   has not landed, whatever else passed. Then a **mutation sample** on the sim rules the
   milestone added (`slice-and-test.md`, Properties and mutants): killed / survived, and each
   survivor written up as a missing test or a deletion candidate.
3. **Review in a fresh context, as a second opinion.** A reviewer that did not write the code
   reads the diff against the spec and reports only. Use a different model from the author's
   (another family or tier) where one is available, and name it in the write-up; with only the
   author's model, say so — that is a fresh context, not a second opinion. Its write-up has
   four parts: Fixed · Deferred · Cleared under attack · Accepted risk. The author owns fixes.
   godotsmith's `review` covers the Godot conventions.
4. **Deletion test** for anything the milestone freezes (a protocol, a save format): delete the
   source, confirm the compiler finds every consumer, restore, and record what the test cannot
   see. A later change to the frozen thing re-runs it.
5. **Deferrals.** Each is named as a deferral with an owner. A deferral seen at an earlier exit
   is flagged as repeated.
6. **Enforcement layer.** Name which layer catches the riskiest change: compiler, analyzer, CI,
   a grep gate, a runtime assert, or only human review — and say so when it is only review.
7. **State the weaker true thing.** What is reachable, what is verified, what is not built.

The gate ruling itself — PASS, FAIL, PARKED, UNMEASURED — is godotsmith's `gate`. slicesmith
brings the evidence; it never self-certifies.

## Export gate

An export that exits 0 can still ship no code. After `godot --headless --export-release
"<preset>" <path>`, assert the output holds what it must: the main pack, and for C# every
required assembly. Update the required list in the same commit that adds an assembly. Run the
exported binary once with its proof flag where one exists.

## Integration

After a green slice or exit, offer exactly three options: merge locally, push and open a pull
request, or keep the branch. Discarding work needs the user to type `discard`. Never
force-push.
