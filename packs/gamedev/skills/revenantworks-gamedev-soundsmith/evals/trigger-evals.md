# Trigger evals — revenantworks-gamedev-soundsmith — 22 queries (11 should / 11 shouldn't)

Counts: 22 queries (11 should, 11 should-not, 3 pairs)

Provenance: derived from SKILL.md v0.1.0 (2026-10-01). Status: **authored, not run** — a cold judge
reading only name + description has not scored this table yet. Read each query against the name and
description alone and compare with the Expected column. 11 should fire, 11 should not. **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

**2026-10-01, pack-split unit FX5, version unchanged at v0.1.0:** the description gained "a request to
generate a game sound starts here with the brief" (J1 edit E5, misroute M7 on row 10), and every row was
re-judged against the new text. Run record in `evals/RESULTS.md`.

**2026-10-02, pack-split unit FX6, version unchanged at v0.1.0:** the native case
`mix-vs-file-correction` (a per-file normalize request) scored 0 because the skill never fired: the
request reads as DSP, and the description named no normalize trigger. The description now names
"normalizing files to a LUFS target" and "a request to generate or normalize a sound starts here"; rows
21-22 pin the pair (a game build fires, a non-game batch does not).

| # | Query | Expected | Nearest sibling / note |
|---|---|---|---|
| 1 | Make an SFX list for the combat system in my top-down game: hits, blocks, dodges, deaths. | fire | Direct |
| 2 | My Ogg music loop clicks every time it wraps around in Godot. What's wrong and how do I fix it? | fire | Audit + godot-import (begin-only) |
| 3 | What loudness should my UI sounds be, and what LUFS should the whole game sit at on console? | fire | loudness, mix vs file |
| 4 | Write a brief for a local music model: a calm night theme at 80 BPM that loops cleanly. | fire | Brief |
| 5 | Check these 30 WAV footsteps before I import them — peaks, silence at the start, levels. | fire | Audit |
| 6 | I want to use Woosh to generate the sound effects for the game I'm selling on Steam. Write the prompts. | fire | Brief, licence gate refuses |
| 7 | Define the sound palette and audio style guide for a cozy farming game. | fire | Direct, palette |
| 8 | Which Godot import settings should my ambience loops and dialogue lines use — mono, sample rate, loop mode? | fire | godot-import |
| 9 | soundsmith test — set up a listen test for the market scene. | fire | quoted keyword, Test |
| 10 | Generate a jump sound for my platformer. | fire | Brief first, then the hand-off to the runner |
| 11 | Run this ComfyUI audio workflow JSON on my GPU and save the output. | not fire | comfyrunner (running a workflow) |
| 12 | Write the GDScript for an AudioStreamPlayer pool and the bus layout with a ducking compressor. | not fire | godotsmith (engine code) |
| 13 | Transcribe this voice memo to text and make subtitles. | not fire | whisperrunner |
| 14 | How do I call the SoundSmith time-stretch module in the Redot engine? | not fire | no skill; engine docs (direction, not DSP) |
| 15 | Pitch-shift these samples up a semitone and time-stretch them to 120 BPM. | not fire | an audio editor; DSP is out of scope |
| 16 | Write the in-world history of the river faction and how their names are pronounced. | not fire | lorescribe |
| 17 | My sprites vanish against the forest when I zoom out. | not fire | pixelsmith |
| 18 | Master my podcast episode to -16 LUFS for Spotify. | not fire | not game audio |
| 19 | Is my Godot CI test run actually green? GUT says 0 failures but the count dropped. | not fire | godotsmith |
| 20 | Recommend a good pair of studio headphones under 200 dollars. | not fire | off-topic (a verdict, researchscribe if anything) |
| 21 | Give me one command that normalizes every SFX file in my sounds folder to -18 LUFS for the handheld build. | fire | loudness, mix vs file (corrects the target before any command) |
| 22 | Batch-normalize these audiobook chapters to -19 LUFS with ffmpeg. | not fire | not game audio; DSP on request is an audio tool's |

**Edge notes.** The sharpest pairs: 10 vs 11 (asking for a sound fires soundsmith for the brief; running
a workflow that already exists is comfyrunner's), 2 vs 12 (a clicking loop is the file and its import
line, soundsmith; the player and bus code is godotsmith's), and 14 vs 15 (the name collision with an engine
DSP module, and DSP requests generally, must not pull the skill). Row 18 tests that "LUFS" alone does not
fire it outside games; 21 vs 22 tests that a normalize request fires only for a game. Tuning rule: misses on rows 1-10 → make the triggers pushier; fires on rows 11-20 →
tighten the boundary sentence.
