"""Tests for shieldwarden's signposts scan. Stdlib unittest; every fixture lives in a temp folder.

    python -m unittest discover -s scripts -p "test_*.py"
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import signposts  # noqa: E402
from warden_fs import USERS, redact  # noqa: E402



def make_link(target: Path, link: Path) -> str:
    """A junction on Windows (no admin needed), a symlink elsewhere. Returns the kind made."""
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
        return "junction"
    os.symlink(target, link, target_is_directory=True)
    return "symlink"


def run(fn, argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = fn(argv)
    return code, out.getvalue(), err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sw-sign-"))

    def tearDown(self):
        # remove links first so rmtree never walks through one
        for dp, dns, fns in os.walk(self.tmp, topdown=True):
            for d in list(dns):
                p = Path(dp) / d
                if p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()):
                    os.rmdir(p) if os.name == "nt" else p.unlink()
                    dns.remove(d)
        shutil.rmtree(self.tmp, ignore_errors=True)


ICACLS_SAMPLE = (
    "{path} BUILTIN\\Administrators:(I)(OI)(CI)(F)\n"
    "{pad} NT AUTHORITY\\SYSTEM:(I)(OI)(CI)(F)\n"
    "{pad} NT AUTHORITY\\Authenticated Users:(I)(M)\n"
    "{pad} BUILTIN\\Users:(I)(OI)(CI)(RX)\n"
    "{pad} Everyone:(DENY)(W)\n"
    "\n"
    "Successfully processed 1 files; Failed processing 0 files\n")


def icacls_text(path: str) -> str:
    return ICACLS_SAMPLE.format(path=path, pad=" " * len(path))


class SignpostTests(Base):
    def fixture(self) -> Path:
        root = self.tmp / "tree"
        for d in ("docs", "Bank Statements", "src/node_modules", "src/.git", "deep/a/b", "plain"):
            (root / d).mkdir(parents=True)
        (root / "docs" / "passwords.txt").write_bytes(b"do-not-read")
        (root / "docs" / "syntax-notes.txt").write_bytes(b"x")            # 'tax' only inside a word
        (root / "src" / "node_modules" / "secret.js").write_bytes(b"x")    # package cache: skipped
        (root / "src" / ".git" / "secrets").write_bytes(b"x")              # git internals: skipped
        (root / "deep" / "a" / "b" / "secret.txt").write_bytes(b"x")       # below the depth cap
        (root / "plain" / "bluefinch-notes.md").write_bytes(b"x")          # a private-list word
        make_link(root / "plain", root / "keys")                           # a link named like a signpost
        return root

    def scan(self, argv, access=None):
        code, out, err = run(lambda a: signposts.main(a, access=access), argv)
        return code, (json.loads(out) if out.strip().startswith("{") else None), out, err

    def test_name_matching_is_whole_word(self):
        words = signposts.shipped_words()
        label = lambda n: [m["label"] for m in signposts.match_name(n, words)]  # noqa: E731
        self.assertEqual(label("Passwords.xlsx"), ["passwords"])
        self.assertEqual(label("syntax.txt"), [])
        self.assertEqual(label("taxonomy"), [])
        self.assertEqual(label("Top Secret plans")[0], "top secret")
        self.assertEqual(label("id_rsa"), ["id rsa"])
        self.assertIn("passwords", label("MyPasswords2024.txt"))
        self.assertEqual(label("2FA-backup-codes.txt")[0], "backup codes")
        self.assertEqual(label("PrivateKey.pem")[0], "private key")

    def test_scan_names_only_skips_caches_links_and_caps_depth(self):
        root = self.fixture()
        real_open = open

        def guard(file, *a, **k):
            if str(Path(str(file)).resolve()).startswith(str(root.resolve())):
                raise AssertionError(f"signposts opened a scanned file: {file}")
            return real_open(file, *a, **k)
        with mock.patch("builtins.open", guard), mock.patch("io.open", guard), \
                mock.patch.dict(os.environ, {signposts.ENV_WORDS: ""}), \
                mock.patch.object(signposts, "DEFAULT_WORDS_FILE", self.tmp / "absent.txt"):
            code, d, _, err = self.scan([str(root), "--json", "-", "--access", "none", "--depth", "3"])
        self.assertEqual(code, 1, err)
        names = {Path(h["path"]).name: h for h in d["hits"]}
        self.assertIn("passwords.txt", names)
        self.assertIn("Bank Statements", names)
        self.assertEqual(names["keys"]["kind"], "link")
        for absent in ("syntax-notes.txt", "secret.js", "secrets", "secret.txt", "bluefinch-notes.md"):
            self.assertNotIn(absent, names)
        reasons = {Path(r["path"]).name: r["reason"] for r in d["not_scanned"]["listed"]}
        self.assertEqual(reasons["node_modules"], "package cache")
        self.assertEqual(reasons[".git"], "git internals")
        self.assertIn("not followed", reasons["keys"])
        self.assertIn("depth cap", reasons["b"])
        self.assertNotIn("do-not-read", json.dumps(d))

    def test_private_list_masked_and_accept(self):
        root = self.fixture()
        plist = self.tmp / "private" / "glossary.txt"
        plist.parent.mkdir()
        plist.write_text("# comment\nbluefinch\naccept: " + str(root / "docs" / "passwords.txt") + "\n",
                         encoding="utf-8")
        with mock.patch.dict(os.environ, {signposts.ENV_WORDS: str(plist)}):
            code, d, out, _ = self.scan([str(root), "--json", "-", "--access", "none"])
        names = {Path(h["path"]).name: h for h in d["hits"]}
        self.assertEqual(names["bluefinch-notes.md"]["matched"][0]["label"], "private list #1")
        self.assertNotIn("passwords.txt", names)
        self.assertEqual(d["counts"]["accepted"], 1)
        self.assertEqual(d["words"]["private"]["source"], "env")
        self.assertNotIn('"bluefinch"', out)

    def test_private_list_inside_git_tree_refused(self):
        repo = self.tmp / "repo"
        (repo / ".git").mkdir(parents=True)
        (repo / "words.txt").write_text("x\n", encoding="utf-8")
        code, _, _, err = self.scan([str(self.tmp), "--words", str(repo / "words.txt"), "--access", "none"])
        self.assertEqual(code, 2)
        self.assertIn("git work tree", err)

    def test_parse_icacls_rows_and_broad_grants(self):
        path = "C:\\data\\Bank Statements"
        rows = signposts.parse_icacls(icacls_text(path), path)
        self.assertEqual(len(rows), 5)
        users = next(r for r in rows if r["account"] == "BUILTIN\\Users")
        self.assertEqual(users["rights"], ["read+execute"])
        self.assertTrue(users["inherited"])
        self.assertEqual(users["flags"], ["OI", "CI"])
        self.assertTrue(rows[-1]["deny"])
        self.assertEqual(signposts.broad_from_rows(rows),
                         ["Authenticated Users: modify (inherited)", "Users: read+execute (inherited)"])
        garbled = signposts.parse_icacls(icacls_text("C:\\d?ta\\x"), "C:\\data\\x")   # echoed path differs
        self.assertEqual(garbled[0]["account"], "BUILTIN\\Administrators")

    def test_parse_net_share_skips_admin_shares(self):
        text = ("Share name   Resource                        Remark\n\n"
                "-------------------------------------------------------\n"
                "C$           C:\\                              Default share\n"
                "Team         D:\\Shared Stuff                 Team files\n"
                "The command completed successfully.\n")
        self.assertEqual(signposts.parse_net_share(text), ["d:" + "/shared stuff"])   # split: path-leak test

    def test_windows_access_mocked_ranks_and_proposes(self):
        root = self.fixture()
        share_text = f"Team         {root / 'Bank Statements'}       files\n"
        calls = []

        def fake(cmd):
            calls.append(cmd[0])
            return share_text if cmd[0] == "net" else icacls_text(cmd[1])
        user = sorted(USERS)[0] if USERS else "someone"
        acc = signposts.Access("windows", runner=fake, owner_fn=lambda p: f"HOSTX\\{user}")
        if os.name != "nt":                                                  # net share lists drive paths
            acc._shares = [signposts.norm(str(root / "Bank Statements")).casefold()]
        with mock.patch.dict(os.environ, {"COMPUTERNAME": "HOSTX", signposts.ENV_WORDS: ""}), \
                mock.patch.object(signposts, "DEFAULT_WORDS_FILE", self.tmp / "absent.txt"), \
                mock.patch("subprocess.run", side_effect=AssertionError("no real process in this test")):
            code, d, out, _ = self.scan([str(root), "--json", "-", "--shell", "ps"], access=acc)
        self.assertEqual(calls.count("net"), 1 if os.name == "nt" else 0)
        top = d["hits"][0]
        self.assertEqual(Path(top["path"]).name, "Bank Statements")          # shared + broad ranks first
        self.assertEqual(top["risk"], "high")
        self.assertIn("shared on the network", top["access"]["broad"])
        self.assertEqual(top["access"]["owner"], "<host>\\<user>")
        self.assertNotIn("HOSTX", out)
        actions = [s["action"] for s in top["suggestions"]]
        self.assertEqual(actions[:3], ["lock down", "move", "rename"])
        self.assertIn("/inheritance:r", top["suggestions"][0]["command"])
        self.assertIn("(OI)(CI)F", top["suggestions"][0]["command"])
        pw = next(h for h in d["hits"] if h["path"].endswith("passwords.txt"))
        self.assertIn("encrypt", [s["action"] for s in pw["suggestions"]])
        self.assertNotIn("password", next(s for s in pw["suggestions"] if s["action"] == "rename")["command"]
                         .split("-NewName")[1].lower())

    def test_posix_mode_bits(self):
        loose = signposts.posix_access(0o100644, "u", "staff", False)
        self.assertEqual(loose["broad"], ["world-readable", "group-readable (staff)"])
        self.assertTrue(loose["world"])
        self.assertEqual(signposts.posix_access(0o100600, "u", "g", False)["broad"], [])
        grp = signposts.posix_access(0o040750, "u", "g", True)
        self.assertEqual(grp["broad"], ["group-readable (g)"])
        self.assertFalse(grp["world"])

    @unittest.skipIf(os.name == "nt", "POSIX mode bits")
    def test_posix_real_chmod(self):
        f = self.tmp / "tax-2025.pdf"
        f.write_bytes(b"x")
        os.chmod(f, 0o644)
        code, d, _, _ = self.scan([str(self.tmp), "--json", "-", "--access", "posix", "--shell", "sh"])
        hit = next(h for h in d["hits"] if h["path"].endswith("tax-2025.pdf"))
        self.assertIn("world-readable", hit["access"]["broad"])
        self.assertTrue(hit["suggestions"][0]["command"].startswith("chmod 600"))

    def test_app_owned_names_are_not_renamed_or_moved(self):
        home = str(Path.home())
        hit = {"path": redact(os.path.join(home, ".ssh", "id_rsa")), "name": "id_rsa", "kind": "file",
               "matched": signposts.match_name("id_rsa", signposts.shipped_words()),
               "access": {"checked": True, "broad": ["world-readable"], "world": True},
               "location": {"synced": None, "exposed": None},
               "app_owned": signposts.app_owned(os.path.join(home, ".ssh", "id_rsa"))}
        self.assertTrue(hit["app_owned"])
        acts = [s["action"] for s in signposts.suggestions(hit, signposts.shipped_words(), "sh")]
        self.assertEqual(acts, ["lock down", "encrypt"])

    def test_location_synced_and_exposed(self):
        od = self.tmp / "OneDrive"
        with mock.patch.dict(os.environ, {"OneDrive": str(od)}):
            self.assertEqual(signposts.location(str(od / "tax"))["synced"], "OneDrive")
        self.assertEqual(signposts.location(os.path.join(str(Path.home()), "Downloads", "x"))["exposed"],
                         "Downloads")

    def test_entry_cap_is_partial_and_template_is_comments(self):
        root = self.fixture()
        code, d, _, _ = self.scan([str(root), "--json", "-", "--access", "none", "--max-entries", "2"])
        self.assertEqual(code, 1)
        self.assertIn("entry cap", d["partial"])
        code, _, out, _ = self.scan(["--template"])
        self.assertEqual(code, 0)
        self.assertTrue(all(ln.startswith("#") for ln in out.splitlines() if ln.strip()))


if __name__ == "__main__":
    unittest.main()
