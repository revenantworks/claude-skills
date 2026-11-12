"""Tests for install_hooks.py (the one-command hook install and check).
Stdlib unittest; every fixture lives in a temp folder, both sides. Nothing touches ~/.claude.

    python -m unittest discover -s scripts -p "test_install_hooks.py"
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import install_hooks as ih  # noqa: E402

NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = ih.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@users.noreply.example",
                    *args], check=True, capture_output=True, stdin=subprocess.DEVNULL, **NOWIN)


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.src = self.root / "repo" / "hooks"
        self.live = self.root / "live"
        self.src.mkdir(parents=True)
        self.live.mkdir()
        (self.src / "a_hook.py").write_text("print('a v2')\n", encoding="utf-8", newline="\n")
        (self.src / "b_hook.py").write_text("print('b')\n", encoding="utf-8", newline="\n")

    def args(self, *extra: str) -> list[str]:
        return ["--source", str(self.src), "--hooks", str(self.live), "--no-settings-note", *extra]

    def copy_all(self) -> None:
        for p in self.src.glob("*.py"):
            (self.live / p.name).write_bytes(p.read_bytes())


class CheckTests(Base):
    def test_same_exits_zero(self) -> None:
        self.copy_all()
        rc, out, _ = run("--check", *self.args())
        self.assertEqual(rc, 0)
        self.assertIn("2 same, 0 not same", out)

    def test_crlf_only_reads_same(self) -> None:
        (self.live / "a_hook.py").write_bytes(b"print('a v2')\r\n")
        (self.live / "b_hook.py").write_bytes(b"print('b')\r\n")
        rc, _, _ = run("--check", *self.args())
        self.assertEqual(rc, 0)

    def test_differs_and_missing_exit_one_and_write_nothing(self) -> None:
        (self.live / "a_hook.py").write_text("print('a v1')\n", encoding="utf-8")
        rc, out, _ = run("--check", *self.args())
        self.assertEqual(rc, 1)
        self.assertIn("differs  a_hook.py", out)
        self.assertIn("missing  b_hook.py", out)
        self.assertEqual((self.live / "a_hook.py").read_text(encoding="utf-8"), "print('a v1')\n")
        self.assertFalse((self.live / "b_hook.py").exists())
        self.assertFalse((self.live / ".backup").exists())

    def test_extra_live_file_is_listed_not_failed(self) -> None:
        self.copy_all()
        (self.live / "old_hook.py").write_text("x\n", encoding="utf-8")
        rc, out, _ = run("--check", *self.args())
        self.assertEqual(rc, 0)
        self.assertIn("old_hook.py", out)

    def test_empty_source_is_an_input_error(self) -> None:
        empty = self.root / "none"
        empty.mkdir()
        rc, _, err = run("--check", "--source", str(empty), "--hooks", str(self.live))
        self.assertEqual(rc, 2)
        self.assertIn("no hook files", err)


class InstallTests(Base):
    def test_install_backs_up_copies_and_verifies(self) -> None:
        (self.live / "a_hook.py").write_text("print('a v1')\n", encoding="utf-8")
        (self.live / "pins.json").write_text("{}", encoding="utf-8")
        rc, out, _ = run(*self.args("--allow-branch"))
        self.assertEqual(rc, 0, out)
        self.assertIn("updated   a_hook.py", out)
        self.assertIn("added     b_hook.py", out)
        self.assertEqual((self.live / "a_hook.py").read_bytes(), (self.src / "a_hook.py").read_bytes())
        self.assertEqual(ih.sha(self.live / "b_hook.py", raw=True), ih.sha(self.src / "b_hook.py", raw=True))
        backups = list((self.live / ".backup").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual([p.name for p in backups[0].iterdir()], ["a_hook.py"])
        self.assertEqual((backups[0] / "a_hook.py").read_text(encoding="utf-8"), "print('a v1')\n")
        self.assertEqual((self.live / "pins.json").read_text(encoding="utf-8"), "{}")
        self.assertEqual(run("--check", *self.args())[0], 0)

    def test_same_file_is_not_backed_up(self) -> None:
        self.copy_all()
        rc, out, _ = run(*self.args("--allow-branch"))
        self.assertEqual(rc, 0)
        self.assertEqual(out.count("same      "), 2)
        self.assertFalse((self.live / ".backup").exists())

    def test_failed_verify_exits_one(self) -> None:
        real = ih.sha

        def lying(p, raw=False):
            return "0" * 64 if raw and Path(p).parent == self.live else real(p, raw)

        ih.sha = lying
        try:
            rc, out, _ = run(*self.args("--allow-branch"))
        finally:
            ih.sha = real
        self.assertEqual(rc, 1)
        self.assertIn("FAILED", out)


class CheckoutTests(Base):
    def make_repo(self, branch: str = "main") -> None:
        repo = self.root / "repo"
        subprocess.run(["git", "init", "-q", "-b", branch, str(repo)], check=True, capture_output=True,
                       stdin=subprocess.DEVNULL, **NOWIN)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "init")

    def test_clean_main_installs(self) -> None:
        self.make_repo()
        rc, out, err = run(*self.args())
        self.assertEqual(rc, 0, out + err)
        self.assertTrue((self.live / "a_hook.py").is_file())

    def test_dirty_checkout_refused(self) -> None:
        self.make_repo()
        (self.src / "a_hook.py").write_text("print('edited')\n", encoding="utf-8")
        rc, _, err = run(*self.args())
        self.assertEqual(rc, 2)
        self.assertIn("uncommitted", err)
        self.assertFalse((self.live / "a_hook.py").exists())

    def test_dirty_checkout_allowed_with_flag(self) -> None:
        self.make_repo()
        (self.src / "a_hook.py").write_text("print('edited')\n", encoding="utf-8")
        rc, _, _ = run(*self.args("--allow-branch"))
        self.assertEqual(rc, 0)
        self.assertEqual((self.live / "a_hook.py").read_text(encoding="utf-8"), "print('edited')\n")

    def test_non_main_refused(self) -> None:
        self.make_repo(branch="topic")
        rc, _, err = run(*self.args())
        self.assertEqual(rc, 2)
        self.assertIn("not main", err)
        self.assertFalse((self.live / "a_hook.py").exists())

    def test_not_a_checkout_refused(self) -> None:
        rc, _, err = run(*self.args())
        self.assertEqual(rc, 2)
        self.assertIn("not inside a git checkout", err)


class SettingsNoteTests(Base):
    def test_note_reads_and_never_writes_settings(self) -> None:
        settings = self.root / "settings.json"
        cmd = 'python "~/.claude/hooks/gatewarden/a_hook.py"'
        settings.write_text(json.dumps({"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [
            {"type": "command", "command": cmd}]}]}}), encoding="utf-8")
        before = settings.read_bytes()
        orig = ih.documented_hooks
        ih.documented_hooks = lambda: {"a_hook.py", "b_hook.py"}
        try:
            rc, out, _ = run("--source", str(self.src), "--hooks", str(self.live), "--allow-branch",
                             "--settings", str(settings))
        finally:
            ih.documented_hooks = orig
        self.assertEqual(rc, 0)
        self.assertIn("documented but not registered: b_hook.py", out)
        self.assertEqual(settings.read_bytes(), before)

    def test_missing_settings_is_a_note_not_an_error(self) -> None:
        rc, out, _ = run("--source", str(self.src), "--hooks", str(self.live), "--allow-branch",
                         "--settings", str(self.root / "nope.json"))
        self.assertEqual(rc, 0)
        self.assertIn("settings: not read", out)

    def test_shipped_doc_names_real_hooks(self) -> None:
        shipped = {p.name for p in ih.hook_files(ih.DEFAULT_SOURCE)}
        self.assertTrue(ih.documented_hooks())
        self.assertTrue(ih.documented_hooks() <= shipped)


if __name__ == "__main__":
    unittest.main()
