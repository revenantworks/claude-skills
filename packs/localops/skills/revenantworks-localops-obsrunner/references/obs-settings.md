# OBS settings — the dated facts the audit reads

> **Last verified: 2026-10-01** — calendar surface, 90 days (`volatile.json`). `obsrunner
> refresh` re-reads the sources named per section and restamps this file only. Everything here
> is a fact about OBS or the hardware, read on that date; the audit re-reads this machine live.

## Contents

1. Versions
2. Where the profile lives and what the audit reads
3. Encoder ids
4. Hardware encoders by AMD GPU generation
5. Streaming settings the audit checks
6. Plugins and OBS 33

---

## 1. Versions

- **Stable:** OBS Studio 32.2.2, published 2026-08-14 (GitHub releases API). **Beta:** 33.0.0-beta5,
  2026-10-01. Read the running version live: `obs_ws.py status` (GetVersion).
- obs-websocket is bundled since 28.0.0; it was at 5.7.4 on 2026-06-18.

## 2. Where the profile lives and what the audit reads

On Windows the profile folder is `%APPDATA%\obs-studio\basic\profiles\<profile>` (portable
installs keep it beside the program; ask the user which). Files:

| File | Keys read |
|---|---|
| `basic.ini` `[Output]` | `Mode` (Simple or Advanced) |
| `basic.ini` `[AdvOut]` | `Encoder`, `RecEncoder`, `RecFormat2`, `TrackIndex`, `VodTrackEnabled`, `VodTrackIndex`, `RecFilePath` |
| `basic.ini` `[SimpleOutput]` | `StreamEncoder`, `RecEncoder`, `RecFormat2`, `VodTrackEnabled`, `FilePath` |
| `basic.ini` `[Video]` | `BaseCX`, `BaseCY`, `OutputCX`, `OutputCY`, `FPSCommon` |
| `streamEncoder.json` | `rate_control`, `keyint_sec`, `bf` (Advanced mode) |
| `service.json` | `type` and `settings.service` only — the rest, stream key included, is dropped unread |

Sources: `frontend/utility/AdvancedOutput.cpp` and `SimpleOutput.cpp` (config keys and the
`streamEncoder.json` / `recordEncoder.json` names), read 2026-10-01.

## 3. Encoder ids

- AMD AMF (texture path): `h264_texture_amf`, `h265_texture_amf`, `av1_texture_amf`, each with a
  `*_fallback_amf` twin. Each registers only when OBS's AMF test reports the adapter supports it
  (`plugins/obs-ffmpeg/texture-amf.cpp`).
- Simple mode names: `amd` → `h264_texture_amf`, `amd_hevc` → `h265_texture_amf`; the AV1 name
  maps to `av1_texture_amf` (its string was not shown in the read; the audit matches any name
  containing `av1`).
- AMF settings keys and defaults: `rate_control` CBR, `bitrate` 6000, `preset` quality, `bf` 2
  (H.264 and AV1), `keyint_sec` with no default (0 = auto).
- Software: `obs_x264` / `x264` — no GPU limit applies.

## 4. Hardware encoders by AMD GPU generation

| Series | Architecture (video block) | Hardware encode |
|---|---|---|
| RX 5000 | RDNA 1 (VCN 2) | H.264, HEVC |
| RX 6000 | RDNA 2 (VCN 3) | H.264, HEVC — **no AV1 encode** (AV1 decode only) |
| RX 7000, RX 9000 | RDNA 3, RDNA 4 (VCN 4+) | H.264, HEVC, AV1 |

Sources: Video Core Next (VCN 3.0 encode list), GPUOpen AMF AV1 encoder page, a streaming app's
AMD support notes (AV1 only on RX 7000/9000), read 2026-10-01. Other vendors are not in the table:
the audit marks the encoder row NOT-RUN and asks the user to read the encoder list in OBS
Settings > Output.

**AV1 on an RX 6000 card** happens when a profile is copied from another machine. OBS will not
offer `av1_texture_amf` there; OBS 33 warns about missing encoders when a profile loads. The fix
is the HEVC or H.264 AMF encoder.

## 5. Streaming settings the audit checks

- **Rate control** CBR for live streaming; **keyframe interval** 2 s (the common platform ingest
  rule; platform-notes.md). An unset interval is a FAIL with that fix.
- **AMF B-frames:** 32.2.2 fixed "an issue with B-frame offset calculation in AMF that could cause
  streams to disconnect" (release notes). Older OBS with `bf` > 0 on AMF H.264 is a FAIL: update
  OBS or set B-frames to 0.
- **Recording format:** MKV or hybrid MP4 survive a crash; plain MP4/MOV do not (remux MKV after).
- **VOD track:** the VOD-only audio track must differ from the stream track, so music can stay off
  the archive. Off is reported as INFO, not a fail.
- **Disk free** at the record path: FAIL under 20 GB (`--min-free-gb`).
- **HEVC and multitrack:** HEVC over enhanced RTMP and multitrack Enhanced Broadcasting
  (RX 6000 and newer, driver 24.4.1+, OBS 30.2+) depend on the platform; check live before
  recommending them.

## 6. Plugins and OBS 33

OBS 33 moves first-party plugins into a `core` folder and gives third-party plugins a new install
location; legacy locations keep loading until 34.0 (33.0.0-beta5 notes). The install walkthrough
therefore says "read the plugin path live" for any plugin, and trustwarden vets a plugin first.
Re-verify this section when 33.0.0 ships as stable.
