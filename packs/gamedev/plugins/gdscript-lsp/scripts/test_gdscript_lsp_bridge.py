"""Tests for gdscript_lsp_bridge.py. No test starts Godot: a fake TCP server stands in for it.

    python -m unittest discover -s scripts -p "test_*.py"
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRIDGE = HERE / "gdscript_lsp_bridge.py"
sys.path.insert(0, str(HERE))

import gdscript_lsp_bridge as br  # noqa: E402

NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def frame(obj: dict) -> bytes:
    body = json.dumps(obj).encode("utf-8")
    return b"Content-Length: %d\r\n\r\n" % len(body) + body


def read_frame(stream) -> dict:
    """Read one Content-Length framed message from a binary stream."""
    length = None
    while True:
        line = stream.readline()
        if not line:
            raise EOFError("stream closed before a header")
        if line in (b"\r\n", b"\n"):
            break
        name, _, value = line.decode("ascii").partition(":")
        if name.strip().lower() == "content-length":
            length = int(value.strip())
    return json.loads(stream.read(length).decode("utf-8"))


class FakeGodotLsp:
    """A one-client TCP server that answers each request with {"echo": method} and can push
    one notification of its own, the way Godot pushes publishDiagnostics."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.received = []
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        conn, _ = self.sock.accept()
        with conn, conn.makefile("rb") as rf:
            while True:
                try:
                    msg = read_frame(rf)
                except (EOFError, OSError, ValueError):
                    return
                self.received.append(msg)
                if msg.get("method") == "initialize":
                    conn.sendall(frame({"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
                                        "params": {"uri": "file:///p/a.gd", "diagnostics": []}}))
                if "id" in msg:
                    conn.sendall(frame({"jsonrpc": "2.0", "id": msg["id"],
                                        "result": {"echo": msg.get("method")}}))
                if msg.get("method") == "exit":
                    return

    def close(self):
        self.sock.close()


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def run_bridge(*args, stdin=subprocess.PIPE):
    return subprocess.Popen([sys.executable, str(BRIDGE), *args], stdin=stdin,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=NO_WINDOW)


class RelayTest(unittest.TestCase):
    def test_relays_requests_responses_and_pushed_notifications(self):
        fake = FakeGodotLsp()
        p = run_bridge("--port", str(fake.port), "--timeout", "5")
        try:
            p.stdin.write(frame({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                 "params": {"rootUri": "file:///p"}}))
            p.stdin.flush()
            first = read_frame(p.stdout)
            second = read_frame(p.stdout)
            self.assertEqual(first["method"], "textDocument/publishDiagnostics")
            self.assertEqual(second, {"jsonrpc": "2.0", "id": 1, "result": {"echo": "initialize"}})
            p.stdin.write(frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown"}))
            p.stdin.write(frame({"jsonrpc": "2.0", "method": "exit"}))
            p.stdin.flush()
            self.assertEqual(read_frame(p.stdout)["result"], {"echo": "shutdown"})
            p.stdin.close()
            p.communicate(timeout=10)
            self.assertEqual(p.returncode, 0)
        finally:
            if p.poll() is None:
                p.kill()
            fake.close()
        self.assertEqual([m.get("method") for m in fake.received], ["initialize", "shutdown", "exit"])

    def test_large_message_arrives_whole(self):
        fake = FakeGodotLsp()
        p = run_bridge("--port", str(fake.port), "--timeout", "5")
        try:
            text = "x" * 300_000
            p.stdin.write(frame({"jsonrpc": "2.0", "id": 7, "method": "textDocument/didOpen-big",
                                 "params": {"text": text}}))
            p.stdin.flush()
            self.assertEqual(read_frame(p.stdout)["result"], {"echo": "textDocument/didOpen-big"})
            p.stdin.close()
            p.communicate(timeout=10)
        finally:
            if p.poll() is None:
                p.kill()
            fake.close()
        self.assertEqual(len(fake.received[0]["params"]["text"]), 300_000)

    def test_stdout_carries_only_protocol_bytes(self):
        fake = FakeGodotLsp()
        p = run_bridge("--port", str(fake.port), "--timeout", "5")
        try:
            p.stdin.write(frame({"jsonrpc": "2.0", "id": 1, "method": "initialize"}))
            p.stdin.flush()
            read_frame(p.stdout)
            read_frame(p.stdout)
            p.stdin.close()
            out, _ = p.communicate(timeout=10)
        finally:
            if p.poll() is None:
                p.kill()
            fake.close()
        self.assertEqual(out, b"")


class RefusalTest(unittest.TestCase):
    def test_no_server_exits_1_with_a_reason_on_stderr(self):
        port = free_port()
        start = time.monotonic()
        p = run_bridge("--port", str(port), "--timeout", "1")
        out, err = p.communicate(timeout=20)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(out, b"")
        self.assertIn(b"no Godot language server", err)
        self.assertIn(str(port).encode(), err)
        self.assertLess(time.monotonic() - start, 15)

    def test_non_loopback_host_is_refused_before_any_connection(self):
        p = run_bridge("--host", "192.0.2.10", "--timeout", "1")
        out, err = p.communicate(timeout=20)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(out, b"")
        self.assertIn(b"loopback", err)

    def test_env_host_is_checked_too(self):
        env = dict(os.environ, GODOT_LSP_HOST="example.com")
        p = subprocess.Popen([sys.executable, str(BRIDGE), "--timeout", "1"], env=env,
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, creationflags=NO_WINDOW)
        _, err = p.communicate(timeout=20)
        self.assertEqual(p.returncode, 2)
        self.assertIn(b"loopback", err)

    def test_bad_port_is_a_usage_error(self):
        p = run_bridge("--port", "70000", "--timeout", "1")
        _, err = p.communicate(timeout=20)
        self.assertEqual(p.returncode, 2)
        self.assertIn(b"port", err)


class HelperTest(unittest.TestCase):
    def test_is_loopback(self):
        for host in ("127.0.0.1", "127.8.0.1", "::1", "localhost", "LOCALHOST"):
            self.assertTrue(br.is_loopback(host), host)
        for host in ("0.0.0.0", "192.0.2.10", "example.com", "", "localhost.example.com"):
            self.assertFalse(br.is_loopback(host), host)

    def test_find_project_walks_up_to_project_godot(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "game"
            (root / "src" / "sim").mkdir(parents=True)
            (root / "project.godot").write_text("config_version=5\n", encoding="utf-8")
            self.assertEqual(br.find_project(root / "src" / "sim"), root.resolve())
            self.assertIsNone(br.find_project(Path(d)))

    def test_spawn_command_is_headless_editor_on_the_named_port(self):
        cmd = br.spawn_command("godot", Path("/p"), 6123)
        self.assertEqual(cmd[0], "godot")
        for flag in ("--headless", "--editor", "--lsp-port"):
            self.assertIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("--lsp-port") + 1], "6123")
        self.assertEqual(cmd[cmd.index("--path") + 1], str(Path("/p")))

    def test_spawn_without_a_project_exits_1(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.Popen([sys.executable, str(BRIDGE), "--port", str(free_port()),
                                  "--timeout", "1", "--spawn", "--project-dir", d],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, creationflags=NO_WINDOW)
            out, err = p.communicate(timeout=20)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(out, b"")
        self.assertIn(b"project.godot", err)


if __name__ == "__main__":
    unittest.main()
