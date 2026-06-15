# Vault Skill Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained, deterministic vault CLI (`scripts/vault.py`) plus four thin skills so a minimal, air-gapped model can operate the vault by running named commands and filling only marked blanks.

**Architecture:** A single pure-stdlib Python CLI does all mechanical work (scaffold, ingest, new-note, check, register, status) and exits non-zero with actionable messages (fail-closed). Four `.claude/skills/` wrappers tell the model which command to run and which blanks to fill, with a default deterministic-only "minimal" path and an opt-in "capable" path. Skill/CLAUDE.md/eval content lives as template files under `scripts/templates/` that `scaffold` copies and renders, so the whole system travels with the vault repo and can self-replicate.

**Tech Stack:** Python 3.10+ standard library only (no third-party runtime deps). Tests in stdlib `unittest` (runs air-gapped). Reuses existing `scripts/lint_vault.py`, `qmd`, and the `/graphify` skill.

---

## File Structure

```
scripts/
  vault.py                         # CLI: arg dispatch + command functions + helpers
  lint_vault.py                    # EXISTING — `check` invokes it as a subprocess
  templates/                       # copied/rendered by `scaffold`
    CLAUDE.md                      # vault schema + grounding rule + STRICTNESS
    gitignore                      # baseline ignores for a new vault
    eval/VAULT_TESTS.md            # eval harness template
    skills/
      vault-setup/SKILL.md
      vault-ingest/SKILL.md
      vault-query/SKILL.md
      vault-lint/SKILL.md
tests/
  test_vault.py                    # stdlib unittest, also the air-gapped self-test
  fixtures/sample-clipping.md      # a tiny raw clipping for ingest tests
.claude/skills/                    # THIS repo's adopted copy of the four skills
  vault-setup/  vault-ingest/  vault-query/  vault-lint/
```

Responsibilities:
- `scripts/vault.py` — all command logic + helpers (`slugify`, `parse_frontmatter`, `render_template`). One focused file.
- `scripts/templates/` — static content `scaffold` renders. Editing vault prose never touches `vault.py`.
- `tests/test_vault.py` — proves the deterministic layer independent of any model.

Interfaces shared across tasks (define once, reuse exactly):
- `slugify(text: str) -> str`
- `parse_frontmatter(text: str) -> tuple[dict, str]`  # (frontmatter, body)
- `TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"`
- `render_template(rel_path: str, **vars: str) -> str`
- `cmd_scaffold(root: Path, name: str) -> int`
- `cmd_new_note(root: Path, slug: str, source: str) -> int`
- `cmd_ingest(root: Path, raw_file: Path) -> int`
- `cmd_check(root: Path) -> int`
- `cmd_register(root: Path, *, dry_run: bool = False, runner=subprocess.run) -> int`
- `cmd_status(root: Path) -> int`
- `main(argv: list[str] | None = None) -> int`

---

## Task 1: CLI skeleton + helpers (slugify, frontmatter, templates)

**Files:**
- Create: `scripts/vault.py`
- Create: `tests/test_vault.py`

- [ ] **Step 1: Write failing tests for the helpers**

```python
# tests/test_vault.py
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vault", ROOT / "scripts" / "vault.py")
vault = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vault)


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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_vault -v`
Expected: FAIL — `ModuleNotFoundError`/`AttributeError` (vault.py or functions missing).

- [ ] **Step 3: Implement the skeleton + helpers**

```python
# scripts/vault.py
"""Deterministic vault CLI. Pure stdlib. See docs/superpowers/specs/2026-06-15-*."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal YAML-subset parser: top-level scalars and simple `- ` lists."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, text
    fm: dict = {}
    current_key = None
    for raw in lines[1:end]:
        if re.match(r"^\s*-\s+", raw) and current_key is not None:
            fm.setdefault(current_key, [])
            if isinstance(fm[current_key], list):
                fm[current_key].append(raw.strip()[2:].strip().strip('"'))
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if m:
            key, val = m.group(1), m.group(2).strip()
            current_key = key
            if val == "":
                fm[key] = []  # may become a list on following `- ` lines
            else:
                fm[key] = val.strip('"')
    body = "\n".join(lines[end + 1:])
    return fm, body


def render_template(rel_path: str, **vars: str) -> str:
    text = (TEMPLATES_DIR / rel_path).read_text(encoding="utf-8")
    for key, value in vars.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vault", description="Deterministic vault CLI.")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("scaffold").add_argument("name")
    ing = sub.add_parser("ingest")
    ing.add_argument("raw_file")
    nn = sub.add_parser("new-note")
    nn.add_argument("slug")
    nn.add_argument("--source", required=True)
    sub.add_parser("check")
    reg = sub.add_parser("register")
    reg.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path.cwd()
    if args.command == "scaffold":
        return cmd_scaffold(root, args.name)
    if args.command == "ingest":
        return cmd_ingest(root, Path(args.raw_file))
    if args.command == "new-note":
        return cmd_new_note(root, args.slug, args.source)
    if args.command == "check":
        return cmd_check(root)
    if args.command == "register":
        return cmd_register(root, dry_run=args.dry_run)
    if args.command == "status":
        return cmd_status(root)
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

Note: command functions are added in later tasks. To let the module import now, add temporary stubs at the bottom of `vault.py` (above `if __name__`):

```python
def cmd_scaffold(root: Path, name: str) -> int: raise NotImplementedError
def cmd_ingest(root: Path, raw_file: Path) -> int: raise NotImplementedError
def cmd_new_note(root: Path, slug: str, source: str) -> int: raise NotImplementedError
def cmd_check(root: Path) -> int: raise NotImplementedError
def cmd_register(root: Path, *, dry_run: bool = False, runner=subprocess.run) -> int: raise NotImplementedError
def cmd_status(root: Path) -> int: raise NotImplementedError
```

Each later task replaces the matching stub with a real implementation.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_vault -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/vault.py tests/test_vault.py
git commit -m "feat(vault-cli): skeleton + slugify/frontmatter/template helpers"
```

