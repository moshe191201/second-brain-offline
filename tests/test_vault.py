# tests/test_vault.py
import json
import unittest
from pathlib import Path

from second_brain_vault_framework import core as vault

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = vault.payload_root()


class TestHelpers(unittest.TestCase):
    def test_slugify_basic(self):
        self.assertEqual(vault.slugify("QLoRA Explained: 4-Bit!"), "qlora-explained-4-bit")

    def test_slugify_collapses_separators(self):
        self.assertEqual(vault.slugify("  A__B  C "), "a-b-c")

    def test_parse_frontmatter_scalars_and_list(self):
        text = (
            "---\n"
            "title: My Title\n"
            "author: Jane Doe\n"
            "tags:\n"
            "  - alpha\n"
            "  - beta\n"
            "---\n"
            "Body line 1\n"
        )
        fm, body = vault.parse_frontmatter(text)
        self.assertEqual(fm["title"], "My Title")
        self.assertEqual(fm["author"], "Jane Doe")
        self.assertEqual(fm["tags"], ["alpha", "beta"])
        self.assertEqual(body.strip(), "Body line 1")

    def test_parse_frontmatter_missing_returns_empty(self):
        fm, body = vault.parse_frontmatter("no frontmatter here\n")
        self.assertEqual(fm, {})
        self.assertEqual(body.strip(), "no frontmatter here")


import re as _re


class TestTemplates(unittest.TestCase):
    SKILLS = ["vault-setup", "vault-ingest", "vault-query", "vault-lint"]

    def test_skill_frontmatter_valid(self):
        for name in self.SKILLS:
            path = PAYLOAD / "dot-claude" / "skills" / name / "SKILL.md"
            self.assertTrue(path.exists(), f"missing {path}")
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), f"{name}: no frontmatter fence")
            fm, _ = vault.parse_frontmatter(text)
            self.assertIn("name", fm, f"{name}: no name")
            self.assertIn("description", fm, f"{name}: no description")
            self.assertEqual(fm["name"], name)

    def test_skill_has_minimal_path(self):
        for name in self.SKILLS:
            text = (PAYLOAD / "dot-claude" / "skills" / name / "SKILL.md").read_text("utf-8")
            self.assertIn("Minimal-model path", text, f"{name}: missing minimal path")


import tempfile


