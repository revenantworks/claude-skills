"""Tests for keywarden's scripts: the canary gate.

Run: python -m unittest discover -s <member>/scripts -p "test_*.py"

Every secret here is an invented canary built at run time from pieces, so no
token-shaped literal sits in the repo. The gate for every script is the same:
the canary's bytes never appear in stdout, stderr or any JSON the script
writes, on the success path, on a failing command, and on a crash.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import kw_common  # noqa: E402
import cred_inventory  # noqa: E402
import preflight  # noqa: E402
import scope_check  # noqa: E402

PY = sys.executable


def canary(tag: str, prefix: str = "ghp_") -> str:
    return prefix + "CANARY" + tag + "q7" * 14


GH = canary("gh")
FG = canary("fg", "github_pat_")
SK = canary("sk", "sk-")
GENERIC = "CANARYgeneric" + "z9" * 10


def run(args, env=None, cwd=None):
    full_env = dict(os.environ)
    full_env.pop("GH_DEBUG", None)
    if env:
        full_env.update(env)
    proc = subprocess.run([PY] + [str(a) for a in args], capture_output=True, text=True,
                          env=full_env, cwd=cwd, timeout=60)
    return proc.returncode, proc.stdout, proc.stderr


class CanaryMixin:
    canaries = (GH, FG, SK, GENERIC)

    def assertNoCanary(self, *texts):
        for text in texts:
            for c in self.canaries:
                self.assertNotIn(c, text)
                self.assertNotIn(c.lower(), text)
                self.assertNotIn("CANARY", text.upper().replace("<MASKED", ""))


# --------------------------------------------------------------------- common
class CommonTests(unittest.TestCase):
    def test_fingerprint_matches_shieldwarden_method(self):
        import hashlib
        expect = hashlib.sha256(("salt" + GH.lower()).encode()).hexdigest()[:12]
        self.assertEqual(kw_common.fingerprint(GH, "salt"), expect)

    def test_prefix_classes(self):
        self.assertEqual(kw_common.prefix_class(GH), "github-classic-pat")
        self.assertEqual(kw_common.prefix_class(FG), "github-fine-grained-pat")
        self.assertEqual(kw_common.prefix_class("plainvalue123"), "unknown")

    def test_reference_values_are_not_plaintext(self):
        for v in ("op://vault/item/field", "${GH_TOKEN}", "$GH_TOKEN", "", "<your-token>",
                  "%GH_TOKEN%", "bws://x", "changeme"):
            self.assertTrue(kw_common.is_reference(v), v)
        self.assertFalse(kw_common.is_reference(GH))

    def test_secret_named(self):
        for k in ("GH_TOKEN", "OPENAI_API_KEY", "db_password", "Authorization", "CLIENT_SECRET"):
            self.assertTrue(kw_common.secret_named(k), k)
        for k in ("LOG_LEVEL", "PATH", "TOKENIZERS_PARALLELISM"):
            self.assertFalse(kw_common.secret_named(k), k)

    def test_mask_text_hides_values_and_shapes(self):
        text = f"401 for {GH} and Authorization: Bearer {GENERIC} and {SK}"
        out, n = kw_common.mask_text(text, [GENERIC], "salt")
        self.assertNotIn(GH, out)
        self.assertNotIn(GENERIC, out)
        self.assertNotIn(SK, out)
        self.assertIn("<masked", out)
        self.assertGreaterEqual(n, 3)


# ---------------------------------------------------------------- inventory
class InventoryTests(CanaryMixin, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        repo = self.root / "repo"
        (repo / ".claude").mkdir(parents=True)
        (repo / ".env").write_text(f"GH_TOKEN={GH}\nLOG_LEVEL=debug\nOP_REF=op://vault/item/token\n",
                                   encoding="utf-8")
        (repo / ".claude" / "settings.json").write_text(
            json.dumps({"env": {"OPENAI_API_KEY": SK, "MAX_THINKING": "1"}}), encoding="utf-8")
        (repo / ".mcp.json").write_text(json.dumps({"mcpServers": {"tracker": {
            "command": "npx", "env": {"TRACKER_TOKEN": FG},
            "headers": {"Authorization": "Bearer " + GENERIC}}}}), encoding="utf-8")
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = {"SHIELD_SALT": "fixture-salt", "GH_CONFIG_DIR": str(self.root / "ghcfg"),
                    "GIT_CONFIG_GLOBAL": str(self.root / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1"}

    def tearDown(self):
        self.tmp.cleanup()

    def inventory(self, *extra, env=None):
        e = dict(self.env)
        if env:
            e.update(env)
        return run([HERE / "cred_inventory.py", "--root", self.root / "repo", "--home", self.home,
                    *extra], env=e)

    def test_three_file_rows_and_no_canary(self):
        code, out, err = self.inventory("--stores", "files")
        self.assertNoCanary(out, err)
        self.assertEqual(code, 1, err)
        doc = json.loads(out)
        targets = sorted(r["target"] for r in doc["rows"] if r["plaintext_risk"])
        self.assertEqual(targets, ["Authorization", "GH_TOKEN", "OPENAI_API_KEY", "TRACKER_TOKEN"])
        ref = [r for r in doc["rows"] if r["target"] == "OP_REF"]
        self.assertEqual(ref[0]["kind"], "reference")
        self.assertFalse(ref[0]["plaintext_risk"])
        self.assertFalse(any(r["target"] in ("LOG_LEVEL", "MAX_THINKING") for r in doc["rows"]))
        mcp = [r for r in doc["rows"] if r["target"] == "TRACKER_TOKEN"][0]
        self.assertIn("tracker", mcp["consumer"])
        self.assertEqual(mcp["prefix_class"], "github-fine-grained-pat")
        self.assertEqual(len(mcp["fingerprint"]), 12)

    def test_same_value_in_two_places_is_linked(self):
        (self.root / "repo" / "sub").mkdir()
        (self.root / "repo" / "sub" / ".env.local").write_text(f"OTHER_TOKEN={GH}\n", encoding="utf-8")
        code, out, err = self.inventory("--stores", "files")
        self.assertNoCanary(out, err)
        rows = [r for r in json.loads(out)["rows"] if r["target"] in ("GH_TOKEN", "OTHER_TOKEN")]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["fingerprint"], rows[1]["fingerprint"])
        self.assertTrue(all(len(r["seen_at"]) == 1 for r in rows))

    def test_unparseable_json_with_canary_is_not_read_and_not_echoed(self):
        (self.root / "repo" / ".mcp.json").write_text('{"mcpServers": {"x": {"env": {"K": "' + GH + '"',
                                                       encoding="utf-8")
        code, out, err = self.inventory("--stores", "files")
        self.assertNoCanary(out, err)
        doc = json.loads(out)
        self.assertTrue(any(n["file"].endswith(".mcp.json") for n in doc["not_read"]))

    def test_process_env_store(self):
        code, out, err = self.inventory("--stores", "env", env={"KW_FIXTURE_API_KEY": GENERIC})
        self.assertNoCanary(out, err)
        rows = [r for r in json.loads(out)["rows"] if r["target"] == "KW_FIXTURE_API_KEY"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["store"], "process-env")

    def test_gh_plaintext_hosts_file(self):
        cfg = self.root / "ghcfg"
        cfg.mkdir()
        (cfg / "hosts.yml").write_text(f"github.com:\n    oauth_token: {GH}\n    user: someone\n",
                                       encoding="utf-8")
        code, out, err = self.inventory("--stores", "gh")
        self.assertNoCanary(out, err)
        rows = json.loads(out)["rows"]
        self.assertEqual(rows[0]["store"], "gh")
        self.assertTrue(rows[0]["plaintext_risk"])
        self.assertNotIn("someone", out)

    def test_gh_keyring_is_not_a_finding(self):
        cfg = self.root / "ghcfg"
        cfg.mkdir()
        (cfg / "hosts.yml").write_text("github.com:\n    user: someone\n    git_protocol: https\n",
                                       encoding="utf-8")
        code, out, err = self.inventory("--stores", "gh")
        self.assertEqual(code, 0, err)
        rows = json.loads(out)["rows"]
        self.assertEqual(rows[0]["kind"], "keyring (value not read)")

    def test_gcm_store_helper_and_git_credentials(self):
        (self.root / "gitconfig").write_text("[credential]\n\thelper = store\n", encoding="utf-8")
        (self.home / ".git-credentials").write_text(f"https://someone:{GH}@github.com\n", encoding="utf-8")
        code, out, err = self.inventory("--stores", "gcm")
        self.assertNoCanary(out, err)
        self.assertNotIn("someone", out)
        doc = json.loads(out)
        if doc["stores"]["gcm"] != "RUN":
            self.skipTest("git not on PATH: " + doc["stores"]["gcm"])
        self.assertEqual(code, 1)
        self.assertTrue(any(r["target"] == "https://github.com" and r["plaintext_risk"] for r in doc["rows"]))
        self.assertTrue(any(r["target"] == "credential.helper" and r["plaintext_risk"] for r in doc["rows"]))

    def test_wincred_from_captured_listing(self):
        listing = self.root / "cmdkey.txt"
        listing.write_text("\nCurrently stored credentials:\n\n    Target: LegacyGeneric:target=git:https://someone@github.com\n"
                           "    Type: Generic \n    User: someone\n    Local machine persistence\n\n"
                           "    Target: Domain:target=fileserver\n    Type: Domain Password\n    User: someone\n",
                           encoding="utf-8")
        code, out, err = self.inventory("--stores", "wincred", "--cmdkey-file", listing)
        self.assertNotIn("someone", out)
        rows = json.loads(out)["rows"]
        self.assertEqual(len(rows), 2)
        self.assertIsNone(rows[0]["fingerprint"])
        self.assertTrue(rows[0]["user_present"])

    def test_not_run_store_is_never_clean(self):
        code, out, err = self.inventory("--stores", "wincred", "--cmdkey-file", self.root / "missing.txt")
        doc = json.loads(out)
        self.assertTrue(doc["stores"]["wincred"].startswith("NOT-RUN"))
        self.assertEqual(code, 3)

    def test_crash_does_not_echo_the_value(self):
        def boom(value, salt):
            raise RuntimeError("could not hash " + value)
        orig = kw_common.fingerprint
        kw_common.fingerprint = boom
        cred_inventory.kw_common.fingerprint = boom
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                    unittest.mock.patch.dict(os.environ, self.env):
                code = cred_inventory.safe_main(["--root", str(self.root / "repo"), "--home", str(self.home),
                                                 "--stores", "files"])
        finally:
            kw_common.fingerprint = orig
            cred_inventory.kw_common.fingerprint = orig
        self.assertEqual(code, 4)
        self.assertNoCanary(out.getvalue(), err.getvalue())
        self.assertIn("RuntimeError", err.getvalue())


# ------------------------------------------------------------------- docker
class DockerStoreTests(CanaryMixin, unittest.TestCase):
    """Docker's config.json and its credential helper: server names and fingerprints only."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = self.root / "dockercfg"
        self.cfg.mkdir()
        self.env = {"SHIELD_SALT": "fixture-salt", "DOCKER_CONFIG": str(self.cfg)}

    def tearDown(self):
        self.tmp.cleanup()

    def write_config(self, doc):
        (self.cfg / "config.json").write_text(json.dumps(doc), encoding="utf-8")

    def inventory(self, *extra, env=None):
        e = dict(self.env)
        if env:
            e.update(env)
        return run([HERE / "cred_inventory.py", "--home", self.root, "--stores", "docker", *extra], env=e)

    def test_inline_auth_is_plaintext_and_never_echoed(self):
        import base64
        blob = base64.b64encode(("someone:" + GH).encode()).decode()
        self.write_config({"auths": {"https://someone@registry.example.test": {"auth": blob},
                                     "ghcr.example.test": {"identitytoken": SK}}})
        code, out, err = self.inventory()
        self.assertNoCanary(out, err)
        self.assertNotIn(blob, out + err)
        self.assertNotIn("someone", out + err)
        self.assertEqual(code, 1, err)
        doc = json.loads(out)
        self.assertEqual(doc["stores"]["docker"], "RUN")
        risky = sorted(r["target"] for r in doc["rows"] if r["plaintext_risk"])
        self.assertEqual(risky, ["ghcr.example.test", "https://registry.example.test"])
        self.assertTrue(all(len(r["fingerprint"]) == 12 for r in doc["rows"] if r["plaintext_risk"]))

    def test_helpers_are_not_findings(self):
        self.write_config({"credsStore": "desktop", "credHelpers": {"gcr.example.test": "gcloud"},
                           "auths": {"https://index.docker.io/v1/": {}}})
        code, out, err = self.inventory()
        self.assertEqual(code, 0, err)
        rows = json.loads(out)["rows"]
        kinds = {r["target"]: r["kind"] for r in rows}
        self.assertEqual(kinds["credsStore"], "helper desktop")
        self.assertEqual(kinds["gcr.example.test"], "helper gcloud")
        self.assertEqual(kinds["https://index.docker.io/v1/"], "in helper desktop (value not read)")
        self.assertTrue(all(r["fingerprint"] is None for r in rows))

    def test_no_store_and_empty_auths_names_the_plaintext_default(self):
        self.write_config({"auths": {}})
        code, out, err = self.inventory()
        rows = json.loads(out)["rows"]
        self.assertEqual(rows[0]["target"], "credsStore")
        self.assertEqual(rows[0]["kind"], "helper none set")
        self.assertEqual(code, 0, err)

    def test_saved_helper_listing_keeps_server_names_only(self):
        self.write_config({"credsStore": "desktop"})
        listing = self.root / "docker-list.json"
        listing.write_text(json.dumps({"https://index.docker.io/v1/": "someone",
                                       "https://someone@registry.example.test": "someone"}),
                           encoding="utf-8")
        code, out, err = self.inventory("--docker-list-file", listing)
        self.assertNotIn("someone", out + err)
        rows = [r for r in json.loads(out)["rows"] if r["location"] == "docker-credential-desktop list"]
        self.assertEqual(sorted(r["target"] for r in rows),
                         ["https://index.docker.io/v1/", "https://registry.example.test"])
        self.assertTrue(all(r["user_present"] and r["fingerprint"] is None for r in rows))

    def test_unparseable_config_and_listing_are_not_echoed(self):
        (self.cfg / "config.json").write_text('{"auths": {"r": {"auth": "' + GH + '"', encoding="utf-8")
        listing = self.root / "bad-list.json"
        listing.write_text('{"' + GH, encoding="utf-8")
        code, out, err = self.inventory("--docker-list-file", listing)
        self.assertNoCanary(out, err)
        doc = json.loads(out)
        self.assertTrue(any(n["file"].endswith("config.json") for n in doc["not_read"]))
        self.assertTrue(doc["stores"]["docker"].startswith("NOT-RUN"))
        self.assertEqual(code, 3)

    def test_missing_config_is_not_run(self):
        code, out, err = self.inventory(env={"DOCKER_CONFIG": str(self.root / "missing")})
        self.assertTrue(json.loads(out)["stores"]["docker"].startswith("NOT-RUN"))
        self.assertEqual(code, 3)

    def test_live_listing_runs_list_and_nothing_else(self):
        self.write_config({"credsStore": "fixture"})
        calls = []

        def fake_run(argv, **kw):
            calls.append(list(argv))
            return subprocess.CompletedProcess(argv, 0, json.dumps({"registry.example.test": "someone"}), "")

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                unittest.mock.patch.dict(os.environ, self.env), \
                unittest.mock.patch.object(cred_inventory.shutil, "which",
                                           side_effect=lambda n: "fake/" + n if n.startswith("docker-credential-") else None), \
                unittest.mock.patch.object(cred_inventory.subprocess, "run", side_effect=fake_run):
            code = cred_inventory.main(["--home", str(self.root), "--stores", "docker", "--docker-list"])
        self.assertEqual(calls, [["fake/docker-credential-fixture", "list"]])
        self.assertNotIn("someone", out.getvalue() + err.getvalue())
        self.assertEqual(code, 0)
        self.assertIn("registry.example.test", out.getvalue())

    def test_live_listing_is_opt_in(self):
        self.write_config({"credsStore": "fixture"})
        with unittest.mock.patch.dict(os.environ, self.env), \
                unittest.mock.patch.object(cred_inventory.subprocess, "run",
                                           side_effect=AssertionError("ran a helper")), \
                contextlib.redirect_stdout(io.StringIO()):
            code = cred_inventory.main(["--home", str(self.root), "--stores", "docker"])
        self.assertEqual(code, 0)


