"""Guards on the framework/ingest-pipeline boundary.

The split is only worth anything if it stays split. These are the executable
form of the rules in CLAUDE.md:

  - the framework is pure stdlib, so it survives an air gap with nothing installed
  - the framework has no knowledge that the pipeline exists
  - a vault owner never receives a pipeline file

Each of these was true by inspection when the split landed. Without a test they
stay true only until the next person adds an import.
"""
from __future__ import annotations

import ast
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "second_brain_vault_framework"

_OWN_PACKAGE = "second_brain_vault_framework"


def _dynamic_import_target(node: ast.AST) -> str | None:
    """Module name from `__import__("x")` / `importlib.import_module("x")`.

    Plain `import x` is the easy case. A dependency introduced as an optional
    lazy import is the realistic way one sneaks in, and it is invisible to an
    ast.Import walk.
    """
    if not isinstance(node, ast.Call) or not node.args:
        return None
    fn = node.func
    name = (fn.id if isinstance(fn, ast.Name)
            else fn.attr if isinstance(fn, ast.Attribute) else None)
    if name not in ("__import__", "import_module"):
        return None
    arg = node.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value.split(".")[0]
    # A computed module name cannot be checked statically; flag it rather than
    # let it through, since that is the one form that could hide anything.
    return "<dynamic>"


def _imported_top_level_modules(py: Path) -> set[str]:
    """Every top-level module name a file imports, static or dynamic."""
    mods: set[str] = set()
    for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
        else:
            dyn = _dynamic_import_target(node)
            if dyn:
                mods.add(dyn)
    return mods


class TestFrameworkIsPureStdlib(unittest.TestCase):
    """`pyproject.toml` declares no runtime deps. This proves the code agrees."""

    def test_package_imports_stdlib_only(self):
        offenders = []
        for py in sorted(PKG.rglob("*.py")):
            for mod in _imported_top_level_modules(py) - {_OWN_PACKAGE}:
                if mod not in sys.stdlib_module_names:
                    offenders.append(f"{py.relative_to(ROOT)} imports {mod!r}")
        self.assertEqual(offenders, [], "framework must run with nothing installed")

    def test_framework_tests_import_stdlib_only(self):
        # A test dependency is still a dependency: if the suite needs a package,
        # CI can no longer prove the air-gap claim.
        offenders = []
        for py in sorted((ROOT / "tests").rglob("*.py")):
            for mod in _imported_top_level_modules(py) - {_OWN_PACKAGE}:
                if mod not in sys.stdlib_module_names:
                    offenders.append(f"{py.relative_to(ROOT)} imports {mod!r}")
        self.assertEqual(offenders, [], "framework tests must run with nothing installed")

    def test_pyproject_declares_no_runtime_dependencies(self):
        txt = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("dependencies = []", txt,
                      "adding a runtime dep breaks the air-gap guarantee")