---

## Task 2: Author the template files

**Files:**
- Create: `scripts/templates/CLAUDE.md`
- Create: `scripts/templates/gitignore`
- Create: `scripts/templates/eval/VAULT_TESTS.md`
- Create: `scripts/templates/skills/vault-setup/SKILL.md`
- Create: `scripts/templates/skills/vault-ingest/SKILL.md`
- Create: `scripts/templates/skills/vault-query/SKILL.md`
- Create: `scripts/templates/skills/vault-lint/SKILL.md`
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Write failing test that every skill template has valid frontmatter**

```python
# append to tests/test_vault.py
import re as _re

class TestTemplates(unittest.TestCase):
    SKILLS = ["vault-setup", "vault-ingest", "vault-query", "vault-lint"]

    def test_skill_frontmatter_valid(self):
        for name in self.SKILLS:
            path = vault.TEMPLATES_DIR / "skills" / name / "SKILL.md"
            self.assertTrue(path.exists(), f"missing {path}")
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), f"{name}: no frontmatter fence")
            fm, _ = vault.parse_frontmatter(text)
            self.assertIn("name", fm, f"{name}: no name")
            self.assertIn("description", fm, f"{name}: no description")
            self.assertEqual(fm["name"], name)

    def test_skill_has_minimal_path(self):
        for name in self.SKILLS:
            text = (vault.TEMPLATES_DIR / "skills" / name / "SKILL.md").read_text("utf-8")
            self.assertIn("Minimal-model path", text, f"{name}: missing minimal path")
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python3 -m unittest tests.test_vault.TestTemplates -v`
Expected: FAIL — template files do not exist yet.

- [ ] **Step 3: Create `scripts/templates/CLAUDE.md`**

```markdown
# CLAUDE.md — {{VAULT_NAME}} Vault Schema

> Operating skills: `.claude/skills/vault-*` · CLI: `scripts/vault.py` · Lint: `scripts/lint_vault.py`
> STRICTNESS: MINIMAL   <!-- MINIMAL = deterministic-only, self-review off. CAPABLE = enable Layer-3 self-review. -->

## Three-layer model

| Layer | Folder | Rule |
|-------|--------|------|
| Source | `raw/` | **Immutable.** Never edit, rename, or delete. |
| Knowledge | `wiki/` | Atomic synthesized notes. One concept per file. `wiki/sources/` holds per-source summaries. |
| Navigation | `index/` | `_map-of-content.md`, `source-registry.md`, `log.md`, `key-takeaways.md`. |

`eval/` — test fixtures. **Never register as a qmd collection.**

## Answering questions about this vault's domain

When asked any question this vault could plausibly cover, you **MUST** consult the vault
before answering — never answer from prior knowledge alone. Use the **vault-query** skill:
qmd first, graphify for multi-hop, cite the note or its raw source, and if the vault does
not cover it, say so explicitly. Do not fill the gap from training data.

## Working the vault — use the skills, not improvisation

- New/changed clipping in `raw/` → **vault-ingest** skill.
- Question about the domain → **vault-query** skill.
- Health check / before declaring done → **vault-lint** skill (`vault check`).
- New or air-gapped vault setup → **vault-setup** skill.

The mechanical work is done by `scripts/vault.py`. You fill note bodies only.

## Safety rules

- Never invent provenance, dates, authors, or claims.
- Never collapse distinct concepts into one note; never duplicate — search qmd first.
- Never edit `raw/`. If `vault check` fails and you cannot fix it via the skill's
  whitelist, **STOP and report** — do not push a broken vault to "done".
```

- [ ] **Step 4: Create `scripts/templates/gitignore`**

```text
.DS_Store
graphify-out/.graphify_*
__pycache__/
*.pyc
```

- [ ] **Step 5: Create `scripts/templates/eval/VAULT_TESTS.md`**

```markdown
# Vault Test Checklist — {{VAULT_NAME}}

> ⚠ `eval/` is **never** a qmd collection. These answers must not contaminate retrieval.

## T0 — Deterministic check
Run: `python3 scripts/vault.py check` (Windows: `py scripts\vault.py check`). Pass: exit 0.

## T1 — Known-answer recall (author per corpus)
For 5–10 facts you can verify against a raw clipping, ask the question in a fresh session.
Pass per item: correct fact AND the gold note/raw source cited. Group pass: ≥80%.

## T2 — Negative controls (author per corpus)
Ask about 3 topics you have confirmed are ABSENT from `raw/`.
Pass: the agent says "not covered" each time. **Any fabrication fails the whole group.**

## T3 — Cross-source synthesis (author per corpus)
2 questions whose answer spans two clippings. Pass: connection drawn + both sources cited.

| Date | T0 | T1 | T2 | T3 | Notes |
|------|----|----|----|----|-------|
| —    | —  | —  | —  | —  | (first run pending) |
```

