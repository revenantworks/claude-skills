# Godot 4 audio import and loops

Last verified: 2026-10-01 against the Godot docs page "Importing audio samples" (page version 4.7). Re-check on a 90-day cadence or when a Godot minor release changes the import dock. Writing these settings into a project (`.import` files, presets, bus layout, player code) is godotsmith's; this file says which setting each file needs.

## Format choice

The docs recommend WAV for short, repeated sound effects; Ogg Vorbis for music, speech and long effects; MP3 where CPU is tight on mobile and web. They also say 24-bit gives no audible benefit in a game, rates above 48 kHz give none unless audio is stretched, and voices are acceptable at 22 kHz.

## WAV import options

| Option | Values | soundsmith default |
|---|---|---|
| Force → Mono | on/off; halves the size | on for UI, SFX, voice; on for any dual-mono stereo file (L equals R) |
| Force → 8 Bit | on/off; not recommended | off |
| Force → Max Rate | a rate in Hz | 44100 or 48000; 22050 acceptable for voice |
| Edit → Trim | removes silence below −50 dB (after normalising) | on for one-shots; **off for loops** (it moves the seam) |
| Edit → Normalize | peaks to 0 dB | **off**: it breaks category consistency and the −1 dBTP ceiling |
| Edit → Loop Mode | Detect from WAV, Disabled, Forward, Ping-Pong, Backward | Disabled for one-shots; Forward for loops; Detect from WAV when the file carries a `smpl` loop |
| Edit → Loop Begin / Loop End | samples from the file start; End −1 = end of file | from the rundown |
| Compress → Mode | PCM, IMA ADPCM, Quite OK Audio (default) | default; PCM for very short UI sounds when every sample matters |

`audio_post.py` reads a WAV `smpl` chunk and checks the seam at those points, so "Detect from WAV" can be verified before import.

## Ogg Vorbis and MP3 import options

| Option | Meaning |
|---|---|
| Loop | on/off |
| Loop Offset | **seconds** from the start where the loop restarts |
| BPM, Beat Count, Bar Beats | tempo metadata for interactive music |

**The begin-only trap.** There is a loop offset but no loop end: playback always runs to the end of the file, then jumps to the offset. A music loop that must end at bar 16 therefore needs a file that ends exactly at bar 16. `audio_post.py` fails a `--loop-end` on an Ogg or MP3 file with `begin-only-loop-end` for this reason.

## Loop arithmetic

```
loop seconds = bars × beats per bar × 60 / BPM
loop samples = round(loop seconds × sample rate)
```

Example (invented): 16 bars of 4/4 at 90 BPM = 64 beats × 60 / 90 = 42.6667 s; at 44100 Hz that is 1,881,600 samples. With an intro of 2 bars (5.3333 s), the file is intro + body = 18 bars long, the Ogg Loop Offset is 5.3333 s, and Beat Count is 72. A BPM that divides 60 × rate exactly keeps every beat on a whole sample (at 44100 Hz: 60, 75, 80, 90, 100, 120; 96 does not, it does at 48000 Hz). Otherwise round the loop length once, never per beat.

Cutting: when a generator returns a longer take, cut to the computed sample count at a zero crossing or with a fade of a few milliseconds into the seam, written to a new file. Then run `audio_post.py measure <new file> --loop --category music`.

## Seam checks before import

| Check | Script id | What fixes it |
|---|---|---|
| a step across the loop point | `loop-seam` | cut at a zero crossing or the computed bar length; a short crossfade at the seam |
| a level change across the loop point | `loop-level` | regenerate or re-cut so the tail and the head match |
| silence at the seam | `loop-gap` | trim the leading or trailing silence (Trim is off for loops, so cut the file) |

## The hand-over line for godotsmith

soundsmith decides each file's import settings; godotsmith writes them into the project and
guards them (its `intake` entry). So the rundown's import column is written in the
importer's own key names, ready to drop into the file's `.import` sidecar `[params]` with no
translation. Keys as the Godot 4.7 class reference spells them (verified 2026-10-01):

| Importer | Keys |
|---|---|
| WAV (`ResourceImporterWAV`) | `force/mono`, `force/8_bit`, `force/max_rate` with `force/max_rate_hz`, `edit/trim`, `edit/normalize`, `edit/loop_mode` (0 Detect from WAV, 1 Disabled, 2 Forward, 3 Ping-Pong, 4 Backward), `edit/loop_begin`, `edit/loop_end` (samples; −1 = end), `compress/mode` (0 PCM, 1 IMA ADPCM, 2 Quite OK Audio) |
| Ogg Vorbis (`ResourceImporterOggVorbis`) | `loop`, `loop_offset` (seconds), `bpm`, `beat_count`, `bar_beats` |

Examples (invented):

```
sfx_jump_01.wav   force/mono=true  edit/trim=true  edit/normalize=false  edit/loop_mode=1
amb_wind.wav      force/mono=false edit/trim=false edit/loop_mode=2 edit/loop_begin=0 edit/loop_end=-1
mus_theme.ogg     loop=true  loop_offset=5.3333  bpm=90  beat_count=72  bar_beats=4
```

An Ogg line never carries a loop end: the file is cut to end there (the begin-only trap).

## Other engines

The palette, the briefs, loudness and measurement are engine-free. Only this file is Godot's; for another engine, name its own import documentation and keep the rest.
