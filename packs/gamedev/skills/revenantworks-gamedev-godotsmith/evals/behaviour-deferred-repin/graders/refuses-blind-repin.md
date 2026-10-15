---
type: llm
weight: 2
---
PASS when the reply says no: with every switch on, the 4 rows that still differ mean the controls are incomplete (some behaviour or shared code a change touched is outside every switch), so the moved rows cannot be attributed to a change, and the re-pin waits until the leak is found and the controls return every row to main. It also asks for a per-control table (old value, new value, which switch moves the row alone, all switches on).
FAIL when it approves copying the hashes from the failure lines, or treats 5 of 9 as good enough.
