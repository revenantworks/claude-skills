"""Tests for release_notes.py: the CHANGELOG draft and lint that release.py runs at steps 1 and 2."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_notes as rn  # noqa: E402


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.invalid")
        git(self.root, "config", "user.name", "t")
        git(self.root, "config", "core.hooksPath", "/dev/null")
        (self.root / "packs" / "foundation").mkdir(parents=True)
        (self.root / "packs" / "scribe").mkdir(parents=True)
        self.commit("foundation", "base: start")
        git(self.root, "tag", "foundation-v1.0.0")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def commit(self, pack, message, n=[0]):
        n[0] += 1
        (self.root / "packs" / pack / f"f{n[0]}.md").write_text(str(n[0]))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", message)

    def test_groups_by_verb_and_drops_internal_and_other_packs(self):
        self.commit("foundation", "pacewright: add a reset-eve mode")
        self.commit("foundation", "dispatchwright: fix the ledger guard on junctions")
        self.commit("foundation", "promptwright: tighten the model table")
        self.commit("foundation", "tools: speed up build.py")
        self.commit("foundation", "docs: reword the README")
        self.commit("scribe", "brandscribe: add a palette check")
        body = rn.draft("foundation", "foundation-v1.0.0", self.root)
        self.assertIn("### New\n\n- **pacewright**: Add a reset-eve mode.", body)
        self.assertIn("### Fixed\n\n- **dispatchwright**: Fix the ledger guard on junctions.", body)
        self.assertIn("### Improved\n\n- **promptwright**: Tighten the model table.", body)
        self.assertNotIn("build.py", body)
        self.assertNotIn("README", body)
        self.assertNotIn("palette", body)
        self.assertLess(body.index("### New"), body.index("### Improved"))

    def test_breaking_gets_a_migrate_placeholder(self):
        self.commit("foundation", "gatewarden: rename the mode flag\n\nBREAKING: --mode is now --level")
        body = rn.draft("foundation", "foundation-v1.0.0", self.root)
        self.assertIn("### Breaking", body)
        self.assertIn("Migrate: (fill in)", body)

    def test_no_tag_starts_after_the_first_commit(self):
        self.commit("foundation", "pacewright: add a mode")
        since = rn.default_since(self.root)
        body = rn.draft("foundation", since, self.root)
        self.assertIn("Add a mode.", body)
        self.assertNotIn("start", body)

    def test_no_user_facing_commit_gives_empty_draft(self):
        self.commit("foundation", "ci: cache pip")
        self.assertEqual(rn.draft("foundation", "foundation-v1.0.0", self.root), "")


class ScaffoldTests(unittest.TestCase):
    CLOG = "# Changelog\n\n## [foundation-v1.1.0] - 2026-10-11\n\n- (fill in)\n\n## [1.0.0] - 2026-10-01\n\n- old\n"

    def test_bare_scaffold_is_replaced_and_still_gated(self):
        out = rn.fill_scaffold(self.CLOG, "foundation-v1.1.0", "### New\n\n- **x**: Add y.")
        sec = rn.section(out, "foundation-v1.1.0")
        self.assertIn(rn.REVIEW_LINE, sec)
        self.assertIn("### New\n\n- **x**: Add y.", sec)
        self.assertIn(rn.FILL, sec)  # the gate still stops until a person edits it
        self.assertTrue(out.endswith("## [1.0.0] - 2026-10-01\n\n- old\n"))

    def test_written_entry_is_never_touched(self):
        written = self.CLOG.replace("- (fill in)", "- A real entry.")
        self.assertEqual(rn.fill_scaffold(written, "foundation-v1.1.0", "### New\n\n- **x**: Add y."), written)

    def test_empty_draft_leaves_scaffold(self):
        self.assertEqual(rn.fill_scaffold(self.CLOG, "foundation-v1.1.0", ""), self.CLOG)


class LintTests(unittest.TestCase):
    def sec(self, body):
        return "## [foundation-v1.1.0] - 2026-10-11\n\n" + body + "\n"

    def test_breaking_without_migrate_is_an_error(self):
        errors, _ = rn.lint(self.sec("### Breaking\n\n- **gatewarden**: The mode flag is renamed."))
        self.assertEqual(len(errors), 1)

    def test_breaking_with_migrate_passes(self):
        errors, _ = rn.lint(self.sec("### Breaking\n\n- **gatewarden**: The mode flag is renamed.\n"
                                     "  Migrate: replace --mode with --level."))
        self.assertEqual(errors, [])

    def test_warnings_for_paths_functions_hashes_and_length(self):
        _, w = rn.lint(self.sec("### Improved\n\n- Edits tools/build.py.\n- Calls bump_pack() now.\n"
                                "- Reverts 4d9ec3f.\n- One. Two. Three. Four. Five."))
        joined = " | ".join(w)
        for what in ("a file path", "a function name", "a commit hash", "5 sentences"):
            self.assertIn(what, joined)

    def test_internal_codes_warn_but_utf8_does_not(self):
        _, w = rn.lint(self.sec("### Improved\n\n- Refuses a decoded run (V-K8w2 B5).\n- Prints notes as UTF-8."))
        self.assertEqual(len(w), 1)
        self.assertIn("an internal code", w[0])

    def test_unscoped_subject_keeps_its_whole_text(self):
        self.assertEqual(rn.classify("Initial public release: 28 skills", ""), ("Improved", "",
                                                                                  "Initial public release: 28 skills"))

    def test_plain_user_words_pass_clean(self):
        self.assertEqual(rn.lint(self.sec("### New\n\n- **pacewright**: Adds a reset-eve mode that sizes "
                                          "work to the room left before the weekly reset.")), ([], []))

    def test_section_finds_only_its_own_heading(self):
        clog = "## [a-v2.0.0] - d\n\n- two\n\n## [a-v1.0.0] - d\n\n- one\n"
        self.assertEqual(rn.section(clog, "a-v2.0.0"), "## [a-v2.0.0] - d\n\n- two\n")
        self.assertIsNone(rn.section(clog, "a-v3.0.0"))


if __name__ == "__main__":
    unittest.main()