class TestFrameworkDoesNotKnowAboutThePipeline(unittest.TestCase):
    _PIPELINE_MARKERS = ("ingest-pipeline", "ingest_pipeline")

    def test_no_manifest_path_belongs_to_the_pipeline(self):
        manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
        paths = manifest["owned_paths"] + manifest["scaffold_only_paths"]
        bad = [p for p in paths
               if any(m in p for m in self._PIPELINE_MARKERS)
               or "classification" in p or "vault-classify" in p]
        self.assertEqual(bad, [], "the pipeline must not ship into user vaults")

    def _is_pipeline_ref(self, text: str) -> bool:
        return (any(m in text for m in self._PIPELINE_MARKERS)
                or "classification" in text or "vault-classify" in text)

    def test_no_payload_file_belongs_to_the_pipeline(self):
        payload = PKG / "payload"
        # Match on the path RELATIVE to the payload. Matching str(f) tested the
        # absolute path, so any checkout living under a directory named e.g.
        # ".../ingest-pipeline/repo" failed listing every payload file.
        bad = [f.relative_to(payload).as_posix() for f in payload.rglob("*")
               if f.is_file() and self._is_pipeline_ref(f.relative_to(payload).as_posix())]
        self.assertEqual(bad, [], "payload is what a vault owner receives")

    def test_no_payload_file_mentions_the_pipeline(self):
        # Paths alone are not enough: a payload doc whose body tells a vault owner
        # to run ingest-pipeline/scripts/... ships that instruction to every vault.
        payload = PKG / "payload"
        bad = []
        for f in sorted(payload.rglob("*")):
            if not f.is_file() or f.name == ".DS_Store":
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if self._is_pipeline_ref(text):
                bad.append(f.relative_to(payload).as_posix())
        self.assertEqual(bad, [], "payload content must not reference the pipeline")

    def test_package_source_never_references_the_pipeline(self):
        bad = []
        for py in sorted(PKG.rglob("*.py")):
            txt = py.read_text(encoding="utf-8")
            for marker in (*self._PIPELINE_MARKERS, "cmd_classify"):
                if marker in txt:
                    bad.append(f"{py.relative_to(ROOT)} mentions {marker!r}")
        self.assertEqual(bad, [])


class TestManifestMatchesPayload(unittest.TestCase):
    """`owned_paths` is the only definition of what the framework owns, so a file
    present but unowned is never installed and a path owned but missing breaks
    `vault upgrade` in a consumer's repo rather than here."""

    def _payload_rel_paths(self) -> set[str]:
        payload = PKG / "payload"
        out = set()
        for f in payload.rglob("*"):
            if not f.is_file() or f.name == ".DS_Store":
                continue
            rel = f.relative_to(payload).as_posix()
            out.add(rel.replace("dot-claude/", ".claude/", 1) if rel.startswith("dot-claude/") else rel)
        return out

    # Payload files that are deliberately in neither owned_paths nor
    # scaffold_only_paths. `gitignore` is written by cmd_scaffold directly
    # (core.py, via render_template("gitignore")) and is never re-laid by
    # cmd_upgrade, so editing it in the payload does NOT reach existing vaults
    # and `vault upgrade` cannot fix a stale one. Listed here so that stays a
    # deliberate exception rather than an invisible one.
    _UNMANIFESTED = {"gitignore"}

    def _manifested(self) -> set[str]:
        manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
        return set(manifest["owned_paths"]) | set(manifest["scaffold_only_paths"])

    def test_every_owned_path_exists_in_the_payload(self):
        missing = sorted(self._manifested() - self._payload_rel_paths())
        self.assertEqual(missing, [], "owned but not shipped — upgrade would never install it")

    def test_every_payload_file_is_claimed_by_the_manifest(self):
        # The reverse direction. src/second_brain_vault_framework/CLAUDE.md names
        # this exact failure: a payload file with no manifest entry is silently
        # ignored by both scaffold and upgrade, so it ships to nobody and nothing
        # says so.
        unclaimed = sorted(self._payload_rel_paths() - self._manifested() - self._UNMANIFESTED)
        self.assertEqual(unclaimed, [],
                         "payload file with no manifest entry — add it to owned_paths "
                         "or to _UNMANIFESTED with a reason")