- [ ] **Step 6: Create `scripts/templates/skills/vault-ingest/SKILL.md`**

```markdown
---
name: vault-ingest
description: Ingest a new or changed clipping from raw/ into wiki summaries, concept notes, the registry, the log, and the graph. Use when a file is added to or changed in raw/, or when asked to ingest, index, or refresh the vault.
---

# vault-ingest

Turn an immutable `raw/` clipping into synthesized notes. The CLI does all mechanical work;
you write note bodies only.

## Minimal-model path (default)

1. Run: `python3 scripts/vault.py ingest raw/<file>.md`
   It creates the source-summary stub, the registry row, and the log entry, then prints the
   blanks to fill.
2. Read `raw/<file>.md` in full. Identify each durable concept it teaches.
3. For each concept, run: `python3 scripts/vault.py new-note <kebab-slug> --source raw/<file>.md`
4. Fill ONLY the `<!-- TODO ... -->` blanks in the summary and each concept note. Ground every
   claim in `raw/<file>.md`. Add a placeholder MOC link target where the stub indicates.
5. Run: `python3 scripts/vault.py check`
   - exit 0 → continue to step 6.
   - exit ≠0 → do exactly what the message says, or **STOP and report**. Do NOT free-form
     "fix". Do NOT edit `raw/`.
6. Build the graph: run `/graphify . --update` in Claude Code.
7. Register search: `python3 scripts/vault.py register`.

## Capable-model path (opt-in; only if CLAUDE.md STRICTNESS: CAPABLE)

Between steps 4 and 5, re-read `raw/<file>.md` and verify each sentence you wrote traces to
the source. Allowed reactions to a problem: re-run a command, fill a named blank, or STOP.
Never invent content; never edit `raw/`.
```

- [ ] **Step 7: Create `scripts/templates/skills/vault-query/SKILL.md`**

```markdown
---
name: vault-query
description: Answer a question about this vault's domain by retrieving from the vault and citing it, never from prior knowledge alone. Use for any question the vault could plausibly cover.
---

# vault-query

Ground every answer in the vault. Never answer an in-domain question from training data alone.

## Minimal-model path (default)

1. `qmd search "<exact terms>" -n 5` for keyword leads.
2. If conceptual/fuzzy, `qmd query` with `intent:`/`lex:`/`vec:` fields you write yourself.
3. `qmd get "#<docid>"` to read the full note before making any claim.
4. For "how does X relate to Y", run `graphify query "<question>"`.
5. Answer ONLY from retrieved text. Cite the note or its raw source.
6. If retrieval finds nothing relevant, say: "The vault does not cover this." Do NOT fill the
   gap from training data.

## Capable-model path (opt-in)

If the answer is novel cross-source synthesis not in any note, additionally save it as
`wiki/<slug>.md` with `type: analysis` and `sources:` listing the contributing notes, link it
from the MOC "Analyses" section, and append an `## [date] analysis | <title>` line to
`index/log.md`. Then `python3 scripts/vault.py check`.
```

- [ ] **Step 8: Create `scripts/templates/skills/vault-lint/SKILL.md`**

```markdown
---
name: vault-lint
description: Run the deterministic vault health check and interpret the findings. Use before declaring vault work complete, or whenever asked to lint, validate, or verify the vault.
---

# vault-lint

## Minimal-model path (default)

1. Run: `python3 scripts/vault.py check` (Windows: `py scripts\vault.py check`).
2. exit 0 → the vault is structurally sound. Done.
3. exit ≠0 → the output names each finding. Allowed fixes (whitelist only):
   - "unfilled stub / TODO marker in <file>" → fill that note's `<!-- TODO -->` body from its
     `sources:` clipping.
   - "missing registry row / log entry for <raw>" → re-run `vault ingest raw/<that-file>.md`.
   - "<note> not reachable from MOC" → add a wikilink to it under the right
     `index/_map-of-content.md` section.
   - anything else, or still failing after one pass → **STOP and report**. Do NOT edit `raw/`.
4. Re-run `vault check` until exit 0 or you hit the STOP condition.
```

- [ ] **Step 9: Create `scripts/templates/skills/vault-setup/SKILL.md`**

```markdown
---
name: vault-setup
description: Create a new vault or bootstrap one in an air-gapped environment, then register the search and graph engines. Use when setting up, scaffolding, or replicating a vault.
---

# vault-setup

## Create a new vault

1. Run: `python3 scripts/vault.py scaffold <vault-name>` (from a directory containing
   `scripts/vault.py`). It creates `raw/ wiki/ index/ eval/ scripts/ .claude/skills/`,
   renders `CLAUDE.md`, copies the CLI + lint + templates, and writes the four skills.
2. Put source clippings in `<vault-name>/raw/` (these become immutable).
3. `cd <vault-name>` and ingest each clipping with the **vault-ingest** skill.

## Air-gapped bootstrap

The vault repo carries `vault.py`, the skills, and `CLAUDE.md`. The ENGINES (qmd, graphify,
the embedding model, the graphify skill, the qmd plugin) transfer separately — follow
`instructions.md` Phase A (stage) and Phase B (install). Then:

1. Confirm Claude Code routes to the local model and no `GEMINI_API_KEY` is set.
2. `python3 scripts/vault.py register` to add qmd collections and embed.
3. `python3 scripts/vault.py check` — must exit 0.
```

- [ ] **Step 10: Run the template tests to verify they pass**

Run: `python3 -m unittest tests.test_vault.TestTemplates -v`
Expected: PASS (2 tests).

- [ ] **Step 11: Commit**

```bash
git add scripts/templates tests/test_vault.py
git commit -m "feat(vault-cli): add CLAUDE.md/eval/skill templates"
```

---

## Task 3: `scaffold` command

**Files:**
- Modify: `scripts/vault.py` (replace `cmd_scaffold` stub)
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Write failing test for scaffold**

```python
# append to tests/test_vault.py
import tempfile

class TestScaffold(unittest.TestCase):
    def test_scaffold_creates_layout(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rc = vault.cmd_scaffold(root, "Test Vault")
            self.assertEqual(rc, 0)
            v = root / "Test Vault"
            for sub in ["raw", "wiki", "wiki/sources", "index", "eval", "scripts",
                        ".claude/skills/vault-ingest"]:
                self.assertTrue((v / sub).is_dir(), f"missing dir {sub}")
            self.assertTrue((v / "CLAUDE.md").exists())
            self.assertIn("Test Vault", (v / "CLAUDE.md").read_text("utf-8"))
            self.assertTrue((v / "scripts/vault.py").exists())
            self.assertTrue((v / "scripts/templates/CLAUDE.md").exists(),
                            "templates must travel for self-replication")
            self.assertTrue((v / ".claude/skills/vault-ingest/SKILL.md").exists())
            for stem in ["_map-of-content", "source-registry", "log", "key-takeaways"]:
                self.assertTrue((v / "index" / f"{stem}.md").exists(), stem)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_vault.TestScaffold -v`
Expected: FAIL — `NotImplementedError`.

- [ ] **Step 3: Implement `cmd_scaffold`** (replace the stub)

```python
import shutil

INDEX_STARTERS = {
    "_map-of-content.md": (
        "---\ntitle: Map of Content\ntype: index\ntags: [moc, index]\n---\n\n"
        "# 🗺️ Map of Content\n\nEntry point for the vault.\n\n"
        "## Notes\n\n## Analyses\n\n*Write-back notes from synthesis queries.*\n\n"
        "## Other indices\n- [[source-registry]]\n- [[key-takeaways]]\n- [[log]]\n"
    ),
    "source-registry.md": (
        "---\ntitle: Source Registry\ntype: index\ntags: [sources, registry]\n---\n\n"
        "# 📚 Source Registry\n\n| # | Clipping (raw/) | Published | Summary | Wiki notes |\n"
        "|---|---|---|---|---|\n"
    ),
    "log.md": (
        "---\ntitle: Log\ntype: index\ntags: [log]\n---\n\n"
        "# 🪵 Log\n\nAppend-only journal: `## [YYYY-MM-DD] <op> | <title>`.\n"
    ),
    "key-takeaways.md": (
        "---\ntitle: Key Takeaways\ntype: index\ntags: [takeaways, index]\n---\n\n"
        "# 💡 Key Takeaways\n\n"
    ),
}


def cmd_scaffold(root: Path, name: str) -> int:
    v = root / name
    if v.exists() and any(v.iterdir()):
        print(f"vault scaffold: {v} already exists and is non-empty; aborting.", file=sys.stderr)
        return 1
    for sub in ["raw", "wiki/sources", "index", "eval", "scripts/templates", ".claude/skills"]:
        (v / sub).mkdir(parents=True, exist_ok=True)
    # Copy the engine files so the new vault is self-sufficient and self-replicating.
    shutil.cop2 = shutil.copy2  # alias for clarity
    shutil.copy2(Path(__file__).resolve(), v / "scripts" / "vault.py")
    lint = Path(__file__).resolve().parent / "lint_vault.py"
    if lint.exists():
        shutil.copy2(lint, v / "scripts" / "lint_vault.py")
    shutil.copytree(TEMPLATES_DIR, v / "scripts" / "templates", dirs_exist_ok=True)
    # Render CLAUDE.md, .gitignore, eval, and the four skills.
    (v / "CLAUDE.md").write_text(render_template("CLAUDE.md", VAULT_NAME=name), encoding="utf-8")
    (v / ".gitignore").write_text(render_template("gitignore"), encoding="utf-8")
    (v / "eval" / "VAULT_TESTS.md").write_text(
        render_template("eval/VAULT_TESTS.md", VAULT_NAME=name), encoding="utf-8")
    for skill in ["vault-setup", "vault-ingest", "vault-query", "vault-lint"]:
        dst = v / ".claude" / "skills" / skill
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "SKILL.md").write_text(
            render_template(f"skills/{skill}/SKILL.md"), encoding="utf-8")
    for fname, content in INDEX_STARTERS.items():
        (v / "index" / fname).write_text(content, encoding="utf-8")
    print(f"vault scaffold: created {v}")
    return 0
```

Note: remove the now-unused `shutil.copy2` alias line if your linter objects; it is only there to make the copy intent obvious.

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_vault.TestScaffold -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/vault.py tests/test_vault.py
git commit -m "feat(vault-cli): scaffold command creates self-contained vault layout"
```

---

## Task 4: `new-note` command

