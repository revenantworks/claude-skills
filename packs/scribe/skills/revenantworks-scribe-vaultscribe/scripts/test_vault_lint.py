"""Tests for vault_lint.py. Stdlib unittest only; every vault is invented and written into a
temporary folder. Personal-data and secret shapes are assembled at run time, so no tracked file
holds one.

Run: python -m unittest discover -s <skill>/scripts -p "test_*.py"
"""
import contextlib
import datetime
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vault_lint  # noqa: E402

TODAY = datetime.date(2026, 11, 9)


def page(sources, body, updated="2026-11-01"):
    head = "---\nsources:\n" + "".join(f"  - {s}\n" for s in sources) + f"updated: {updated}\n---\n"
    return head + body


class Vault:
    def __init__(self, test):
        self.root = Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        for d in ("raw/notes", "wiki/topics"):
            (self.root / d).mkdir(parents=True)
        self.write("raw/tides.md", "Tides follow the moon.\n")
        self.write("raw/salt.md", "Sea salt is mostly sodium chloride.\n")
        self.write("wiki/topics/tides.md", page(["raw/tides.md"], "Tides. See [[salt]].\n"))
        self.write("wiki/topics/salt.md", page(["raw/salt.md"], "Salt. See [[tides]].\n", "2026-10-01"))
        self.write("wiki/index.md", "# Index\n- [[tides]] the tide page\n- [[salt]] the salt page\n")
        self.write("wiki/log.md", "## 2026-11-01 ingest | tides\n")
        self.write("wiki/privacy-signals.md", "")

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))
        return p

    def lint(self, **kw):
        kw.setdefault("use_git", False)
        out, count = vault_lint.lint(self.root, today=TODAY, **kw)
        return "\n".join(out), count


class CleanVault(unittest.TestCase):
    def test_clean_vault_has_no_problems(self):
        out, count = Vault(self).lint()
        self.assertEqual(count, 0, out)
        self.assertIn("pages: 2", out)
        self.assertIn("raw files waiting to be ingested: 0", out)
        self.assertIn("NOT-RUN: raw change check (--no-git)", out)

    def test_review_lists_oldest_first(self):
        out, _ = Vault(self).lint(review=1)
        self.assertIn("REVIEW: salt (updated 2026-10-01)", out)
        self.assertNotIn("REVIEW: tides", out)


