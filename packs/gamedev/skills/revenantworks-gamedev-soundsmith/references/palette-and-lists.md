# Palette, SFX lists, rundown and briefs (Direct)

Loaded by Entry — Direct. Templates are starting points: fill only the rows the game has.

## Contents

1. The sound palette
2. The SFX list per game system
3. The rundown line (the gate before any brief)
4. Music brief fields
5. Voice brief fields
6. Variation and repetition

## 1. The sound palette

One page. It answers "what does this game sound like" before any file exists.

| Field | What goes in it | Example (invented) |
|---|---|---|
| Identity | Three to five lines: the world, the camera distance, the emotional range | "Close, dry, wooden. A small settlement seen from above. Calm by day, tense at night." |
| Families | The instrument and texture families allowed, per category | music: hand percussion, plucked strings, low drones; SFX: wood, cloth, stone, water |
| Banned | What never appears, and why | "No synth leads (breaks the era). No reverb tails over 1.5 s on UI." |
| Space | Reverb and distance policy: dry assets with reverb on a bus, or reverb baked in | "All SFX dry; the engine's bus adds the room" |
| Loudness intent | Which category leads, which sits under | "Dialogue leads; music ducks under it; ambience is the floor" |
| Motifs | Recurring musical or sonic signatures and what each means | "Three-note falling figure = loss; bell = new day" |

A lorescribe bible, when one exists, supplies motif lines per faction or place and the pronunciation key; soundsmith turns them into the Motifs row and the voice briefs, and never edits the canon.

## 2. The SFX list per game system

List the game systems first (movement, combat, building, economy, UI, weather...), then every event in each system that makes a sound. One row per event.

| System | Event | Category | Variations | Priority | Loop | Spatial | Notes |
|---|---|---|---|---|---|---|---|
| Movement | footstep on grass | SFX | 6 | high (heard constantly) | no | 3D | per surface type |
| Building | placement confirmed | UI | 1 | high | no | none | under 300 ms |
| Weather | rain bed | Ambience | 1 | medium | yes | 2D | seamless, 30 to 60 s |

Rules:

- **Priority** follows how often a sound plays, not how dramatic it is. A footstep heard ten thousand times outranks a boss roar heard once.
- **Variations** for anything heard more than a few times in a row (steps, hits, UI clicks). See section 6.
- **Spatial**: `3D` sounds are positioned in the world (mono files); `2D` sounds play flat (UI, music, ambience beds).
- A system with no sound is listed with "none (by choice)" so the gap is a decision, not an omission.

## 3. The rundown line

One line per file. The rundown is the gate before any brief: shown complete, approved once.

```
id | category | length | loop (begin..end, samples or bars) | channels | rate | format | Godot import line | source + licence
```

Example (invented):

```
sfx_step_grass_03 | SFX | 0.25 s | no | mono | 44100 | WAV | Force Mono on, Trim on, Loop Disabled, QOA | local model (allowed: see brief)
mus_day_theme | Music | 16 bars @ 90 BPM in 4/4 = 42.667 s | 0..end | stereo | 44100 | Ogg Vorbis | Loop on, offset 0, BPM 90, Beat Count 64, Bar Beats 4 | local model (allowed)
```

The import line comes from `godot-import.md`; the licence column from `model-briefs.md`. A line with an empty licence column is not approved.

## 4. Music brief fields

| Field | Rule |
|---|---|
| Purpose | where it plays and what the player is doing then |
| Tempo | BPM, whole number where possible (loop arithmetic stays exact) |
| Meter and bars | beats per bar and bar count; the loop length follows from them (law 4) |
| Key and mode | name it; adjacent tracks that crossfade share a key or a related key |
| Instrumentation | from the palette's families only |
| Energy curve | flat for a bed; build-and-release for an event cue |
| Loop | whole-file loop or an intro + loop body (the intro is the Ogg loop offset) |
| Ending | none for a loop; a tail length for a one-shot cue |
| Layers | when the game adds or removes layers by intensity, every layer has the same length and tempo |

## 5. Voice brief fields

Line text, speaker, emotion, pace, the pronunciation of every name (from the lorescribe key when present), a maximum length, and the processing that is applied later on a bus (never baked into the line). Voice is mono. A synthetic voice that imitates a real person is out of scope.

## 6. Variation and repetition

- A sound heard repeatedly gets several recorded or generated variations, not one file. Small random pitch and volume offsets at playback are an engine setting (godotsmith writes the code); the rundown records the intended range.
- Variations of one event belong to one category and sit within the category spread (`loudness.md`), or the randomizer makes some of them jump out.
- Generated variations come from separate generations with a varied seed, never from one file pitched up and down.