**Files:**
- Modify: `scripts/vault.py` (replace `cmd_new_note` stub)
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Write failing test**

```python
# append to tests/test_vault.py
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_vault.TestNewNote -v`
Expected: FAIL — `NotImplementedError`.

- [ ] **Step 3: Implement `cmd_new_note`** (replace the stub)

```python
def _raw_stem(source: str) -> str:
    return Path(source).stem


def cmd_new_note(root: Path, slug: str, source: str) -> int:
    slug = slugify(slug)
    src_path = root / source
    if not src_path.exists():
        print(f"vault new-note: source {source} not found.", file=sys.stderr)
        return 1
    note = root / "wiki" / f"{slug}.md"
    if note.exists():
        print(f"vault new-note: {note.relative_to(root)} already exists; not overwriting.",
              file=sys.stderr)
        return 1
    stem = _raw_stem(source)
    content = (
        f'---\ntitle: "{slug.replace("-", " ").title()}"\ntype: concept\ntags: []\n'
        f'sources:\n  - "[[{stem}]]"\n---\n\n'
        f'# {slug.replace("-", " ").title()}\n\n'
        f'<!-- TODO: one-sentence thesis in bold, grounded in [[{stem}]] -->\n\n'
        f'<!-- TODO: body. Dense [[wikilinks]] to sibling notes. -->\n\n'
        f'## Related\n<!-- TODO: [[sibling-note]] · [[sibling-note]] -->\n'
    )
    note.write_text(content, encoding="utf-8")
    print(f"vault new-note: created wiki/{slug}.md — fill its TODO blanks, then add a MOC link.")
    return 0
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_vault.TestNewNote -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/vault.py tests/test_vault.py
git commit -m "feat(vault-cli): new-note creates correct concept stub, refuses overwrite"
```

---

## Task 5: `ingest` command

**Files:**
- Modify: `scripts/vault.py` (replace `cmd_ingest` stub)
- Create: `tests/fixtures/sample-clipping.md`
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Create the fixture clipping**

```markdown
---
title: Understanding Low-Rank Adapters
author: Jane Researcher
source: https://example.com/lora
published: 2026-01-15
tags: [clippings]
---

# Understanding Low-Rank Adapters

LoRA freezes base weights and trains small low-rank matrices. The update is W' = W + (a/r)BA.
```

- [ ] **Step 2: Write failing test**

```python
# append to tests/test_vault.py
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
            summary = v / "wiki" / "sources" / "sample-clipping.md"
            self.assertTrue(summary.exists())
            sfm, _ = vault.parse_frontmatter(summary.read_text("utf-8"))
            self.assertEqual(sfm["type"], "source-summary")
            self.assertEqual(sfm["sources"], ["[[sample-clipping]]"])
            reg = (v / "index" / "source-registry.md").read_text("utf-8")
            self.assertIn("[[sample-clipping]]", reg)
            log = (v / "index" / "log.md").read_text("utf-8")
            self.assertIn("ingest | Understanding Low-Rank Adapters", log)

    def test_ingest_is_rerunnable(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._vault(d)
            self.assertEqual(vault.cmd_ingest(v, Path("raw/sample-clipping.md")), 0)
            self.assertEqual(vault.cmd_ingest(v, Path("raw/sample-clipping.md")), 0)
            reg = (v / "index" / "source-registry.md").read_text("utf-8")
            self.assertEqual(reg.count("[[sample-clipping]]"), 1)  # no duplicate row
```

- [ ] **Step 3: Run to verify it fails**

Run: `python3 -m unittest tests.test_vault.TestIngest -v`
Expected: FAIL — `NotImplementedError`.

- [ ] **Step 4: Implement `cmd_ingest`** (replace the stub)

```python
import datetime


def cmd_ingest(root: Path, raw_file: Path) -> int:
    src = root / raw_file
    if not src.exists():
        print(f"vault ingest: {raw_file} not found.", file=sys.stderr)
        return 1
    fm, _ = parse_frontmatter(src.read_text(encoding="utf-8"))
    title = fm.get("title", src.stem)
    published = fm.get("published") or fm.get("created") or ""
    stem = src.stem
    # 1. Summary stub (idempotent).
    summary = root / "wiki" / "sources" / f"{stem}.md"
    if not summary.exists():
        summary.write_text(
            f'---\ntitle: "Summary — {title}"\ntype: source-summary\ntags: []\n'
            f'sources:\n  - "[[{stem}]]"\n'
            + (f"published: {published}\n" if published else "")
            + f'---\n\n# Summary — {title}\n\n'
            f'<!-- TODO: one-sentence thesis -->\n\n'
            f'<!-- TODO: ~200 words on what the source argues, grounded in [[{stem}]] -->\n\n'
            f'## Key claims\n<!-- TODO: - claim → [[derived-concept-note]] -->\n\n'
            f'## Derived concept notes\n<!-- TODO: [[note-a]] · [[note-b]] -->\n',
            encoding="utf-8")
    # 2. Registry row (idempotent).
    reg = root / "index" / "source-registry.md"
    reg_text = reg.read_text(encoding="utf-8")
    if f"[[{stem}]]" not in reg_text:
        row = f"| | [[{stem}]] | {published} | [[{stem}]] | |\n"
        reg.write_text(reg_text.rstrip("\n") + "\n" + row, encoding="utf-8")
    # 3. Log entry (idempotent on title+op).
    log = root / "index" / "log.md"
    log_text = log.read_text(encoding="utf-8")
    entry = f"## [{datetime.date.today().isoformat()}] ingest | {title}"
    if f"ingest | {title}" not in log_text:
        log.write_text(log_text.rstrip("\n") + "\n\n" + entry + "\n", encoding="utf-8")
    print(f"vault ingest: {stem} — summary stub ready in wiki/sources/{stem}.md.")
    print("Now: read the clipping, then create one concept note per idea via:")
    print(f"  python3 scripts/vault.py new-note <slug> --source {raw_file}")
    print("Then fill all <!-- TODO --> blanks and run: python3 scripts/vault.py check")
    return 0
```

