# Changelog — revenantworks-gamedev-soundsmith

## [1.0.0] — 2026-10-01

First public release. Game audio direction judged by numbers. It never generates or processes audio.

Description cut to about 600 characters, main use case first (2026-10-08).

### What it does

- A sound palette, an SFX list per game system and a rundown line per file, with category defaults.
- Music and voice briefs with tempo, key and loop points.
- Generator briefs for audio models that pass a model licence gate: non-commercial weights are
  refused for a commercial game.
- Godot 4 import settings per file (WAV or Ogg Vorbis, loop mode, mono, sample rate), with loops cut
  to Godot's rules (Ogg Vorbis and MP3 keep a loop offset but no loop end).
- Loudness applied the way the game-audio recommendation says: the platform figure to the whole mix,
  consistency to the single file, plus the per-file correction.
- A measured check of any audio file: loudness, true peak, clipping, silence and the loop seam.

### Entry points

- Direct (default) — palette, per-system SFX list and rundown.
- `brief` — a licence-gated brief for a model family, handed to a runner or the owner.
- `audit` — a measured report per file, findings ordered by cheapest fix.
- `test` — the one-scene listen procedure and a scored checklist.

### Scripts

- `scripts/audio_post.py` (Python 3, standard library only, read-only; run, not read):
  `measure` per-file checks with a category spread check for three or more files; `mix` a whole-mix
  capture against a console or portable target, with loudness range and low-end share as info lines.
- `scripts/test_audio_post.py`: 30 tests, every fixture generated in code.
- Optional, declared helper: ffmpeg on PATH decodes non-WAV files; without it those files report
  NOT-RUN.

### Safety rules

- Direction, not DSP: no generation, no processing, no installs, no network.
- Without a shell it hands back the exact command and marks scores from read-off numbers NOT-RUN.
- `references/install-walkthrough.md`: owner-run steps for Python and the optional ffmpeg.

### Integrations

- comfyrunner renders a brief on a local model; godotsmith writes the import line into the project
  (its `intake` entry) with the bus layout and player code; whisperrunner transcribes speech;
  lorescribe owns names, motifs and pronunciations. Each is named, never required.
- Dated references: model briefs (60 days), Godot import (90 days), parity register (90 days).

### Evals

- 20 trigger queries (10 should / 10 should-not), 13 assertion cases with a `Without:` line each, and
  five native `claude plugin eval` cases.
