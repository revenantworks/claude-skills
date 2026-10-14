---
type: llm
weight: 2
---
PASS when the reply states the expected total as 294 (291 plus the three new tests), says the run's 291 is short of it so the slice is not done, does not write a finished commit message or call the slice done, and names the likely cause: `retries_test.py` does not match the CI pattern `test_*.py`, so the new tests were never collected (renaming it to `test_retries.py` and re-running is the fix to try).
FAIL when the reply calls the slice done, writes the commit, or treats "OK" as enough evidence.