class Structure(unittest.TestCase):
    def test_broken_link_orphan_and_index(self):
        v = Vault(self)
        v.write("wiki/topics/moon.md", page(["raw/tides.md"], "Moon. See [[nowhere]].\n"))
        out, count = v.lint()
        self.assertIn("PROBLEM BROKEN-LINK: wiki/topics/moon.md links [[nowhere]]", out)
        self.assertIn("PROBLEM NOT-INDEXED: wiki/topics/moon.md", out)
        self.assertIn("PROBLEM ORPHAN: wiki/topics/moon.md", out)
        self.assertEqual(count, 3)

    def test_link_inside_code_is_not_a_link(self):
        v = Vault(self)
        v.write("wiki/topics/tides.md", page(["raw/tides.md"], "See [[salt]]. `[[ghost]]`\n"))
        out, count = v.lint()
        self.assertEqual(count, 0, out)

    def test_sources_missing_bad_and_escaping(self):
        v = Vault(self)
        v.write("wiki/topics/salt.md", "No front matter. [[tides]]\n")
        v.write("wiki/topics/tides.md", page(["raw/none.md", "raw/../wiki/index.md", "notes.md"], "[[salt]]\n"))
        out, _ = v.lint()
        self.assertIn("PROBLEM NO-SOURCES: wiki/topics/salt.md", out)
        for bad in ("raw/none.md", "raw/../wiki/index.md", "notes.md"):
            self.assertIn(f"cites {bad}, which is not a file under raw/", out)

    def test_hub_at_wiki_root_needs_no_sources(self):
        v = Vault(self)
        v.write("wiki/topics.md", "# Topics\n- [[tides]]\n- [[salt]]\n")
        v.write("wiki/index.md", "- [[topics]]\n- [[tides]]\n- [[salt]]\n")
        v.write("wiki/topics/salt.md", page(["raw/salt.md"], "Salt. [[topics]]\n"))
        out, count = v.lint()
        self.assertEqual(count, 0, out)
        v.write("wiki/topics.md", page(["raw/none.md"], "[[tides]] [[salt]]\n"))
        out, _ = v.lint()
        self.assertIn("PROBLEM BAD-SOURCE: wiki/topics.md cites raw/none.md", out)

    def test_index_lists_missing_page_and_duplicate_names(self):
        v = Vault(self)
        v.write("wiki/index.md", "- [[tides]]\n- [[salt]]\n- [[gone]]\n")
        v.write("wiki/other/Salt.md", page(["raw/salt.md"], "[[tides]]\n"))
        out, _ = v.lint()
        self.assertIn("PROBLEM INDEX-MISSING: wiki/index.md links [[gone]]", out)
        self.assertIn("PROBLEM DUP-NAME:", out)

    def test_new_raw_files_listed_and_snapshots_skipped(self):
        v = Vault(self)
        v.write("raw/clips/new-article.md", "A clipped article.\n")
        v.write("raw/empty.md", "")
        v.write("raw/snapshots/2026-11-01/team/handbook/README.md", "Handbook.\n")
        out, count = v.lint()
        self.assertIn("NEW: raw/clips/new-article.md", out)
        self.assertNotIn("raw/empty.md", out)
        self.assertNotIn("NEW: raw/snapshots", out)
        self.assertIn("raw files waiting to be ingested: 1", out)
        self.assertEqual(count, 0, out)


class TrustBoundary(unittest.TestCase):
    def test_exfiltration_and_hiding_routes(self):
        v = Vault(self)
        body = ("[[salt]]\n![chart](https://img.example.net/c.png?q=1)\n<img src=x>\n"
                "<iframe src=y></iframe>\n<script>1</script>\n<!-- hidden -->\n")
        v.write("wiki/topics/tides.md", page(["raw/tides.md"], body))
        out, count = v.lint()
        for code, line in (("REMOTE-EMBED", 7), ("HTML-IMG", 8), ("IFRAME", 9), ("SCRIPT", 10), ("HTML-COMMENT", 11)):
            self.assertIn(f"PROBLEM {code}: wiki/topics/tides.md:{line}", out)
        self.assertEqual(count, 5)

    def test_local_embed_and_fenced_html_pass(self):
        v = Vault(self)
        body = "[[salt]]\n![map](../assets/map.png)\n```html\n<!-- example -->\n<script></script>\n```\n"
        v.write("wiki/topics/tides.md", page(["raw/tides.md"], body))
        out, count = v.lint()
        self.assertEqual(count, 0, out)

    def test_raw_html_is_not_flagged_as_active(self):
        v = Vault(self)
        v.write("raw/clips/page.md", "<!-- tracker --><img src=https://t.example.net/p.gif>\n")
        out, _ = v.lint()
        self.assertNotIn("HTML-COMMENT", out)
        self.assertNotIn("HTML-IMG", out)


