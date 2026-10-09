#!/usr/bin/env python3
"""obs_audit.py — read-only audit of an OBS Studio profile folder against this machine.

Run, not read. Prints one JSON document: one row per check, each PASS, FAIL, NOT-RUN or INFO.

  obs_audit.py --profile <profile folder> [--gpu-name "<adapter name, read live>"]
               [--obs-version 32.2.2] [--min-free-gb 20]

The profile folder is the one that holds basic.ini, streamEncoder.json and recordEncoder.json
(on Windows: %APPDATA%\\obs-studio\\basic\\profiles\\<profile>). The script reads files only; it never
connects to OBS and never writes. From service.json it keeps the service type and the service
name and drops everything else, so the stream key never reaches the output.

Facts behind each row (encoder ids, settings keys, the GPU table) are in references/obs-settings.md,
which carries the Last-verified stamp.
"""
from __future__ import annotations

import argparse
import configparser
import json
import re
import shutil
import sys
from pathlib import Path

AMF_BFRAME_FIX = (32, 2, 2)  # release notes: AMF B-frame offset fix "could cause streams to disconnect"


def encoder_caps(gpu_name: str | None) -> set | None:
    """Hardware encode codecs for an AMD Radeon RX card by series; None when not identified."""
    if not gpu_name:
        return None
    m = re.search(r"\bRX\s*(\d)(\d{3})\b", gpu_name, re.I)
    if not m or "radeon" not in gpu_name.lower() and "amd" not in gpu_name.lower():
        return None
    series = int(m.group(1))
    if series in (5, 6):          # RDNA 1 (VCN 2) and RDNA 2 (VCN 3): no AV1 encode
        return {"h264", "hevc"}
    if series in (7, 9):          # RDNA 3 and RDNA 4: AV1 encode added
        return {"h264", "hevc", "av1"}
    return None


def codec_of(enc: str | None) -> str | None:
    if not enc:
        return None
    e = enc.lower()
    if "av1" in e:
        return "av1"
    if "h265" in e or "hevc" in e:
        return "hevc"
    if "264" in e or e in ("amd", "nvenc", "qsv", "x264"):
        return "h264"
    return None


def is_hardware(enc: str | None) -> bool:
    e = (enc or "").lower()
    return not (e in ("x264", "obs_x264") or e.startswith("obs_x264") or e == "")


def is_amf(enc: str | None) -> bool:
    e = (enc or "").lower()
    return "amf" in e or e.startswith("amd")


def _version(v: str | None):
    if not v:
        return None
    nums = re.findall(r"\d+", v)
    return tuple(int(n) for n in nums[:3]) if nums else None


def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def _row(name, verdict, detail, fix=""):
    return {"row": name, "verdict": verdict, "detail": detail, "fix": fix}


def encoder_row(name: str, enc: str | None, caps: set | None, gpu_name: str | None) -> dict:
    codec = codec_of(enc)
    if not enc:
        return _row(name, "NOT-RUN", "no encoder set in the profile")
    if not is_hardware(enc):
        return _row(name, "PASS", f"{enc}: software encoder (CPU); no GPU limit applies")
    if codec is None:
        return _row(name, "NOT-RUN", f"{enc}: codec not recognised")
    if caps is None:
        return _row(name, "NOT-RUN", f"{enc} ({codec}): GPU not identified; read the adapter name live and "
                    "pass --gpu-name, or check the encoder list in OBS Settings > Output")
    if codec not in caps:
        return _row(name, "FAIL", f"{enc}: {codec.upper()} encoder missing on this GPU ({gpu_name}); OBS 33 now "
                    "warns on missing encoders at profile load. A profile copied from another machine does this",
                    "pick the HEVC or H.264 AMF encoder (HEVC only where the platform takes HEVC over enhanced "
                    "RTMP; H.264 works everywhere)")
    return _row(name, "PASS", f"{enc} ({codec}) is a hardware encoder this GPU has")