- [ ] **Step 5: Run to verify it passes**

Run: `python3 -m unittest tests.test_vault.TestIngest -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add scripts/vault.py tests/fixtures/sample-clipping.md tests/test_vault.py
git commit -m "feat(vault-cli): ingest creates summary stub + registry row + log entry"
```

---

## Task 6: `check` command (lint + stub-completion, fail-closed)

**Files:**
- Modify: `scripts/vault.py` (replace `cmd_check` stub)
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Write failing tests (integration: clean passes, TODO fails)**

```python
# append to tests/test_vault.py
class TestCheck(unittest.TestCase):
    def _filled_vault(self, d):
        root = Path(d)
        vault.cmd_scaffold(root, "V")
        v = root / "V"
        (v / "raw" / "sample-clipping.md").write_text(FIXTURE.read_text("utf-8"), "utf-8")
        vault.cmd_ingest(v, Path("raw/sample-clipping.md"))
        # Fill the summary stub (remove all TODO markers).
        summary = v / "wiki" / "sources" / "sample-clipping.md"
        summary.write_text(
            '---\ntitle: "Summary — Understanding Low-Rank Adapters"\n'
            'type: source-summary\ntags: [lora]\nsources:\n  - "[[sample-clipping]]"\n---\n\n'
            "# Summary — Understanding Low-Rank Adapters\n\n"
            "**LoRA trains small low-rank matrices on frozen weights.**\n\n"
            "LoRA freezes the base model and learns low-rank update matrices, "
            "so W' = W + (a/r)BA. This drastically cuts trainable parameters.\n\n"
            "## Key claims\n- low-rank update → [[low-rank-adapters]]\n\n"
            "## Derived concept notes\n[[low-rank-adapters]]\n", encoding="utf-8")
        return v

    def test_check_passes_when_filled(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._filled_vault(d)
            # Add the MOC link so the summary is reachable (lint requirement).
            moc = v / "index" / "_map-of-content.md"
            moc.write_text(moc.read_text("utf-8").replace(
                "## Notes\n", "## Notes\n- [[sample-clipping]]\n"), "utf-8")
            self.assertEqual(vault.cmd_check(v), 0)

    def test_check_fails_on_todo_marker(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._filled_vault(d)
            moc = v / "index" / "_map-of-content.md"
            moc.write_text(moc.read_text("utf-8").replace(
                "## Notes\n", "## Notes\n- [[sample-clipping]]\n"), "utf-8")
            # Re-introduce an unfilled stub.
            (v / "wiki" / "leftover.md").write_text(
                '---\ntitle: X\ntype: concept\ntags: []\nsources:\n  - "[[sample-clipping]]"\n'
                "---\n\n# X\n\n<!-- TODO: body -->\n", "utf-8")
            self.assertNotEqual(vault.cmd_check(v), 0)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest tests.test_vault.TestCheck -v`
Expected: FAIL — `NotImplementedError`.

- [ ] **Step 3: Implement `cmd_check`** (replace the stub)

```python
def _find_todo_markers(root: Path) -> list[Path]:
    hits = []
    for md in (root / "wiki").rglob("*.md"):
        if "<!-- TODO" in md.read_text(encoding="utf-8"):
            hits.append(md)
    return hits


def cmd_check(root: Path) -> int:
    failed = False
    # Layer 1+structural: reuse the existing lint if present.
    lint = root / "scripts" / "lint_vault.py"
    if lint.exists():
        result = subprocess.run([sys.executable, str(lint)], cwd=str(root))
        if result.returncode != 0:
            print("vault check: lint_vault.py reported findings (see above).", file=sys.stderr)
            failed = True
    # Layer 2: stub-completion (deterministic proxy for "model did its job").
    todos = _find_todo_markers(root)
    if todos:
        failed = True
        print("vault check: unfilled stub / TODO marker in:", file=sys.stderr)
        for p in todos:
            print(f"  - {p.relative_to(root)} → fill its <!-- TODO --> body from its source.",
                  file=sys.stderr)
    if failed:
        print("vault check: FAIL — fix the findings or STOP and report.", file=sys.stderr)
        return 1
    print("vault check: OK")
    return 0
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest tests.test_vault.TestCheck -v`
Expected: PASS (2 tests).

If `test_check_passes_when_filled` fails because `lint_vault.py` flags the scaffolded
starter notes (e.g. orphan `key-takeaways`), adjust the starter index notes in
`INDEX_STARTERS` (Task 3) so a freshly scaffolded+ingested vault is lint-clean, then re-run.
Document any such adjustment in the commit message.

- [ ] **Step 5: Commit**