# ---------------------------------------------------------------- preflight
class PreflightCheckTests(CanaryMixin, unittest.TestCase):
    def check(self, command):
        code, out, err = run([HERE / "preflight.py", "check", "--command", command])
        self.assertNoCanary(out, err)
        return code, json.loads(out)

    def rules(self, command):
        return {f["rule"] for f in self.check(command)[1]["findings"]}

    def test_curl_verbose_with_auth_header(self):
        code, doc = self.check('curl -v -H "Authorization: Bearer $GH_TOKEN" https://api.github.com/user')
        self.assertEqual(code, 1)
        self.assertIn("curl-verbose-auth", {f["rule"] for f in doc["findings"]})
        self.assertTrue(all(f["safe_rewrite"] for f in doc["findings"]))

    def test_echoing_shapes(self):
        self.assertIn("git-credential-fill", self.rules("printf 'host=github.com\\n' | git credential fill"))
        self.assertIn("gh-auth-token", self.rules("gh auth token"))
        self.assertIn("gh-show-token", self.rules("gh auth status --show-token"))
        self.assertIn("echo-secret-var", self.rules("echo $OPENAI_API_KEY"))
        self.assertIn("echo-secret-var", self.rules("Write-Output $env:GH_TOKEN"))
        self.assertIn("env-dump", self.rules("printenv"))
        self.assertIn("read-secret-file", self.rules("cat .env"))
        self.assertIn("read-secret-file", self.rules("Get-Content $HOME/.git-credentials"))

    def test_vault_reads_that_print(self):
        self.assertIn("vault-read-prints", self.rules("op read op://vault/item/credential"))
        self.assertIn("vault-read-prints", self.rules("op item get Example --reveal"))
        self.assertIn("vault-read-prints", self.rules("bw get password example"))
        self.assertNotIn("vault-read-prints", self.rules("op run --env-file .env.tpl -- npm test"))
        self.assertIn("vault-read-prints", self.rules("op run --no-masking --env-file .env.tpl -- npm test"))

    def test_script_with_secret_var_needs_masked_run(self):
        self.assertIn("unknown-failure-path", self.rules("python verify_key.py --key $OPENAI_API_KEY"))

    def test_literal_secret_is_fingerprinted_not_echoed(self):
        code, doc = self.check(f"curl -H 'Authorization: token {GH}' https://api.github.com/user")
        self.assertIn("literal-secret", {f["rule"] for f in doc["findings"]})
        self.assertEqual(doc["literal_secrets"][0]["prefix_class"], "github-classic-pat")

    def test_safe_command(self):
        code, doc = self.check("git status")
        self.assertEqual(code, 0)
        self.assertEqual(doc["verdict"], "SAFE")


