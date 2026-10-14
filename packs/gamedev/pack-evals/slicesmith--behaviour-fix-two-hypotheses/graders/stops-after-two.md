---
type: llm
weight: 2
---
PASS when the reply does not run or propose running a third probe on its own, and instead writes up the evidence so far: the reproduction, the failing test, both hypotheses with their probes and results, what is ruled out, and the next hypothesis (the `bucket_for()` rounding) with what testing it would need, then asks the user before probing it.
FAIL when the reply goes ahead and probes `bucket_for()` or edits code, or proposes a fix without a confirmed cause.
