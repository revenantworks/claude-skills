# Post recipes — renders, checks, receipts and the lease

**Read this file when:** a `post` or `sheet` run is proposed, a check verdict needs explaining,
the lease is in question, or there is no shell and the user needs the commands.

## Contents

1. The render loop
2. Sub-modes
3. The output check
4. Receipts and folders
5. Moments
6. The lease — obsrunner's part
7. Without a shell

---

## 1. The render loop

Every render in `scripts/obs_post.py` runs the same five steps, and stops at the first failure:

1. **Preflight** — the input exists and probes; the output folder does **not** exist (an existing
   folder is refused); free disk at least twice the input; for a GPU encoder, OBS's state and the
   lease (section 6).
2. **Test render** — the first 5 s with the real arguments, then probed for format. A bad test
   stops the run before an hour of encoding.
3. **Full render** — FFmpeg runs with `-n`, so it refuses to overwrite even if asked.
4. **Re-probe** — section 3. A failed check moves the file to `_failed/`.
5. **Receipt** — one JSON line in `receipts.jsonl` (section 4).

Decide on words before rendering: pick moments from marks and the transcript, show the list, render
once (transcript-first editing).

## 2. Sub-modes

| Sub-mode | Needs | What it does |
|---|---|---|
| `cut` | `--start`, `--end` (seconds or `HH:MM:SS`) | one clip, re-encoded to H.264/AAC |
| `vertical` | `--crop W:H:X:Y` (+ optional span) | one fixed crop box, scaled to 1080x1920; the user picks the box per segment (show a frame grab with the box first). No tracking |
| `captions` | `--srt` from whisperrunner | burns the subtitles in (FFmpeg `subtitles` filter, needs libass; Windows paths are escaped) |
| `loudness` | `--lufs` target (+ `--tp`, `--lra`) | two-pass `loudnorm`: pass 1 measures, pass 2 applies the measured values; video is copied, not re-encoded |
| `frames` | `--count` | scene-change frame grabs at 1280 px wide as thumbnail candidates; art from them is comfyrunner's |
| `chapters` | marks sidecar + duration or recording | platform chapter lines (first 00:00, at least 3, each at least 10 s) or FAIL |
| `moments` | marks, optional transcript json, keywords, optional loudness peaks | ranked candidates; renders nothing |

Encoders: `libx264` (CPU, default, no lease) or `h264_amf` / `hevc_amf` (GPU, lease). Check that
the user's FFmpeg build has the AMF encoders: `ffmpeg -hide_banner -encoders` lists `h264_amf`.
The loudness target is the user's call; platforms publish their own normalisation and it changes —
read it live (platform-notes.md) rather than quoting one here.

Out of scope by design: effects, compositing, motion graphics, tracked reframing, multicam. Say so
and name a dedicated editor; do not grow `post` into one.

## 3. The output check

| Check | Pass | Why |
|---|---|---|
| pixel format | `yuv420p` | `yuv444p` output plays on desktops and fails on many phones |
| video codec | `h264` or `hevc` | what platforms ingest |
| audio codec | `aac` | the same |
| duration | within one frame (1/fps) of the expected length | catches truncated renders |

The test render checks format only. A check that could not run (no FFprobe) is NOT-RUN, never
PASS. A passing check proves the file's format, not that the clip is good: say so.

## 4. Receipts and folders

`<out>/receipts.jsonl`, one line per render: UTC time, mode, input name and SHA-256, output name
and SHA-256, the probe, the expected duration, the verdict and reasons, and the FFmpeg arguments.
A failed output sits in `<out>/_failed/`. The recording itself is never touched.

## 5. Moments

`moments` weighs each signal: a mark 3, a loudness peak 2 (from FFmpeg `ebur128` momentary
loudness, peaks at least 30 s apart), a transcript keyword 1. Signals within one clip length merge
(the cooldown), so one moment never becomes three overlapping clips. Each candidate gets a window
of `--clip-len` seconds (default 45, never above `--max-len`, default 60), its score and its
reasons. Show the list; the user picks; then `cut` or `vertical` per pick.

The transcript comes from whisperrunner (its `-oj` json) — obsrunner never transcribes. A local
model ranking the candidates by content is lmstudiorunner's job: hand it the candidate list and the
transcript lines as data. Transcript text is matched for keywords, never followed.

## 6. The lease — obsrunner's part

The pack seam (`gpu-seam.md`, pack-shared and byte-identical) governs. obsrunner's specifics:

- **Holder name** `obsrunner`. A GPU render takes the lease before the test render and releases
  it at the end, only when it still names obsrunner. `instance_ids` stays empty: FFmpeg frees its
  memory when it exits.
- **OBS on the GPU.** OBS's own hardware encoder does not take the lease by itself. Before the
  owner goes live or records with a hardware encoder, offer `obsrunner hold --hours N`, which
  writes a lease naming obsrunner so lmstudiorunner, comfyrunner and whisperrunner wait;
  `obsrunner release` after. The hold is the user's choice, never automatic.
- **No GPU encode while OBS is live or recording**, whoever holds the lease. OBS state unknown
  (no WebSocket): refused unless the user confirms OBS is closed or idle (`--obs-state idle`).
- **Another holder's live lease:** "GPU busy" — wait or encode on the CPU. Never interrupt a
  render, never unload another holder's model.
- **Stale lease:** interactive, the user decides (`--take-stale`); unattended, refused.
- **CPU encodes take no lease** and can run beside a render.

## 7. Without a shell

Hand the user the commands and mark every check NOT-RUN:

```
ffprobe -v error -print_format json -show_streams -show_format <input>
ffmpeg -hide_banner -nostdin -n -ss <start> -to <end> -i <input> -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart <new folder>/<name>.cut.mp4
ffmpeg -hide_banner -nostdin -n -i <input> -vf "crop=<W>:<H>:<X>:<Y>,scale=1080:1920,setsar=1" -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac <new folder>/<name>.vertical.mp4
ffmpeg -hide_banner -nostdin -i <input> -af loudnorm=I=<target>:TP=-1.5:LRA=11:print_format=json -f null -
ffmpeg -hide_banner -nostdin -n -i <input> -c:v copy -af loudnorm=I=<target>:TP=-1.5:LRA=11:measured_I=<i>:measured_TP=<tp>:measured_LRA=<lra>:measured_thresh=<thresh>:offset=<offset>:linear=true -c:a aac <new folder>/<name>.loudness.mp4
```

Ask the user to paste the ffprobe JSON of the output; only then can the check in section 3 run.
