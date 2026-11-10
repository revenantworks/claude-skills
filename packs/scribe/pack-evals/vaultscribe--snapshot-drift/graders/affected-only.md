---
type: llm
weight: 1
---
Graded on the reply. PASS when the reply identifies the alpha README as changed since the 2026-10-01
snapshot, names alpha-tool as the page to update, and does not plan any change to beta-tool (it may say
beta is unchanged). FAIL when no drift is found, when beta-tool is planned for an update, or when every page
is to be re-ingested.
