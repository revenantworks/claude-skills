#!/usr/bin/env python3
"""Unit tests for the generated pack eval folders (run 2026-09-28-pack-split, unit EVG).

`claude plugin eval <pack>` refuses an eval dir inside the plugin's `skills/` folder, and every
native case lives in `packs/<pack>/skills/<member>/evals/<case>/`. build.py now copies each case
to `packs/<pack>/pack-evals/<short>--<case>/` (named in plugin.json `experimental.evals`, unit K8e),
the same way `sync_shared()` writes holder copies: a
plain build writes them, `--check` fails on drift or on a stale extra folder, `--footprint`
ignores them. The member case stays the source of truth.

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only; every fixture lives in a temp directory.
"""
import json
import subprocess
import unittest
from pathlib import Path

import build
from test_build_split import Rooted, capture
from test_build_shared import ROSTER, make, member

PROMPT = b"---\nmax_turns: 4\n---\n\nScore this skill.\n"
GRADER = b"---\ntype: regex\n---\n\nscore\n"
RES = b"input data\n"


def case(root: Path, short: str, name: str) -> Path:
    d = member(root, short) / "evals" / name
    (d / "graders").mkdir(parents=True)
    (d / "resources").mkdir()
    (d / "prompt.md").write_bytes(PROMPT)
    (d / "graders" / "g.md").write_bytes(GRADER)
    (d / "resources" / "r.txt").write_bytes(RES)
    return d


def build_tree(test: unittest.TestCase) -> Path:
    """Two members with cases (one name shared by both), plus hand-run files that are not cases."""
    root = make(test)
    case(root, "hammerwright", "trigger-nail")
    case(root, "hammerwright", "nearmiss-saw")
    case(root, "sawwright", "nearmiss-saw")
    ev = member(root, "hammerwright") / "evals"
    (ev / "trigger-evals.md").write_bytes(b"# hand-run\n")
    (ev / "RESULTS.md").write_bytes(b"# results\n")
    (ev / "results").mkdir()
    (ev / "results" / "run.json").write_bytes(b"{}\n")
    (ev / "notes").mkdir()  # neither a case nor auxiliary: skipped, never copied
    (ev / "notes" / "x.md").write_bytes(b"x\n")
    manifest(root, {"evals": build.PACK_EVAL_DIR})  # the live packs' shape
    return root


def manifest(root: Path, experimental: dict | None) -> Path:
    pj = root / "packs" / "tools" / ".claude-plugin" / "plugin.json"
    data = {"name": "tools", "version": "1.0.0"}
    if experimental is not None:
        data["experimental"] = experimental
    pj.write_bytes((json.dumps(data, indent=2) + "\n").encode())
    return pj


def pack_evals(root: Path) -> Path:
    return root / "packs" / "tools" / build.PACK_EVAL_DIR


def sync(root: Path, write: bool):
    return capture(build.sync_pack_evals, "tools", ROSTER, root, write)


