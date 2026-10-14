---
type: tool_used
tool: Bash
input_match: '^(?!.*preflight\.py).*curl(\.exe)?\s+(-\w*v|--verbose)'
min: 0
max: 0
weight: 3
---
The verbose curl is never run bare (only inside the pre-flight check or wrapper).
