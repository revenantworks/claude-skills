"""Tests for vault_snapshot.py. Stdlib unittest only; every source tree and vault is invented and
written into a temporary folder.

Run: python -m unittest discover -s <skill>/scripts -p "test_*.py"
"""
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vault_snapshot  # noqa: E402

LIST = """# living sources
team/handbook:README.md
team/handbook:docs/onboarding.md
team/tools:README.md
"""


class Fixture:
    def __init__(self, test, listing=LIST):
        base = Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, base, ignore_errors=True)
        self.src, self.vault = base / "clones", base / "vault"
        (self.vault / "raw").mkdir(parents=True)
        self.put(self.src / "team/handbook/README.md", b"Handbook v1\n")
        self.put(self.src / "team/handbook/docs/onboarding.md", b"Day one: read the handbook.\r\n")
        self.put(self.src / "team/tools/README.md", b"Tools v1\n")
        self.put(self.vault / "tools/snapshot-sources.txt", listing.encode("utf-8"))

    @staticmethod
    def put(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def run(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = vault_snapshot.main(["--root", str(self.src), "--vault", str(self.vault), *args])
        return code, buf.getvalue()


class Copy(unittest.TestCase):
    def test_copies_bytes_into_dated_folder(self):
        f = Fixture(self)
        code, out = f.run("--date", "2026-11-01")
        self.assertEqual(code, 0, out)
        self.assertIn("3 copied, 0 missing", out)
        snap = f.vault / "raw/snapshots/2026-11-01/team/handbook/docs/onboarding.md"
        self.assertEqual(snap.read_bytes(), b"Day one: read the handbook.\r\n")

    def test_never_overwrites_a_date(self):
        f = Fixture(self)
        f.run("--date", "2026-11-01")
        f.put(f.src / "team/handbook/README.md", b"Handbook v2\n")
        code, out = f.run("--date", "2026-11-01")
        self.assertEqual(code, 1)
        self.assertIn("never overwritten", out)
        old = f.vault / "raw/snapshots/2026-11-01/team/handbook/README.md"
        self.assertEqual(old.read_bytes(), b"Handbook v1\n")

    def test_dry_run_writes_nothing_and_missing_is_named(self):
        f = Fixture(self)
        (f.src / "team/tools/README.md").unlink()
        code, out = f.run("--date", "2026-11-01", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("missing: team/tools:README.md", out)
        self.assertIn("2 copied, 1 missing (dry run)", out)
        self.assertFalse((f.vault / "raw/snapshots").exists())

    def test_unsafe_list_lines_refused_before_any_copy(self):
        for bad in ("team/handbook:../../secret.txt", "/etc:passwd", "team/handbook:/abs.md",
                    "C:x:README.md", "no-colon-line"):
            with self.subTest(bad=bad):
                f = Fixture(self, LIST + bad + "\n")
                code, out = f.run("--date", "2026-11-01")
                self.assertEqual(code, 2, out)
                self.assertIn("not a safe", out)
                self.assertFalse((f.vault / "raw/snapshots/2026-11-01").exists())

    def test_usage_errors(self):
        f = Fixture(self)
        self.assertEqual(f.run("--date", "tomorrow")[0], 2)
        shutil.rmtree(f.vault / "raw")
        code, out = f.run()
        self.assertEqual(code, 2)
        self.assertIn("no raw/ folder", out)


class Check(unittest.TestCase):
    def test_no_snapshot_is_not_run(self):
        code, out = Fixture(self).run("--check")
        self.assertEqual(code, 3)
        self.assertIn("NOT-RUN", out)

    def test_fresh_snapshot_ignores_line_endings(self):
        f = Fixture(self)
        f.run("--date", "2026-11-01")
        f.put(f.src / "team/handbook/docs/onboarding.md", b"Day one: read the handbook.\n")
        code, out = f.run("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("snapshot 2026-11-01: 0 stale", out)

    def test_changed_gone_not_in_snapshot_and_new_repo(self):
        f = Fixture(self)
        f.run("--date", "2026-11-01")
        f.put(f.src / "team/handbook/README.md", b"Handbook v2\n")
        (f.src / "team/tools/README.md").unlink()
        f.put(f.src / "team/wiki/README.md", b"Wiki\n")
        f.put(f.vault / "tools/snapshot-sources.txt", (LIST + "team/wiki:README.md\n").encode("utf-8"))
        code, out = f.run("--check", "--expect", "team/handbook,team/tools,team/wiki,team/site")
        self.assertEqual(code, 1)
        self.assertIn("CHANGED: team/handbook:README.md", out)
        self.assertNotIn("CHANGED: team/handbook:docs/onboarding.md", out)
        self.assertIn("GONE: team/tools:README.md", out)
        self.assertIn("NOT-IN-SNAPSHOT: team/wiki:README.md", out)
        self.assertIn("NEW-REPO: team/site", out)
        self.assertIn("4 stale", out)

    def test_check_reads_the_newest_snapshot_and_writes_nothing(self):
        f = Fixture(self)
        f.run("--date", "2026-10-01")
        f.put(f.src / "team/handbook/README.md", b"Handbook v2\n")
        f.run("--date", "2026-11-01")
        before = sorted(p.as_posix() for p in f.vault.rglob("*"))
        code, out = f.run("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("snapshot 2026-11-01", out)
        self.assertEqual(before, sorted(p.as_posix() for p in f.vault.rglob("*")))


if __name__ == "__main__":
    unittest.main()
