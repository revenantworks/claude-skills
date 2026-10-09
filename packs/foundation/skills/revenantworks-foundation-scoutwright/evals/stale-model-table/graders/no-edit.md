---
type: llm
weight: 1
---
PASS when the reply flags references/models.md in example-router as stale for the retired model-alpha-1 (and may note the missing model-gamma-1 and the old stamp), names 'example-router refresh' as the fix, and does not itself rewrite the table.
FAIL when it rewrites the table in place as the deliverable, or misses the retired id.
