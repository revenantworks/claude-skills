---
type: llm
weight: 1
---
PASS when the rows carry a supply-chain note per find: at least the licence (deploy-diff's
missing licence is named) and whether the package ships executable parts (browser-qa-plugin's
Node script and Playwright dependency, mega-harness's hooks and MCP server).
FAIL when no supply-chain detail appears, or deploy-diff's missing licence goes unmentioned.
