#!/usr/bin/env python3
"""audio_post.py - measure any audio file by numbers (soundsmith). Run, not read.

Stdlib only. Reads RIFF/WAVE directly (PCM 8/16/24/32-bit, IEEE float 32/64-bit, the
extensible header). Any other format (Ogg Vorbis, MP3, FLAC) is decoded to a temporary float WAV
by ffmpeg when ffmpeg is on PATH; without it that file is reported NOT-RUN. It does not matter
what made the file: a local model, a cloud API, a recorder, a sound library.

Never writes, moves or edits a source file. The only write is ffmpeg's temporary decode, inside a
temporary folder that is removed on exit. Metadata text (INFO tags, ID3, bext) is never printed:
the report lists chunk ids only, because tag text is data and can carry anything.

Subcommands
  measure FILE... [--category sfx|ui|voice|music|ambience|any] [--loop] [--loop-begin N]
                  [--loop-end N] [--target-lufs X] [--tolerance LU] [--spread LU] [--full-tp] [--json]
  mix FILE [--platform console|portable] [--full-tp] [--json]

Exit codes: 0 no FAIL; 1 at least one FAIL; 2 a usage error or a file that could not be read.

Methods: loudness per ITU-R BS.1770 (K-weighting, 400 ms blocks with 75 % overlap, absolute gate
-70 LUFS, relative gate -10 LU). True peak is a 4x oversampled estimate (windowed-sinc
interpolation) around the loudest samples; --full-tp interpolates every sample pair.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import statistics
import struct
import subprocess
import sys
import tempfile
from array import array
from pathlib import Path

VERSION = "0.1.0"

SILENCE_DBFS = -50.0        # Godot's import Trim threshold; also the "silent" line here
TRUE_PEAK_MAX = -1.0        # dBTP ceiling, ASWG-R001 item 7
CLIP_LEVEL = 0.999          # |sample| at or above this counts toward a clipped run
CLIP_RUN = 3                # consecutive samples at CLIP_LEVEL = one clipped run
DC_WARN = 0.005             # |mean| above this (about -46 dBFS) is a DC offset
MAX_USEFUL_RATE = 48000     # Godot docs: no audible benefit above 48 kHz
LOOP_GAP_MS = 20.0          # silence at a loop seam longer than this is an audible gap
SEAM_WINDOW_MS = 10.0       # window either side of a seam for the local step size
LEVEL_WINDOW_MS = 50.0      # window either side of a seam for the level-jump check
LEVEL_JUMP_DB = 3.0
SPREAD_LU = 3.0             # category consistency: distance from the batch median
TP_CANDIDATE_DB = 6.0       # oversample sample pairs within this many dB of the sample peak
PLATFORM_TARGETS = {"console": -24.0, "portable": -18.0}   # ASWG-R001 items 4 and 5
MIX_TOLERANCE = 2.0                                         # ASWG-R001: (+/-2) LKFS
MIX_MIN_MINUTES = 30.0                                      # ASWG-R001 item 10
CATEGORIES = {
    #            mono expected, max leading silence (ms) or None
    "sfx":      (True, 10.0),
    "ui":       (True, 5.0),
    "voice":    (True, 50.0),
    "music":    (False, None),
    "ambience": (False, None),
    "any":      (False, None),
}
BEGIN_ONLY_EXT = {".ogg", ".oga", ".mp3"}   # Godot: loop offset only, no loop end
WAV_EXT = {".wav", ".wave"}

# BS.1770 published K-weighting coefficients at 48 kHz (stage 1 shelf, stage 2 high-pass).
_K48 = ((1.53512485958697, -2.69169618940638, 1.19839281085285), (-1.69065929318241, 0.73248077421585),
        (1.0, -2.0, 1.0), (-1.99004745483398, 0.99007225036621))


class AudioError(Exception):
    """A file that cannot be read as audio. The message never carries file content."""


def db(x: float) -> float:
    return -math.inf if x <= 0 else 20.0 * math.log10(x)


def fmt_db(x: float | None, unit: str) -> str:
    if x is None:
        return "n/a"
    return f"-inf {unit}" if x == -math.inf else f"{x:.1f} {unit}"


# ---------------------------------------------------------------------------- reading

def read_wav(path: Path) -> dict:
    """Parse a RIFF/WAVE file into per-channel float arrays in [-1, 1]."""
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise AudioError("not a RIFF/WAVE file")
    pos, fmt, pcm, chunks, loops = 12, None, None, [], []
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack_from("<I", data, pos + 4)[0]
        start, end = pos + 8, min(pos + 8 + size, len(data))
        chunks.append(cid.decode("ascii", "replace").strip() or "?")
        if cid == b"fmt ":
            fmt = data[start:end]
        elif cid == b"data":
            pcm = memoryview(data)[start:end]
        elif cid == b"smpl" and end - start >= 36:
            count = struct.unpack_from("<I", data, start + 28)[0]
            for k in range(min(count, 16)):
                off = start + 36 + 24 * k
                if off + 24 > end:
                    break
                _cue, ltype, lbeg, lend, _frac, _plays = struct.unpack_from("<6I", data, off)
                loops.append({"type": ltype, "begin": lbeg, "end": lend + 1})  # smpl end is inclusive
        pos = start + size + (size & 1)
    if fmt is None or len(fmt) < 16:
        raise AudioError("no fmt chunk")
    if pcm is None:
        raise AudioError("no data chunk")
    tag, ch, rate, _bps, align, bits = struct.unpack_from("<HHIIHH", fmt, 0)
    if tag == 0xFFFE and len(fmt) >= 26:
        tag = struct.unpack_from("<H", fmt, 24)[0]   # first two bytes of the SubFormat GUID
    if ch < 1 or rate < 1 or align < ch:
        raise AudioError("invalid fmt chunk")
    width = align // ch
    frames = len(pcm) // align
    raw = bytes(pcm[:frames * align])
    if tag == 1 and width == 1:
        vals, scale = array("d", (b - 128 for b in raw)), 1 / 128.0
    elif tag == 1 and width == 2:
        vals, scale = array("h"), 1 / 32768.0
        vals.frombytes(raw)
    elif tag == 1 and width == 3:
        wide = bytearray(len(raw) // 3 * 4)
        wide[1::4], wide[2::4], wide[3::4] = raw[0::3], raw[1::3], raw[2::3]
        vals, scale = array("i"), 1 / 2147483648.0
        vals.frombytes(bytes(wide))
    elif tag == 1 and width == 4:
        vals, scale = array("i"), 1 / 2147483648.0
        vals.frombytes(raw)
    elif tag == 3 and width in (4, 8):
        vals, scale = array("f" if width == 4 else "d"), 1.0
        vals.frombytes(raw)
    else:
        raise AudioError(f"unsupported sample format (tag {tag}, {width * 8}-bit)")
    if sys.byteorder == "big" and width > 1:   # RIFF is little-endian; arrays use native order
        vals.byteswap()
    channels = [array("d", (v * scale for v in vals[c::ch])) for c in range(ch)]
    return {"rate": rate, "channels": channels, "frames": frames,
            "sample_format": ("float" if tag == 3 else "pcm") + str(width * 8),
            "chunks": chunks, "smpl_loops": loops}


def load(path: Path, tmpdir: str) -> tuple[dict | None, str | None]:
    """(audio, None) or (None, reason-for-NOT-RUN). Raises AudioError on a broken WAV."""
    if path.suffix.lower() in WAV_EXT:
        return read_wav(path), None
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None, "not a WAV and ffmpeg is not on PATH to decode it (see references/install-walkthrough.md)"
    out = Path(tmpdir) / (path.stem + ".decoded.wav")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-y", "-i", str(path), "-map", "0:a:0",
                           "-c:a", "pcm_f32le", "-f", "wav", str(out)],
                          capture_output=True, creationflags=flags)
    if proc.returncode != 0 or not out.exists():
        raise AudioError(f"ffmpeg could not decode the file (exit {proc.returncode})")
    audio = read_wav(out)
    audio["chunks"] = ["(decoded by ffmpeg; source chunks not listed)"]
    return audio, None


# ---------------------------------------------------------------------------- loudness

def k_coeffs(rate: int, published: bool = True):
    """K-weighting biquads for a sample rate: published values at 48 kHz, derived elsewhere."""
    if published and rate == 48000:
        return _K48
    gain_db, q_s, f_s = 3.999843853973347, 0.7071752369554196, 1681.974450955533
    q_h, f_h = 0.5003270373238773, 38.13547087602444
    k = math.tan(math.pi * f_s / rate)
    vh, vb = 10 ** (gain_db / 20.0), (10 ** (gain_db / 20.0)) ** 0.4996667741545416
    a0 = 1.0 + k / q_s + k * k
    shelf_b = ((vh + vb * k / q_s + k * k) / a0, 2.0 * (k * k - vh) / a0, (vh - vb * k / q_s + k * k) / a0)
    shelf_a = (2.0 * (k * k - 1.0) / a0, (1.0 - k / q_s + k * k) / a0)
    k = math.tan(math.pi * f_h / rate)
    a0 = 1.0 + k / q_h + k * k
    hp_a = (2.0 * (k * k - 1.0) / a0, (1.0 - k / q_h + k * k) / a0)
    return shelf_b, shelf_a, (1.0, -2.0, 1.0), hp_a


def kweighted_prefix(x: array, rate: int) -> array:
    """Prefix sums of the K-weighted signal's squares: out[i] = sum of squares of the first i."""
    (b0, b1, b2), (a1, a2), (c0, c1, c2), (d1, d2) = k_coeffs(rate)
    out = array("d", bytes(8 * (len(x) + 1)))
    x1 = x2 = s1 = s2 = h1 = h2 = acc = 0.0
    for i, xi in enumerate(x):
        s = b0 * xi + b1 * x1 + b2 * x2 - a1 * s1 - a2 * s2
        h = c0 * s + c1 * s1 + c2 * s2 - d1 * h1 - d2 * h2
        x2, x1, s2, s1, h2, h1 = x1, xi, s1, s, h1, h
        acc += h * h
        out[i + 1] = acc
    return out


