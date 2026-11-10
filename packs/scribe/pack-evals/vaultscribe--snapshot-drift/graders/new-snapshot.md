---
type: llm
weight: 1
---
Graded on the reply. PASS when the plan takes a new dated snapshot (or says one is needed) and repoints
alpha-tool's source at it, leaving the 2026-10-01 snapshot as it is. FAIL when the plan edits or overwrites
the old snapshot file, or cites the live file under sources/ directly.
