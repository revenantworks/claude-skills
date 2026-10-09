# Trigger evals — revenantworks-localops-whisperrunner

Counts: 22 queries (11 should, 11 should-not, 3 pairs)

> Provenance: written for 0.1.0 (2026-10-01) against the description as built. **Authored, not
> run.** Read each query cold against name + description only and route it. The native
> `claude plugin eval` cases in this folder run two of these rows (Y1 `trigger-srt-subtitles`,
> N1 `near-miss-voiceover`) plus three behaviour cases from `test-cases.md` (T2, T3, T8). **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

22 queries: 11 should fire, 11 should not (Y11 and N11 added in P1e2 for the obsrunner seam).

**Re-anchored to the K6b description cut, 2026-10-08 (commit b338715):** every row re-read against the cut text; row wording only, no row added, removed or flipped; a row whose routing words left the description says so in its reason. A reader re-read, not a cold judge: the `tools/blind_queries.py` cold re-judge is still owed.

Should-fire ids renamed S<n> to Y<n> on 2026-10-08: S<n> names a source in SOURCES.md (observation 0305).

## Should fire

| # | Query | Expected |
|---|---|---|
| Y1 | "Transcribe the meeting recording in my Downloads folder (meeting.m4a) into srt subtitles, on this machine." | fire |
| Y2 | "Make subtitles for this mp4 locally, nothing goes to the cloud." | fire |
| Y3 | "Why did whisper run on my CPU? I have a GPU and it took forever." | fire |
| Y4 | "Which whisper model fits a 16 GB card, and should I use the turbo one?" | fire |
| Y5 | "The transcript just repeats 'thank you' over and over for the last ten minutes." | fire |
| Y6 | "Batch transcribe my voice-notes folder overnight and only keep the ones that came out right." | fire |
| Y7 | "How long will it take to transcribe these 40 podcast episodes on my own PC?" | fire |
| Y8 | "The transcript stops at minute 12 but the recording is 45 minutes long." | fire |
| Y9 | "whisperrunner audit" | fire |
| Y10 | "Can I transcribe an interview while ComfyUI is rendering? They share the one GPU." | fire |
| Y11 | "Make an srt caption file for last night's OBS recording, stream.mkv." | fire |

## Should not fire

| # | Query | Expected | Goes to |
|---|---|---|---|
| N1 | "Generate a 30-second voice-over for the game trailer locally with ComfyUI." | no fire | comfyrunner |
| N2 | "Write the sound brief for the forest level: ambience, footsteps, the mix." | no fire | soundsmith |
| N3 | "Summarise this transcript text file with the local model in LM Studio." | no fire | lmstudiorunner |
| N4 | "Send this file to a cloud speech-to-text API and give me the transcript." | no fire | none (cloud; out of scope) |
| N5 | "Render a five-second video clip of a campfire in ComfyUI." | no fire | comfyrunner |
| N6 | "Translate this English srt file into Spanish, keep the timings." | no fire | none (a text job) |
| N7 | "Shift every timestamp in my srt file two seconds later." | no fire | none (subtitle edit, no speech) |
| N8 | "Scan the transcripts folder for personal data before I publish it." | no fire | the pack's leak scanner |
| N9 | "Set up a nightly schedule with a kill switch for my transcription batch." | no fire | agentwright |
| N10 | "What's the best cloud speech-to-text service for a mobile app?" | no fire | a research verdict |
| N11 | "Cut the three best moments from my OBS recording into vertical clips with burned-in captions." | no fire | obsrunner |

## Edge notes

- **Sharpest pair: Y10 vs N5.** Both name ComfyUI. Y10 asks to *transcribe* while it renders
  (whisperrunner, through the lease); N5 asks for a render (comfyrunner). The object produced
  decides: text from speech, or pixels and sound from a graph.
- **N3 vs Y8.** A transcript is in both. Doing something *with* finished text is lmstudiorunner's;
  a transcript that is wrong *as a transcript* is whisperrunner's.
- **Y11 vs N11.** Both start from an OBS recording. A caption *file* is whisperrunner's; clips,
  cuts and captions burned into video are obsrunner's, which hands the recording here for the file.
- **N9.** The batch is whisperrunner's to run; the schedule and kill switch around it are
  agentwright's.
- **Tuning rule.** Misses on the yes-set → make the trigger list pushier (add the user's words).
  Fires on the no-set → tighten the boundary sentence, never widen it.
