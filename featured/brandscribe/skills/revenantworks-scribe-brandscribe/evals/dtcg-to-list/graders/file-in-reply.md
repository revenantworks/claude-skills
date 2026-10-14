---
type: regex
pattern: '"name"\s*:\s*"[^"]+"[\s\S]{0,200}"value"\s*:'
target: last_message
---

The converted file is in the reply as list entries (name, then value). A case cannot grant Write (only read-only tools are grantable per case; Write needs a run-wide --allow-tools), so the file is graded in the reply, not on disk.
