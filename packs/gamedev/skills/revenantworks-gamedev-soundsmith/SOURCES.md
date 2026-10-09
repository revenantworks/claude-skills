# Sources

Last verified: 2026-10-01. The research pass for this build ran 2026-09-28 (the pack-split research report, section 2) and was re-checked live on 2026-10-01 for every row marked so. Fetched pages were read as data; none carried a directive addressed to the run.

## Engine and loudness facts

| Claim | Source |
|---|---|
| WAV for short repeated SFX, Ogg Vorbis for music, speech and long SFX, MP3 for CPU-limited mobile and web; WAV Force Mono / 8 Bit / Max Rate, Trim below −50 dB, Normalize to 0 dB, Loop Mode values, loop begin and end in samples (end −1 = file end), compress modes with Quite OK Audio the default; Ogg and MP3 Loop, Loop Offset in seconds, BPM, Beat Count, Bar Beats; no audible benefit from 24-bit or rates above 48 kHz; voices acceptable at 22 kHz | docs.godotengine.org, "Importing audio samples", page version 4.7 (fetched 2026-10-01) |
| Home console −24 (±2) LKFS, portable −18 (±2) LKFS, true peak at most −1 dBTP; measure as a whole, not per dialogue, effects or music; at least 30 minutes of representative play; BS.1770-3 algorithms | Sony ASWG-R001 (gameaudiopodcast.com/ASWG-R001.pdf, recommendations items 4, 5, 7, 9, 10; text extracted and read 2026-10-01) |
| K-weighting coefficients at 48 kHz; 400 ms blocks, 75 % overlap; gates at −70 LUFS and −10 LU; a 0 dBFS 1 kHz sine in one channel reads −3.01 | ITU-R BS.1770 (method as published; the script's calibration tests pin the figures) |

## Model licences and limits (model-briefs.md)

| Claim | Source |
|---|---|
| ACE-Step 1.5: MIT; 10 s to 10 min | github.com/ace-step/ACE-Step-1.5 README (fetched 2026-10-01) |
| Stable Audio 3: Small-Music and Small-SFX 433M, up to 120 s, CPU; Medium 1.4B, up to 380 s, CUDA; Large API-only; 44.1 kHz autoencoder; Stability AI Community License | github.com/Stability-AI/stable-audio-3 README (fetched 2026-10-01) |
| Community License: free commercial use below USD 1,000,000 annual revenue; last updated 2024-07-05 | stability.ai/community-license-agreement (fetched 2026-10-01) |
| Woosh: code MIT and Apache-2.0; open weights CC-BY-NC | github.com/SonyResearch/Woosh README, License section (fetched 2026-10-01) |
| MMAudio: code MIT; checkpoints CC-BY-NC 4.0; no guarantee of commercial suitability | github.com/hkchengrex/MMAudio README (fetched 2026-10-01) |
| AudioCraft: code MIT; model weights CC-BY-NC 4.0 | github.com/facebookresearch/audiocraft README (fetched 2026-10-01) |
| ElevenLabs sound effects: duration 0.5 to 30 s (the research report's 22 s figure is superseded); loop flag on the v2 model; prompt influence 0 to 1, default 0.3; PCM up to 48 kHz | elevenlabs.io/docs, text-to-sound-effects convert reference (fetched 2026-10-01) |

## Parity register (dated 2026-10-01; 90-day cadence)

| Incumbent | Licence / origin | Covers | Checked |
|---|---|---|---|
| **A1** audio-forge — github.com/Eshannaithani/audio-forge | MIT; created 2026-09-24 | Unity-only AI game audio: brief to rundown gate, generation through Unity AI credits, trim/loop/gain edits, per-category import settings, a measured check (length, peak and RMS dBFS, silence, loop seam, channels, rate), a report | 2026-09-28 (R3), search hit 2026-10-01 |
| **A2** Tone — github.com/simota/agent-skills (`tone` skill) | MIT | Generates code for SFX, music, voice, ambience and UI across many generators (including AudioCraft and MusicGen), LUFS normalisation through ffmpeg loudnorm or pyloudnorm, engine integration including Godot | 2026-10-01 |
| **A3** audio-design — github.com/gamedev-skills/awesome-gamedev-agent-skills (`skills/disciplines/audio-design`) | 425 stars on the collection; updated 2026-07-25 | Bus and mixer architecture, ducking, adaptive music, SFX variation, beat sync; names Godot and Unity; an example mix target of −14 to −16 LUFS; no measurement, no licence check | 2026-10-01 |
| also read | elevenlabs/skills (vendor generation skills, no direction); opusgamelabs/game-creator `game-audio` (procedural Web Audio for browser games); a team-audio skill in Donchitos/Claude-Code-Game-Studios (search hit only, not read) | | 2026-09-28 / 2026-10-01 |

| Line | vs A1 | vs A2 | vs A3 | Reason |
|---|---|---|---|---|
| Direction (palette, SFX list per system, rundown) | beaten | beaten | met | A1 has a per-clip rundown only; A2 generates; A3 covers mixing and adaptive music, not a per-system list. Case TC1 |
| Generator briefs | met | met | out of scope | Brief per model family, with length limits and post steps. Case TC8 |
| Licence gate on model weights | beaten | beaten | beaten | A2 routes to AudioCraft and MusicGen (CC-BY-NC weights) with no gate; nobody checks. Cases TC2, native `license-gate-nc-weights` |
| Measured check on any file | met (ours is engine-free) | beaten | beaten | A1 measures inside Unity; A2 writes normalisation code; A3 measures nothing. Ours runs on any WAV, decodes the rest with ffmpeg. Cases TC5, TC6 |
| True peak, not sample peak | beaten | met | beaten | A1 reports peak dBFS; a sample meter misses intersample overs. Case TC6 |
| Godot import and loop rules | beaten | met | met | A1 is Unity; the Ogg/MP3 begin-only trap is checked in the brief and the script. Case TC3, native `trigger-ogg-loop-click` |
| Mix versus file loudness | beaten | beaten | beaten | A1 gives per-file targets; A2 normalises files; A3 gives a mix figure with no measurement. Ours follows ASWG-R001 items 9 and 10. Cases TC4, native `mix-vs-file-correction` |
| Generation itself | out of scope | out of scope | out of scope | comfyrunner or the user runs it; soundsmith never generates |

**Named margins.**

1. **Godot-first loops.** Import line per file; loop arithmetic to whole samples; the begin-only trap caught before import (TC3, `trigger-ogg-loop-click`).
2. **The licence gate.** NC weights refused for a commercial or undecided game; conditional licences named with their condition (TC2, `license-gate-nc-weights`).
3. **Whole-mix loudness.** Platform targets on a capture of play; files held to true peak and category consistency (TC4, `mix-vs-file-correction`, the script's spread check).

**Iterate proposals, built 2026-10-01** (owner standing rule: nothing deferred). Direction: the lorescribe motif-to-brief seam is in `palette-and-lists.md` (Motifs row, voice pronunciations) and `model-briefs.md`. Measurement: `mix` reports the EBU Tech 3342 loudness range and a low-end share below 150 Hz for listen line L9, both INFO lines with tests. Godot: the rundown's import column is written in the importer's own key names (`godot-import.md`, the hand-over line), which godotsmith's `intake` writes into the project. Licence gate: add rows as new open audio models appear (60-day stamp), an ongoing refresh rather than a deferral.

**Retire condition.** Retire soundsmith if a maintained public skill covers Godot audio direction with a measured check on any file and a model licence gate (for example, a Godot port of A1 with a licence step). Then keep a pointer to it.

**Verdict: PARITY + MARGIN.** A1 is the nearest rival in form and is Unity-bound with paid generation; A2 is wide but generates code and routes to non-commercial weights unchecked; A3 is direction-only with no proof.

## Injection check (2026-10-01)

skillspector stage 1 (`--no-llm`, audit A5) scored this member 57/100 HIGH from five pattern classes: an instruction-override string in a test fixture (`scripts/test_audio_post.py`), four owner-run `sudo` installs in `references/install-walkthrough.md`, no `allowed-tools` key (which grants nothing on the live docs), and the declared `ffmpeg` subprocess (list-form argv, `-nostdin`, no window). Read by file role and matched string, zero are runtime findings. The direct read wins over the headline.

## Unverified

- ROCm support for Stable Audio Open, Woosh and Stable Audio 3 Medium (the runner's concern, not this skill's).
- The script's decode path through ffmpeg was not exercised on the build machine (ffmpeg absent); its absence path is tested.
- Forum and user complaints for this job were not read; the niche comes from READMEs and docs.