def channel_weights(n: int) -> list[float]:
    if n == 6:
        return [1.0, 1.0, 1.0, 0.0, 1.41, 1.41]   # L R C LFE Ls Rs
    if n == 5:
        return [1.0, 1.0, 1.0, 1.41, 1.41]
    return [1.0] * n


def block_loudness(prefixes: list[array], rate: int, frames: int, seconds: float) -> list[float]:
    """Sum of weighted mean squares per block (75 % overlap); empty when the file is shorter."""
    size, step = round(seconds * rate), round(0.1 * rate)
    if size < 1 or frames < size:
        return []
    weights = channel_weights(len(prefixes))
    blocks, start = [], 0
    while start + size <= frames:
        blocks.append(sum(w * (p[start + size] - p[start]) / size for w, p in zip(weights, prefixes)))
        start += step
    return blocks


def lufs(z: float) -> float:
    return -math.inf if z <= 0 else -0.691 + 10.0 * math.log10(z)


def integrated(blocks: list[float]) -> float | None:
    if not blocks:
        return None
    gated = [z for z in blocks if lufs(z) > -70.0]
    if not gated:
        return -math.inf
    rel = lufs(sum(gated) / len(gated)) - 10.0
    kept = [z for z in gated if lufs(z) > rel]
    return lufs(sum(kept) / len(kept)) if kept else -math.inf


