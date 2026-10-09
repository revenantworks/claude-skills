"""release.py must survive a fresh clone, and the tools must carry no local path.

History: before 2026-08-18 two private-repo paths were hardcoded here; making them
environment-read fixed a leak on this public repo, and a later crash on unset vars was
caught by these tests. The brand step those paths served was removed on 2026-10-01
(decision 36: no skill applies a brand), so the tests now prove it stays removed.
"""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARS = ("CLAUDE_SKILLS_BRAND_REPO_SOURCE", "CLAUDE_SKILLS_PEER_SOURCE")


def _bare_env():
    """The environment of a fresh clone: none of the private-repo vars set."""
    env = dict(os.environ)
    for v in VARS:
        env.pop(v, None)
    return env


RETIRED = ("brandwright", "commwright", "lorewright", "evalwright", "tokenwright")


class TestUnsetPathVars(unittest.TestCase):
    def test_import_survives_bare_env_and_carries_no_brand_surface(self):
        """Import must not raise on a fresh clone, and the retired brand step stays gone
        (decision 36, 2026-10-01: no skill applies a brand; the brand member retired)."""
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, r'%s'); import release, build; "
             "print('COPIES', hasattr(release, 'BRAND_COPIES')); "
             "print('REFRESH', hasattr(release, 'refresh_brand')); "
             "print('BUILD', [n for n in dir(build) if 'BRAND' in n or 'PEER' in n]); "
             "print('REQUIRED', sorted(release.REQUIRED_ON_CLAUDE_AI))"
             % (ROOT / "tools")],
            capture_output=True, text=True, env=_bare_env(), cwd=ROOT)
        self.assertEqual(r.returncode, 0, f"import failed:\n{r.stderr}")
        self.assertIn("COPIES False", r.stdout)
        self.assertIn("REFRESH False", r.stdout)
        self.assertIn("BUILD []", r.stdout)
        for name in RETIRED:
            self.assertNotIn(name, r.stdout)

    def test_help_names_no_retired_member_and_refresh_brand_is_gone(self):
        """--help is read-only; it and every tool script name no retired member folder,
        and the removed --refresh-brand flag is refused instead of silently running."""
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "release.py"), "--help"],
                           capture_output=True, text=True, env=_bare_env(), cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        for script in ("release.py", "build.py", "apply-install-swaps.py"):
            text = (ROOT / "tools" / script).read_text(encoding="utf-8")
            for name in RETIRED:
                self.assertNotIn(f"revenantworks-foundation-{name}", text, f"{script} points at {name}")
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "release.py"), "--refresh-brand"],
                           capture_output=True, text=True, env=_bare_env(), cwd=ROOT)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown flag", r.stdout + r.stderr)

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
