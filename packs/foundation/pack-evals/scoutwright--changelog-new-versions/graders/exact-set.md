---
type: llm
weight: 1
---
PASS when the reply presents 9.4.2 and 9.4.3 as the new versions and does not present 9.4.0 or 9.4.1 as new changes (mentioning 9.4.1 as the previous ledger state is fine), and the removed --legacy-output flag is classed Breaking.
FAIL when 9.4.0 or 9.4.1 appear as new changes, a version is missing, or the date inside the 9.4.3 bullet is treated as a version header.
