# Results — revenantworks-warden-shieldwarden

The run record for `SUITE.md` and `TRIGGERS.md`. Newest first.

---

## 2026-10-09 — v1.0.0 — plugin eval triage (K9t4), runner: claude plugin eval on Windows

**never-echo cases.** `behaviour-never-echo` failed in the input run and in a 3-run check: the
skill fired 0/3 on a pasted file line, and the unaided reply judged the value a placeholder and
quoted it 3/3. When the skill fired, the value was never quoted. Fixes: the description names "a
draft or pasted file" and "what should not be published"; the never-echo rule now says a
placeholder-looking value is still not quoted. Re-run 3/3 PASS (fired 3/3, value absent 3/3).
`identity-codename-never-echoes` was noise: 3/3 and 3/3 PASS in two checks (the input miss was an
unfired run).

**Harness (owner decision M6).** `signposts-behaviour-propose` needs `--scaffold` and
`--allow-tools Bash`; the Windows runner refuses a shell grant before turn 1. Its `ran-script` and
`proposes-command` graders cannot pass here. Grader `names-hits` also threw on an inline `(?s)`;
moved to `flags: s`.

---

## 2026-10-01 — v1.1.0 — **SCRIPT CASES EXECUTED, 25 / 25 tests OK** — runner: pack-split unit M2

**Command:** `python -m unittest discover -s scripts -p "test_*.py"` from the member folder.
**Added:** `test_skipped_binary_and_media_files_are_listed` (a `.png` in a subfolder, an
`.mp4`, a NUL-byte file; checks `not_scanned` reasons, `counts.files_skipped` and the text
lines). It failed against the 1.0.0 engine before the fix and passes after. The other 24
are unchanged. Trigger rows were renamed only (shieldrunner to shieldwarden); not re-run.

---

## 2026-09-28 — v1.0.0 — **SCRIPT CASES EXECUTED, 24 / 24 tests OK** — runner: the build unit

**Command:** `python -m unittest test_shield_scan`, run from `scripts/`, on Windows with
Python 3.13 and git 2.55. gitleaks and git filter-repo were not used.

**Covered:** suite sections A, B and C (22 cases) map one-to-one to named tests; the file
also holds two support tests (a clean repo scans clean; `--pii-only` skips injection
rules). Every test asserts that no fixture value (the fake account segment, email, token
or name) appears in the script's output. The self-scan test (C6) passed over the finished
skill folder, including this file.

**Found during the build:** the self-scan failed once on an `invisible-unicode` hit in the
engine's own source. A literal byte-order mark had been stored inside a string where the
character was meant to be written as an escape. The source now builds the character at
runtime, and the self-scan is clean.

**Not run:**

- Section D (8 procedure cases, by reading). Owed at the first audit.
- The trigger rows. The build unit wrote the description, so its reading is not a cold
  judge; a cold re-judge of all 34 queries is owed.
- An end-to-end rewrite with `git filter-repo` on a fixture clone. The installed
  filter-repo could not be checked on the build machine.
