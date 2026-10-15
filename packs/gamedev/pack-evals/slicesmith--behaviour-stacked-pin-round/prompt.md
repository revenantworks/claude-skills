---
description: Behaviour - an arc of pin-moving sim units with OFF controls is planned as a stack with one re-pin at the join, with the cases where not to stack named (spec-and-plan, test case C19).
tags: [behaviour, plan, pins]
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---
slicesmith plan. Our Godot colony sim has a trajectory-hash test (about 15 pinned values). We are about to build three sim features, A, B and C. Each moves the hashes and each will ship a tests-only `_OFF` switch that turns it off. Today we build one, re-pin everything, review, publish, wait for CI, then start the next. Propose the build order and when to re-pin.
