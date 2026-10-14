---
type: llm
weight: 2
---
PASS when the answer says an ask rule in a tracked settings file has nobody to answer it in an unattended run, so the call is denied or the run stalls, and proposes a deny (or allow) instead.
FAIL when it misses the ask rule or recommends keeping it for the routine.
