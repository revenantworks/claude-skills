---
description: "Should not fire: code unit tests are engineering test tooling."
max_turns: 4
allowed_tools: [Read, Glob, Grep, Skill]
---

Write pytest unit tests for this function:

```python
def slugify(s):
    return s.strip().lower().replace(' ', '-')
```
