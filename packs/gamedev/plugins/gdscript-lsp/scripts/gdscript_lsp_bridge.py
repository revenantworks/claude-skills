#!/usr/bin/env python3
"""gdscript_lsp_bridge - relay a stdio LSP client to Godot's TCP language server.

Claude Code runs every language server over stdio. Godot's GDScript language server listens on
TCP instead (port 6005 by default) while an editor runs. This bridge connects to that port and
copies bytes both ways, unchanged: both sides already speak Content-Length framed JSON-RPC.

Python 3 standard library only. Loopback only: a host that is not 127.0.0.0/8, ::1 or localhost
is refused before any connection, so no byte leaves the machine.

    python gdscript_lsp_bridge.py [--host H] [--port N] [--timeout S] [--spawn]
                                  [--godot BIN] [--project-dir DIR]

Every flag has an environment twin, read when the flag is absent:
GODOT_LSP_HOST (127.0.0.1), GODOT_LSP_PORT (6005), GODOT_LSP_CONNECT_TIMEOUT (10 s, 90 s with
--spawn), GODOT_LSP_SPAWN=1, GODOT_BIN (godot), and the project directory from
CLAUDE_PROJECT_DIR or the working directory.

--spawn: when nothing listens, start `godot --headless --editor --path <project> --lsp-port N`
(no window: CREATE_NO_WINDOW on Windows), wait for the port, and stop that editor on exit. The
headless editor imports the project and writes its `.godot/` cache, as an open editor does.

stdout carries protocol bytes only; every message goes to stderr.
Exit codes: 0 the session ended, 1 no server (or the spawned editor died), 2 usage error.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

DEFAULT_PORT = 6005
CREATE_NO_WINDOW = 0x08000000
CHUNK = 65536


def log(msg: str) -> None:
    sys.stderr.write(f"gdscript-lsp-bridge: {msg}\n")
    sys.stderr.flush()


def is_loopback(host: str) -> bool:
    """True only for a loopback address or the bare name localhost."""
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def find_project(start: Path) -> Path | None:
    """The nearest folder at or above `start` that holds project.godot."""
    p = Path(start).resolve()
    for d in (p, *p.parents):
        if (d / "project.godot").is_file():
            return d
    return None


def spawn_command(godot: str, project: Path, port: int) -> list[str]:
    return [godot, "--headless", "--editor", "--path", str(project), "--lsp-port", str(port)]


def spawn_godot(godot: str, project: Path, port: int) -> subprocess.Popen:
    exe = shutil.which(godot) or godot  # honours PATHEXT, so a godot.cmd shim is found
    kw: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kw["creationflags"] = CREATE_NO_WINDOW
    else:
        kw["start_new_session"] = True
    return subprocess.Popen(spawn_command(exe, project, port), **kw)


def stop_godot(proc: subprocess.Popen | None) -> None:
    """Stop a spawned editor and its children (a .cmd shim starts Godot as a child)."""
    if proc is None or proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=CREATE_NO_WINDOW, timeout=15)
        else:
            os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=15)
    except (OSError, subprocess.SubprocessError):
        proc.kill()


def connect(host: str, port: int, timeout: float,
            proc: subprocess.Popen | None = None) -> socket.socket:
    deadline = time.monotonic() + timeout
    last: OSError | None = None
    while True:
        try:
            s = socket.create_connection((host, port), timeout=2)
            s.settimeout(None)
            return s
        except OSError as e:
            last = e
        if proc is not None and proc.poll() is not None:
            raise ConnectionError(f"the spawned Godot editor exited with code {proc.returncode} "
                                  f"before its language server opened port {port}")
        if time.monotonic() >= deadline:
            hint = ("" if proc is not None else
                    "; open the project in the Godot editor, or set GODOT_LSP_SPAWN=1 to start a "
                    "headless one")
            raise ConnectionError(f"no Godot language server on {host}:{port} after "
                                  f"{timeout:g}s ({last}){hint}")
        time.sleep(0.25)


def pump_stdin_to_socket(sock: socket.socket, done: threading.Event) -> None:
    fd = sys.stdin.fileno()
    try:
        while True:
            chunk = os.read(fd, CHUNK)
            if not chunk:
                break
            sock.sendall(chunk)
    except OSError:
        pass
    finally:
        try:
            sock.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        done.set()


def pump_socket_to_stdout(sock: socket.socket) -> None:
    out = sys.stdout.buffer
    try:
        while True:
            chunk = sock.recv(CHUNK)
            if not chunk:
                break
            out.write(chunk)
            out.flush()
    except (OSError, ValueError):
        pass


def relay(sock: socket.socket, grace: float = 3.0) -> None:
    """Copy bytes both ways until the server closes, or `grace` seconds after stdin ends."""
    stdin_done = threading.Event()
    reader = threading.Thread(target=pump_socket_to_stdout, args=(sock,), daemon=True)
    writer = threading.Thread(target=pump_stdin_to_socket, args=(sock, stdin_done), daemon=True)
    reader.start()
    writer.start()
    while reader.is_alive():
        reader.join(0.2)
        if stdin_done.is_set():
            reader.join(grace)
            break
    try:
        sock.close()
    except OSError:
        pass


def parse(argv: list[str]) -> argparse.Namespace:
    env = os.environ
    ap = argparse.ArgumentParser(prog="gdscript_lsp_bridge.py",
                                 description="Relay a stdio LSP client to Godot's TCP language server.")
    ap.add_argument("--host", default=env.get("GODOT_LSP_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--timeout", type=float, default=None, help="seconds to wait for the port")
    ap.add_argument("--spawn", action="store_true",
                    default=env.get("GODOT_LSP_SPAWN", "") in ("1", "true", "yes"))
    ap.add_argument("--godot", default=env.get("GODOT_BIN", "godot"))
    ap.add_argument("--project-dir", default=env.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    a = ap.parse_args(argv)
    if a.port is None:
        try:
            a.port = int(env.get("GODOT_LSP_PORT", DEFAULT_PORT))
        except ValueError:
            ap.error("GODOT_LSP_PORT is not a port number")
    if not 0 < a.port < 65536:
        ap.error(f"port {a.port} is out of range 1-65535")
    if a.timeout is None:
        raw = env.get("GODOT_LSP_CONNECT_TIMEOUT")
        try:
            a.timeout = float(raw) if raw else (90.0 if a.spawn else 10.0)
        except ValueError:
            ap.error("GODOT_LSP_CONNECT_TIMEOUT is not a number")
    if not is_loopback(a.host):
        ap.error(f"host {a.host!r} is not a loopback address; this bridge only connects to "
                 f"127.0.0.0/8, ::1 or localhost")
    return a


def main(argv: list[str] | None = None) -> int:
    a = parse(sys.argv[1:] if argv is None else argv)
    proc = None
    try:
        try:
            sock = connect(a.host, a.port, 0.5 if a.spawn else a.timeout)
        except ConnectionError as first:
            if not a.spawn:
                log(str(first))
                return 1
            project = find_project(Path(a.project_dir))
            if project is None:
                log(f"--spawn needs a Godot project: no project.godot at or above {a.project_dir}")
                return 1
            log(f"nothing on port {a.port}; starting a headless Godot editor for {project}")
            try:
                proc = spawn_godot(a.godot, project, a.port)
            except OSError as e:
                log(f"could not start {a.godot!r}: {e}")
                return 1
            try:
                sock = connect(a.host, a.port, a.timeout, proc)
            except ConnectionError as e:
                log(str(e))
                return 1
        log(f"connected to {a.host}:{a.port}")
        relay(sock)
        return 0
    finally:
        stop_godot(proc)


if __name__ == "__main__":
    sys.exit(main())