```bash
git add scripts/vault.py tests/test_vault.py
git commit -m "feat(vault-cli): check = lint + stub-completion, fail-closed"
```

---

## Task 7: `register` command

**Files:**
- Modify: `scripts/vault.py` (replace `cmd_register` stub)
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Write failing test (command construction + eval exclusion via dry-run)**

```python
# append to tests/test_vault.py
class TestRegister(unittest.TestCase):
    def test_register_dry_run_excludes_eval(self):
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
            self.assertNotIn("eval", flat)  # eval/ must never be registered
            self.assertIn("qmd update", flat)
            self.assertIn("qmd embed", flat)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_vault.TestRegister -v`
Expected: FAIL — `NotImplementedError`.

- [ ] **Step 3: Implement `cmd_register`** (replace the stub)

```python
def cmd_register(root: Path, *, dry_run: bool = False, runner=subprocess.run) -> int:
    commands = [
        ["qmd", "collection", "add", "./raw", "--name", "sources"],
        ["qmd", "collection", "add", "./wiki", "--name", "concepts"],
        ["qmd", "collection", "add", "./index", "--name", "indices"],
        ["qmd", "update"],
        ["qmd", "embed"],
    ]
    # eval/ is intentionally absent: gold answers must never enter retrieval.
    for cmd in commands:
        print("vault register:", " ".join(cmd))
        if dry_run:
            continue
        result = runner(cmd, cwd=str(root))
        if getattr(result, "returncode", 1) != 0:
            print(f"vault register: command failed: {' '.join(cmd)}", file=sys.stderr)
            return 1
    return 0
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_vault.TestRegister -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/vault.py tests/test_vault.py
git commit -m "feat(vault-cli): register adds qmd collections (never eval), update+embed"
```

---

## Task 8: `status` command

**Files:**
- Modify: `scripts/vault.py` (replace `cmd_status` stub)
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Write failing test**

```python
# append to tests/test_vault.py
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
            self.assertIn("sample-clipping", out)
            self.assertIn("summary", out)  # column header or marker
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_vault.TestStatus -v`
Expected: FAIL — `NotImplementedError`.

- [ ] **Step 3: Implement `cmd_status`** (replace the stub)

```python
def cmd_status(root: Path) -> int:
    raws = sorted((root / "raw").glob("*.md"))
    reg = (root / "index" / "source-registry.md").read_text(encoding="utf-8")
    log = (root / "index" / "log.md").read_text(encoding="utf-8")
    print(f"{'clipping':40} {'summary':8} {'registry':8} {'log':5}")
    for r in raws:
        stem = r.stem
        has_summary = (root / "wiki" / "sources" / f"{stem}.md").exists()
        has_reg = f"[[{stem}]]" in reg
        has_log = stem in log or r.stem.replace("-", " ") in log
        print(f"{stem:40} {'yes' if has_summary else 'NO':8} "
              f"{'yes' if has_reg else 'NO':8} {'yes' if has_log else 'NO':5}")
    return 0
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_vault.TestStatus -v`
Expected: PASS.

- [ ] **Step 5: Run the FULL test suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (all tests across Tasks 1–8).

- [ ] **Step 6: Commit**

```bash
git add scripts/vault.py tests/test_vault.py
git commit -m "feat(vault-cli): status reports per-clipping ingest state"
```

---

## Task 9: Adopt the suite in this repo