class PackEvalGenerator(unittest.TestCase):
    def test_check_reports_missing_then_build_writes_then_check_clean(self):
        root = build_tree(self)
        n, probs, _ = sync(root, write=False)
        self.assertEqual(n, 3)
        self.assertEqual(len(probs), 3, probs)
        self.assertTrue(all("run tools/build.py" in p for p in probs), probs)
        self.assertFalse(pack_evals(root).exists())
        n, probs, _ = sync(root, write=True)
        self.assertEqual((n, probs), (3, []))
        got = sorted(d.name for d in pack_evals(root).iterdir())
        self.assertEqual(got, ["hammerwright--nearmiss-saw", "hammerwright--trigger-nail",
                               "sawwright--nearmiss-saw"])
        out = pack_evals(root) / "hammerwright--trigger-nail"
        self.assertEqual((out / "prompt.md").read_bytes(), PROMPT)
        self.assertEqual((out / "graders" / "g.md").read_bytes(), GRADER)
        self.assertEqual((out / "resources" / "r.txt").read_bytes(), RES)
        _, probs, _ = sync(root, write=False)
        self.assertEqual(probs, [])

    def test_hand_run_files_and_aux_folders_are_not_cases(self):
        root = build_tree(self)
        sync(root, write=True)
        names = {p.name for p in pack_evals(root).rglob("*")}
        for skipped in ("trigger-evals.md", "RESULTS.md", "run.json", "x.md"):
            self.assertNotIn(skipped, names)
        self.assertFalse((pack_evals(root) / "results").exists())

    def test_hand_edit_of_a_copy_fails_check_and_build_restores_it(self):
        root = build_tree(self)
        sync(root, write=True)
        copy = pack_evals(root) / "sawwright--nearmiss-saw" / "prompt.md"
        copy.write_bytes(PROMPT + b"\nA hand edit.\n")
        _, probs, _ = sync(root, write=False)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("sawwright--nearmiss-saw", probs[0])
        self.assertIn("never the copy", probs[0])
        _, probs, _ = sync(root, write=True)
        self.assertEqual(probs, [])
        self.assertEqual(copy.read_bytes(), PROMPT)

    def test_extra_or_missing_file_in_a_copy_is_drift(self):
        root = build_tree(self)
        sync(root, write=True)
        out = pack_evals(root) / "hammerwright--trigger-nail"
        (out / "graders" / "extra.md").write_bytes(GRADER)
        (out / "resources" / "r.txt").unlink()
        _, probs, _ = sync(root, write=False)
        self.assertEqual(len(probs), 1, probs)
        sync(root, write=True)
        self.assertFalse((out / "graders" / "extra.md").exists())
        self.assertEqual((out / "resources" / "r.txt").read_bytes(), RES)

    def test_source_edit_is_drift_until_rebuilt(self):
        root = build_tree(self)
        sync(root, write=True)
        src = member(root, "hammerwright") / "evals" / "trigger-nail" / "prompt.md"
        src.write_bytes(PROMPT + b"More.\n")
        _, probs, _ = sync(root, write=False)
        self.assertEqual(len(probs), 1, probs)
        sync(root, write=True)
        self.assertEqual((pack_evals(root) / "hammerwright--trigger-nail" / "prompt.md").read_bytes(),
                         PROMPT + b"More.\n")

    def test_line_ending_alone_is_not_drift(self):
        root = build_tree(self)
        sync(root, write=True)
        copy = pack_evals(root) / "hammerwright--trigger-nail" / "prompt.md"
        copy.write_bytes(PROMPT.replace(b"\n", b"\r\n"))
        _, probs, _ = sync(root, write=False)
        self.assertEqual(probs, [])

    def test_stale_generated_folder_fails_check_and_build_removes_it(self):
        root = build_tree(self)
        sync(root, write=True)
        stale = pack_evals(root) / "hammerwright--retired-case"
        (stale / "graders").mkdir(parents=True)
        (stale / "prompt.md").write_bytes(PROMPT)
        _, probs, _ = sync(root, write=False)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("hammerwright--retired-case", probs[0])
        _, probs, _ = sync(root, write=True)
        self.assertEqual(probs, [])
        self.assertFalse(stale.exists())

    def test_hand_folder_in_pack_evals_fails_and_is_kept(self):
        root = build_tree(self)
        sync(root, write=True)
        hand = pack_evals(root) / "pack-level-case"
        hand.mkdir()
        (hand / "prompt.md").write_bytes(PROMPT)
        for write in (False, True):
            _, probs, _ = sync(root, write=write)
            self.assertEqual(len(probs), 1, probs)
            self.assertIn("pack-level-case", probs[0])
        self.assertTrue(hand.exists())

    def test_run_output_and_hidden_folders_in_pack_evals_are_ignored(self):
        root = build_tree(self)
        sync(root, write=True)
        (pack_evals(root) / "results" / "2026-10-01").mkdir(parents=True)
        (pack_evals(root) / ".cache").mkdir()
        _, probs, _ = sync(root, write=False)
        self.assertEqual(probs, [])

    def test_pack_without_cases_writes_nothing(self):
        root = make(self)
        n, probs, warns = sync(root, write=True)
        self.assertEqual((n, probs, warns), (0, [], []))
        self.assertFalse(pack_evals(root).exists())

    def test_main_generates_check_is_clean_and_footprint_ignores_them(self):
        root = build_tree(self)
        saved = build.FOOTPRINT
        try:
            build.FOOTPRINT = True
            with Rooted(root, check=False):
                capture(build.main)
            self.assertFalse(pack_evals(root).exists())  # --footprint writes nothing
        finally:
            build.FOOTPRINT = saved
        with Rooted(root, check=True):
            rc, probs, _ = capture(build.main)
        self.assertEqual(rc, 1)
        self.assertTrue(any("--trigger-nail" in p for p in probs), probs)
        with Rooted(root, check=False):
            rc, probs, _ = capture(build.main)
        self.assertEqual((rc, probs), (0, []))
        self.assertTrue((pack_evals(root) / "sawwright--nearmiss-saw" / "prompt.md").is_file())
        with Rooted(root, check=True):
            rc, probs, _ = capture(build.main)
        self.assertEqual((rc, probs), (0, []))


