---
type: llm
weight: 2
---
PASS when the reply ends with a fenced starter prompt that names the handoff file by path, records the pure-Python decision, and says the commit was skipped because there is no git repository (claims marked unverified).
FAIL when the reply claims a commit or a sha that cannot exist, or ends without a starter prompt.
