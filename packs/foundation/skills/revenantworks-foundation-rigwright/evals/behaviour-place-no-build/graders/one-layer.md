---
type: llm
weight: 2
---
PASS when the answer names one layer for the rule (a hook, since skipping it has a real cost) with a one-line reason, and emits no config file content.
FAIL when it writes a CLAUDE.md or settings file, or leaves the rule as prose in CLAUDE.md as the only answer.
