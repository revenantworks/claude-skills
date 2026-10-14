---
type: llm
weight: 1
---
PASS when the spec states the exact output of a run that finds nothing (a zero-signal line, such as a dated "no signal" or "no change" line) sent to the same destination as findings, so a quiet run is distinguishable from a dead one.
FAIL when a run with no findings stays silent, or the spec never says what such a run outputs.
