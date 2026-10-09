---
description: "Behaviour (T15): a story-draft brief for a local model; expect a BRIEF block carrying the canon slice, the dead captain as a must-not, and a names rule, with no scene drafted."
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

I want my local model in LM Studio to draft the scene at T-0601 where the Salt Guild mourns its captain. Write me the brief from my story bible so the draft stays in canon. Do not write the scene yourself.

`characters/ila-varn.md`:

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

`factions/salt-guild.md`:

```yaml
---
id: salt-guild
kind: faction
name: The Salt Guild
level: hard
seat: the-weir
visual: [rust-red banners, round shields, salt-white stone]
---
```

`timeline.md`:

| at | event | entities |
|---|---|---|
| T-0587 | Ila Varn drowns at the weir | ila-varn |
| T-0601 | The guild holds the river vigil | salt-guild |