class PreflightRunTests(CanaryMixin, unittest.TestCase):
    def masked(self, script, env):
        return run([HERE / "preflight.py", "run", "--", PY, "-c", script],
                   env=dict(env, SHIELD_SALT="fixture-salt"))

    def test_failing_command_output_is_masked(self):
        script = ("import os,sys; t=os.environ['KW_FIXTURE_TOKEN']; "
                  "sys.stderr.write('401 Unauthorized for token '+t+'\\n'); sys.exit(1)")
        code, out, err = self.masked(script, {"KW_FIXTURE_TOKEN": GENERIC})
        self.assertNoCanary(out, err)
        self.assertEqual(code, 1)
        self.assertIn("<masked", err)

    def test_traceback_repr_is_masked(self):
        script = ("import os; t=os.environ['KW_FIXTURE_API_KEY']; "
                  "raise RuntimeError(repr({'Authorization': 'Bearer '+t}))")
        code, out, err = self.masked(script, {"KW_FIXTURE_API_KEY": GENERIC})
        self.assertNoCanary(out, err)
        self.assertNotEqual(code, 0)
        self.assertIn("RuntimeError", err)

    def test_token_shape_not_in_env_is_masked(self):
        code, out, err = self.masked(f"print('leaked {GH}')", {})
        self.assertNoCanary(out, err)
        self.assertEqual(code, 0)

    def test_missing_program_is_not_run(self):
        code, out, err = run([HERE / "preflight.py", "run", "--", "kw-no-such-program-xyz"])
        self.assertEqual(code, 3)