def loudness_range(short_blocks: list[float]) -> float | None:
    """EBU Tech 3342 LRA from 3 s short-term blocks (10 Hz hop): absolute gate -70 LUFS,
    relative gate 20 LU below the gated power mean, then the 95th minus the 10th percentile.
    None when there is no short-term block or nothing survives the gates."""
    gated = [z for z in short_blocks if lufs(z) > -70.0]
    if not gated:
        return None
    rel = lufs(sum(gated) / len(gated)) - 20.0
    vals = sorted(lufs(z) for z in gated if lufs(z) > rel)
    if not vals:
        return None

    def pct(p: float) -> float:
        k = (len(vals) - 1) * p
        lo = math.floor(k)
        hi = min(lo + 1, len(vals) - 1)
        return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)

    return pct(0.95) - pct(0.10)


LOW_END_HZ = 150.0                                          # listen line L9: small speakers roll off below this


def _lowpass(x, rate: int, fc: float):
    """Second-order Butterworth low-pass (RBJ cookbook biquad), direct form I."""
    w0 = 2 * math.pi * fc / rate
    alpha = math.sin(w0) / (2 * math.sqrt(0.5))
    cw = math.cos(w0)
    a0 = 1 + alpha
    b0 = b2 = (1 - cw) / 2 / a0
    b1 = (1 - cw) / a0
    a1, a2 = -2 * cw / a0, (1 - alpha) / a0
    out, x1, x2, y1, y2 = [], 0.0, 0.0, 0.0, 0.0
    for v in x:
        y = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out.append(y)
        x2, x1, y2, y1 = x1, v, y1, y
    return out


