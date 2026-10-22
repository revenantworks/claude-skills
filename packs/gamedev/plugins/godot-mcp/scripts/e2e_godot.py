#!/usr/bin/env python3
"""End-to-end check against a real headless Godot editor. Needs Godot 4.5+ on PATH.

    python e2e_godot.py [--godot BIN] [--keep]

Builds a throwaway project in a temp folder (main scene, the addon, an override.cfg giving the
game its own user folder, games played with --headless so no window opens), starts
`godot --headless --editor` there with no window, drives every tool through
godot_mcp_server.py over stdio, probes the socket's guards directly, checks each answer, then
stops the editor and its children and removes the temp folder and its Godot user folders.
Exit 0 = every check passed, 1 = a check failed, 3 = NOT-RUN (no Godot). Never touches any
other project.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ADDON = HERE.parent / "addon" / "claude_mcp"
SERVER = HERE / "godot_mcp_server.py"
NOT_RUN = 3
NAME = "godot-mcp-e2e"
CUSTOM = "godot-mcp-e2e-game"
KNOWN = ('Parameter "t" is null',)   # dummy renderer, scene thumbnail on a headless save

PROJECT = f"""config_version=5

[application]

config/name="{NAME}"
run/main_scene="res://main.tscn"

[editor]

run/main_run_args="--headless --quit-after 600"

[editor_plugins]

enabled=PackedStringArray("res://addons/claude_mcp/plugin.cfg")
"""
OVERRIDE = f"""[application]

