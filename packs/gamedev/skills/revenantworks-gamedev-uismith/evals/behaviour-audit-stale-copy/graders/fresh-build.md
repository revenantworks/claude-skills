---
type: llm
focus: last_message
weight: 2
---

PASS if the reply says the committed docs/status.html is older than its generator, plans to rebuild the page from tools/build_status.py into a scratch location and probe that build (not the committed copy), names both commits (a1b2c3d and e4f5a6b), and points any fix at the generator rather than at the committed HTML. FAIL if it audits or edits docs/status.html as the source of truth, or proposes hand-editing the generated file.
