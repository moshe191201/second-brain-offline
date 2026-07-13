# Vault-local qmd state (v0.2.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all qmd search state into the vault directory — `vault register` creates a vault-local `.qmd/` index (`qmd init`), the repo commits `.qmd/index.yml`, and the derived sqlite is gitignored — shipping as framework v0.2.0.

**Architecture:** qmd natively auto-discovers a project-local `.qmd/index.yml` by walking up from cwd, overriding the global `~/.cache/qmd` index. We prepend `["qmd", "init"]` to `cmd_register`'s command list (it already runs with `cwd=root`), add `.qmd/*.sqlite*` to the payload gitignore, update the docs, bump to 0.2.0, and migrate the live vault.

**Tech Stack:** Python stdlib (existing package), pytest, qmd CLI (`@tobilu/qmd`).

**Repos:**
- Package: `/Users/moshe/Desktop/Code/second-brain-vault-framework/` (branch `master`)
- Vault: `/Users/moshe/Desktop/Code/Moshe Vault/` (branch `design/vault-framework-package`)
- Spec: `docs/superpowers/specs/2026-07-13-vault-local-qmd-state-design.md` (vault repo)

---

## File Structure

```
second-brain-vault-framework/
├── src/second_brain_vault_framework/
│   ├── __init__.py                      # MODIFY: 0.1.0 → 0.2.0 (Task 4)
│   ├── core.py                          # MODIFY: cmd_register prepends qmd init (Task 1)
│   └── payload/
│       ├── gitignore                    # MODIFY: + .qmd/*.sqlite* (Task 2)
│       ├── instructions.md              # MODIFY: copied from vault repo after doc edits (Task 3)
│       └── dot-claude/skills/vault-setup/SKILL.md   # MODIFY: register step mentions .qmd (Task 3)
└── tests/
    ├── test_register.py                 # CREATE (Task 1)
    └── test_scaffold.py                 # MODIFY: gitignore assertion (Task 2)

Moshe Vault/
├── instructions.md                      # MODIFY: architecture line, Phase C ×2, Distribution subsection (Task 3)
├── .claude/skills/vault-setup/SKILL.md  # MODIFY: same register-step edit (Task 3)
├── .gitignore                           # MODIFY: + .qmd/*.sqlite* (Task 5)
└── .qmd/index.yml                       # CREATE (by qmd init) + commit (Task 5)
```

`scripts/templates/` in the vault repo is legacy (superseded by the package payload) — do NOT update it.

---

## Task 1: `cmd_register` prepends `qmd init` (TDD)

**Files:**
- Test: `tests/test_register.py` (create)
- Modify: `src/second_brain_vault_framework/core.py` (the `commands` list inside `cmd_register`)

Work from `/Users/moshe/Desktop/Code/second-brain-vault-framework/`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_register.py`:
```python
from second_brain_vault_framework import core


class FakeResult:
    def __init__(self, returncode=0):
        self.returncode = returncode


def test_register_runs_init_then_collections_update_embed(tmp_path):
    calls = []

    def runner(cmd, cwd=None):
        calls.append((cmd, cwd))
        return FakeResult(0)

    rc = core.cmd_register(tmp_path, runner=runner)
    assert rc == 0
    cmds = [c for c, _ in calls]
    assert cmds == [
        ["qmd", "init"],
        ["qmd", "collection", "add", "./raw", "--name", "sources"],
        ["qmd", "collection", "add", "./wiki", "--name", "concepts"],
        ["qmd", "collection", "add", "./index", "--name", "indices"],
        ["qmd", "update"],
        ["qmd", "embed"],
    ]
    # every command runs from the vault root so qmd's .qmd/ auto-discovery engages
    assert all(cwd == str(tmp_path) for _, cwd in calls)


def test_register_dry_run_prints_but_does_not_run(tmp_path, capsys):
    calls = []

    def runner(cmd, cwd=None):
        calls.append(cmd)
        return FakeResult(0)

    rc = core.cmd_register(tmp_path, dry_run=True, runner=runner)
    assert rc == 0
    assert calls == []
    out = capsys.readouterr().out
    assert "qmd init" in out
    assert "qmd embed" in out


def test_register_stops_on_first_failure(tmp_path):
    calls = []

    def runner(cmd, cwd=None):
        calls.append(cmd)
        return FakeResult(1)

    rc = core.cmd_register(tmp_path, runner=runner)
    assert rc == 1
    assert calls == [["qmd", "init"]]
