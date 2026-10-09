# Measure: audio_post.py (Audit)

`scripts/audio_post.py` is run, never read into context. Python 3, standard library only. It measures any audio file, whatever made it. It reads WAV itself (PCM 8, 16, 24, 32-bit; float 32 and 64-bit; the extensible header). Any other format (Ogg Vorbis, MP3, FLAC) is decoded by ffmpeg when ffmpeg is on PATH, into a temporary folder that is removed on exit; without ffmpeg that file is `NOT-RUN` and the report says so. Installing ffmpeg is the user's step (`install-walkthrough.md`).

It never writes, moves or edits a source file. It never prints metadata text: the report lists chunk ids (`LIST`, `smpl`, `bext`) and nothing inside them, because tag text is data and can carry anything.

## Contents

1. Commands
2. Checks and thresholds
3. Exit codes and output
4. The fix table
5. No shell

## 1. Commands

```
python scripts/audio_post.py measure <file>... [--category sfx|ui|voice|music|ambience|any]
       [--loop] [--loop-begin N] [--loop-end N]       # loop points in samples; end is exclusive
       [--target-lufs X] [--tolerance LU]             # an owner's house rule, never a platform figure
       [--spread LU] [--full-tp] [--json]
python scripts/audio_post.py mix <capture> [--platform console|portable] [--full-tp] [--json]
```

- Pass every file of one category in one `measure` call: three or more files get the category spread check.
- `--loop` checks the whole file as a loop. A WAV with a `smpl` loop is checked at those points without any flag.
- `mix` is for a recording of the master output during play (`loudness.md`), never for one asset.
- Speed: pure Python. A short SFX takes well under a second; a three-minute stereo track takes tens of seconds. `--full-tp` interpolates every sample pair and is slower.

## 2. Checks and thresholds

| Id | Status | Rule |
|---|---|---|
| `true-peak` | FAIL above −1.0 dBTP | 4x oversampled estimate around the loudest samples |
| `clipping` | FAIL on any run | 3 or more consecutive samples at full scale in a channel |
| `silent` | FAIL | nothing above −50 dBFS in the whole file |
| `empty` | FAIL | no frames in the data chunk |
| `dc-offset` | WARN above 0.005 | the largest per-channel mean |
| `sample-rate` | WARN above 48 kHz | no audible benefit in a game |
| `integrated` | NOT-RUN under 400 ms | integrated loudness undefined; momentary max and RMS stand in |
| `dual-mono` | WARN | stereo with identical channels: Force Mono halves the file |
| `channels` | WARN | stereo where the category is usually mono (UI, SFX, voice) |
| `leading-silence` | WARN over 5 ms (UI), 10 ms (SFX), 50 ms (voice) | delay between the trigger and the sound |
| `loop-seam` | FAIL | the step across the loop point is larger than twice every step within 10 ms either side, and above −50 dBFS |
| `loop-level` | WARN over 3 dB | RMS of the last 50 ms against the first 50 ms after the loop begin |
| `loop-gap` | WARN over 20 ms | silence at the seam |
| `begin-only-loop-end` | FAIL | a loop end asked of an Ogg or MP3 file (Godot keeps only an offset) |
| `category-spread` | WARN over 3 LU | distance from the batch median (integrated, or momentary max when any file is short) |
| `target` | FAIL outside the tolerance | only with `--target-lufs` |
| `mix-console` / `mix-portable` | FAIL outside ±2 LU of −24 / −18 | whole-mix capture only |
| `capture-length` | WARN under 30 minutes | whole-mix capture only |
| `loudness-range` | INFO (no pass line); NOT-RUN under one 3 s block | whole-mix capture only: EBU Tech 3342 LRA in LU (short-term blocks, gates at −70 LUFS and 20 LU below the gated mean, 95th minus 10th percentile). Read it against the game's dynamics: a near-zero LRA on a whole session of play is a flattened mix, a very wide one makes quiet lines inaudible on a portable |
| `low-end-share` | INFO (no pass line) | whole-mix capture only: energy below 150 Hz as a share of all energy, in dB (fourth-order low-pass). Feeds listen line L9: a large share means impacts and drones carry little on a small speaker, so check them there |
| `decode` | NOT-RUN | not a WAV and no ffmpeg |

Measured values printed for every file: sample peak (dBFS), true peak (dBTP), RMS (dBFS), integrated, momentary max and short-term max (LUFS), leading and trailing silence (ms), DC offset, clipped runs, the chunk ids, and the loop points with their source (arguments, `smpl` chunk, or whole file).

## 3. Exit codes and output

`0` no FAIL · `1` at least one FAIL · `2` a usage error or a file that could not be read (status `ERROR`). WARN and NOT-RUN never change the exit code; the report counts them. INFO lines carry a measured value with no pass line and are not counted. `--json` prints the same report as JSON (minus infinity as the string `"-inf"`). The last line of the text report is a reminder that the listen is the user's.

## 4. The fix table

Cheapest first: an import setting, then an edit written to a **new file**, then a regenerate.

| Finding | First fix | Then |
|---|---|---|
| `true-peak` FAIL | lower gain on a new file by the overshoot + 0.5 dB | a true-peak limiter in the user's editor |
| `clipping` | regenerate or re-record (clipping cannot be undone by gain) | a lower input gain at the source |
| `leading-silence` | trim the head on a new file (Godot Trim works for one-shots) | — |
| `dual-mono` | Force Mono on import | export mono at the source |
| `loop-seam` | re-cut at the computed loop length or a zero crossing; a few-ms crossfade at the seam | regenerate with a loop-friendly prompt |
| `loop-level` | re-cut where the tail and head match | regenerate |
| `loop-gap` | cut the silence (Trim is off for loops) | — |
| `begin-only-loop-end` | cut the file so it ends at the loop end | use WAV for that loop |
| `category-spread` | gain the outlier on a new file toward the median | check the brief asked for the same distance and intensity |
| `mix-*` FAIL | adjust bus volumes, then re-capture | per-category gain, then re-capture |
| `dc-offset` | high-pass at a few Hz on a new file | — |

Every edit command is shown to the user and runs on their yes. The source file is never overwritten; the new file name carries a suffix (`_fixed`, `_mono`, `_cut`).

## 5. No shell

With no shell, hand back the exact command for the user to run and stop. If the user reads numbers off their own meter instead, score those numbers against section 2, label every value "owner-read", and mark the checks the meter cannot give (true peak, seam step) `NOT-RUN`.
