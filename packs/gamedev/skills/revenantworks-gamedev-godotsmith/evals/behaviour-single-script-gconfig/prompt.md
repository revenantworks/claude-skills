---
description: Behaviour - a single-script GUT run passes an empty -gconfig= beside -gtest=, and the run's own Scripts count confirms the narrowing (gut-traps section 4, test case G9).
tags: [behaviour, gut-traps]
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---
In our Godot 4 project I ran one test file with `godot --headless -s addons/gut/gut_cmdln.gd -gtest=res://tests/sim/test_night.gd -gexit` and it took 25 minutes. Our `.gutconfig.json` has `"dirs": ["res://tests"]` and `"include_subdirs": true`. Why did a one-file run take that long, and what command runs just that file?