def audit_profile(profile, gpu_name: str | None = None, obs_version: str | None = None,
                  min_free_gb: float = 20.0) -> dict:
    prof = Path(profile)
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    try:
        with open(prof / "basic.ini", encoding="utf-8-sig") as f:
            cp.read_file(f)
    except OSError as e:
        return {"profile": str(prof), "verdict": "NOT-RUN", "reason": f"basic.ini unreadable: {e}", "rows": []}

    def get(sec, key, default=None):
        return cp.get(sec, key, fallback=default) if cp.has_section(sec) else default

    mode = (get("Output", "Mode", "Simple") or "Simple").strip()
    adv = mode.lower() == "advanced"
    caps = encoder_caps(gpu_name)
    rows = [_row("output mode", "INFO", mode)]

    if adv:
        s_enc, r_enc = get("AdvOut", "Encoder"), get("AdvOut", "RecEncoder")
        if (r_enc or "").lower() in ("", "none"):
            r_enc = s_enc  # "use stream encoder"
        fmt = get("AdvOut", "RecFormat2")
        rec_path = get("AdvOut", "RecFilePath")
    else:
        s_enc, r_enc = get("SimpleOutput", "StreamEncoder"), get("SimpleOutput", "RecEncoder")
        fmt = get("SimpleOutput", "RecFormat2")
        rec_path = get("SimpleOutput", "FilePath")

    rows.append(encoder_row("stream encoder", s_enc, caps, gpu_name))
    rows.append(encoder_row("record encoder", r_enc, caps, gpu_name))

    senc = _read_json(prof / "streamEncoder.json") if adv else None
    if not adv:
        rows.append(_row("stream rate control", "NOT-RUN", "simple output mode: OBS sets rate control itself; "
                         "switch to Advanced to audit it"))
        rows.append(_row("keyframe interval", "NOT-RUN", "simple output mode: not stored in the profile"))
    elif senc is None:
        rows.append(_row("stream rate control", "NOT-RUN", "streamEncoder.json missing (encoder defaults in use)"))
        rows.append(_row("keyframe interval", "FAIL", "unset (streamEncoder.json missing)",
                         "set the keyframe interval to 2 s"))
    else:
        rc = str(senc.get("rate_control", "")).upper()
        rows.append(_row("stream rate control", "PASS" if rc == "CBR" else "FAIL", rc or "unset",
                         "" if rc == "CBR" else "use CBR for live streaming"))
        k = senc.get("keyint_sec")
        ok = k is not None and float(k) == 2
        rows.append(_row("keyframe interval", "PASS" if ok else "FAIL", f"{k} s" if k else "unset (0 = auto)",
                         "" if ok else "set the keyframe interval to 2 s"))

    if adv and is_amf(s_enc) and codec_of(s_enc) != "hevc":
        bf = int((senc or {}).get("bf", 2))
        ver = _version(obs_version)
        if bf == 0:
            rows.append(_row("AMF B-frames", "PASS", "B-frames off"))
        elif ver is None:
            rows.append(_row("AMF B-frames", "NOT-RUN", f"bf={bf}; OBS version unknown (read it live with "
                             "`obs_ws.py status`); AMF B-frames before 32.2.2 could disconnect streams"))
        elif ver < AMF_BFRAME_FIX:
            rows.append(_row("AMF B-frames", "FAIL", f"bf={bf} on OBS {obs_version}: the AMF B-frame offset bug "
                             "fixed in 32.2.2 could disconnect streams", "update OBS, or set B-frames to 0"))
        else:
            rows.append(_row("AMF B-frames", "PASS", f"bf={bf} on OBS {obs_version} (fix present)"))

    f = (fmt or "").lower()
    if not f:
        rows.append(_row("recording format", "NOT-RUN", "RecFormat2 not set"))
    elif f in ("mp4", "mov"):
        rows.append(_row("recording format", "FAIL", f"{f}: a crash or power loss leaves an unreadable file",
                         "record to MKV or hybrid MP4, then remux"))
    else:
        rows.append(_row("recording format", "PASS", f))

    if adv:
        en = (get("AdvOut", "VodTrackEnabled", "false") or "").lower() == "true"
        vt, tt = get("AdvOut", "VodTrackIndex"), get("AdvOut", "TrackIndex")
        if not en:
            rows.append(_row("VOD track", "INFO", "off: music played on stream is also in the VOD"))
        elif vt and tt and vt == tt:
            rows.append(_row("VOD track", "FAIL", f"VOD track {vt} is the stream track",
                             "route the VOD to a track without the music source"))
        else:
            rows.append(_row("VOD track", "PASS", f"stream track {tt}, VOD track {vt}"))
    else:
        en = (get("SimpleOutput", "VodTrackEnabled", "false") or "").lower() == "true"
        rows.append(_row("VOD track", "INFO", "on (simple mode)" if en else "off (simple mode)"))

    if rec_path and Path(rec_path).exists():
        free = shutil.disk_usage(rec_path).free / 1024 ** 3
        rows.append(_row("disk free", "PASS" if free >= min_free_gb else "FAIL", f"{free:.0f} GB at the record path",
                         "" if free >= min_free_gb else f"free space or move the record path (want {min_free_gb:.0f} GB)"))
    else:
        rows.append(_row("disk free", "NOT-RUN", "record path not set or not on this machine"))

    rows.append(_row("resolution and fps", "INFO",
                     f"base {get('Video', 'BaseCX')}x{get('Video', 'BaseCY')}, output "
                     f"{get('Video', 'OutputCX')}x{get('Video', 'OutputCY')}, fps {get('Video', 'FPSCommon')}"))

    svc = _read_json(prof / "service.json")
    service = None
    if isinstance(svc, dict):
        settings = svc.get("settings") if isinstance(svc.get("settings"), dict) else {}
        service = {"type": svc.get("type"), "service": settings.get("service")}
    verdict = "FAIL" if any(r["verdict"] == "FAIL" for r in rows) else "PASS"
    return {"profile": str(prof), "gpu_name": gpu_name, "obs_version": obs_version, "verdict": verdict,
            "service": service, "rows": rows}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--profile", required=True)
    p.add_argument("--gpu-name")
    p.add_argument("--obs-version")
    p.add_argument("--min-free-gb", type=float, default=20.0)
    a = p.parse_args(argv)
    print(json.dumps(audit_profile(a.profile, a.gpu_name, a.obs_version, a.min_free_gb), indent=2,
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
