# Loudness: the whole mix and the single file

Loaded for any loudness target or complaint ("too loud", "too quiet", "uneven", "what LUFS").

Volatile, event-driven: the figures here (and the copy in SKILL.md's laws) follow published recommendations that move rarely. Re-check them when a platform holder or a standards body revises one; no calendar cadence.

## The rule: the mix is measured as a whole

The published game-audio loudness recommendation (Sony ASWG-R001, read 2026-10-01) says audio content should be "measured as a whole" rather than per dialogue, effects or music (item 9), over at least 30 minutes of representative play (item 10). Its targets:

| Platform | Integrated loudness | True peak |
|---|---|---|
| Home console | −24 LUFS (±2 LU) | at most −1 dBTP |
| Portable | −18 LUFS (±2 LU) | at most −1 dBTP |

LKFS and LUFS are the same unit. These figures apply to a **capture of play** (the master output recorded while playing), measured with `audio_post.py mix <capture> --platform console|portable`. A mobile or PC game with no platform rule picks one of the two and says which.

## What a single file is held to

A single SFX, UI sound or music file is never measured against −24 or −18. It is held to:

1. **True peak at most −1 dBTP**, every file (a sample-peak meter misses the overs between samples; the script estimates them).
2. **Consistency within its category.** All footsteps sit close together; all UI clicks sit close together. The script's spread check flags a file more than 3 LU (default) from its batch's median, on integrated loudness when every file is at least 400 ms, otherwise on momentary maximum.
3. **No clipping, no DC offset, no surprise silence** at the start or the seam.

The balance *between* categories (dialogue over music, music over ambience) is set by the engine's bus volumes and ducking, then proven by the mix capture. Normalising every file to one number destroys that balance and is the classic mistake.

## Correcting a per-file target request

When asked "make every SFX −18 LUFS" (or any platform figure per file):

1. Say plainly that −18 is a whole-mix target for portable platforms, measured over at least 30 minutes of play.
2. Offer what a file can be held to: true peak at most −1 dBTP, and a category spread of ±3 LU (or the user's figure).
3. If the user still wants a per-file reference level for a category (some teams do, for consistency), record it as a house rule with `--target-lufs` and `--tolerance`, labelled as the user's rule, not a standard.

## Short files

Integrated loudness needs at least one 400 ms block. A file shorter than 400 ms has none: the script reports `integrated NOT-RUN` and the spread check falls back to momentary maximum or RMS. Never quote an integrated figure for a 200 ms click.

## Measurement notes

- Loudness follows ITU-R BS.1770: K-weighting, 400 ms blocks with 75 % overlap, an absolute gate at −70 LUFS and a relative gate at −10 LU. A 0 dBFS 1 kHz sine in one channel reads −3.01 LUFS; the script's tests pin that.
- True peak is a 4x oversampled estimate; it can read up to about 0.15 dB high near the top of the spectrum, which errs toward a FAIL, never toward a false PASS.
- Loudness range (LRA) is not measured by the script; a mix with very wide range is judged in the listen test.
