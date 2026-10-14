---
description: "Behaviour (T2): a dead character speaks; expect STATE-AFTER-DEATH with file and line."
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

Check this scene against my story bible. Here is the one bible file that matters, `characters/ila-varn.md`:

```yaml
---
id: ila-varn
kind: character
name: Ila Varn
level: hard
state:
  - {at: "T-0412", value: alive}
  - {at: "T-0587", value: dead, cause: "drowned at the weir"}
source: "owner"
---
```

Scene `scenes/scene-12.md`, set in T-0601:

```
1  The barge slid past the weir at first light.
2  Ila Varn stood at the rail and called the crew to the ropes.
3  "Hold her steady," Ila said. "The current is wrong today."
```
