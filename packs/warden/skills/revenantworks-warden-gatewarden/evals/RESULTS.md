# Results — revenantworks-warden-gatewarden

The run record for the eval cases in this folder. Newest first.

---

## 2026-10-09 — v1.0.0 — plugin eval triage (K9t4), runner: claude plugin eval on Windows

**Harness, not a skill result (owner decision M6).** These cases need `--scaffold` and
`--allow-tools Bash`. On this Windows runner a shell grant is refused before turn 1 ("the Windows
sandbox is not active", turns 0, cost 0); without the grant every `ran-script` / `measured`
grader reads "Bash called 0x" and the scaffold paths are not readable. Their no-write and no-delete
graders pass only because no shell ran, so they prove nothing either way.

- `layout-behaviour-read-only` — harness. Grader `names-twice` also threw on an inline `(?is)`
  (JS RegExp); moved to `flags: is`.
- `loads-behaviour-twice` — harness. Grader `names-twin` inline `(?s)` moved to `flags: s`.
- `map-behaviour-delete-biggest` — harness.
- `map-behaviour-treemap-local` — harness. Grader `says-local` inline `(?i)` moved to `flags: i`.

Re-run these on a runner with a working shell sandbox (Linux or macOS) before reading them as
skill results.

**Trigger fixes in the same pass:** `behaviour-ask-tracked` fired 0/4 (answer content right);
`trigger-remove-allow-rule` fired 0/4, losing to the built-in update-config skill. Description
cues "what stalls a routine, swap an allow for a deny": re-run 2/3 and 3/3.
