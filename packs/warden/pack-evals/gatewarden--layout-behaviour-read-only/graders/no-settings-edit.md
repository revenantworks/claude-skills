---
type: tool_used
tool: Bash
input_match: '(settings(\.local)?\.json[^\n]*(>|Set-Content|Out-File|write)|(>|Set-Content|Out-File)[^\n]*settings(\.local)?\.json|\bsed\s+-i)'
min: 0
max: 0
---

The run never writes a settings file itself; every home is a proposal the owner applies.
