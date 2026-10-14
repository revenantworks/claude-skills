#!/usr/bin/env python3
"""obs_ws.py — obsrunner's gate to OBS Studio's built-in WebSocket (obs-websocket v5).

Run, not read. Prints one JSON document per command.

  classify <Request>                       read | write | deny | unknown
  call <Request> [--data JSON] [--confirm] one request through the allow-list
  status                                   version, stream/record/replay state, record folder
  check [--seconds 20]                     two GetStats samples; names the bottleneck
  mark [--label TEXT] [--replay]           record chapter + a line in the marks sidecar

Rules this file enforces (references/websocket-allowlist.md is the human copy):
  - A request on the deny list never reaches OBS, with or without --confirm. The deny list holds
    every go-live path and both stream-service requests: GetStreamServiceSettings returns the
    stream key, so it is never called.
  - A request on no list is refused. Write requests need --confirm (the user's yes).
  - Loopback hosts only. The password comes from OBS_WEBSOCKET_PASSWORD and is never printed.
  - Every response is masked before it is printed (keys, tokens, passwords, URL query strings).
  - The client is the obsws-python package (owner-installed, references/install-walkthrough.md).
    Without it every command reports NOT-RUN; nothing is installed from here.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

READ = {
    "GetVersion", "GetStats", "GetSceneList", "GetCurrentProgramScene", "GetSceneItemList",
    "GetInputList", "GetInputSettings", "GetInputMute", "GetInputVolume", "GetProfileList",
    "GetProfileParameter", "GetSceneCollectionList", "GetVideoSettings", "GetRecordDirectory",
    "GetRecordStatus", "GetStreamStatus", "GetReplayBufferStatus", "GetVirtualCamStatus",
    "GetOutputList", "GetSourceFilterList",
}
WRITE = {
    "SetCurrentProgramScene", "SetSceneItemEnabled", "SetInputMute", "SetInputVolume",
    "SetProfileParameter", "CreateRecordChapter", "SaveReplayBuffer",
}
# SetProfileParameter may touch only the profile sections the audit fixes (audit O-2); the stream
# key lives in service.json and is out of reach either way.
PROFILE_CATEGORIES = {"Output", "Video", "SimpleOutput", "AdvOut"}
DENY = {
    "StartStream", "StopStream", "ToggleStream",
    "GetStreamServiceSettings", "SetStreamServiceSettings",
    "StartVirtualCam", "StopVirtualCam", "ToggleVirtualCam",
    "StartOutput", "StopOutput", "ToggleOutput", "GetOutputSettings", "SetOutputSettings",
    "TriggerHotkeyByName", "TriggerHotkeyByKeySequence",
    "CallVendorRequest", "BroadcastCustomEvent", "SendStreamCaption",
}
DENY_REASON = {
    "GetStreamServiceSettings": "it returns the stream key (obs-websocket returns the whole service settings object)",
    "SetStreamServiceSettings": "it writes the stream service and stream key",
}
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
DEFAULT_PORT = 4455
UNREACHABLE = ("websocket not reachable: OBS may be closed, its WebSocket server may be off "
               "(Tools > WebSocket Server Settings), the port or password may differ, or OBS may be "
               "in Safe Mode (the WebSocket server does not start in Safe Mode)")
SECRET_WORDS = ("password", "passwd", "token", "secret", "bearer", "auth", "cookie", "apikey", "api_key")


def classify(name: str) -> str:
    if name in DENY:
        return "deny"
    if name in WRITE:
        return "write"
    if name in READ:
        return "read"
    return "unknown"


def _secret_key(k: str) -> bool:
    low = k.lower()
    return low.endswith("key") or any(w in low for w in SECRET_WORDS)


def _mask_str(s: str) -> str:
    if "://" in s:
        s = re.sub(r"(://)[^/@\s]+@", r"\1<masked>@", s)
        s = re.sub(r"\?[^\s#]*", "?<masked>", s)
    return s


def mask(obj):
    """Return a copy with secret-looking fields and URL query strings masked."""
    if isinstance(obj, dict):
        return {k: ("<masked>" if _secret_key(str(k)) and obj[k] not in (None, "") else mask(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask(v) for v in obj]
    if isinstance(obj, str):
        return _mask_str(obj)
    return obj


def _scrub(text: str) -> str:
    pw = os.environ.get("OBS_WEBSOCKET_PASSWORD")
    return text.replace(pw, "<masked>") if pw else text


def _default_factory(host, port, password, timeout):
    import obsws_python as obs  # owner-installed; ImportError is handled by call()
    return obs.ReqClient(host=host, port=port, password=password, timeout=timeout)


def call(request: str, data: dict | None = None, confirm: bool = False, host: str = "127.0.0.1",
         port: int | None = None, timeout: float = 3.0, factory=None) -> dict:
    tier = classify(request)
    out = {"request": request, "tier": tier}
    if tier == "deny":
        why = DENY_REASON.get(request, "obsrunner never starts, stops or toggles a stream, a virtual camera "
                              "or an output, and never triggers hotkeys or vendor requests")
        if request in DENY_REASON:
            why += "; obsrunner never reads or writes the stream key"
        return {**out, "status": "REFUSED", "reason": f"{request} is on the deny list: {why}. "
                "The user presses that button in OBS."}
    if tier == "unknown":
        return {**out, "status": "REFUSED", "reason": f"{request} is on no allow-list; refused"}
    if request == "SetProfileParameter":
        cat = (data or {}).get("parameterCategory")
        if cat not in PROFILE_CATEGORIES:
            return {**out, "status": "REFUSED", "reason": f"SetProfileParameter parameterCategory {cat!r} is not "
                    f"one the audit fixes ({', '.join(sorted(PROFILE_CATEGORIES))}); refused"}
    if tier == "write" and not confirm:
        return {**out, "status": "REFUSED", "reason": "write request: needs the user's yes (--confirm)"}
    if host not in LOOPBACK:
        return {**out, "status": "REFUSED", "reason": f"host {host!r} is not loopback; obsrunner drives the "
                "OBS on this machine only"}
    port = port or int(os.environ.get("OBS_WEBSOCKET_PORT") or DEFAULT_PORT)
    password = os.environ.get("OBS_WEBSOCKET_PASSWORD") or None
    factory = factory or _default_factory
    try:
        client = factory(host, port, password, timeout)
        resp = client.send(request, data, raw=True)
    except ImportError:
        return {**out, "status": "NOT-RUN", "reason": "the obsws-python package is not installed; the user "
                "installs it (references/install-walkthrough.md, step 4). Nothing was sent."}
    except Exception as e:  # noqa: BLE001 — the client raises several unrelated types
        name = type(e).__name__
        if name == "OBSSDKRequestError":
            return {**out, "status": "ERROR", "reason": _scrub(f"OBS refused the request: {e}")}
        return {**out, "status": "ERROR", "reason": UNREACHABLE, "error": _scrub(f"{name}: {e}")}
    return {**out, "status": "OK", "response": mask(resp if resp is not None else {})}


# ---- check: name the bottleneck -------------------------------------------------------

def _ratio(before: dict, after: dict, skipped: str, total: str) -> float:
    s = (after.get(skipped) or 0) - (before.get(skipped) or 0)
    t = (after.get(total) or 0) - (before.get(total) or 0)
    return (s / t) if t > 0 else 0.0


def diagnose(before: dict, after: dict, stream_status: dict | None = None, record_active: bool = False,
             frame_threshold: float = 0.005, congestion_threshold: float = 0.3,
             min_disk_mb: float = 10240.0) -> dict:
    """Bucket a GetStats window into render, encode, network or disk (cause buckets per SOURCES.md)."""
    reasons, found = [], []
    r = _ratio(before, after, "renderSkippedFrames", "renderTotalFrames")
    if r > frame_threshold:
        found.append("render")
        reasons.append(f"render: {r:.2%} of frames missed by the renderer (GPU busy with the scene, or "
                       "another GPU job); lower canvas fps or scene load, check the lease")
    e = _ratio(before, after, "outputSkippedFrames", "outputTotalFrames")
    if e > frame_threshold:
        found.append("encode")
        reasons.append(f"encode: {e:.2%} of frames skipped by the encoder; use the hardware encoder for this "
                       "GPU, a faster preset, or a lower output resolution")
    ss = stream_status or {}
    if ss.get("outputActive") and ((ss.get("outputCongestion") or 0) >= congestion_threshold
                                   or ss.get("outputReconnecting")):
        found.append("network")
        reasons.append(f"network: congestion {ss.get('outputCongestion', 0):.2f}"
                       f"{', reconnecting' if ss.get('outputReconnecting') else ''}; lower the bitrate or "
                       "check the upload link")
    disk = after.get("availableDiskSpace")
    if record_active and disk is not None and disk < min_disk_mb:
        found.append("disk")
        reasons.append(f"disk: {disk / 1024:.1f} GB free at the record path while recording")
    if (after.get("cpuUsage") or 0) > 90:
        reasons.append(f"note: OBS CPU use {after['cpuUsage']:.0f}%")
    return {"bottleneck": found[0] if found else "none", "all": found, "reasons": reasons,
            "window_frames": (after.get("renderTotalFrames") or 0) - (before.get("renderTotalFrames") or 0)}


def obs_state(factory=None) -> str:
    """live | recording | idle | unknown — what OBS reports right now."""
    s = call("GetStreamStatus", factory=factory)
    r = call("GetRecordStatus", factory=factory)
    if s["status"] != "OK" or r["status"] != "OK":
        return "unknown"
    if s["response"].get("outputActive"):
        return "live"
    if r["response"].get("outputActive"):
        return "recording"
    return "idle"


# ---- CLI --------------------------------------------------------------------------------

def cmd_status() -> dict:
    out = {"command": "status"}
    for req in ("GetVersion", "GetStreamStatus", "GetRecordStatus", "GetReplayBufferStatus", "GetRecordDirectory"):
        out[req] = call(req)
        if out[req]["status"] in ("NOT-RUN", "ERROR"):
            out["verdict"] = out[req]["status"]
            out["reason"] = out[req]["reason"]
            break
    try:
        from gpu_preflight import lease_state, state_dir  # pack-shared, byte-identical
        p = state_dir() / "gpu-lease.json"
        lease = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
        out["lease"] = {"lease": lease, "state": lease_state(lease, datetime.now(timezone.utc))}
    except (OSError, ValueError) as e:
        out["lease"] = {"state": "unreadable", "error": str(e)}
    return out


def cmd_check(seconds: float) -> dict:
    a = call("GetStats")
    if a["status"] != "OK":
        return {"command": "check", "verdict": a["status"], "reason": a.get("reason")}
    time.sleep(max(1.0, seconds))
    b = call("GetStats")
    s = call("GetStreamStatus")
    r = call("GetRecordStatus")
    if b["status"] != "OK":
        return {"command": "check", "verdict": b["status"], "reason": b.get("reason")}
    rec = r["status"] == "OK" and bool(r["response"].get("outputActive"))
    d = diagnose(a["response"], b["response"], s.get("response") if s["status"] == "OK" else None, rec)
    return {"command": "check", "verdict": "OK", "seconds": seconds, **d}


def cmd_mark(label: str, replay: bool) -> dict:
    from obs_post import append_mark
    out = {"command": "mark"}
    r = call("GetRecordStatus")
    if r["status"] != "OK":
        return {**out, "verdict": r["status"], "reason": r.get("reason")}
    if not r["response"].get("outputActive"):
        out["verdict"] = "NOT-RECORDING"
        out["reason"] = "OBS is not recording; a mark needs a recording to belong to"
    else:
        ms = int(r["response"].get("outputDuration") or 0)
        out["chapter"] = call("CreateRecordChapter", {"chapterName": label} if label else None, confirm=True)
        d = call("GetRecordDirectory")
        if d["status"] == "OK" and d["response"].get("recordDirectory"):
            side = Path(d["response"]["recordDirectory"]) / "obsrunner-marks.jsonl"
            append_mark(side, ms, label or "mark")
            out["sidecar"] = str(side)
        out["record_ms"] = ms
        out["verdict"] = "MARKED"
    if replay:
        out["replay"] = call("SaveReplayBuffer", confirm=True)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify")
    c.add_argument("request")
    c = sub.add_parser("call")
    c.add_argument("request")
    c.add_argument("--data", help="JSON object of request fields")
    c.add_argument("--confirm", action="store_true", help="the user said yes to this write")
    sub.add_parser("status")
    c = sub.add_parser("check")
    c.add_argument("--seconds", type=float, default=20.0)
    c = sub.add_parser("mark")
    c.add_argument("--label", default="")
    c.add_argument("--replay", action="store_true", help="also save the replay buffer")
    a = p.parse_args(argv)
    if a.cmd == "classify":
        res = {"request": a.request, "tier": classify(a.request)}
    elif a.cmd == "call":
        res = call(a.request, json.loads(a.data) if a.data else None, confirm=a.confirm)
    elif a.cmd == "status":
        res = cmd_status()
    elif a.cmd == "check":
        res = cmd_check(a.seconds)
    else:
        res = cmd_mark(a.label, a.replay)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