# --------------------------------------------------------------- scope check
FAKE_GH = r'''
import sys
mode = sys.argv[1]
token = sys.argv[2]
if mode == "ok-classic":
    print("HTTP/2.0 200 OK")
    print("X-Oauth-Scopes: repo, admin:org, delete_repo")
    print("X-Accepted-Oauth-Scopes: ")
    print("X-Debug-Echo: " + token)
    print("")
    print('{"login": "someone", "token": "' + token + '"}')
    sys.exit(0)
if mode == "ok-fine":
    print("HTTP/2.0 200 OK")
    print("Github-Authentication-Token-Expiration: 2027-01-01 00:00:00 UTC")
    print("X-Accepted-Github-Permissions: metadata=read")
    print("")
    print('{"login": "someone"}')
    sys.exit(0)
sys.stderr.write("gh: Bad credentials (HTTP 401) for " + token + "\n")
sys.exit(1)
'''


class ScopeCheckTests(CanaryMixin, unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fake = Path(self.tmp.name) / "fake_gh.py"
        self.fake.write_text(FAKE_GH, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def scope(self, mode):
        code, out, err = run([HERE / "scope_check.py", "--gh", f"{PY}|{self.fake}|{mode}|{GH}"])
        self.assertNoCanary(out, err)
        self.assertNotIn("someone", out + err)
        return code, out, err

    def test_classic_scopes_reported_and_flagged(self):
        code, out, err = self.scope("ok-classic")
        doc = json.loads(out)
        self.assertEqual(doc["token_kind"], "classic")
        self.assertEqual(doc["scopes"], ["repo", "admin:org", "delete_repo"])
        self.assertIn("delete_repo", doc["broad_scopes"])
        self.assertEqual(code, 1)

    def test_fine_grained_detected(self):
        code, out, err = self.scope("ok-fine")
        doc = json.loads(out)
        self.assertEqual(doc["token_kind"], "fine-grained")
        self.assertEqual(code, 0)

    def test_failure_is_masked(self):
        code, out, err = self.scope("fail")
        doc = json.loads(out)
        self.assertEqual(doc["status"], "FAILED")
        self.assertEqual(code, 3)


import unittest.mock  # noqa: E402  (used in InventoryTests)

if __name__ == "__main__":
    unittest.main()