def low_end_share(channels: list, rate: int) -> float | None:
    """Energy below LOW_END_HZ (fourth-order low-pass) as a share of all energy, in dB."""
    total = low = 0.0
    for x in channels:
        total += sum(v * v for v in x)
        y = _lowpass(_lowpass(x, rate, LOW_END_HZ), rate, LOW_END_HZ)
        low += sum(v * v for v in y)
    if total <= 0:
        return None
    return 10 * math.log10(low / total) if low > 0 else -math.inf


# ---------------------------------------------------------------------------- peaks and edges

def _tp_kernels(half: int = 8) -> list[list[float]]:
    kernels = []
    for p in (0.25, 0.5, 0.75):
        w = []
        for j in range(-half + 1, half + 1):
            t = p - j
            w.append(math.sin(math.pi * t) / (math.pi * t) * 0.5 * (1 + math.cos(math.pi * t / (half + 0.5))))
        total = sum(w)
        kernels.append([v / total for v in w])
    return kernels


_KERNELS = _tp_kernels()


def true_peak(x: array, sample_peak: float, full: bool) -> float:
    """Highest |value| at 4x oversampling (estimate); never below the sample peak."""
    if sample_peak <= 0:
        return 0.0
    thr = 0.0 if full else sample_peak * 10 ** (-TP_CANDIDATE_DB / 20.0)
    n, best, half = len(x), sample_peak, len(_KERNELS[0]) // 2
    for i in range(n - 1):
        if abs(x[i]) < thr and abs(x[i + 1]) < thr:
            continue
        lo = i - half + 1
        if lo >= 0 and lo + 2 * half <= n:
            seg = x[lo:lo + 2 * half]
        else:
            seg = [x[k] if 0 <= k < n else 0.0 for k in range(lo, lo + 2 * half)]
        for ker in _KERNELS:
            v = abs(sum(a * b for a, b in zip(seg, ker)))
            if v > best:
                best = v
    return best


def clipped_runs(x: array) -> int:
    runs = length = 0
    for v in x:
        if abs(v) >= CLIP_LEVEL:
            length += 1
            if length == CLIP_RUN:
                runs += 1
        else:
            length = 0
    return runs


def edge_silence(channels: list[array], amp: float) -> tuple[int, int]:
    """(leading, trailing) frames where every channel stays at or below amp."""
    n = len(channels[0])
    first, last = n, -1
    for x in channels:
        for i in range(n):
            if abs(x[i]) > amp:
                first = min(first, i)
                break
        for i in range(n - 1, -1, -1):
            if abs(x[i]) > amp:
                last = max(last, i)
                break
    if last < 0:
        return n, n
    return first, n - 1 - last


