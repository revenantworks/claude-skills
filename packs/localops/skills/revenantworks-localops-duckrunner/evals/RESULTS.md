# Results — revenantworks-localops-duckrunner

Run record for this member's evals. Hand-run suites: `trigger-evals.md` and
`test-cases.md`; native cases: `evals/<case>/`. Script tests run with
`python -m unittest discover -s scripts -p "test_*.py"` from the member folder.

## Model tiers checked

Recorded 2026-10-01 (audit PK-3): **none yet.** The trigger tables were judged by reading, from
name + description only (the 2026-10-01 cold re-judge included), not on a model, and the
native `claude plugin eval` cases under `evals/<case>/` have not run. The first native run
writes its model tier(s) and date here, one line per run; until then no tier claim is made.

## 2026-10-09 — K9 plugin-eval run (Windows, Claude Code 2.1.295)

harness: the Windows eval runner cannot grant a shell (no sandbox backend: "Windows sandbox is not active on this session"); needs a Linux or macOS runner; not a skill result.

`behaviour-check-tracked-cache` needs `--scaffold --allow-tools Bash` (its `prompt.md` now grants Bash). On this runner the shell grant is refused before the first turn, so the case scores 0 at zero cost. Without the grant it cannot run `duck_run.py check` and has no fixture repo.
