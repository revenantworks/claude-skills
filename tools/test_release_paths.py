"""release.py must survive a machine where the private-repo env vars are unset.

That is the DEFAULT state — the vars point at private repos that exist only on the
owner's rig. Before 2026-08-18 the paths were hardcoded, so "unset" could not happen.
Making them environment-read fixed a leak on this public repo and introduced a crash:
refresh_brand() called .is_file() on None and died with AttributeError, taking the
brand-escrow step with it. build.py's own tests never touched release.py, so nothing
caught it. These tests are that gap closed.
"""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARS = ("CLAUDE_SKILLS_BRAND_REPO_SOURCE", "CLAUDE_SKILLS_PEER_SOURCE_NORTHSTAR")


def _bare_env():
    """The environment of a fresh clone: none of the private-repo vars set."""
    env = dict(os.environ)
    for v in VARS:
        env.pop(v, None)
    return env


class TestUnsetPathVars(unittest.TestCase):
    def test_import_survives_unset_vars(self):
        """Import must not raise. A path derived from an unset var stays None."""
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, r'%s'); import release; "
             "print('BRAND', release.BRAND_COPIES['brand-definition.md']); "
             "print('PEER', release.BRAND_COPIES['brand-definition-northstar.md'])"
             % (ROOT / "tools")],
            capture_output=True, text=True, env=_bare_env(), cwd=ROOT)
        self.assertEqual(r.returncode, 0, f"import failed:\n{r.stderr}")
        self.assertIn("BRAND None", r.stdout)
        self.assertIn("PEER None", r.stdout)

    def test_refresh_brand_skips_instead_of_crashing(self):
        """The exact regression: AttributeError on None.is_file()."""
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "release.py"), "--refresh-brand"],
                           capture_output=True, text=True, env=_bare_env(), cwd=ROOT)
        self.assertNotIn("AttributeError", r.stderr)
        self.assertEqual(r.returncode, 0, f"--refresh-brand failed:\n{r.stdout}\n{r.stderr}")
        self.assertIn("not configured on this machine", r.stdout)

    def test_no_absolute_local_path_in_tracked_files(self):
        """This repo is public. A local path in a tracked file publishes the owner's
        layout and the existence of private repos. Dated CHANGELOGs are frozen history.

        Widened 2026-09-10 (estate finding `path-leak-test-scoped-to-one-drive-string`):
        the pattern used to match only the literal `V:[\\/]Projects` string, so a
        different drive letter, a UNC path, or a Unix-style home directory would leak
        clean. Now any drive-letter-colon-slash path (any letter, either slash) plus
        `/home/` and `/Users/` are all caught; the CHANGELOG exemption is unchanged here —
        see `test_changelog_entries_dated_today_or_later_carry_no_local_path` below for why
        the exemption itself no longer covers every CHANGELOG line.
        """
        out = subprocess.run(["git", "grep", "-n", "-I", "-E",
                              r"\b[A-Za-z]:[\\/][A-Za-z]|/home/[^ )\n]|/Users/[^ )\n]", "--",
                              ".", ":(exclude)*CHANGELOG*",
                              ":(exclude)tools/test_release_paths.py"],
                             capture_output=True, text=True, cwd=ROOT).stdout.strip()
        self.assertEqual(out, "", f"absolute local path in tracked file(s):\n{out}")

    def test_changelog_entries_dated_today_or_later_carry_no_local_path(self):
        """The blanket `*CHANGELOG*` exclusion above only makes sense for entries that are
        already frozen history. It does not generalize to a fresh entry landing the same day
        as this test runs — that is a live leak wearing a CHANGELOG's exemption, not history
        (estate observation #0013, `changelog-exempt-but-eval-files-caught-a-local-path-leak`:
        the CHANGELOG-only exemption does not travel to sibling file classes, and per the same
        principle it should not travel to un-frozen entries within a CHANGELOG either).

        This narrows the exemption instead of removing it: an entry is "historical" only once
        its own dated header (`## [x.y.z] - YYYY-MM-DD` or the em-dash form) is strictly before
        the cutoff below. Bump the cutoff forward, deliberately, when the day rolls over —
        never widen the pattern back to the whole file.
        """
        CUTOFF = "2026-09-10"
        PATH_RE = re.compile(r"[A-Za-z]:[\\/][A-Za-z]|/home/[^ )\n]|/Users/[^ )\n]")
        HEADER_RE = re.compile(r"^##\s*\[[^\]]+\]\s*[-–—]\s*(\d{4}-\d{2}-\d{2})", re.M)

        offenders = []
        for path in ROOT.rglob("CHANGELOG.md"):
            text = path.read_text(encoding="utf-8")
            headers = list(HEADER_RE.finditer(text))
            if not headers:
                continue
            for i, m in enumerate(headers):
                entry_start = m.end()
                entry_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
                entry_date = m.group(1)
                if entry_date < CUTOFF:
                    continue  # frozen history — the file-level exemption still covers it
                entry_text = text[entry_start:entry_end]
                for line_no, line in enumerate(entry_text.splitlines(), 1):
                    if PATH_RE.search(line):
                        offenders.append(f"{path.relative_to(ROOT)} :: entry {entry_date} line {line_no} :: {line.strip()}")
        self.assertEqual(offenders, [],
                          "local path in a CHANGELOG entry dated today or later (not frozen "
                          "history, so the blanket exemption must not cover it):\n" + "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