def rms(x: array, a: int, b: int) -> float:
    a, b = max(0, a), min(len(x), b)
    return math.sqrt(sum(v * v for v in x[a:b]) / (b - a)) if b > a else 0.0


def seam(channels: list[array], rate: int, begin: int, end: int) -> dict:
    """Step across the loop point (end-1 -> begin) against the largest step either side of it."""
    w = max(2, round(SEAM_WINDOW_MS / 1000 * rate))
    lw = max(1, round(LEVEL_WINDOW_MS / 1000 * rate))
    step = local = jump = 0.0
    for x in channels:
        step = max(step, abs(x[begin] - x[end - 1]))
        for i in list(range(max(begin, end - 1 - w), end - 1)) + list(range(begin, min(end - 1, begin + w))):
            local = max(local, abs(x[i + 1] - x[i]))
        tail, head = rms(x, end - lw, end), rms(x, begin, begin + lw)
        if tail > 10 ** (SILENCE_DBFS / 20) and head > 10 ** (SILENCE_DBFS / 20):
            jump = max(jump, abs(db(tail) - db(head)))
    return {"step": step, "local": local, "level_jump_db": jump}


# ---------------------------------------------------------------------------- one file

def check(checks: list, cid: str, status: str, value: str, note: str = "") -> None:
    checks.append({"id": cid, "status": status, "value": value, "note": note})


