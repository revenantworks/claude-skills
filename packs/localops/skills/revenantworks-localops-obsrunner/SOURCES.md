# Sources — revenantworks-localops-obsrunner

> **Last verified: 2026-10-01** — the primary sources and the parity register below (calendar
> surface, 90 days, declared in `volatile.json`). The incumbent scan and the host comparison
> were run on 2026-10-01 by two research passes; OBS release facts, settings keys, encoder ids and
> the client package were re-read raw at the build the same day.

## Primary — the program this skill drives

- **OBS Studio releases** (GitHub releases API), read 2026-10-01: 33.0.0-beta5 (2026-10-01),
  33.0.0-beta4 (2026-09-25), 32.2.2 stable (2026-08-14), 32.2.1 (2026-07-24). 32.2.2 notes: AMF
  B-frame offset fix ("could cause streams to disconnect"). 33 notes: missing-encoder check,
  first-party plugins in a `core` folder, a new third-party plugin location.
- **obs-studio source**, raw, read 2026-10-01: `frontend/utility/AdvancedOutput.cpp` and
  `SimpleOutput.cpp` (the `[AdvOut]` and `[SimpleOutput]` keys, `streamEncoder.json`,
  `recordEncoder.json`, `amd` → `h264_texture_amf`, `amd_hevc` → `h265_texture_amf`);
  `plugins/obs-ffmpeg/texture-amf.cpp` (encoder ids, registration gated by the AMF test, settings
  keys and defaults: `rate_control` CBR, `bitrate` 6000, `bf` 2, `keyint_sec` unset).
- **obs-websocket**, read 2026-10-01: README (GPL-2.0, port 4455, auth on with a generated
  password, bundled since OBS 28, `--websocket_port`, `--websocket_password`,
  `--websocket_ipv4_only`); `docs/generated/protocol.md` (rpcVersion 1, request names used here);
  `src/requesthandler/RequestHandler_Config.cpp` (`GetStreamServiceSettings` returns the whole
  service settings, key included); commit of 2026-09-28 (no server in Safe Mode).
- **obsws-python** (PyPI JSON), read 2026-10-01: 1.8.0 (2025-07-01), GPL-3.0-only, Python ≥ 3.9,
  depends on `websocket-client`; `ReqClient(host, port, password, timeout)`, `send(param, data,
  raw)`, `OBSSDKError` / `OBSSDKTimeoutError` / `OBSSDKRequestError`.
- **AMD encode by generation**: Video Core Next (VCN 3.0: H.264 and HEVC encode, AV1 decode
  only), GPUOpen AMF AV1 encoder page, a streaming app's AMD support notes (AV1 on RX 7000/9000),
  all read 2026-10-01.

## Platforms and policy (read 2026-10-01; the dated copy is `references/platform-notes.md`)

- A major video platform's help on chapters and thumbnails; its `videos.insert` docs (upload
  quota, private-only before an audit) and developer policies (consent for automated actions, no
  download or caching of platform video).
- A streaming platform's API reference (clips, markers, schedule, chat). Its developer agreement
  did not render for the fetcher: **unverified**.
- Enhanced Broadcasting and enhanced-RTMP guides (RX 6000 support, HEVC ingest, 2 s keyframes,
  CBR); disclosure and music-muting guidance (secondary sources; never legal advice).

## Claude platform

- **Plugin evals** — code.claude.com/docs/en/plugin-evals, read 2026-10-01: case layout
  (`evals/<case>/prompt.md` + `graders/*.md`), `prompt.md` fields, grader types (`tool_used` with
  `input_match`, `min`/`max`, `arm: both`; `regex` with `target: last_message` default; `llm`).
  Every run bills the plan; not run here.

## Sibling contracts

- `references/gpu-seam.md` and `scripts/gpu_preflight.py` — pack-shared, copied byte-identical
  from whisperrunner (itself identical to comfyrunner) at the 0.1.0 build. obsrunner's holder
  name, hold/release and the OBS-state rule live in `references/post-recipes.md`, section 6.