class TestScaffold(unittest.TestCase):
    def test_scaffold_creates_layout(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rc = vault.cmd_scaffold(root, "Test Vault")
            self.assertEqual(rc, 0)
            v = root / "Test Vault"
            for sub in ["raw", "wiki", "wiki/sources", "index", "tests", "scripts",
                        ".claude/skills/vault-ingest"]:
                self.assertTrue((v / sub).is_dir(), f"missing dir {sub}")
            self.assertTrue((v / "CLAUDE.md").exists())
            self.assertIn("Test Vault", (v / "CLAUDE.md").read_text("utf-8"))
            self.assertTrue((v / "scripts/vault.py").exists())
            self.assertTrue((v / "scripts/check_vault_answer.py").exists())
            self.assertTrue((v / "tests/VAULT_TESTS.md").exists(),
                            "scaffold-only paths must land too")
            self.assertTrue((v / ".claude/skills/vault-ingest/SKILL.md").exists())
            for stem in ["_map-of-content", "source-registry", "log", "key-takeaways"]:
                self.assertTrue((v / "index" / f"{stem}.md").exists(), stem)


class TestNewNote(unittest.TestCase):
    def _vault(self, d):
        root = Path(d)
        vault.cmd_scaffold(root, "V")
        return root / "V"

    def test_new_note_creates_concept_stub(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            (v / "raw" / "my-clip.md").write_text("---\ntitle: My Clip\n---\nbody\n", "utf-8")
            rc = vault.cmd_new_note(v, "low-rank-adapters", "raw/my-clip.md")
            self.assertEqual(rc, 0)
            note = v / "wiki" / "low-rank-adapters.md"
            self.assertTrue(note.exists())
            fm, _ = vault.parse_frontmatter(note.read_text("utf-8"))
            self.assertEqual(fm["type"], "concept")
            self.assertEqual(fm["sources"], ["[[my-clip]]"])
            self.assertIn("<!-- TODO", note.read_text("utf-8"))

    def test_new_note_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            (v / "raw" / "c.md").write_text("---\ntitle: C\n---\n", "utf-8")
            self.assertEqual(vault.cmd_new_note(v, "x", "raw/c.md"), 0)
            self.assertEqual(vault.cmd_new_note(v, "x", "raw/c.md"), 1)  # already exists


FIXTURE = ROOT / "tests" / "fixtures" / "sample-clipping.md"


class TestIngest(unittest.TestCase):
    def _vault(self, d):
        root = Path(d)
        vault.cmd_scaffold(root, "V")
        v = root / "V"
        (v / "raw" / "sample-clipping.md").write_text(FIXTURE.read_text("utf-8"), "utf-8")
        return v

    def test_ingest_creates_summary_registry_log(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            rc = vault.cmd_ingest(v, Path("raw/sample-clipping.md"))
            self.assertEqual(rc, 0)
            summary = v / "wiki" / "sources" / "understanding-low-rank-adapters.md"
            self.assertTrue(summary.exists())
            sfm, _ = vault.parse_frontmatter(summary.read_text("utf-8"))
            self.assertEqual(sfm["type"], "source-summary")
            self.assertEqual(sfm["sources"], ["[[sample-clipping]]"])
            reg = (v / "index" / "source-registry.md").read_text("utf-8")
            self.assertIn("[[sample-clipping]]", reg)
            self.assertIn("[[understanding-low-rank-adapters]]", reg)
            log = (v / "index" / "log.md").read_text("utf-8")
            self.assertIn("ingest | Understanding Low-Rank Adapters", log)
            self.assertIn("sample-clipping", log)

    def test_ingest_is_rerunnable(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            self.assertEqual(vault.cmd_ingest(v, Path("raw/sample-clipping.md")), 0)
            self.assertEqual(vault.cmd_ingest(v, Path("raw/sample-clipping.md")), 0)
            reg = (v / "index" / "source-registry.md").read_text("utf-8")
            self.assertEqual(reg.count("[[sample-clipping]]"), 1)  # no duplicate row


class TestCheck(unittest.TestCase):
    def _filled_vault(self, d):
        root = Path(d)
        vault.cmd_scaffold(root, "V")
        v = root / "V"
        (v / "raw" / "sample-clipping.md").write_text(FIXTURE.read_text("utf-8"), "utf-8")
        vault.cmd_ingest(v, Path("raw/sample-clipping.md"))
        vault.cmd_new_note(v, "low-rank-adapters", "raw/sample-clipping.md")
        (v / "wiki" / "sources" / "understanding-low-rank-adapters.md").write_text(
            '---\ntitle: "Summary — Understanding Low-Rank Adapters"\n'
            'type: source-summary\ntags: [lora]\nsources:\n  - "[[sample-clipping]]"\n'
            'published: 2026-01-15\n---\n\n'
            "# Summary — Understanding Low-Rank Adapters\n\n"
            "**LoRA trains small low-rank matrices on frozen weights.**\n\n"
            "The article explains low-rank adaptation, grounded in [[sample-clipping]].\n\n"
            "## Key claims\n- low-rank update -> [[low-rank-adapters]]\n\n"
            "## Derived concept notes\n[[low-rank-adapters]]\n", "utf-8")
        (v / "wiki" / "low-rank-adapters.md").write_text(
            '---\ntitle: "Low Rank Adapters"\ntype: concept\ntags: [lora]\n'
            'sources:\n  - "[[sample-clipping]]"\n---\n\n'
            "# Low Rank Adapters\n\n"
            "**LoRA adds trainable low-rank matrices to frozen weights.**\n\n"
            "Body grounded in [[sample-clipping]]. W' = W + (a/r)BA.\n\n"
            "## Related\n[[understanding-low-rank-adapters]]\n", "utf-8")
        return v

    def test_check_passes_when_filled(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._filled_vault(d)
            self.assertEqual(vault.cmd_check(v), 0)

    def test_check_fails_on_todo_marker(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._filled_vault(d)
            note = v / "wiki" / "low-rank-adapters.md"
            note.write_text(note.read_text("utf-8") + "\n<!-- TODO: extra -->\n", "utf-8")
            self.assertNotEqual(vault.cmd_check(v), 0)


class TestRegister(unittest.TestCase):
    def test_register_excludes_tests(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            vault.cmd_scaffold(root, "V")
            v = root / "V"
            calls = []
            def fake_runner(cmd, **kw):
                calls.append(cmd)
                class R: returncode = 0
                return R()
            rc = vault.cmd_register(v, runner=fake_runner)
            self.assertEqual(rc, 0)
            flat = " ".join(" ".join(c) for c in calls)
            self.assertIn("collection add ./raw", flat)
            self.assertIn("collection add ./wiki", flat)
            self.assertIn("collection add ./index", flat)
            self.assertNotIn("tests", flat)  # tests/ must never be registered
            self.assertIn("qmd update", flat)
            self.assertIn("qmd embed", flat)


import io
from contextlib import redirect_stdout


class TestStatus(unittest.TestCase):
    def test_status_lists_raw_state(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            vault.cmd_scaffold(root, "V")
            v = root / "V"
            (v / "raw" / "sample-clipping.md").write_text(FIXTURE.read_text("utf-8"), "utf-8")
            vault.cmd_ingest(v, Path("raw/sample-clipping.md"))
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = vault.cmd_status(v)
            out = buf.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("summary", out)  # column header
            # After ingest, the clipping row must show all three present (no NO).
            row = [ln for ln in out.splitlines() if ln.startswith("sample-clipping")][0]
            self.assertIn("yes", row)       # summary detected via title-slug
            self.assertNotIn("NO", row)     # registry + log also present


class TestUserZone(unittest.TestCase):
    START, END = "<!-- USER ZONE START -->", "<!-- USER ZONE END -->"

    def test_extract_and_inject_roundtrip(self):
        text = f"head\n{self.START}\nmine\n{self.END}\ntail\n"
        zone = vault.extract_user_zone(text, self.START, self.END)
        self.assertEqual(zone, "\nmine\n")
        fresh = f"NEW head\n{self.START}\n{self.END}\nNEW tail\n"
        out = vault.inject_user_zone(fresh, self.START, self.END, zone)
        self.assertIn("mine", out)
        self.assertIn("NEW head", out)

    def test_extract_returns_none_when_markers_absent(self):
        self.assertIsNone(vault.extract_user_zone("no markers\n", self.START, self.END))

    def test_extract_returns_none_when_markers_reversed(self):
        text = f"{self.END}\nmine\n{self.START}\n"
        self.assertIsNone(vault.extract_user_zone(text, self.START, self.END))

    def test_inject_into_unmarked_payload_is_a_noop(self):
        self.assertEqual(vault.inject_user_zone("plain\n", self.START, self.END, "z"), "plain\n")


class TestUpgrade(unittest.TestCase):
    def _vault(self, d):
        root = Path(d)
        vault.cmd_scaffold(root, "V")
        return root / "V"

    def test_upgrade_is_idempotent_and_leaves_no_backup(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            before = (v / "CLAUDE.md").read_text("utf-8")
            self.assertEqual(vault.cmd_upgrade(v), 0)
            self.assertEqual((v / "CLAUDE.md").read_text("utf-8"), before)
            self.assertFalse((v / vault.BACKUP_DIR).exists(),
                             "a clean vault must not be reported as drifted")

    def test_upgrade_preserves_user_zone(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            claude = v / "CLAUDE.md"
            claude.write_text(claude.read_text("utf-8").replace(
                "<!-- USER ZONE START -->", "<!-- USER ZONE START -->\nMY LOCAL RULE"), "utf-8")
            vault.cmd_upgrade(v)
            self.assertIn("MY LOCAL RULE", claude.read_text("utf-8"))

    def test_upgrade_never_touches_content(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            note = v / "wiki" / "mine.md"
            note.write_text("my content\n", "utf-8")
            vault.cmd_upgrade(v)
            self.assertEqual(note.read_text("utf-8"), "my content\n")

    def test_upgrade_backs_up_a_drifted_framework_file(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            skill = v / ".claude/skills/vault-lint/SKILL.md"
            skill.write_text("hand-edited\n", "utf-8")
            vault.cmd_upgrade(v)
            backup = v / vault.BACKUP_DIR / vault.framework_version() / \
                ".claude/skills/vault-lint/SKILL.md"
            self.assertTrue(backup.exists(), "edited file must be backed up, not lost")
            self.assertEqual(backup.read_text("utf-8"), "hand-edited\n")
            self.assertNotEqual(skill.read_text("utf-8"), "hand-edited\n")

    def test_upgrade_does_not_relay_scaffold_only_paths(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            tests_md = v / "tests" / "VAULT_TESTS.md"
            tests_md.write_text("my own gold answers\n", "utf-8")
            vault.cmd_upgrade(v)
            self.assertEqual(tests_md.read_text("utf-8"), "my own gold answers\n",
                             "a vault's eval is rewritten per corpus; upgrade must not clobber it")

    def test_upgrade_removes_orphaned_framework_files_only(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            # Pretend the previous version shipped a file this one no longer does,
            # alongside a content file with a similar name.
            orphan = v / "scripts" / "gone.py"
            orphan.write_text("old\n", "utf-8")
            keeper = v / "wiki" / "gone.md"
            keeper.write_text("content\n", "utf-8")
            stamp = json.loads((v / vault.STAMP_FILE).read_text("utf-8"))
            stamp["manifest"]["owned_paths"].append("scripts/gone.py")
            (v / vault.STAMP_FILE).write_text(json.dumps(stamp), "utf-8")

            vault.cmd_upgrade(v)
            self.assertFalse(orphan.exists(), "orphaned framework file must be removed")
            self.assertTrue(keeper.exists(), "content is never a deletion candidate")

    def test_upgrade_handles_a_vault_with_no_stamp(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            (v / vault.STAMP_FILE).unlink()
            self.assertEqual(vault.cmd_upgrade(v), 0)
            stamp = json.loads((v / vault.STAMP_FILE).read_text("utf-8"))
            self.assertEqual(stamp["framework_version"], vault.framework_version())


class TestManifest(unittest.TestCase):
    def test_every_manifest_path_exists_in_the_payload(self):
        manifest = vault.load_manifest()
        for rel in manifest["owned_paths"] + manifest.get("scaffold_only_paths", []):
            self.assertTrue(vault.payload_path_for(rel).exists(),
                            f"{rel} is in the manifest but missing from the payload")

    def test_manifest_version_matches_package(self):
        self.assertEqual(vault.load_manifest()["framework_version"], vault.framework_version())

    def test_manifest_claims_no_content_paths(self):
        for rel in vault.load_manifest()["owned_paths"]:
            self.assertFalse(rel.startswith(("raw/", "wiki/", "index/", "graphify-out/")),
                             f"{rel} is content — the framework must never own it")

    def test_dot_claude_paths_map_into_the_payload(self):
        p = vault.payload_path_for(".claude/skills/vault-lint/SKILL.md")
        self.assertIn("dot-claude", str(p))
        self.assertTrue(p.exists())


if __name__ == "__main__":
    unittest.main()
