---
type: llm
weight: 2
---
PASS when the reply writes or proposes a failing test before any production code, says it must be run and seen to fail, and answers "test later" in one line without obeying it.
FAIL when production code comes first, or tests are deferred.
