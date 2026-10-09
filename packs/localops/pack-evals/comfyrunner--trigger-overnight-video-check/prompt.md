---
description: Trigger row 5 — checking a workflow before a long unattended render must load comfyrunner.
expected_outcome: The comfyrunner skill is invoked.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Before I leave it rendering overnight, can you check my ComfyUI video workflow? It is saved as wan_shore.json in my workflows folder: a 1024 by 1024 clip, 121 frames.
