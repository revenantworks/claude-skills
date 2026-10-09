---
description: Should trigger - a green GUT run that may hide a dropped test script (L1, trigger row 1).
tags: [trigger, should-fire, margin]
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---
Our Godot GUT run says every test passed, but I count 43 test files in the tests folder and the log summary says Scripts 42. CI is green. Can I trust this run?