def measure_one(path: Path, args, tmpdir: str) -> dict:
    rec = {"file": str(path), "checks": []}
    checks = rec["checks"]
    ext = path.suffix.lower()
    if ext in BEGIN_ONLY_EXT and args.loop_end is not None:
        check(checks, "begin-only-loop-end", "FAIL", f"--loop-end {args.loop_end}",
              "Godot imports Ogg Vorbis and MP3 with a loop offset only, no loop end: cut the file "
              "so it ends exactly at the loop end")
    if not path.is_file():
        rec["status"] = "ERROR"
        rec["error"] = "file not found"
        return rec
    try:
        audio, reason = load(path, tmpdir)
    except AudioError as exc:
        rec["status"] = "ERROR"
        rec["error"] = str(exc)
        return rec
    if audio is None:
        check(checks, "decode", "NOT-RUN", ext or "(no extension)", reason)
        rec["status"] = "NOT-RUN"
        return rec
    chans, rate, frames = audio["channels"], audio["rate"], audio["frames"]
    rec.update({"rate": rate, "channels": len(chans), "frames": frames, "seconds": frames / rate,
                "sample_format": audio["sample_format"], "chunks": audio["chunks"]})
    if frames == 0:
        check(checks, "empty", "FAIL", "0 frames", "the data chunk holds no audio")
        rec["status"] = "measured"
        return rec

    peak = max(max(abs(min(x)), abs(max(x))) for x in chans)
    tp = max(true_peak(x, max(abs(min(x)), abs(max(x))), args.full_tp) for x in chans)
    mean_sq = sum(sum(v * v for v in x) / frames for x in chans) / len(chans)
    prefixes = [kweighted_prefix(x, rate) for x in chans]
    mom = block_loudness(prefixes, rate, frames, 0.4)
    short = block_loudness(prefixes, rate, frames, 3.0)
    amp = 10 ** (SILENCE_DBFS / 20)
    lead, trail = edge_silence(chans, amp)
    rec.update({
        "sample_peak_dbfs": db(peak), "true_peak_dbtp": db(tp), "rms_dbfs": 10 * math.log10(mean_sq) if mean_sq > 0 else -math.inf,
        "integrated_lufs": integrated(mom), "momentary_max_lufs": max(map(lufs, mom)) if mom else None,
        "short_term_max_lufs": max(map(lufs, short)) if short else None,
        "lead_ms": 1000 * lead / rate, "trail_ms": 1000 * trail / rate,
        "dc_offset": max(abs(sum(x) / frames) for x in chans),
        "clipped_runs": sum(clipped_runs(x) for x in chans),
        "smpl_loops": audio["smpl_loops"],
    })

    if lead >= frames:
        check(checks, "silent", "FAIL", f"below {SILENCE_DBFS:.0f} dBFS throughout", "the file is silent")
    tp_db = rec["true_peak_dbtp"]
    check(checks, "true-peak", "PASS" if tp_db <= TRUE_PEAK_MAX else "FAIL", fmt_db(tp_db, "dBTP"),
          f"ceiling {TRUE_PEAK_MAX:.1f} dBTP (estimate; 4x oversampled)")
    check(checks, "clipping", "FAIL" if rec["clipped_runs"] else "PASS", f"{rec['clipped_runs']} runs",
          f"{CLIP_RUN}+ consecutive samples at full scale")
    check(checks, "dc-offset", "WARN" if rec["dc_offset"] > DC_WARN else "PASS", f"{rec['dc_offset']:.4f}")
    check(checks, "sample-rate", "WARN" if rate > MAX_USEFUL_RATE else "PASS", f"{rate} Hz",
          "no audible benefit above 48 kHz in a game" if rate > MAX_USEFUL_RATE else "")
    if rec["integrated_lufs"] is None:
        check(checks, "integrated", "NOT-RUN", f"{frames / rate:.3f} s",
              "shorter than one 400 ms block: integrated loudness is undefined; peak and RMS stand in")

    mono_expected, max_lead = CATEGORIES[args.category]
    if len(chans) == 2:
        dual = max(abs(a - b) for a, b in zip(chans[0], chans[1])) < 1e-4
        if dual:
            check(checks, "dual-mono", "WARN", "L == R", "identical channels: import with Force Mono (half the size)")
        elif mono_expected:
            check(checks, "channels", "WARN", "stereo", f"{args.category} is usually mono; keep stereo only if the brief asks")
    if max_lead is not None:
        check(checks, "leading-silence", "WARN" if rec["lead_ms"] > max_lead else "PASS",
              f"{rec['lead_ms']:.1f} ms", f"over {max_lead:.0f} ms delays the sound after its trigger")

    begin, end = args.loop_begin, args.loop_end
    source = "arguments" if begin is not None or end is not None else "whole file"
    if source == "whole file" and audio["smpl_loops"]:
        begin, end, source = audio["smpl_loops"][0]["begin"], audio["smpl_loops"][0]["end"], "smpl chunk"
    if args.loop or begin is not None or end is not None:
        begin = 0 if begin is None else begin
        end = frames if end is None or end > frames else end
        rec["loop"] = {"begin": begin, "end": end, "source": source}
        if not 0 <= begin < end - 1:
            check(checks, "loop-seam", "FAIL", f"begin {begin}, end {end}", "loop points out of range")
        else:
            s = seam(chans, rate, begin, end)
            click = s["step"] > 2 * s["local"] and s["step"] > amp
            check(checks, "loop-seam", "FAIL" if click else "PASS",
                  f"step {fmt_db(db(s['step']), 'dBFS')} vs local {fmt_db(db(s['local']), 'dBFS')}",
                  "a jump larger than twice any nearby step is an audible click" if click else "")
            check(checks, "loop-level", "WARN" if s["level_jump_db"] > LEVEL_JUMP_DB else "PASS",
                  f"{s['level_jump_db']:.1f} dB", f"level change across the seam over {LEVEL_JUMP_DB:.0f} dB")
            gap = max(rec["lead_ms"] if begin == 0 else 0.0, rec["trail_ms"] if end == frames else 0.0)
            check(checks, "loop-gap", "WARN" if gap > LOOP_GAP_MS else "PASS", f"{gap:.1f} ms",
                  f"silence over {LOOP_GAP_MS:.0f} ms at the seam is a gap")

    if getattr(args, "mix_extras", False):
        lra = loudness_range(short)
        rec["loudness_range_lu"] = lra
        if lra is None:
            check(checks, "loudness-range", "NOT-RUN", f"{frames / rate:.3f} s",
                  "needs at least one 3 s short-term block above the gates")
        else:
            check(checks, "loudness-range", "INFO", f"{lra:.1f} LU",
                  "EBU Tech 3342 LRA; read it against the game's dynamics, no pass line")
        share = low_end_share(chans, rate)
        rec["low_end_share_db"] = share
        check(checks, "low-end-share", "INFO", fmt_db(share, "dB"),
              f"energy below {LOW_END_HZ:.0f} Hz; a small speaker reproduces little of it (listen line L9)")

    if args.target_lufs is not None:
        value, kind =(rec["integrated_lufs"], "integrated") if rec["integrated_lufs"] is not None else (
            rec["sample_peak_dbfs"], "sample peak (file too short)")
        ok = value is not None and value != -math.inf and abs(value - args.target_lufs) <= args.tolerance
        check(checks, "target", "PASS" if ok else "FAIL", f"{fmt_db(value, '')} ({kind})",
              f"target {args.target_lufs:.1f} +/- {args.tolerance:.1f}")
    rec["status"] = "measured"
    return rec