```

- [ ] **Step 2: Run tests to verify the first one fails**

Run: `cd /Users/moshe/Desktop/Code/second-brain-vault-framework && python3 -m pytest tests/test_register.py -v`
Expected: `test_register_runs_init_then_collections_update_embed` and `test_register_stops_on_first_failure` FAIL (current command list has no `qmd init`); `test_register_dry_run_prints_but_does_not_run` fails on the `"qmd init" in out` assertion.

- [ ] **Step 3: Implement — prepend init to the command list**

In `src/second_brain_vault_framework/core.py`, inside `cmd_register`, replace the `commands` list:
```python
    commands = [
        ["qmd", "init"],
        ["qmd", "collection", "add", "./raw", "--name", "sources"],
        ["qmd", "collection", "add", "./wiki", "--name", "concepts"],
        ["qmd", "collection", "add", "./index", "--name", "indices"],
        ["qmd", "update"],
        ["qmd", "embed"],
    ]
    # eval/ is intentionally absent: gold answers must never enter retrieval.
    # `qmd init` creates the vault-local .qmd/ (index.yml + index.sqlite); every
    # later command runs with cwd=root, so qmd auto-discovers and targets it.
```
(The existing `# eval/ is intentionally absent` comment stays; the second comment line is new.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_register.py -v`
Expected: 3 passed.

- [ ] **Step 5: Run the whole suite**

Run: `python3 -m pytest -q`
Expected: 24 passed (21 existing + 3 new).

- [ ] **Step 6: Commit**

```bash
git add tests/test_register.py src/second_brain_vault_framework/core.py
git commit -m "feat: register creates the vault-local .qmd index via qmd init"
```

---

## Task 2: Payload gitignore excludes the derived index (TDD)

**Files:**
- Test: `tests/test_scaffold.py` (append one test)
- Modify: `src/second_brain_vault_framework/payload/gitignore`

