# The listen test (Test)

The script proves the numbers; this test is where taste is judged, by the user. soundsmith runs the procedure and scores the user's answers. It never answers a line for them.

## Set-up

1. **One scene** where every category plays: a stretch of play with UI use, repeated SFX (steps, hits), at least one one-shot event, the music bed, the ambience, and a voice line if the game has voice.
2. **Two playback paths**: the speakers the game is aimed at (TV, laptop, phone speaker) and headphones.
3. **The game's own volume**: master at its default; no system enhancers.
4. **Length**: at least two full passes of the music loop, so the seam is heard twice.
5. Audit first: run `audio_post.py` on the files in the scene, so the test does not spend a listen on a measured fault.

## Checklist

The user answers each line yes or no, per playback path.

| # | Line | A "no" usually breaks |
|---|---|---|
| L1 | Dialogue (or the most important cue) is understood every time without raising the volume | loudness intent; ducking |
| L2 | No category jumps out unexpectedly; repeated sounds do not stand out one by one | category spread |
| L3 | Repeated sounds do not become tiring or obviously identical | variation count |
| L4 | The music loop seam is not heard (no click, gap, or jump in level) | law 4; loop checks |
| L5 | UI sounds feel instant on the click | leading silence |
| L6 | Nothing distorts at the loudest moment | true peak; clipping |
| L7 | The palette holds: nothing sounds from another game | palette Banned row |
| L8 | Motifs land where the palette says they do | palette Motifs row |
| L9 | On the small speaker, low-end sounds (impacts, drones) still read | spectral balance (`mix` reports `low-end-share`); brief |

## Scoring

- Each "no" becomes a finding: the line, the playback path, the file or category the user names, and the law or rule it breaks.
- A line not listened to is `not run`, never a pass.
- The scene passes when every line is "yes" on both playback paths.
- Findings go to the fix table in `measure.md`, cheapest first. A finding with no measured cause (L3, L7, L8) goes back to the palette or the brief.
