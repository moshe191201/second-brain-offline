# Design — Vault-local qmd state (framework v0.2.0)

> Status: approved for planning · Date: 2026-07-13
> Extends: `2026-07-12-vault-framework-package-distribution-design.md`
> Package: `second-brain-vault-framework` v0.2.0

## Problem

A vault's state is split across two places: the markdown content lives in the user's git
repo, but qmd's search state — the collection registry, model config, and the sqlite/vector
index — lives in a **global, machine-local** cache (`~/.cache/qmd/index.sqlite`). Consequences:

- The vault directory is not a complete unit: cloning or copying it loses the search setup.
- Collection names (`sources`/`concepts`/`indices`) are global — **two vaults on one machine
  collide.**
- Nothing in the repo records what was indexed or with which embedding models.

Goal: the entire vault state is managed in one place — the user's git repo (with derived
state co-located in the vault directory and rebuildable).

## Key discovery

qmd natively supports project-local indexes; the vault simply doesn't use them:

- `qmd init` (run inside a project) creates `<project>/.qmd/` containing **`index.yml`**
  (collection registry + pinned model config) and **`index.sqlite`** (the index).
- `findLocalConfigPath()` walks up from cwd on **every** qmd command; if `.qmd/index.yaml|yml`
  exists, qmd uses the local index instead of the global one automatically. No flags, no env
  vars. (Verified in `@tobilu/qmd` `dist/collections.js:78` and `dist/cli/qmd.js:2510`.)
- `initLocalIndex()` is idempotent: existing `.qmd/index.yml` is kept, models are ensured.

## State taxonomy & policy

| State | Policy |
|---|---|
| Markdown content (`raw/`, `wiki/`, `index/`) | In git (unchanged) |
| graphify graph (`graphify-out/`) | In git (unchanged, already vault-local) |
| qmd collection registry + model config (`.qmd/index.yml`) | **Vault-local, committed** — declarative, small, text; pins embedding models per vault |
| qmd index (`.qmd/index.sqlite` + `-shm`/`-wal`) | **Vault-local, gitignored** — derived binary; rebuilt deterministically via `vault register` (`qmd update && qmd embed`) |
| Embedding models (`~/.cache/qmd/models/`, ~2 GB) | Machine asset (like a compiler) — not vault state; in the qmd-api variant embeddings come from the internal API |

Rationale for not committing the sqlite: it churns on every ingest, WAL sidecars must never
be committed, merges are unresolvable, and the index is coupled to the embedding model — a
committed index can silently mismatch another machine. Fresh clones run one rebuild command.

## Changes (framework v0.2.0)

### 1. `cmd_register` prepends `qmd init`

`register` is the single "wire up qmd" command; it now creates/adopts the vault-local index
first. New command sequence (unchanged `runner` injection, `cwd=root`):

```python
commands = [
    ["qmd", "init"],
    ["qmd", "collection", "add", "./raw", "--name", "sources"],
    ["qmd", "collection", "add", "./wiki", "--name", "concepts"],
    ["qmd", "collection", "add", "./index", "--name", "indices"],
    ["qmd", "update"],
    ["qmd", "embed"],
]
```

Because `cwd=root` and `.qmd/index.yml` exists after `init`, every subsequent command
auto-targets the vault-local index. `eval/` remains intentionally unregistered. Collection
name collisions across vaults disappear (each vault has its own registry).

`cmd_scaffold` is unchanged — qmd wiring stays out of scaffold (no external dependency);
`register` remains the explicit step, per the existing vault-setup skill flow.

### 2. Payload `gitignore` gains the index-exclusion line

```
.qmd/*.sqlite*
```

Covers `index.sqlite`, `-shm`, `-wal`; leaves `.qmd/index.yml` committable. `gitignore` is
scaffold-only (not framework-owned), so existing vaults add this line during migration.

### 3. Documentation

- `instructions.md` architecture overview: the "(qmd index) … lives outside the vault in
  ~/.cache/qmd/" description changes to the vault-local `.qmd/` layout.
- `instructions.md` Part 3 (Phase C register step) and the Distribution section: note that
  `vault register` creates `.qmd/`, that `index.yml` is committed while the sqlite is
  ignored, and that a fresh clone rebuilds with `vault register`.
- `CLAUDE.md`, skills: no behavioral change required (qmd commands run from the vault root
  and auto-discover). vault-setup SKILL.md gets a one-line note about `.qmd/`.

### 4. Version bump

`__version__ = "0.2.0"`, rebuild wheel, tag `v0.2.0`.

## Migration (existing vaults, incl. the live Moshe Vault)

1. From the vault root: `vault register` (new version) — creates `.qmd/`, registers
   collections locally, `update` + `embed`.
2. Append `.qmd/*.sqlite*` to the vault's `.gitignore`.
3. Commit `.qmd/index.yml`.
4. Optional hygiene: remove the vault's collections from the global index
   (`qmd collection remove <name>` against the global config, run from outside the vault).

## Non-goals

- Committing the sqlite index (plain or LFS) — revisit only if clone-and-go without a
  rebuild becomes a hard requirement.
- `vault check` warning when the sqlite is git-tracked (YAGNI).
- Any change to graphify state handling.

## Testing

- `tests/test_register.py`: with a recording fake `runner`, assert the exact command
  sequence (init first, then the three collection adds, update, embed) and `cwd=root`;
  assert `--dry-run` prints but does not invoke the runner.
- Scaffold test addition: a scaffolded vault's `.gitignore` contains `.qmd/*.sqlite*`.
- Manual verification: in a scaffolded vault with qmd installed, `vault register` →
  `qmd status` shows `Index: <vault>/.qmd/index.sqlite`; from inside the vault the MCP
  server / CLI hit the local index; a second vault on the same machine registers without
  collection-name collisions.

## Open questions

- None blocking. (MCP-server cwd behavior is a verification item, not a design unknown:
  discovery is cwd-based, and the plugin starts in the workspace root.)
