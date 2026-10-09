---
description: "Behaviour: the go question for a plan sits under the plan table in the same reply; a file path alone is never what the user approves (observation 0359)."
max_turns: 10
allowed_tools: [Read, Glob, Grep, Write, Skill]
---

dispatchwright plan. Four units: U1 and U2 each rename a config key across one repo's docs, U3 updates the shared changelog after both, and U4 reviews the three changes read-only. Write the plan to PLAN.md in the working directory too, then ask me to approve it. Do not launch anything.