class TestExampleVaultIsCurrent(unittest.TestCase):
    """`payload/` is the source of truth; `example_vault/` is an artifact.

    CLAUDE.md has long claimed CI enforced this. It did not: the `example-vault`
    job ran `vault check` and then `git diff --exit-code`, without ever running
    `vault upgrade` — and on a fresh CI checkout that diff is trivially empty, so
    the check could never detect a stale example. A payload edit that was never
    laid down would have reached a consumer's repo before it failed here.

    Done as a temp-directory copy rather than by upgrading the real example and
    diffing: `.vault-framework.json` carries an `installed_at` wall-clock stamp
    rewritten on every upgrade, so a naive diff is red on every run regardless of
    drift.
    """

    _VOLATILE = ("installed_at",)

    def test_upgrading_example_vault_would_change_nothing(self):
        import shutil
        import tempfile
        from second_brain_vault_framework import core

        example = ROOT / "example_vault"
        self.assertTrue(example.is_dir(), "example_vault/ missing")

        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "example_vault"
            shutil.copytree(example, copy)
            rc = core.cmd_upgrade(copy)
            self.assertEqual(rc, 0, "vault upgrade failed on example_vault")

            drifted = []
            for after in sorted(copy.rglob("*")):
                if not after.is_file():
                    continue
                rel = after.relative_to(copy)
                before = example / rel
                if not before.exists():
                    drifted.append(f"{rel} (upgrade would ADD it)")
                    continue
                # read_text, NOT read_bytes: cmd_upgrade writes via Path.write_text
                # with no newline= argument, so Python text mode emits CRLF on
                # Windows while git may have checked the file out as LF. A byte
                # comparison would report all 8 owned paths as drifted on a clean
                # tree, and the suggested remedy (upgrade + commit) would not help.
                a = after.read_text(encoding="utf-8")
                b = before.read_text(encoding="utf-8")
                if a == b:
                    continue
                if rel.name == ".vault-framework.json":
                    ja, jb = json.loads(a), json.loads(b)
                    for k in self._VOLATILE:
                        ja.pop(k, None)
                        jb.pop(k, None)
                    if ja != jb:
                        drifted.append(f"{rel} (stamp/manifest drift)")
                    continue
                drifted.append(f"{rel} (upgrade would CHANGE it)")

            for before in sorted(example.rglob("*")):
                if before.is_file() and not (copy / before.relative_to(example)).exists():
                    drifted.append(f"{before.relative_to(example)} (upgrade would REMOVE it)")

            self.assertEqual(
                drifted, [],
                "example_vault is stale — run `vault upgrade example_vault` and commit")

if __name__ == "__main__":
    unittest.main()


class TestConsoleOutputSurvivesLegacyWindowsEncoding(unittest.TestCase):
    """The framework claims to be cross-platform. A Windows console defaults to
    cp1252, and `print()` of a character outside that set raises
    UnicodeEncodeError — killing the command, not just garbling a line.

    `vault upgrade` printed U+2192 (RIGHTWARDS ARROW), which cp1252 has no
    mapping for, so upgrade crashed on every Windows machine. It went unnoticed
    because there was no Windows CI: the first run of the new matrix turned 8
    tests red, 7 of them pre-existing.

    Reproduced here on any platform by encoding to cp1252 explicitly, so the
    guard holds even for developers who never touch Windows. Note the em dash,
    bullet and en dash used elsewhere in the CLI ARE in cp1252 and are fine —
    this is not a ban on non-ASCII, only on characters Windows cannot print.
    """

    def test_no_package_string_is_unprintable_on_a_windows_console(self):
        offenders = []
        for py in sorted(PKG.rglob("*.py")):
            for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                for ch in dict.fromkeys(c for c in line if ord(c) > 127):
                    try:
                        ch.encode("cp1252")
                    except UnicodeEncodeError:
                        offenders.append(
                            f"{py.relative_to(ROOT)}:{lineno} has U+{ord(ch):04X} {ch!r}")
        self.assertEqual(offenders, [],
                         "character cannot be printed on a cp1252 Windows console")

    def test_upgrade_prints_cleanly_to_a_cp1252_stream(self):
        # The behavioural half: exercises the real code path that crashed.
        import contextlib
        import io
        import shutil
        import tempfile
        from second_brain_vault_framework import core

        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "example_vault"
            shutil.copytree(ROOT / "example_vault", copy)
            cp1252 = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
            with contextlib.redirect_stdout(cp1252):
                rc = core.cmd_upgrade(copy)
            self.assertEqual(rc, 0)