Work from `/Users/moshe/Desktop/Code/second-brain-vault-framework/`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_scaffold.py`:
```python
def test_scaffold_gitignore_excludes_qmd_index(tmp_path):
    # .qmd/index.yml is committed (declarative registry + model pins);
    # the derived sqlite (+ -shm/-wal sidecars) must never enter git.
    target = tmp_path / "myvault"
    assert core.cmd_scaffold(target, "myvault") == 0
    gi = (target / ".gitignore").read_text(encoding="utf-8")
    assert ".qmd/*.sqlite*" in gi
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest tests/test_scaffold.py::test_scaffold_gitignore_excludes_qmd_index -v`
Expected: FAIL (`.qmd/*.sqlite*` not in the scaffolded `.gitignore`).

- [ ] **Step 3: Add the line to the payload gitignore**

`src/second_brain_vault_framework/payload/gitignore` becomes exactly:
```
.DS_Store
graphify-out/.graphify_*
__pycache__/
*.pyc
.qmd/*.sqlite*
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_scaffold.py -v`
Expected: 4 passed (3 existing + 1 new).

- [ ] **Step 5: Commit**

```bash
git add tests/test_scaffold.py src/second_brain_vault_framework/payload/gitignore
git commit -m "feat: scaffolded vaults gitignore the derived .qmd sqlite index"
```

---

## Task 3: Documentation — instructions.md + vault-setup skill

**Files:**
- Modify: `/Users/moshe/Desktop/Code/Moshe Vault/instructions.md` (three edits)
- Modify: `/Users/moshe/Desktop/Code/Moshe Vault/.claude/skills/vault-setup/SKILL.md`
- Modify (copies): `src/second_brain_vault_framework/payload/instructions.md`, `src/second_brain_vault_framework/payload/dot-claude/skills/vault-setup/SKILL.md`

Do NOT touch Part 1 of instructions.md (historical narrative, including its `qmd collection add` block around line 186 — that records what was done with the old global index). Do NOT touch `scripts/templates/` (legacy).

- [ ] **Step 1: Edit the architecture overview (instructions.md ~line 47)**

Replace:
```
└── (qmd index)     ENGINE B — hybrid BM25 + vector search over raw/, wiki/, index/ (NOT eval/).
                               Lives outside the vault in ~/.cache/qmd/. Queried via `qmd`.
```
with:
```
└── .qmd/           ENGINE B — hybrid BM25 + vector search over raw/, wiki/, index/ (NOT eval/).
                               Vault-local: index.yml (collections + model pins, committed)
                               + index.sqlite (derived index, gitignored). Queried via `qmd`.
```

- [ ] **Step 2: Edit BOTH Phase C register blocks (instructions.md ~lines 529 and ~551)**

Bash block — replace:
```
cd "<Vault>"
qmd collection add ./raw   --name sources
```
with:
```
cd "<Vault>"
qmd init                                     # create the vault-local .qmd/ (registry + index)
qmd collection add ./raw   --name sources
```
PowerShell block — replace:
```
cd "<Vault>"
qmd collection add ./raw   --name sources
```
with:
```
cd "<Vault>"
qmd init                                     # create the vault-local .qmd/ (registry + index)
qmd collection add ./raw   --name sources
```
(Both blocks contain the identical two lines; use `replace_all` or edit each occurrence — there are exactly two after excluding Part 1, whose block has different surrounding text and `# + context description` comments.)

- [ ] **Step 3: Add the state-policy subsection to the Distribution section**

In instructions.md, insert immediately BEFORE the `### Maintainer — cutting and shipping a release` heading:
```markdown
### Search-index state (`.qmd/`) — the one-place state policy

`vault register` runs `qmd init` first, creating a **vault-local** `.qmd/` directory. qmd
auto-discovers `.qmd/index.yml` from any cwd inside the vault and uses it instead of the
global `~/.cache/qmd` index — so all vault state lives in the vault directory, and two
vaults on one machine no longer collide on collection names.

| File | Git | Why |
|------|-----|-----|
| `.qmd/index.yml` | **committed** | Declarative: collection registry + pinned embedding models |
| `.qmd/index.sqlite` (+ `-shm`/`-wal`) | **ignored** (`.qmd/*.sqlite*`) | Derived binary; churns on every ingest; rebuildable |
| `~/.cache/qmd/models/` | not vault state | Machine asset (like a compiler) — or the internal embedding API |

Fresh clone → rebuild the index with one command:
```bash
cd <vault> && vault register        # qmd init + collection adds + qmd update + qmd embed
```

Migrating a pre-v0.2.0 vault (index still global):
1. `cd <vault> && vault register` — creates `.qmd/`, registers collections locally, update + embed
2. Append `.qmd/*.sqlite*` to the vault's `.gitignore`
3. Commit `.qmd/index.yml`
4. Optional hygiene: `qmd collection remove sources|concepts|indices` run from OUTSIDE the vault, to drop the old entries from the global registry

```

- [ ] **Step 4: Edit the vault-setup skill (both copies)**

In `/Users/moshe/Desktop/Code/Moshe Vault/.claude/skills/vault-setup/SKILL.md`, replace:
```
2. `python3 scripts/vault.py register` to add qmd collections and embed.
```
with:
```
2. `python3 scripts/vault.py register` — creates the vault-local `.qmd/` index (`qmd init`),
   adds the collections, and embeds. Commit `.qmd/index.yml`; the sqlite stays gitignored.
```
Apply the identical replacement in `src/second_brain_vault_framework/payload/dot-claude/skills/vault-setup/SKILL.md`.

- [ ] **Step 5: Sync instructions.md into the payload**

```bash
cp "/Users/moshe/Desktop/Code/Moshe Vault/instructions.md" \
   /Users/moshe/Desktop/Code/second-brain-vault-framework/src/second_brain_vault_framework/payload/instructions.md
```

- [ ] **Step 6: Verify and commit in BOTH repos**

```bash
cd "/Users/moshe/Desktop/Code/Moshe Vault"
grep -c "qmd init" instructions.md          # expect 4 (2 Phase C blocks + 2 in the new subsection; Part 1 untouched)
grep -c "Search-index state" instructions.md # expect 1
git add instructions.md .claude/skills/vault-setup/SKILL.md
git commit -m "docs: vault-local .qmd state policy (v0.2.0)"

cd /Users/moshe/Desktop/Code/second-brain-vault-framework
git add src/second_brain_vault_framework/payload/instructions.md \
        src/second_brain_vault_framework/payload/dot-claude/skills/vault-setup/SKILL.md
git commit -m "docs: payload carries vault-local .qmd state policy"
```

---

## Task 4: Version 0.2.0 — suite, wheel, tag

**Files:**
- Modify: `src/second_brain_vault_framework/__init__.py`

Work from `/Users/moshe/Desktop/Code/second-brain-vault-framework/`.

- [ ] **Step 1: Bump the version**

In `src/second_brain_vault_framework/__init__.py`:
```python
__version__ = "0.2.0"
```

- [ ] **Step 2: Full suite**

Run: `python3 -m pytest -q`
Expected: 25 passed (24 from Task 1 + 1 from Task 2).

- [ ] **Step 3: Build and verify the wheel**

```bash
rm -rf dist build
/tmp/vf-venv/bin/python -m build 2>&1 | tail -3
python3 - <<'PY'
import zipfile
z = zipfile.ZipFile("dist/second_brain_vault_framework-0.2.0-py3-none-any.whl")
payload_gi = z.read("second_brain_vault_framework/payload/gitignore").decode()
payload_instr = z.read("second_brain_vault_framework/payload/instructions.md").decode()
assert ".qmd/*.sqlite*" in payload_gi, "gitignore line missing from wheel"
assert "Search-index state" in payload_instr, "doc subsection missing from wheel"
print("wheel payload OK")
PY
```
Expected: `Successfully built ...0.2.0...` then `wheel payload OK`.
(If `/tmp/vf-venv/bin/python -m build` reports no module `build`: `/tmp/vf-venv/bin/pip install build` and retry.)

- [ ] **Step 4: Commit and tag**

```bash
git add src/second_brain_vault_framework/__init__.py
git commit -m "chore: release v0.2.0 — vault-local qmd state"
git tag v0.2.0
git tag --list
```
Expected: tags `v0.1.0` and `v0.2.0`.

---

## Task 5: Migrate the live vault (additive; verify before committing)

**Files:**
- Modify: `/Users/moshe/Desktop/Code/Moshe Vault/.gitignore`
- Create (by qmd): `/Users/moshe/Desktop/Code/Moshe Vault/.qmd/` → commit only `index.yml`

The live vault has NOT adopted the package's file layout (that's fine — `register` only shells out to qmd; it does not touch framework files). The editable install in `/tmp/vf-venv` reflects v0.2.0 source automatically.

- [ ] **Step 1: Pre-check**

```bash
cd "/Users/moshe/Desktop/Code/Moshe Vault"
git status --short          # note pre-existing state; expect clean
qmd status | head -5        # expect Index: ~/.cache/qmd/index.sqlite (global, pre-migration)
```

- [ ] **Step 2: Run the new register (creates .qmd/, registers, indexes, embeds)**

```bash
cd "/Users/moshe/Desktop/Code/Moshe Vault"
/tmp/vf-venv/bin/vault register
```
Expected: prints the six commands starting with `vault register: qmd init`; each succeeds. `qmd embed` embeds ~39 docs with the local GGUF models — allow up to 10 minutes (Bash timeout 600000).

- [ ] **Step 3: Verify the local index took over**

```bash
cd "/Users/moshe/Desktop/Code/Moshe Vault"
qmd status | head -8         # Index: .../Moshe Vault/.qmd/index.sqlite; 3 collections; vectors > 0
qmd search "GRPO" -n 3       # returns hits from the local index
ls .qmd/                     # index.yml + index.sqlite (+ sidecars)
```
Expected: the Index path is INSIDE the vault; search returns results. Note: the qmd MCP server in a running Claude Code session was started before `.qmd/` existed and may still hold the global DB — verify with the CLI as above; the MCP picks up the local index on its next session start.

- [ ] **Step 4: Gitignore the sqlite, commit the registry**

```bash
cd "/Users/moshe/Desktop/Code/Moshe Vault"
grep -qxF ".qmd/*.sqlite*" .gitignore || printf ".qmd/*.sqlite*\n" >> .gitignore
git add .gitignore .qmd/index.yml
git status --short           # MUST show only .gitignore + .qmd/index.yml staged; NO sqlite
git commit -m "chore: adopt vault-local qmd index (.qmd/) — registry committed, sqlite ignored"
```
If `git status` shows any `.sqlite` file staged, STOP — fix the gitignore line before committing.

- [ ] **Step 5: Report the optional global-registry cleanup (do NOT execute)**

Report to the user that the old global collections still exist in `~/.cache/qmd` and can be removed later by running, from any directory OUTSIDE the vault: `qmd collection remove sources && qmd collection remove concepts && qmd collection remove indices`. Leave execution to the user.

---

## Notes for the executor

- Task 1 and Task 2 are package-repo TDD tasks; Task 3 spans both repos; Task 4 is package-only; Task 5 is vault-only and runs REAL qmd commands (needs qmd on PATH and the local embedding models already present — both true on this machine).
- The vault repo is on branch `design/vault-framework-package`; commit there (do not switch branches).
- Publishing v0.2.0 to the internal index (airgap-pack + twine) is out of scope, same as v0.1.0.
