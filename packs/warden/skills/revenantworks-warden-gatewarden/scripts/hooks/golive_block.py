#!/usr/bin/env python3
"""golive_block.py: PreToolUse hook (matcher Bash|PowerShell|Read|Write|Edit|MultiEdit|mcp__.*)
that blocks go-live and stream-key requests to OBS Studio from any Claude tool call.

Blocked:
  - obs-websocket request names, case-sensitive whole words, anywhere in a shell line:
    StartStream, StopStream, ToggleStream, Get/SetStreamServiceSettings, Start/Stop/ToggleVirtualCam,
    Start/Stop/ToggleOutput, Get/SetOutputSettings, TriggerHotkeyByName, TriggerHotkeyByKeySequence,
    CallVendorRequest, BroadcastCustomEvent, SendStreamCaption;
  - the same calls as obsws-python methods (start_stream, toggle_virtual_cam, ...);
  - OBS's command-line go-live flags (--startstreaming, --startvirtualcam) and the obs-cmd / obs-cli
    verbs that start, stop or toggle the stream or the virtual camera (V-K8w2 B6);
  - an MCP tool on any server whose name holds start_stream, stop_stream, toggle_stream,
    stream_service, virtual_cam or stream_key, and an MCP tool on an OBS server whose input
    names a blocked request;
  - reading an OBS profile's service.json (it holds the stream key) through a shell command or
    the Read tool;
  - writing any of the above into a script file outside obsrunner's scripts folder (in gatewarden,
    only this hook by exact name, and the hook-test batteries: any `test_hooks*.py` in its scripts
    folder, hooklib.hook_test_file, observation 0375);
  - the unwrapped forms (hooklib.expand): spliced or concatenated names, -EncodedCommand, and a
    script file run or piped into an interpreter that holds a name.

Allowed: `obs_ws.py classify <Name>` (prints a tier, sends nothing); read-only searches (grep, rg,
findstr, Select-String, git grep) that only name a request; listing the profile folder; everything
else, GetStats included.

Fail mode: closed for anything that names a blocked request or service.json; open otherwise.
Limit, stated plainly: it binds the calls Claude makes, not the owner's. Going live is the owner's
button in OBS; obsrunner's own allow-list refuses the same requests inside its script, and this
hook is the second lock for every other route (an ad-hoc one-liner, an installed OBS MCP server).
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402

REQUESTS = ("StartStream", "StopStream", "ToggleStream", "GetStreamServiceSettings",
            "SetStreamServiceSettings", "StartVirtualCam", "StopVirtualCam", "ToggleVirtualCam",
            "StartOutput", "StopOutput", "ToggleOutput", "GetOutputSettings", "SetOutputSettings",
            "TriggerHotkeyByName", "TriggerHotkeyByKeySequence", "CallVendorRequest",
            "BroadcastCustomEvent", "SendStreamCaption")
METHODS = tuple(re.sub(r"(?<!^)(?=[A-Z])", "_", r).lower() for r in REQUESTS)
MCP_PARTS = ("start_stream", "stop_stream", "toggle_stream", "stream_service", "virtual_cam", "stream_key")

NAMES = re.compile(r"(?<![A-Za-z0-9_])(?:" + "|".join(REQUESTS + METHODS) + r")(?![A-Za-z0-9_])")
# OBS's own command-line go-live flags, and the obs-cmd / obs-cli verbs that start, stop or toggle the
# stream or the virtual camera (V-K8w2 B6). Recording, scenes and status stay allowed.
CLI = re.compile(r"(?i)(?<![\w-])--start(?:streaming|virtualcam)(?![\w-])"
                 r"|(?<![\w-])obs-c(?:md|li)(?:\.exe)?['\"]?\s+(?:-\S+\s+)*"
                 r"(?:stream(?:ing)?|virtual-?cam(?:era)?)\s+(?:start|stop|toggle)(?![\w-])")
SERVICE_JSON = re.compile(r"(?i)obs-studio[\\/].*service\.json")
LISTING = re.compile(r"(?i)^\s*(?:ls|dir|get-childitem|gci|test-path)\b")
SEARCH = re.compile(r"(?i)^\s*(?:grep|egrep|rg|findstr|select-string|sls|git\s+grep|git\s+log)\b")
CLASSIFY = re.compile(r"(?i)^\s*(?:python3?|py)(?:\s+-\S+)*\s+\S*obs_ws\.py\s+classify\s+[A-Za-z]+\s*$")
# obsrunner's scripts folder, gatewarden's own hook by exact name, and gatewarden's hook-test batteries by
# one rule (hooklib.hook_test_file, observation 0375); nothing else under gatewarden (warden audit G-4: a
# new file there was a way around the write check).
OWN_FOLDER = re.compile(r"(?i)revenantworks-localops-obsrunner[\\/]scripts[\\/]"
                        r"|revenantworks-warden-gatewarden[\\/]scripts[\\/]hooks[\\/]golive_block\.py$")


def own_file(path: str) -> bool:
    return bool(OWN_FOLDER.search(path)) or hl.hook_test_file(path)
SCRIPT_EXT = re.compile(r"(?i)\.(ps1|psm1|psd1|bat|cmd|py|sh|vbs|js|ts|mjs)$")
# The words that make a line this hook cannot read a go-live risk: a stream, the virtual camera, a hotkey,
# or an OBS client that sends requests. Merely naming OBS is not one (observation 0384): `obs64` in a
# Get-Command inventory, an `obs-studio` install folder, `find_spec('obsws_python')` or an `observer`
# folder on a file-create line sends nothing.
HINT = re.compile(r"(?i)stream|virtual_?cam|hotkey|reqclient|send_request|websocket|obs_ws\b"
                  r"|obs-c(?:md|li)(?![\w-])|(?<!\d)4455(?!\d)")
CLIENT = re.compile(r"(?i)obsws|obs[-_]?websocket")
# On a line the hook cannot read, an OBS client script run or imported still fails closed (ADV1 HK-2); a
# client name only looked up (`find_spec('obsws_python')`) does not.
CLIENT_RUN = re.compile(r"(?i)(?:obsws|obs[-_]?websocket)[\w.-]*\.(?:py|js|mjs|ts|ps1|sh)\b"
                        r"|\b(?:import|from)\s+obsws")

REASON = ("go-live block: go-live and stream-key requests are the owner's button; obsrunner never "
          "sends them. Tell the owner what to press in OBS instead.")


def segment_blocked(seg: str) -> bool:
    for text in (seg, hl.despliced(seg)):
        if SERVICE_JSON.search(text) and not LISTING.search(seg):
            return True
        if (NAMES.search(text) or CLI.search(text)) and not (SEARCH.search(seg) or CLASSIFY.search(seg)):
            return True
    return False


# A wildcard under an OBS profiles folder can match service.json (`cat …/profiles/p/s*e.json`).
PROFILE_GLOB = re.compile(r"(?i)obs-studio[\\/](?:.*[\\/])?profiles[\\/].*[*?\[]")


def path_blocked(seg: str, cwd: str) -> bool:
    """A relative path read inside an OBS profile folder: the cwd the line tracked (`cd …/profiles/p &&
    cat service.json`) or the event's cwd, joined to each word that may name the key file (V-K8w F14)."""
    if not cwd or LISTING.search(seg):
        return False
    for tok in hl.tokens(seg):
        word = hl.unquote(tok)
        if re.search(r"(?i)service\.json|[*?\[]", word) and not word.startswith("-"):
            full = hl.resolve(word, cwd).replace("\\", "/")
            if SERVICE_JSON.search(full) or PROFILE_GLOB.search(full):
                return True
    return False