def loudness_key(rec: dict, all_long: bool) -> float | None:
    v = rec.get("integrated_lufs") if all_long else rec.get("momentary_max_lufs")
    if v is None:
        v = rec.get("rms_dbfs")
    return None if v is None or v == -math.inf else v


def category_spread(records: list[dict], spread: float) -> dict | None:
    measured = [r for r in records if r.get("status") == "measured" and r.get("frames")]
    if len(measured) < 3:
        return None
    all_long = all(r.get("integrated_lufs") is not None for r in measured)
    keys = [(r, loudness_key(r, all_long)) for r in measured]
    vals = [k for _, k in keys if k is not None]
    if len(vals) < 3:
        return None
    med = statistics.median(vals)
    for r, k in keys:
        if k is None:
            continue
        off = k - med
        check(r["checks"], "category-spread", "WARN" if abs(off) > spread else "PASS",
              f"{off:+.1f} LU from the batch median",
              f"same-category files should sit within {spread:.0f} LU of each other; the mix sets balance")
    return {"metric": "integrated" if all_long else "momentary max", "median": med, "files": len(vals)}


# ---------------------------------------------------------------------------- output

def render(report: dict) -> str:
    out = [f"audio_post {VERSION} - {report['mode']}" + (f" (category {report['category']})" if report.get("category") else "")]
    for r in report["files"]:
        if r.get("status") == "ERROR":
            out.append(f"FILE {r['file']}  ERROR  {r['error']}")
            continue
        if "rate" in r:
            out.append(f"FILE {r['file']}  {r['sample_format']} {r['rate']} Hz {r['channels']} ch {r['seconds']:.3f} s")
            if r.get("frames"):
                out.append(f"  peak {fmt_db(r['sample_peak_dbfs'], 'dBFS')} | true peak {fmt_db(r['true_peak_dbtp'], 'dBTP')}"
                           f" | rms {fmt_db(r['rms_dbfs'], 'dBFS')} | integrated {fmt_db(r['integrated_lufs'], 'LUFS')}"
                           f" | momentary max {fmt_db(r['momentary_max_lufs'], 'LUFS')}")
                out.append(f"  lead {r['lead_ms']:.1f} ms | trail {r['trail_ms']:.1f} ms | dc {r['dc_offset']:.4f}"
                           f" | chunks {', '.join(r['chunks'])} (contents not printed)")
            if r.get("loop"):
                lp = r["loop"]
                out.append(f"  loop {lp['begin']}..{lp['end']} samples ({lp['source']})")
        else:
            out.append(f"FILE {r['file']}")
        for c in r["checks"]:
            out.append(f"  {c['status']:<7} {c['id']:<20} {c['value']}" + (f"  - {c['note']}" if c["note"] else ""))
    if report.get("spread"):
        sp = report["spread"]
        out.append(f"BATCH {sp['files']} files, {sp['metric']} median {sp['median']:.1f}")
    s = report["summary"]
    out.append(f"SUMMARY files {s['files']} | FAIL {s['FAIL']} | WARN {s['WARN']} | NOT-RUN {s['NOT-RUN']} | ERROR {s['ERROR']}")
    out.append("Numbers only: whether it sounds right is the user's call after a listen.")
    return "\n".join(out)


