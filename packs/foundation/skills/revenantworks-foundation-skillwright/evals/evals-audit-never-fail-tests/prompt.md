---
description: "Behaviour: the never-fail lint flags constant and assertion-free tests and leaves a real test alone."
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

skillwright evals audit the tests that ship with the skill in `resources/` (SKILL.md saved as `SKILL.snapshot.md`; its test file `scripts/test_tool.py` is saved as `scripts/test_tool.py.txt` so no runner collects it). Are any of them unable to fail?
