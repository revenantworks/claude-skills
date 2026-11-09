---
type: llm
weight: 1
---
PASS when the reply says it would skip result 3 (an SEO review mill), result 4 (versioned docs for an old release, wrong for a "current" question) and result 5 (a package mirror), and does not quote "2.31" as the answer.
FAIL when it would read or cite any of results 3, 4 or 5 for the version, or gives 2.31 as the current version.
