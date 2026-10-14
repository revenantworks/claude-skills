# Trigger evals — revenantworks-localops-obsrunner

Counts: 20 queries (10 should, 10 should-not, 1 pairs)

> Provenance: written for 0.1.0 (2026-10-01) against the description as built (999 characters).
> **Authored, not run.** Read each query cold against name + description only and route it. The
> native `claude plugin eval` cases in this folder run two of these rows (Y1
> `trigger-dropped-frames`, N1 `near-miss-podcast-srt`) plus three behaviour cases from
> `test-cases.md` (T1, T2/T3, T6). **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

20 queries: 10 should fire, 10 should not.

**Re-anchored to the K6b description cut, 2026-10-08 (commit b338715):** every row re-read against the cut text; row wording only, no row added, removed or flipped; a row whose routing words left the description says so in its reason. A reader re-read, not a cold judge: the `tools/blind_queries.py` cold re-judge is still owed.

Should-fire ids renamed S<n> to Y<n> on 2026-10-08: S<n> names a source in SOURCES.md (observation 0305).

## Should fire

| # | Query | Expected |
|---|---|---|
| Y1 | "My stream keeps dropping frames every few minutes and the stats dock shows encoding lag. What's wrong?" | fire (check) |
| Y2 | "Audit my OBS setup for this graphics card before tonight's stream." | fire (audit) |
| Y3 | "Cut the three best moments from last night's recording into vertical clips with burned-in captions." | fire (post) |
| Y4 | "Mark this moment, it was a great play." (said while OBS is recording) | fire (mark) |
| Y5 | "Make YouTube chapters from the markers I dropped during the stream." | fire (post chapters) |
| Y6 | "Switch OBS to the BRB scene and mute the desktop audio." | fire (set) |
| Y7 | "Can I run a ComfyUI render while I'm streaming? OBS uses the same GPU." | fire (lease) |
| Y8 | "Normalize the loudness of this VOD to -14 LUFS without re-encoding the video." | fire (post loudness) |
| Y9 | "obsrunner status" | fire |
| Y10 | "Go live now and paste my stream key so I can check it's right." | fire, then refuses both actions and hands the user the button |

## Should not fire

| # | Query | Expected | Goes to |
|---|---|---|---|
| N1 | "Transcribe this podcast episode to an srt file on my machine." | no fire | whisperrunner |
| N2 | "Write a title and a description for my last VOD." | no fire | commscribe |
| N3 | "Generate a thumbnail background image of a neon city." | no fire | comfyrunner |
| N4 | "Time out the spammer in my chat and add a !discord command." | no fire | out of scope (platform tools or a bot app; the description says it never moderates chat) |
| N5 | "How many views did my streams get last month? Here's the analytics CSV export." | no fire | duckrunner |
| N6 | "Design the sound mix and footstep audio for my game's forest level." | no fire | soundsmith |
| N7 | "Run a 7B model in LM Studio to summarise these notes." | no fire | lmstudiorunner |
| N8 | "Is this OBS plugin I downloaded from a forum safe to install?" | no fire | trustwarden |
| N9 | "Add motion-graphics titles and a picture-in-picture effect to my edit in a video editor." | no fire | out of scope (an editor) |
| N10 | "Set up a Docker container for a self-hosted clip app." | no fire | dockerrunner |

## Edge notes

- Sharpest pair: **obsrunner ↔ whisperrunner**. "Burn captions into this clip" is obsrunner
  (it hands whisperrunner the recording for the srt); "make an srt" alone is whisperrunner.
- **obsrunner ↔ comfyrunner**: frame grabs are obsrunner's; generating any image is comfyrunner's.
- N8 is a near-miss on the word OBS; the job is vetting, not driving.
- Y10 must fire: the refusal is the skill's job, and an unrouted "go live" is the risk.
- Tuning rule: misses on the yes-set → make triggers pushier; fires on the no-set → tighten the
  boundary sentence.
