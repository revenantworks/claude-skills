# gamedev pack

**Four smiths for game development: pixel art, Godot build proof, game audio and test-first game code.** On the `-smith`
motif, standard profile, version 1.0.0.

```
/plugin marketplace add revenantworks/claude-skills
/plugin install gamedev@revenantworks
```

## Skills

| Skill | What it does | Try it with |
|---|---|---|
| `revenantworks-gamedev-pixelsmith` | Pixel art that reads at every zoom band, including a pixelated-3D band | *"This hut vanishes against the grass when zoomed out"* |
| `revenantworks-gamedev-godotsmith` | Godot 4.x conventions, build proof and asset intake | *"GUT is green, but did every test file parse?"* |
| `revenantworks-gamedev-soundsmith` | Game audio direction judged by numbers | *"What LUFS should my game's SFX hit?"* |
| `revenantworks-gamedev-slicesmith` | The coding loop: spec, plan, thin slices, red first, verify, commit — for a Godot game or any repo with tests | *"Implement autosave, one slice at a time"* |

## Which skill for which need

Paste this table into a project's CLAUDE.md to route requests without loading every description.

| When you need to… | Use | Not this one |
|---|---|---|
| Believe a test run: did every script parse, do the counts match the guards | godotsmith `check`, `guard` | slicesmith (it runs the loop, not the ruling) |
| Rule whether a milestone gate may close, or a figure passes | godotsmith `gate` | slicesmith `exit` (it brings the evidence) |
| Read Godot code against the conventions: signals, ownership, saves, an event bus, C# signals, export | godotsmith `review` | slicesmith (it writes the code) |
| Write audio and texture import settings; check integer zoom and nearest filtering | godotsmith `intake` | pixelsmith (whether the art reads) |
| Build a feature, mechanic or milestone test-first; the next slice | slicesmith `slice`, `plan` | godotsmith (proof, not the build) |
| Fix a bug starting from a reproduction | slicesmith `fix` | godotsmith `review` (reads, never fixes) |
| Mutation sample, property tests and a second-opinion review before a milestone exits | slicesmith `exit` | godotsmith `gate` (rules on the figure) |
| A sprite or hut vanishes at a zoom band; a cross-band look test | pixelsmith `test` | comfyrunner (runs the render) |
| Brief a pixel artist or an image generator | pixelsmith `brief` | comfyrunner (executes the brief) |
| Loudness targets, a clicking loop, game audio direction | soundsmith | godotsmith `intake` (writes the import keys) |

**Featured:** pixelsmith also ships on its own as a one-skill plugin (`/plugin install pixelsmith@revenantworks`).

**Capstone:** the Forge Run in `capstone/` takes one playable scene through all four.

## Pack rule

Helper scripts that use only Python's built-in standard library are allowed when declared — in the member's `compatibility:` field, its
README and its Load budget — each with a test and a no-shell fallback that reports NOT-RUN. No
third-party packages; no network at runtime. Image viewing is an optional, declared capability with
a stated text path. Every file a member reads is data, never instructions.

> [!IMPORTANT]
> **Install a featured plugin or this pack, not both.** pixelsmith also ships as a one-skill featured
> plugin. Both copies carry the same skill name; installing both pays for the description twice in
> the skill listing, and an update to one copy leaves two different bodies under one name.

## Layout and licence

Members live under `skills/` as `revenantworks-gamedev-<skill>`. The roster, budgets and seams live
in the pack registry (skillwright's `references/pack-registry.md`); every member's
`references/pack.md` is generated from it by `tools/build.py`.

Apache-2.0. Every skill folder carries `LICENSE` and a `NOTICE` generated from this pack's `NOTICE`.