def text_hits(text: str) -> bool:
    return any(NAMES.search(t) or CLI.search(t) or SERVICE_JSON.search(t) for t in (text, hl.despliced(text)))


def command_blocked(cmd: str, cwd: str = "") -> bool:
    """Check every shell text and code body the command runs (hooklib.expand)."""
    if len(cmd) > hl.BIG:  # V-K8w F8: a regex scan, never a word-by-word parse
        return text_hits(cmd) or bool(PROFILE_GLOB.search(cmd))
    try:
        ex = hl.expand(cmd, cwd)
    except hl.Unparseable as exc:
        return exc.hard or bool(HINT.search(hl.despliced(cmd)) or CLIENT_RUN.search(cmd))
    # A scratch script rewritten in place and run (observation 0384) counts as read when neither its text
    # nor the line holds a request name, a go-live flag, service.json, a go-live word or an OBS client.
    hl.settle_rewrites(ex, cmd, cwd, lambda text: not (text_hits(cmd + "\n" + text) or HINT.search(
        hl.despliced(cmd + "\n" + text)) or CLIENT.search(text)))
    if ex.unread or ex.unread_code:  # a script on disk the block could not read: fail closed (K7-4-03)
        return True
    if any(text_hits(t) for t in ex.big):
        return True
    for text, where in ex.shells:
        cur = where or cwd
        for s in hl.segments(text):
            target = hl.cd_target(s)
            if target:
                cur = hl.resolve(target, cur)
                continue
            if segment_blocked(s) or path_blocked(s, cur) or (PROFILE_GLOB.search(s) and not LISTING.search(s)):
                return True
    for body, path in ex.code:
        if (NAMES.search(body) or CLI.search(body) or SERVICE_JSON.search(body)) and not (path and own_file(path)):
            return True
    return bool(ex.opaque) and bool(HINT.search(hl.despliced(cmd)) or CLIENT_RUN.search(cmd))


