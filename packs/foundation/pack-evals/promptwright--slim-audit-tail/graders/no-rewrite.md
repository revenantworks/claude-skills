---
type: llm
weight: 1
---
PASS when the reply is a findings catalog with an efficiency score, one SL| tail line per catalog row in the same order, and no rewritten prompt.
FAIL when it includes a rewritten prompt, or the tail count differs from the catalog row count.
