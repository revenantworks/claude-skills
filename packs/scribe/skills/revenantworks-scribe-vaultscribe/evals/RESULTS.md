# Eval results — revenantworks-scribe-vaultscribe

## 2026-11-09 — build (no model run yet)

No `claude plugin eval` run yet: the 15 native cases and both hand-run suites are authored, not run.
The owed run is `claude plugin eval packs/scribe --trust-plugin --runs 3` (with and without the
skill), on a Linux runner for the scaffolded cases.

Checked at build: the script suites (`scripts/test_vault_lint.py`, `scripts/test_vault_snapshot.py`)
pass; each scaffold (`clip-injection`, `privacy-lint`, `snapshot-drift`, `conflict-keep-both`,
`no-push`) was run under Git Bash and its vault linted: the fixtures hold what the graders expect
(the clip is `NEW`; email, path and secret hits with 3 privacy signals; one `CHANGED` living source).
