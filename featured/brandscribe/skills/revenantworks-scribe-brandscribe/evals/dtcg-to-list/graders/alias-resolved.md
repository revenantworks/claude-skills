---
type: llm
weight: 1
---

PASS when the link token is an alias of an accent token that exists in the converted file (for example {brand-accent}), and no family is a name-to-value map.
FAIL when a family keeps the nested $value map, or the alias points at a token name that does not exist.