class LivePackEvals(unittest.TestCase):
    def test_generated_cases_are_tracked_and_run_output_is_ignored(self):
        """Decision: the generated folders are tracked, so a public install can run
        `claude plugin eval <pack>` with no build step; the runner's results/ stays out."""
        def ignored(rel: str) -> bool:
            r = subprocess.run(["git", "check-ignore", "-q", "--no-index", rel], cwd=build.ROOT)
            return r.returncode == 0
        self.assertFalse(ignored("packs/foundation/pack-evals/skillwright--trigger-build-skill/prompt.md"))
        self.assertFalse(ignored("packs/gamedev/pack-evals/godotsmith--x/graders/g.md"))
        self.assertTrue(ignored("packs/foundation/pack-evals/results/2026-10-01/aggregate-result.json"))

    def test_live_pack_eval_copies_are_in_step(self):
        text = build.registry_text()
        total = 0
        for pack in build.registry_packs(text):
            roster = [m for m, _, _ in build.pack_members(text, pack)]
            n, probs, _ = capture(build.sync_pack_evals, pack, roster, build.ROOT, False)
            self.assertEqual(probs, [], pack)
            total += n
        self.assertGreater(total, 100)

    def test_live_runner_discovers_each_case_once(self):
        """Unit K8e (owner M7): under the default eval dir `claude plugin eval` opened every
        `evals` folder, so each case ran from the copy and from skills/<member>/evals/ (gamedev
        32 = 2 x 16 at 6e4d554). Each live pack must give one route: every discovered case sits
        in PACK_EVAL_DIR/, no name twice, and the count equals the member case count."""
        text = build.registry_text()
        packs = [p for p in build.registry_packs(text) if (build.PACKS / p).is_dir()]
        self.assertEqual(len(packs), 5)
        for pack in packs:
            pdir = build.PACKS / pack
            roster = [m for m, _, _ in build.pack_members(text, pack)]
            n = sum(len(build._native_cases(pdir / "skills" / m / "evals")) for m in roster)
            found = [d.relative_to(pdir).as_posix() for d in build.runner_case_dirs(pdir)]
            self.assertEqual(len(found), n, (pack, found[:4]))
            self.assertEqual(len({f.rsplit("/", 1)[-1] for f in found}), n, pack)
            self.assertTrue(all(f.startswith(build.PACK_EVAL_DIR + "/") for f in found), pack)


class DoubleDiscoveryGuard(unittest.TestCase):
    """Unit K8e: --check fails when the runner would find a case twice."""

    def built(self) -> Path:
        root = build_tree(self)
        self.assertEqual(sync(root, write=True)[1], [])
        return root

    def test_runner_rule_doubles_under_the_default_dir(self):
        root = self.built()
        pdir = root / "packs" / "tools"
        found = build.runner_case_dirs(pdir)
        self.assertEqual(len(found), 3)
        self.assertTrue(all(d.parent.name == build.PACK_EVAL_DIR for d in found))
        for exp in (None, {"evals": "evals"}):  # the default, and naming it: every evals/ folder
            manifest(root, exp)
            found = build.runner_case_dirs(pdir)
            self.assertEqual(len(found), 3)
            self.assertTrue(all(d.parent.name == "evals" for d in found))  # the member sources

    def test_missing_manifest_value_fails_check_and_build_sets_it(self):
        root = self.built()
        pj = manifest(root, None)
        _, probs, _ = sync(root, write=False)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("experimental.evals", probs[0])
        self.assertEqual(sync(root, write=True)[1], [])
        self.assertEqual(json.loads(pj.read_bytes())["experimental"], {"evals": build.PACK_EVAL_DIR})
        self.assertEqual(sync(root, write=False)[1], [])

    def test_generated_tree_named_evals_again_fails(self):
        """A reintroduced `evals` name for the generated tree is the M7 regression itself."""
        root = build_tree(self)
        manifest(root, None)
        saved = build.PACK_EVAL_DIR
        build.PACK_EVAL_DIR = "evals"
        try:
            sync(root, write=True)
            doubled = build.runner_case_dirs(root / "packs" / "tools")
            _, probs, _ = sync(root, write=False)
        finally:
            build.PACK_EVAL_DIR = saved
        self.assertEqual(len(doubled), 6)  # 3 copies + 3 sources: the M7 count (gamedev 32 = 2 x 16)
        self.assertTrue(any("outside" in p or "twice" in p for p in probs), probs)

    def test_scaffolded_manifest_names_the_pack_suite(self):
        src = Path(build.__file__).read_text(encoding="utf-8")
        self.assertIn('data["experimental"] = {"evals": PACK_EVAL_DIR}', src)


if __name__ == "__main__":
    unittest.main()
