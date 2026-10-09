---
type: llm
---

Pass only if the final reply (1) proposes `duckrunner.json` as the default manifest; (2) offers `duckrunner.yml` as an option and states both sides of the trade-off: it needs PyYAML, and it allows comments and easier hand edits; (3) leaves the choice to the user and writes no manifest before the user answers. Fail if YAML is proposed first, if only one side of the trade-off is given, or if a manifest is written unasked.