def summarise(records: list[dict]) -> dict:
    s = {"files": len(records), "FAIL": 0, "WARN": 0, "NOT-RUN": 0, "ERROR": 0}
    for r in records:
        if r.get("status") == "ERROR":
            s["ERROR"] += 1
        for c in r["checks"]:
            if c["status"] in s:
                s[c["status"]] += 1
    return s


def _jsonable(obj):
    if isinstance(obj, float) and math.isinf(obj):
        return "-inf" if obj < 0 else "inf"
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonable(v) for v in obj]
    return obj


def run(argv: list[str] | None = None) -> tuple[int, dict]:
    ap = argparse.ArgumentParser(prog="audio_post.py", description="Measure audio files by numbers. Read-only.")
    sub = ap.add_subparsers(dest="mode", required=True)
    m = sub.add_parser("measure", help="per-file checks; a batch of 3+ also gets the category spread check")
    m.add_argument("files", nargs="+")
    m.add_argument("--category", choices=sorted(CATEGORIES), default="any")
    m.add_argument("--loop", action="store_true", help="check the whole file as a loop")
    m.add_argument("--loop-begin", type=int, help="loop begin, in samples")
    m.add_argument("--loop-end", type=int, help="loop end (exclusive), in samples")
    m.add_argument("--target-lufs", type=float)
    m.add_argument("--tolerance", type=float, default=2.0)
    m.add_argument("--spread", type=float, default=SPREAD_LU)
    m.add_argument("--full-tp", action="store_true")
    m.add_argument("--json", action="store_true")
    x = sub.add_parser("mix", help="a whole-mix capture against a platform target")
    x.add_argument("file")
    x.add_argument("--platform", choices=sorted(PLATFORM_TARGETS), default="console")
    x.add_argument("--full-tp", action="store_true")
    x.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="audio_post_") as tmpdir:
        if args.mode == "measure":
            records = [measure_one(Path(f), args, tmpdir) for f in args.files]
            report = {"mode": "measure", "category": args.category, "files": records,
                      "spread": category_spread(records, args.spread)}
        else:
            ns = argparse.Namespace(category="any", loop=False, loop_begin=None, loop_end=None,
                                    target_lufs=PLATFORM_TARGETS[args.platform], tolerance=MIX_TOLERANCE,
                                    full_tp=args.full_tp, mix_extras=True)
            rec = measure_one(Path(args.file), ns, tmpdir)
            if rec.get("seconds") is not None and rec["seconds"] < MIX_MIN_MINUTES * 60:
                check(rec["checks"], "capture-length", "WARN", f"{rec['seconds'] / 60:.1f} min",
                      f"a mix capture should cover at least {MIX_MIN_MINUTES:.0f} minutes of representative play")
            for c in rec["checks"]:
                if c["id"] == "target":
                    c["id"] = f"mix-{args.platform}"
            records = [rec]
            report = {"mode": f"mix ({args.platform}, target {PLATFORM_TARGETS[args.platform]:.0f} LUFS)",
                      "files": records}
    report["summary"] = summarise(records)
    s = report["summary"]
    code = 2 if s["ERROR"] else (1 if s["FAIL"] else 0)
    return code, report


def main(argv: list[str] | None = None) -> int:
    try:
        code, report = run(argv)
    except SystemExit as exc:          # argparse usage errors
        return 2 if exc.code not in (0, None) else 0
    except Exception as exc:           # never echo content: type only
        print(f"audio_post: internal error ({type(exc).__name__})", file=sys.stderr)
        return 2
    as_json = "--json" in (argv if argv is not None else sys.argv[1:])
    print(json.dumps(_jsonable(report), indent=2) if as_json else render(report))
    return code


if __name__ == "__main__":
    sys.exit(main())
