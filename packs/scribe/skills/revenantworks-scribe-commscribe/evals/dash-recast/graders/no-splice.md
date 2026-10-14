---
type: llm
weight: 2
---
PASS when the rewritten text contains no comma splice (two independent clauses joined by a comma alone, such as "The rollout finished on time, the cache fix cut latency by half") and keeps all three facts: on time, latency cut by half, support tickets fell.
FAIL when a dash was swapped for a comma leaving a splice, a semicolon stands in for the dash with no recast, or any of the three facts is lost or changed.
