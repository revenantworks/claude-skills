"""Tests for identity_check.py. Run: python -m unittest discover -s scripts -p "test_*.py"

Every fixture is invented. Each test runs git in a temporary repo with an isolated global config
(GIT_CONFIG_GLOBAL points at a temp file, GIT_CONFIG_NOSYSTEM=1), so no real identity or config
is read or changed. The canary values must never appear in stdout or stderr, on success or crash.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import identity_check as ic  # noqa: E402

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
CANARY_NAME = "Quillon Marrowby"
CANARY_CLIENT = "Tessaract Holdings"
# Test addresses are assembled at run time from invented parts on the reserved .test domain,
# so the tracked file holds no address literal and a repo-wide email guard stays meaningful.
def at(local, domain):
    return local + chr(64) + domain


CANARY_EMAIL = at("q.marrowby", "canarymail.test")
OTHER_EMAIL = at("someone", "realmail.test")
ASSISTANT_EMAIL = at("noreply", "assistant.test")
NOREPLY = "4242+octo-handle@users.noreply.github.com"
CANARIES = (CANARY_NAME, CANARY_CLIENT, CANARY_EMAIL, "marrowby", "tessaract", "canarymail")

POLICY = {
    "version": 1,
    "values_keys": ["real-name:owner", "client:client-1", "email:personal"],
    "classes": ["real-name", "employer", "client", "email"],
    "codenames": {"client:client-1": "the client", "real-name:owner": "the user"},
    "surfaces": {
        "tracked-files": {"banned": ["real-name", "employer", "client", "email"], "email_any": True},
        "commit-metadata": {"banned": ["real-name", "employer", "client", "email"], "email_any": True},
    },
    "allowed_emails": [r"^(\d+\+)?[A-Za-z0-9-]+@users\.noreply\.github\.com$", r"@example\.(com|org|net)$"],
    "allowed_trailer_emails": ["^" + ASSISTANT_EMAIL.replace(".", r"\.") + "$"],
    "exclude": [],
}
VALUES = (f"# invented test values\nreal-name:owner = {CANARY_NAME}\n"
          f"client:client-1 = {CANARY_CLIENT}\nemail:personal = {CANARY_EMAIL}\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.globalcfg = self.root / "global.gitconfig"
        self.globalcfg.write_text("", encoding="utf-8")
        # The values file sits in a private folder outside the repo, named by the variable; the home
        # folder points at an empty temp folder so the real ~/.warden is never read.
        self.home = self.root / "home"
        self.home.mkdir()
        self.values = self.root / "private" / "aliases.txt"
        self.values.parent.mkdir()
        self.values.write_text(VALUES, encoding="utf-8")
        env = {"GIT_CONFIG_GLOBAL": str(self.globalcfg), "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_TERMINAL_PROMPT": "0", "HOME": str(self.home), "USERPROFILE": str(self.home),
               "WARDEN_IDENTITY_VALUES_FILE": str(self.values)}
        self.env = mock.patch.dict(os.environ, env)
        self.env.start()
        self.git("init", "-q", "-b", "main")
        self.policy = self.repo / "identity-policy.json"
        self.write_policy(POLICY)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def write_policy(self, pol):
        self.policy.write_text(json.dumps(pol), encoding="utf-8")

    def git(self, *args, env=None):
        e = dict(os.environ, **(env or {}))
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True,
                              env=e, check=True, creationflags=NO_WINDOW).stdout

    def commit(self, name, msg, an="Octo", ae=NOREPLY, cn="Octo", ce=NOREPLY, body="x\n"):
        (self.repo / name).write_text(body, encoding="utf-8")
        self.git("add", name)
        self.git("commit", "-q", "-m", msg, env={"GIT_AUTHOR_NAME": an, "GIT_AUTHOR_EMAIL": ae,
                                                 "GIT_COMMITTER_NAME": cn, "GIT_COMMITTER_EMAIL": ce})
        return self.git("rev-parse", "HEAD").strip()

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ic.main(list(argv))
        self.assert_no_canary(out.getvalue() + err.getvalue())
        data = json.loads(out.getvalue()) if out.getvalue().strip() else {}
        return code, data

    def assert_no_canary(self, text):
        low = text.lower()
        for c in CANARIES:
            self.assertNotIn(c.lower(), low, "a banned value reached the output")

    def rules(self, data):
        return [f["rule"] for f in data.get("findings", [])]


class CheckMode(Base):
    def test_codename_required_and_value_absent(self):
        draft = self.root / "draft.md"
        draft.write_text(f"Status update\n{CANARY_CLIENT} signs off on Friday.\n", encoding="utf-8")
        code, data = self.run_main("check", "--policy", str(self.policy), "--surface", "tracked-files",
                                   "--text", str(draft), "--repo", str(self.repo))
        self.assertEqual(code, 1)
        hit = [f for f in data["findings"] if f["rule"] == "codename-required"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["use"], "the client")
        self.assertEqual(hit[0]["where"], "draft.md:2")

    def test_email_in_text_flagged_placeholder_clean(self):
        draft = self.root / "page.md"
        draft.write_text(f"Write to {OTHER_EMAIL}\nor user@example.com\n", encoding="utf-8")
        code, data = self.run_main("check", "--policy", str(self.policy), "--surface", "tracked-files",
                                   "--text", str(draft))
        self.assertEqual(code, 1)
        self.assertEqual(self.rules(data), ["email-not-allowed"])
        self.assertNotIn("realmail", json.dumps(data))

    def test_staged_diff(self):
        self.commit("a.txt", "base")
        (self.repo / "notes.md").write_text("one\ncontact " + CANARY_EMAIL + "\n", encoding="utf-8")
        self.git("add", "notes.md")
        code, data = self.run_main("check", "--policy", str(self.policy), "--surface", "tracked-files",
                                   "--staged", "--repo", str(self.repo))
        self.assertEqual(code, 1)
        self.assertIn("banned-value", self.rules(data))
        self.assertTrue(any(f["where"] == "notes.md:2" for f in data["findings"]))

    def test_exclude_suppresses(self):
        pol = dict(POLICY, exclude=[{"where": "page.md:*", "rule": "email-not-allowed"}])
        self.write_policy(pol)
        draft = self.root / "page.md"
        draft.write_text(f"Write to {OTHER_EMAIL}\n", encoding="utf-8")
        code, data = self.run_main("check", "--policy", str(self.policy), "--surface", "tracked-files",
                                   "--text", str(draft))
        self.assertEqual((code, data["findings"]), (0, []))

    def test_salted_fingerprint(self):
        draft = self.root / "d.md"
        draft.write_text(CANARY_NAME + "\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"VW_SALT": "s3"}):
            _, a = self.run_main("check", "--policy", str(self.policy), "--surface", "tracked-files",
                                 "--text", str(draft), "--salt-env", "VW_SALT")
            _, b = self.run_main("check", "--policy", str(self.policy), "--surface", "tracked-files",
                                 "--text", str(draft), "--salt-env", "VW_SALT")
        fp = a["findings"][0]["fp"]
        self.assertRegex(fp, r"^[0-9a-f]{12}$")
        self.assertEqual(fp, b["findings"][0]["fp"])

    def test_bad_policy_exit_3(self):
        self.policy.write_text("{not json", encoding="utf-8")
        code, data = self.run_main("check", "--policy", str(self.policy), "--surface", "tracked-files",
                                   "--stdin")
        self.assertEqual((code, data["error"]), (3, "input"))


class IdentityMode(Base):
    def test_range_flags_middle_commit_only(self):
        self.commit("1.txt", "first")
        bad = self.commit("2.txt", "second", cn="Octo", ce=CANARY_EMAIL)
        self.commit("3.txt", "third")
        code, data = self.run_main("identity", "--policy", str(self.policy), "--repo", str(self.repo),
                                   "--range", "HEAD")
        self.assertEqual(code, 1)
        hits = [f for f in data["findings"] if f["rule"] == "non-noreply-committer"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["commit"], bad[:12])
        self.assertNotIn("non-noreply-author", self.rules(data))

    def test_trailer_address(self):
        self.commit("1.txt", f"feat\n\nCo-authored-by: Pal <{CANARY_EMAIL}>\nCo-authored-by: Assistant <{ASSISTANT_EMAIL}>\n")
        code, data = self.run_main("identity", "--policy", str(self.policy), "--repo", str(self.repo),
                                   "--range", "HEAD")
        tr = [f for f in data["findings"] if f["rule"] == "trailer-email-not-allowed"]
        self.assertEqual(len(tr), 1)
        self.assertEqual(tr[0]["field"], "trailer:co-authored-by")

    def test_global_fallback_named_with_one_fix(self):
        self.globalcfg.write_text(f"[user]\n\temail = {NOREPLY}\n\tname = Octo\n", encoding="utf-8")
        code, data = self.run_main("identity", "--policy", str(self.policy), "--repo", str(self.repo))
        self.assertEqual(code, 1)
        nl = [f for f in data["findings"] if f["rule"] == "no-local-identity"]
        self.assertEqual(len(nl), 1)
        self.assertEqual(nl[0]["source"], "global-default")
        self.assertIn("config --local user.email", nl[0]["fix"])
        self.assertIn("use-config-only-off", self.rules(data))

    def test_local_identity_ok(self):
        self.git("config", "--local", "user.email", NOREPLY)
        self.git("config", "--local", "user.useConfigOnly", "true")
        code, data = self.run_main("identity", "--policy", str(self.policy), "--repo", str(self.repo))
        self.assertEqual((code, self.rules(data)), (0, ["identity-ok"]))

    def test_no_identity_anywhere(self):
        code, data = self.run_main("identity", "--policy", str(self.policy), "--repo", str(self.repo))
        self.assertEqual(code, 1)
        self.assertEqual(self.rules(data), ["no-identity"])

    def test_root_sweep(self):
        other = self.root / "repo2"
        other.mkdir()
        subprocess.run(["git", "init", "-q", str(other)], check=True, capture_output=True, creationflags=NO_WINDOW)
        subprocess.run(["git", "-C", str(other), "config", "--local", "user.email", CANARY_EMAIL],
                       check=True, capture_output=True, creationflags=NO_WINDOW)
        code, data = self.run_main("identity", "--policy", str(self.policy), "--root", str(self.root))
        self.assertEqual(code, 1)
        wheres = {f["where"] for f in data["findings"]}
        self.assertEqual(wheres, {"repo", "repo2"})
        self.assertIn("identity-email-not-allowed",
                      [f["rule"] for f in data["findings"] if f["where"] == "repo2"])


class LintAndSafety(Base):
    def test_private_values_file_is_clean(self):
        code, data = self.run_main("lint", "--policy", str(self.policy), "--repo", str(self.repo))
        self.assertEqual((code, data["findings"]), (0, []))

    def test_default_private_folder_is_found(self):
        os.environ.pop("WARDEN_IDENTITY_VALUES_FILE")
        (self.home / ".warden").mkdir()
        (self.home / ".warden" / "aliases.txt").write_text(VALUES, encoding="utf-8")
        code, data = self.run_main("lint", "--policy", str(self.policy), "--repo", str(self.repo))
        self.assertEqual((code, data["findings"]), (0, []))

    def test_no_values_file_names_the_setup_command(self):
        os.environ.pop("WARDEN_IDENTITY_VALUES_FILE")
        code, data = self.run_main("lint", "--policy", str(self.policy), "--repo", str(self.repo))
        self.assertEqual((code, self.rules(data)), (1, ["values-file-missing"]))
        self.assertIn("setup identity-values", data["findings"][0]["setup"])
        draft = self.root / "d.md"
        draft.write_text("hello\n", encoding="utf-8")
        code, data = self.run_main("check", "--policy", str(self.policy), "--surface", "tracked-files",
                                   "--text", str(draft))
        self.assertEqual(code, 3)
        self.assertIn("NOT-RUN", data["detail"])

    def test_old_in_repo_values_file_is_reported_not_used(self):
        """Backward compatibility: the earlier gitignored in-repo file gets one move command."""
        os.environ.pop("WARDEN_IDENTITY_VALUES_FILE")
        (self.repo / "aliases.txt").write_text(VALUES, encoding="utf-8")
        (self.repo / ".gitignore").write_text("aliases.txt\n", encoding="utf-8")
        self.write_policy(dict(POLICY, values_file="aliases.txt"))
        code, data = self.run_main("lint", "--policy", str(self.policy), "--repo", str(self.repo))
        self.assertEqual((code, self.rules(data)), (1, ["values-file-in-repo"]))
        self.assertIn("adopt identity-values", data["findings"][0]["fix"])
        draft = self.root / "d.md"
        draft.write_text(f"{CANARY_CLIENT}\n", encoding="utf-8")
        code, data = self.run_main("check", "--policy", str(self.policy), "--surface", "tracked-files",
                                   "--text", str(draft))
        self.assertEqual(code, 3)

    def test_values_flag_inside_a_repo_is_refused(self):
        (self.repo / "v.txt").write_text(VALUES, encoding="utf-8")
        code, data = self.run_main("lint", "--policy", str(self.policy), "--values", str(self.repo / "v.txt"),
                                   "--repo", str(self.repo))
        self.assertEqual((code, self.rules(data)), (1, ["values-file-in-repo"]))

    def test_values_named_but_missing_is_bad_input(self):
        code, data = self.run_main("lint", "--policy", str(self.policy), "--values", str(self.root / "nope.txt"))
        self.assertEqual(code, 3)

    def test_label_containing_value(self):
        self.values.write_text("real-name:marrowby = Marrowby\n", encoding="utf-8")
        self.write_policy(dict(POLICY, values_keys=["real-name:marrowby"], codenames={}))
        code, data = self.run_main("lint", "--policy", str(self.policy), "--repo", str(self.repo))
        self.assertIn("label-contains-value", self.rules(data))

    def test_crash_prints_type_only(self):
        draft = self.root / "d.md"
        draft.write_text("hello\n", encoding="utf-8")
        boom = RuntimeError(f"failed on {CANARY_NAME} <{CANARY_EMAIL}>")
        with mock.patch.object(ic, "scan_text", side_effect=boom):
            code, data = self.run_main("check", "--policy", str(self.policy), "--surface", "tracked-files",
                                       "--text", str(draft))
        self.assertEqual((code, data), (4, {"error": "internal", "type": "RuntimeError"}))


class PolicyFormats(Base):
    """Owner Q26: JSON by default; an optional YAML path, offered with its pros and cons."""

    def test_formats_reports_json_default_and_yaml_trade_offs(self):
        with mock.patch.object(ic, "pyyaml_available", return_value=False):
            code, data = self.run_main("formats", "--repo", str(self.repo))
        self.assertEqual(code, 0)
        self.assertEqual(data["default"], "json")
        self.assertFalse(data["yaml"]["available"])
        text = json.dumps(data["yaml"]).lower()
        for word in ("pyyaml", "install", "comment", "hand-edit"):
            self.assertIn(word, text)
        self.assertIn("never installs", text)
        self.assertEqual(data["found"], ["identity-policy.json"])

    def test_formats_says_when_pyyaml_is_present(self):
        with mock.patch.object(ic, "pyyaml_available", return_value=True):
            code, data = self.run_main("formats", "--repo", str(self.repo))
        self.assertTrue(data["yaml"]["available"])

    def test_policy_is_found_in_the_repo_root_when_not_named(self):
        self.commit("a.txt", "plain message")
        code, data = self.run_main("lint", "--repo", str(self.repo))
        self.assertIn(code, (0, 1))
        self.assertNotIn("error", data)

    def test_json_and_yaml_side_by_side_is_refused(self):
        (self.repo / "identity-policy.yaml").write_text("version: 1\n", encoding="utf-8")
        code, data = self.run_main("lint", "--repo", str(self.repo))
        self.assertEqual(code, 3)
        self.assertIn("two policy files", data["detail"])
        code, data = self.run_main("formats", "--repo", str(self.repo))
        self.assertEqual(code, 1)
        self.assertTrue(data["conflict"])

    def test_yaml_policy_without_pyyaml_names_the_json_form(self):
        y = self.repo / "p.yaml"
        y.write_text("version: 1\n", encoding="utf-8")
        with mock.patch.dict(sys.modules, {"yaml": None}):
            code, data = self.run_main("lint", "--policy", str(y), "--repo", str(self.repo))
        self.assertEqual(code, 3)
        self.assertIn("JSON", data["detail"])

    @unittest.skipUnless(ic.pyyaml_available(), "PyYAML not installed (the skill never installs it)")
    def test_yaml_policy_matches_json_policy(self):
        import yaml
        y = self.repo / "p.yaml"
        y.write_text(yaml.safe_dump(POLICY), encoding="utf-8")
        a = self.run_main("lint", "--policy", str(self.policy), "--repo", str(self.repo))
        b = self.run_main("lint", "--policy", str(y), "--repo", str(self.repo))
        self.assertEqual(a[0], b[0])
        self.assertEqual(self.rules(a[1]), self.rules(b[1]))


if __name__ == "__main__":
    unittest.main()
