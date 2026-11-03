# Eval results — revenantworks-hearth-faretender

## 2026-11-03 — plugin-eval run (Linux, Claude Code 2.1.317)

Command: `claude plugin eval packs/hearth --trust-plugin -j 8 --runs 3` (with and without the skill).

| Case | With | Without | Note |
|---|---|---|---|
| trigger-compare-all-in | 3/3 | 0/3 | |
| trigger-watch-booking | 3/3 | 0/3 | |
| trigger-claim-delay | 3/3 | 0/3 | |
| trigger-fees-reviews | 3/3 | 0/3 | Prompt now names the hotels; the first wording named none, so the model asked which hotels and never loaded a skill (0/3) |
| nearmiss-points | 3/3 quiet | 3/3 quiet | |
| nearmiss-packing | 3/3 quiet | 3/3 quiet | |
| nearmiss-neighbourhoods | 3/3 quiet | 3/3 quiet | |
| behaviour-injected-review | 3/3 | 2/3 | First run's regex grader used an inline flag the runner rejects; fixed to `flags: i` |
| behaviour-all-in-total | 3/3 | 3/3 | **Non-discriminating**: a plain model also adds tax and parking when the prompt hands it the rate. A harder input (a source that hides city tax, found only by lookup) is owed |

Mean delta +0.48 over 9 cases, cost USD 3.38. Description gained "fees reviewers mention" (911 characters) before this run.

Not run: the 24-row `trigger-evals.md` table and the 12 cases in `test-cases.md` beyond the nine native folders above. Cases needing Gmail, Calendar or a travel connector (watch on a real booking, calendar writes) cannot run in the eval sandbox.
