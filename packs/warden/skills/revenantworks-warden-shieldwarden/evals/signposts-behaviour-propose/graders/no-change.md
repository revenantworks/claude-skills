---
type: tool_used
tool: Bash
input_match: '(Rename-Item|Move-Item|\bmv\s|\bchmod\b|\bchown\b|icacls[^\n]*/(grant|inheritance|remove)|\brm\s|Remove-Item)'
min: 0
max: 0
---

The run never renames, moves, deletes or re-permits anything itself; every change is a proposal.
