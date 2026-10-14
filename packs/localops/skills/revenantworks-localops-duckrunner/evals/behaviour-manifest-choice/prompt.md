---
description: Behaviour, owner Q26 (TC-15). No manifest yet — JSON is proposed first, YAML offered once with its trade-off.
expected_outcome: The reply proposes duckrunner.json as the default and offers duckrunner.yml with both its cost (PyYAML) and its gain (comments, easier hand edits), leaving the choice to the user.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

duckrunner: I want a cached copy of state/queue.yml so the counts are quick. This repo has no duckrunner manifest yet. Set one up for me.
