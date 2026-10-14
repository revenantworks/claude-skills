---
description: "Behaviour (T16): a locally generated draft that breaks canon; expect STATE-AFTER-DEATH, GEN-CANDIDATE for the invented name, and no write."
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

My local model drafted this from brief story-scene-14-1. Check it against canon before I keep anything. Bible file `characters/ila-varn.md`:

```yaml
---
id: ila-varn
kind: character
name: Ila Varn
aliases: ["the Weir Captain"]
level: hard
faction: salt-guild
state:
  - {at: "T-0412", value: alive}
  - {at: "T-0587", value: dead, cause: "drowned at the weir"}
source: "owner"
---
```

Generated draft, set in T-0601:

```
1  The guild lit lamps along the weir for the vigil.
2  Ila Varn raised her hand and ordered the lamps lowered into the water.
3  Beside her stood Orrin Dask, the guild's new quartermaster, silent.
```