- whisperrunner (transcripts, srt), comfyrunner (art), lmstudiorunner (local ranking),
  commscribe (all words), brandscribe (overlay palette), duckrunner (analytics CSVs), soundsmith
  (game audio), trustwarden (plugin vetting), keywarden (password inventory), gatewarden (a
  go-live block hook, follow-up) — named, never required.

## Parity register

Incumbents (checked 2026-10-01; re-scanned live the same day by unit PR. Also scanned: sbroenne/mcp-server-obs (.NET), struktured-labs/obs-twitch-mcp, royshil/obs-mcp; none has a read-only default, key masking or a GPU lease):

- **OBS_MCP** (github.com/xDarkzx/OBS_MCP) — Python MCP server, 148 tools over the whole v5
  protocol, frame-drop cause diagnosis; no confirm step, no read-only mode; Apache-2.0.
- **kinocut** (github.com/KyaniteLabs/kinocut) — guardrailed FFmpeg editing MCP and CLI:
  preflight, loudness and black-frame gates, hash receipts, vertical packages; 201 MCP tools;
  Windows issues (default-font crash, yuv444p output); no GPU-lease view; Apache-2.0.
- **openshorts** (github.com/mutonby/openshorts) — long video to 9:16 shorts: faster-whisper,
  LLM moment pick (cloud by default), face-tracked reframe; Docker; NVIDIA-only GPU; posts
  through a third-party service; MIT core.
- Also scanned: obs-mcp (Node), a Linux-only OBS plugin for Claude Code, a combined OBS and chat
  MCP with moderation tools, video-use, clipper and FFmpeg skills, reframe CLIs.

| Line | OBS_MCP | kinocut | openshorts | obsrunner | Case |
|---|---|---|---|---|---|
| Drive OBS (scenes, sources, outputs) | met | out of scope | out of scope | met (fewer requests, by mode) | T4 |
| Audit settings against this GPU and ingest rules | beaten | out of scope | out of scope | **beaten** | T1, `behaviour-av1-audit` |
| Stream health diagnosis | met | out of scope | out of scope | met (cause buckets adopted) | T5 |
| Never go live, never read the key, confirm writes | beaten | n/a | n/a | **beaten** | T2, T3, `behaviour-go-live-refusal` |
| GPU lease with other local AI jobs | beaten | beaten | beaten | **beaten** | T6, T7, `behaviour-lease-live` |
| Cut, loudness, burn captions | n/a | met (deeper) | met | met (streamer subset) | T8 |
| Gates and receipts on renders | n/a | met (adopted) | beaten | met | T8, T9 |
| Vertical reframe | n/a | met | met (tracking) | met (fixed crop, owner picks) | T8 |
| Moment finding | n/a | partial | met (cloud default) | **beaten on locality** | T10 |
| Upload and publish | n/a | n/a | met (third party) | out of scope in v1 (sheet) | T12 |
| Effects, compositing, tracked reframe | n/a | met | n/a | out of scope | T20 |

**Margins.** (M1) Live-safe OBS driving: read-only default, deny list before send, confirm per
write, masked output — T2, T3, T4, T15. (M2) One-GPU studio: OBS encoding, local LLM, image
generation and Whisper share one card through the pack lease — T6, T7, T17. (M3) Fully local on
AMD: marks, whisper.cpp transcripts, loudness peaks, AMF or CPU encode, no cloud key — T1, T10.

**Iterate.** An optional platform API mode (markers, clips, private upload) once the user has
made the API apps; tracked reframe through an adopted, vetted tool if fixed crops prove weak; a
gatewarden hook that blocks the deny list for every Claude tool call; read record chapters back
when the format support settles.

**Retire condition.** An OBS-maintained or widely used agent integration that ships read-only
defaults, stream-key masking and a GPU-sharing view, together with a local AMD clip pipeline.

**Verdict: PARITY + MARGIN** for the streamer subset; general editing is out of scope by design.
