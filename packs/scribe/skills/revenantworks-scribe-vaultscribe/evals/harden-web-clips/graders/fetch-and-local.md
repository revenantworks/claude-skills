---
type: llm
weight: 1
---
Graded on the reply. PASS when the proposed settings deny the WebFetch tool and shell downloads (curl or wget,
and the PowerShell Invoke-WebRequest form or its aliases), and a separate local, git-ignored settings file
denies git push and merge and turns off connectors or MCP tools. FAIL when any of these is missing, when an
"ask" rule appears, or when an allow rule is added.