def mcp_blocked(tool: str, ti) -> bool:
    low = tool.lower()
    if any(p in low for p in MCP_PARTS):
        return True
    parts = low.split("__")
    server = parts[1] if len(parts) > 2 else ""
    return "obs" in server and bool(NAMES.search(json.dumps(ti)))


def main() -> None:
    ev, raw = hl.read_event()
    if hl.stood_down("L2"):
        sys.exit(0)
    cmd = hl.command_of(ev) if ev else ""
    hl.start_budget("golive_block", REASON, lambda: text_hits(cmd or raw) or bool(HINT.search(cmd or raw))
                    or any(text_hits(t) for t in hl.FILES_READ))
    try:
        if ev is None:
            raise ValueError("unreadable hook input")
        tool = str(ev.get("tool_name") or "")
        ti = ev.get("tool_input") or {}
        if tool in hl.SHELL_TOOLS:
            if command_blocked(hl.command_of(ev), str(ev.get("cwd") or "")):
                hl.block(REASON, rule="golive_block", hard=True)
        elif tool.startswith("mcp__"):
            if mcp_blocked(tool, ti):
                hl.block(REASON, rule="golive_block", hard=True)
        elif tool == "Read":
            if SERVICE_JSON.search(str(ti.get("file_path") or "")):
                hl.block(REASON + " service.json holds the stream key.", rule="golive_block", hard=True)
        elif tool in ("Write", "Edit", "MultiEdit"):
            path = str(ti.get("file_path") or "")
            body = " ".join(str(ti.get(k) or "") for k in ("content", "new_string"))
            for e in ti.get("edits") or []:
                body += " " + str((e or {}).get("new_string") or "")
            flat = hl.despliced(body)
            if path and not own_file(path) and SCRIPT_EXT.search(path) \
                    and (NAMES.search(body) or CLI.search(body) or SERVICE_JSON.search(body) or NAMES.search(flat)):
                hl.block(REASON + " Writing it into a script file is the same request.", rule="golive_block", hard=True)
        hl.allow()
    except SystemExit:
        raise
    except Exception:
        if NAMES.search(raw or "") or SERVICE_JSON.search(raw or ""):
            hl.block(REASON + " (hook input could not be read; blocked to be safe)", rule="golive_block", hard=True)
        hl.allow()


if __name__ == "__main__":
    main()