config/use_custom_user_dir=true
config/custom_user_dir_name="Godot/app_userdata/{CUSTOM}"
"""
MAIN_TSCN = """[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://main.gd" id="1"]

[node name="Main" type="Node2D"]
script = ExtResource("1")

[node name="Label" type="Label" parent="."]
text = "scratch"
"""
MAIN_GD = """extends Node2D

func _ready() -> void:
\tprint("e2e: main ready")
\tpush_error("e2e: deliberate error")
"""


def no_window() -> dict:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def stop_tree(p: subprocess.Popen) -> None:
    if p.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True,
                       **no_window())
    else:
        p.kill()
    p.wait(timeout=20)


def data_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ["APPDATA"])
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


class Client:
    def __init__(self, project: Path):
        self.p = subprocess.Popen([sys.executable, str(SERVER), "--project-dir", str(project)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, **no_window())
        self.n = 0

    def rpc(self, method: str, params: dict | None = None) -> dict:
        assert self.p.stdin and self.p.stdout
        self.n += 1
        self.p.stdin.write((json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method,
                                        "params": params or {}}) + "\n").encode())
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())

    def tool(self, tool: str, /, **args) -> tuple[bool, Any]:
        r = self.rpc("tools/call", {"name": tool, "arguments": args})["result"]
        return (not r["isError"]), r["structuredContent"]

    def close(self) -> None:
        assert self.p.stdin
        self.p.stdin.close()
        self.p.wait(timeout=10)


def raw(port: int, payload: bytes) -> bytes:
    """Send bytes to the plugin directly; return what comes back before it closes or 5 s pass."""
    with socket.create_connection(("127.0.0.1", port), timeout=5) as s:
        s.sendall(payload)
        out = b""
        try:
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                out += chunk
        except (socket.timeout, ConnectionError):
            pass
        return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="e2e_godot.py", description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--godot", default=os.environ.get("GODOT_BIN", "godot"))
    ap.add_argument("--keep", action="store_true", help="leave the temp project for inspection")
    a = ap.parse_args(argv)
    godot = shutil.which(a.godot)
    if not godot:
        print(f"NOT-RUN: {a.godot} is not on PATH")
        return NOT_RUN

    tmp = Path(tempfile.mkdtemp(prefix="godot-mcp-e2e-"))
    (tmp / "project.godot").write_text(PROJECT, encoding="utf-8")
    (tmp / "override.cfg").write_text(OVERRIDE, encoding="utf-8")
    (tmp / "main.tscn").write_text(MAIN_TSCN, encoding="utf-8")
    (tmp / "main.gd").write_text(MAIN_GD, encoding="utf-8")
    shutil.copytree(ADDON, tmp / "addons" / "claude_mcp")
    session = tmp / ".godot" / "claude_mcp" / "session.json"
    fails = 0

    def check(label: str, ok: bool, detail: object = "") -> None:
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'} {label}" + ("" if ok else f": {detail}"), flush=True)

    env = dict(os.environ, GODOT_MCP_PORT=os.environ.get("GODOT_MCP_PORT", "6110"))
    ed_log = tmp.with_name(tmp.name + "-editor.log")
    ed_out = ed_log.open("wb")
    ed = subprocess.Popen([godot, "--headless", "--editor", "--path", str(tmp)], env=env,
                          stdin=subprocess.DEVNULL, stdout=ed_out, stderr=subprocess.STDOUT,
                          **no_window())
    c = None
    try:
        deadline = time.time() + 120
        while not session.exists() and time.time() < deadline and ed.poll() is None:
            time.sleep(0.5)
        check("editor wrote session.json", session.exists(), f"editor exit {ed.poll()}")
        if not session.exists():
            return 1
        time.sleep(2)
        port = json.loads(session.read_text())["port"]

        c = Client(tmp)
        init = c.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "e2e", "version": "0"}})
        check("initialize", init["result"]["serverInfo"]["name"] == "godot-mcp", init)
        names = [t["name"] for t in c.rpc("tools/list")["result"]["tools"]]
        check("tools/list has 8 tools", len(names) == 8, names)

        ok, st = c.tool("godot_status")
        check("status", ok and st["project"] == NAME and st["read_only"] is False, st)
        check("status names the game's own user folder (override.cfg)",
              ok and f"/{CUSTOM}/" in st["game_log"].replace("\\", "/"), st)
        ok, tree = c.tool("godot_scene_tree")
        check("scene_tree", ok and tree["tree"]["name"] == "Main"
              and tree["tree"]["children"][0]["name"] == "Label", tree)

        ok, add = c.tool("godot_add_node", parent=".", type="Sprite2D", name="Hero",
                         properties={"visible": False})
        check("add_node", ok and add["path"] == "Hero", add)
        ok, bad = c.tool("godot_add_node", type="OS")
        check("add_node refuses a non-Node class", not ok and bad["error"]["code"] == "REFUSED", bad)
        ok, sp = c.tool("godot_set_property", path="Hero", property="position",
                        value_godot="Vector2(12, 34)")
        check("set_property (value_godot)", ok and sp["new"] == "Vector2(12, 34)", sp)
        ok, sp = c.tool("godot_set_property", path="Label", property="text", value="from claude")
        check("set_property (JSON)", ok and sp["new"] == '"from claude"', sp)
        ok, bad = c.tool("godot_set_property", path="Hero", property="script", value_godot="null")
        check("set_property refuses script", not ok, bad)
        ok, bad = c.tool("godot_set_property", path="Hero", property="visible")
        check("set_property refuses a missing value", not ok, bad)
        ok, sv = c.tool("godot_save_scene")
        saved = (tmp / "main.tscn").read_text(encoding="utf-8")
        check("save_scene wrote the new node", ok and 'name="Hero"' in saved
              and "from claude" in saved, sv if not ok else saved)

        ok, run = c.tool("godot_run_scene", scene="main", capture_seconds=6)
        lines = run.get("game_log", {}).get("lines", []) if ok else []
        check("run_scene captured this run's output",
              ok and any("e2e: main ready" in ln for ln in lines), run)
        ok, out = c.tool("godot_read_output", errors_only=True)
        errs = out["game_log"].get("lines", []) if ok else []
        check("read_output errors_only", ok and any("deliberate error" in ln for ln in errs)
              and not any("main ready" in ln for ln in errs), out)
        ok, bad = c.tool("godot_run_scene", scene="res://../x.tscn", capture_seconds=0)
        check("run_scene refuses a path outside res://", not ok, bad)
        ok, stop = c.tool("godot_stop_scene")
        check("stop_scene", ok, stop)
        ok, out = c.tool("godot_read_output")
        entries = out.get("editor_log", []) if ok else []
        check("editor log kept text, no control characters", ok
              and any("Claude MCP: listening" in e["text"] for e in entries)
              and not any(ch < " " and ch not in "\t\n" for e in entries for ch in e["text"]), out)

        bad_token = raw(port, b'{"token":"nope","cmd":"status"}\n')
        check("a wrong token is refused and the socket closed", b"BAD_TOKEN" in bad_token,
              bad_token[:200])
        flood = raw(port, b"x" * 9000)
        check("an oversized first line gets no answer", flood == b"", flood[:200])
        ok, st = c.tool("godot_status")
        check("the plugin still answers after both probes", ok, st)

        ed_out.flush()
        stray = [ln for ln in ed_log.read_text(encoding="utf-8", errors="replace").splitlines()
                 if ("ERROR" in ln or "Parse Error" in ln) and not any(k in ln for k in KNOWN)]
        check("editor printed no unexpected errors", not stray, stray[:5])
    finally:
        if c:
            c.close()
        stop_tree(ed)
        ed_out.close()
        if fails:
            text = ed_log.read_text(encoding="utf-8", errors="replace").splitlines()
            for ln in [x for x in text if "ERROR" in x][:20]:
                print(f"  editor: {ln}")
        if a.keep:
            print(f"kept: {tmp} and {ed_log}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
            ed_log.unlink(missing_ok=True)
            for d in (NAME, CUSTOM):
                shutil.rmtree(data_dir() / "Godot" / "app_userdata" / d, ignore_errors=True)
    print(f"{'OK' if not fails else 'FAILED'}: {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