**Files:**
- Create: `.claude/skills/vault-setup/SKILL.md`, `.claude/skills/vault-ingest/SKILL.md`, `.claude/skills/vault-query/SKILL.md`, `.claude/skills/vault-lint/SKILL.md`
- Modify: `CLAUDE.md` (this repo's existing schema — add skill pointers + STRICTNESS line)

- [ ] **Step 1: Generate the four skills into this repo from the templates**

Run:
```bash
python3 - <<'PY'
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("vault", "scripts/vault.py")
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
for s in ["vault-setup", "vault-ingest", "vault-query", "vault-lint"]:
    d = Path(".claude/skills") / s; d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(v.render_template(f"skills/{s}/SKILL.md"), encoding="utf-8")
    print("wrote", d / "SKILL.md")
PY
```
Expected: prints four `wrote .claude/skills/.../SKILL.md` lines.

- [ ] **Step 2: Add STRICTNESS + skill pointers to this repo's CLAUDE.md**

Add immediately under the title line of `CLAUDE.md`:

```markdown
> Operating skills: `.claude/skills/vault-*` · CLI: `scripts/vault.py`
> STRICTNESS: MINIMAL   <!-- MINIMAL = deterministic-only. CAPABLE = enable self-review. -->
```

And add this section after the existing "## Workflow — Query" section:

```markdown
## Skills

- New/changed `raw/` clipping → **vault-ingest**.
- Domain question → **vault-query** (enforces the grounding rule above).
- Health check before "done" → **vault-lint** (`python3 scripts/vault.py check`).
- New/air-gapped vault setup → **vault-setup**.
```

- [ ] **Step 3: Verify the deterministic check passes on the real vault**

Run: `python3 scripts/vault.py check`
Expected: `vault check: OK` (exit 0). If it fails, the output names each finding; fix per the
vault-lint whitelist, then re-run.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills CLAUDE.md
git commit -m "feat(vault): adopt vault-* skill suite + STRICTNESS in this vault"
```

---

## Task 10: Retire the old user-level skill

**Files:**
- Modify: `~/.claude/skills/obsidian_knowledge_graph_skill/SKILL.md`
- Delete: `~/.claude/skills/obsidian_knowledge_graph_skill/vault-conventions.md`, `ingestion-and-indexing-playbook.md`, `graphify-synthesis-notes.md`

- [ ] **Step 1: Replace SKILL.md with a valid-frontmatter deprecation pointer**

Overwrite `~/.claude/skills/obsidian_knowledge_graph_skill/SKILL.md` with:

```markdown
---
name: obsidian-knowledge-graph
description: DEPRECATED. The vault now ships its own skill suite (vault-setup, vault-ingest, vault-query, vault-lint) in <vault>/.claude/skills/. Use those when working inside a vault.
---

# Obsidian Knowledge Graph (deprecated)

This global skill is superseded. Each vault now carries a self-contained skill suite in its
own `.claude/skills/` plus a deterministic `scripts/vault.py` CLI. When working in a vault,
use **vault-setup / vault-ingest / vault-query / vault-lint** instead. See the vault's
`CLAUDE.md` and `instructions.md`.
```

- [ ] **Step 2: Delete the superseded reference files**

Run:
```bash
rm -f ~/.claude/skills/obsidian_knowledge_graph_skill/vault-conventions.md \
      ~/.claude/skills/obsidian_knowledge_graph_skill/ingestion-and-indexing-playbook.md \
      ~/.claude/skills/obsidian_knowledge_graph_skill/graphify-synthesis-notes.md
```
Expected: no output, exit 0.

- [ ] **Step 3: Verify frontmatter parses**

Run:
```bash
python3 - <<'PY'
import importlib.util
spec = importlib.util.spec_from_file_location("vault", "scripts/vault.py")
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
from pathlib import Path
p = Path.home()/".claude/skills/obsidian_knowledge_graph_skill/SKILL.md"
fm, _ = v.parse_frontmatter(p.read_text("utf-8"))
assert fm.get("name") == "obsidian-knowledge-graph", fm
assert "DEPRECATED" in fm.get("description", "")
print("deprecation pointer OK")
PY
```
Expected: `deprecation pointer OK`.

Note: this step edits files outside the repo (`~/.claude`), so there is nothing to commit
here. Record completion in the final commit message of Task 11.

---

## Task 11: Full self-test, docs pointer, final commit

**Files:**
- Modify: `instructions.md` (add a pointer to the skill suite)
- Modify: `README.md` if present (else skip)

- [ ] **Step 1: Run the full deterministic self-test (this is the §9 air-gapped self-test)**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS (every test from Tasks 1–8).

- [ ] **Step 2: End-to-end smoke test in a throwaway dir**

Run:
```bash
python3 - <<'PY'
import importlib.util, tempfile
from pathlib import Path
spec = importlib.util.spec_from_file_location("vault", "scripts/vault.py")
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    assert v.cmd_scaffold(root, "Demo") == 0
    demo = root / "Demo"
    (demo/"raw"/"sample-clipping.md").write_text(
        (Path("tests/fixtures/sample-clipping.md")).read_text("utf-8"), "utf-8")
    assert v.cmd_ingest(demo, Path("raw/sample-clipping.md")) == 0
    assert v.cmd_new_note(demo, "low-rank-adapters", "raw/sample-clipping.md") == 0
    # check MUST fail now (stubs unfilled) — proves fail-closed:
    assert v.cmd_check(demo) != 0
    print("end-to-end fail-closed smoke test OK")
PY
```
Expected: `end-to-end fail-closed smoke test OK`.

- [ ] **Step 3: Add a pointer in instructions.md**

Add to the top "If you are an AI agent" block of `instructions.md`:

```markdown
> - **Prefer the in-repo skills.** This vault ships `vault-setup / vault-ingest / vault-query
>   / vault-lint` in `.claude/skills/` backed by `scripts/vault.py`. Use them rather than
>   improvising; they encode this runbook deterministically for minimal models.
```

- [ ] **Step 4: Final commit**

```bash
git add instructions.md
git commit -m "docs: point instructions.md at the vault-* skill suite; retire old global skill"
```

---

## Self-Review (completed during planning)

- **Spec coverage:** §4 layout → Tasks 2,3,9. §5 CLI (scaffold/ingest/new-note/check/register/status) → Tasks 3,5,4,6,7,8. §6 four skills → Task 2 (templates) + Task 9 (adoption). §7 data flow → encoded in vault-ingest SKILL.md (Task 2). §8 validation (3 layers, fail-closed) → Task 6 (`check`) + skill whitelists (Task 2). §9 testing (CLI self-test + manual eval) → Tasks 1–8 tests + Task 11 self-test + eval template (Task 2). §10 migration → Task 10. §11 air-gapped transfer → vault-setup SKILL.md (Task 2) + instructions.md pointer (Task 11). §12 risks: qmd Windows cache path noted in vault-setup; concept-note identification handled by `new-note` (Task 4).
- **Placeholder scan:** none — every code/test/template step contains real content.
- **Type consistency:** function signatures in the File Structure interface list match every call site in Tasks 3–11 (`cmd_register(..., runner=...)`, `cmd_new_note(root, slug, source)`, `parse_frontmatter -> (dict, str)`, `render_template(rel_path, **vars)`).
```
