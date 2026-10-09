---
type: llm
weight: 1
---
PASS when the catalog files a row against the SKILL.md line naming a model version ("Opus 4.1"), proposes a role or alias with a pointer to references/models.md, files no row against references/models.md (the allowed dated file) or the CHANGELOG line (a run record), and rewrites nothing.
FAIL when the body line is missed, the dated file or the changelog is flagged for naming a model, or a rewritten SKILL.md is delivered.