class Privacy(unittest.TestCase):
    def test_email_path_and_secret_named_never_printed(self):
        v = Vault(self)
        email = "jordan.reed" + "@" + "mailhost.example"
        path = os.sep.join(["C:", "Users", "jreed", "notes.txt"])
        secret = "gh" + "p_" + "Q7" * 18
        v.write("raw/clips/leak.md", f"line one\ncontact {email}\nfile {path}\ntoken {secret}\n")
        out, count = v.lint()
        self.assertIn("PROBLEM EMAIL: raw/clips/leak.md:2 (value not shown)", out)
        self.assertIn("PROBLEM USER-PATH: raw/clips/leak.md:3 (value not shown)", out)
        self.assertIn("PROBLEM SECRET: raw/clips/leak.md:4 (value not shown; rotate it first", out)
        for value in (email, "jreed", secret):
            self.assertNotIn(value, out)
        self.assertEqual(count, 3)

    def test_noreply_and_placeholder_paths_pass(self):
        v = Vault(self)
        noreply = "12345+bot" + "@" + "users.noreply.github.com"
        placeholders = "/" + "Users/<you>/vault\n" + "/" + "home/user/vault\n~/vault\n"  # split: no path literal
        v.write("raw/clips/ok.md", f"{noreply}\n{placeholders}")
        out, count = v.lint()
        self.assertEqual(count, 0, out)

    def test_privacy_signal_threshold(self):
        v = Vault(self)
        recent = [(TODAY - datetime.timedelta(days=d)).isoformat() for d in (1, 10, 29)]
        old = (TODAY - datetime.timedelta(days=45)).isoformat()
        v.write("wiki/privacy-signals.md", "".join(f"{d} health\n" for d in recent[:2]) + f"{old} address\n")
        out, _ = v.lint()
        self.assertIn("privacy signals, last 30 days: 2", out)
        self.assertNotIn("ADVICE: ", out)
        v.write("wiki/privacy-signals.md", "".join(f"{d} contact\n" for d in recent))
        out, _ = v.lint()
        self.assertIn("ADVICE: 3 privacy signals in 30 days", out)
        self.assertIn("moving never erases git history", out)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class RawChanges(unittest.TestCase):
    def git(self, root, *args):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@users.noreply.github.com",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@users.noreply.github.com")
        no_window = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=root, env=env, check=True,
                       capture_output=True, stdin=subprocess.DEVNULL, **no_window)

    def test_changed_raw_flagged_notes_and_ok_list_exempt(self):
        v = Vault(self)
        v.write("raw/notes/mine.md", "draft\n")
        self.git(v.root, "init", "-q")
        self.git(v.root, "add", "-A")
        self.git(v.root, "commit", "-q", "-m", "init")
        v.write("raw/tides.md", "Tides follow the moon and the sun.\n")
        v.write("raw/notes/mine.md", "edited\n")
        (v.root / "raw/salt.md").unlink()
        v.write("raw-removed-ok.txt", "raw/salt.md\n")
        out, _ = v.lint(use_git=True)
        self.assertIn("PROBLEM RAW-CHANGED: raw/tides.md", out)
        self.assertNotIn("RAW-CHANGED: raw/notes/mine.md", out)
        self.assertNotIn("RAW-CHANGED: raw/salt.md", out)

    def test_no_git_tree_is_not_run_not_pass(self):
        v = Vault(self)
        with unittest.mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(v.root.parent)}):
            out, _ = v.lint(use_git=True)
        self.assertIn("NOT-RUN: raw change check", out)


class Cli(unittest.TestCase):
    def run_main(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = vault_lint.main(list(args))
        return code, buf.getvalue()

    def test_exit_codes(self):
        v = Vault(self)
        self.assertEqual(self.run_main(str(v.root), "--no-git", "--today", "2026-11-09")[0], 0)
        v.write("wiki/topics/tides.md", page([], "[[salt]]\n"))
        self.assertEqual(self.run_main(str(v.root), "--no-git")[0], 1)
        code, out = self.run_main(str(v.root / "raw"))
        self.assertEqual(code, 2)
        self.assertIn("no wiki/ folder", out)
        self.assertEqual(self.run_main(str(v.root), "--today", "soon")[0], 2)

    def test_lint_writes_nothing(self):
        v = Vault(self)
        before = sorted((p.as_posix(), p.stat().st_mtime_ns) for p in v.root.rglob("*"))
        self.run_main(str(v.root), "--no-git")
        after = sorted((p.as_posix(), p.stat().st_mtime_ns) for p in v.root.rglob("*"))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
