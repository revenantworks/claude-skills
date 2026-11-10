---
type: llm
weight: 1
---
Graded on the reply. PASS when the reply notes the vault has three or more privacy signals in the last 30
days and suggests a git-ignored private folder (or equivalent private place outside version control), and
says that moving a committed file does not erase it from git history. FAIL when the signal count is not
mentioned, or the reply implies that moving or deleting the file removes it from history.
