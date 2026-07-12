# Design — `vault-framework` package distribution & updates

> Status: approved for planning · Date: 2026-07-12
> Supersedes the hand-carried "vault control files" flow in `instructions.md` (Part 3 A6 / B5 / C1b).
> Companion doc: the "Distribution & updates" section of `instructions.md` (consumer/maintainer runbook).

## Problem

Today a consumer obtains the vault by `git clone` → `vault scaffold` → `git init` a new repo.
That **severs the umbilical to upstream**: framework files (`CLAUDE.md`, the `vault-*` skills,
`scripts/`) and the consumer's content (`raw/`, `wiki/`, `index/`) end up commingled in one git
history. Shipping a new framework version then requires consumers to know the internal structure
and manually diff/copy files — merge-conflict roulette. There is no clean update channel.

Additionally, the framework's source-of-truth (`scripts/templates/`, `scripts/vault.py`) lives
*inside* a live vault, so "the framework" and "a vault built with it" are the same repo.

## Goals

- A consumer can obtain, create, and update a vault with **no manual file copying** and **no
  knowledge of the framework's internal structure**.
- Framework updates ship as a **single versioned artifact** and apply with one command.
- **Framework and content are cleanly separated**: a consumer's git repo (if any) contains only
  their content.
- Works **fully air-gapped**: the update channel is an internal package index seeded by one
  one-way transfer per release.
- Framework files land at the **real paths** Claude Code and Obsidian require (`.claude/skills/`,
  root `CLAUDE.md`) — no symlinks.

## Non-goals

- Changing the qmd / graphify / Obsidian / local-LLM environment setup (rest of `instructions.md`
  Part 3 is unchanged).
- Cross-ecosystem packaging (npm). The CLI is Python; one PyPI/Artifactory package suffices.
- Three-way merge of consumer edits to framework files. The contract is read-only-by-convention
  with a marked user-zone; free-forking is not a supported workflow (safety net only, see below).

## Chosen approach

The framework becomes a **published, pip-installable package** (`vault-framework`) whose source
is a standalone GitLab repo. The installed package is the *tool + payload*; a **vault** is a
normal user-owned directory the tool writes into. Updates flow one-way to an internal index once
per release, then reach every consumer via `pip install --upgrade` over the LAN.

Rejected alternatives:
- **Git submodule** — puts framework files in a subfolder while Claude/Obsidian need real root
  paths; forces fragile symlinks/copies (Windows/Obsidian-hostile). Also error-prone for
  non-expert consumers.
- **Upstream remote + merge** — every update merges into a tree full of the user's content,
  interleaving histories and risking `CLAUDE.md` conflicts. Fights the clean-separation goal.

## Architecture

### Source repo (`vault-framework`, canonical on GitLab)

```
vault-framework/
├── pyproject.toml               # name = vault-framework, version = X.Y.Z (single source of version truth)
├── src/vault_framework/
│   ├── cli.py                   # `vault` entry point: scaffold / upgrade / check / ingest / new-note / register / status
│   ├── core.py                  # the current vault.py logic, refactored into an importable module
│   ├── manifest.json            # framework-owned paths + user-zone markers (see below)
│   └── payload/                 # files copied into a vault (package data via importlib.resources)
│       ├── CLAUDE.md
│       ├── instructions.md
│       ├── .claude/skills/vault-{ingest,lint,query,setup}/SKILL.md
│       ├── scripts/vault.py            # thin shim that calls into the installed package (self-contained vault)
│       ├── scripts/lint_vault.py
│       └── eval/VAULT_TESTS.md
└── tests/
```

### A consumer vault (a normal folder, created anywhere)

```
myvault/
├── CLAUDE.md  instructions.md  .claude/skills/  scripts/  eval/   ← framework-owned (laid-down copies)
├── raw/  wiki/  index/  graphify-out/  .obsidian/                 ← their content (never touched)
└── .vault-framework.json                                          ← stamp: {version, manifest, installed_at}
```

The **authoritative** CLI lives in the installed package (`site-packages`), *outside* any vault
— so the tool never overwrites itself mid-run. The vault carries laid-down copies of `scripts/`
so the in-vault skills stay self-contained; those copies are framework-owned artifacts that
`upgrade` replaces. The vault's `scripts/vault.py` is a thin shim that imports
`vault_framework.core` if installed, so behavior can't drift between the two.

## The manifest & ownership contract

`manifest.json` (shipped in the package; a copy stamped into each vault as `.vault-framework.json`)
is the single source of truth for what the framework owns.

```json
{
  "framework_version": "X.Y.Z",
  "owned_paths": [
    "CLAUDE.md", "instructions.md",
    ".claude/skills/vault-ingest/SKILL.md", ".claude/skills/vault-lint/SKILL.md",
    ".claude/skills/vault-query/SKILL.md", ".claude/skills/vault-setup/SKILL.md",
    "scripts/vault.py", "scripts/lint_vault.py",
    "eval/VAULT_TESTS.md"
  ],
  "user_zones": {
    "CLAUDE.md": { "start": "<!-- USER ZONE START -->", "end": "<!-- USER ZONE END -->" }
  }
}
```

| Tier | Paths | `upgrade` behavior |
|------|-------|--------------------|
| Framework-owned | `owned_paths` | Overwritten wholesale from payload. Read-only by convention. |
| User-zone | marked block(s) inside owned files | Extracted before overwrite, re-injected after — preserved verbatim. |
| Content | everything not in `owned_paths` | Never read, never touched. |

Edge cases:
- **Removed files** — `upgrade` diffs the vault's stamped manifest against the new package
  manifest and deletes only orphaned *framework-owned* files. Content is never a candidate.
- **Backup-on-drift** — if an on-disk framework file differs from the previous payload (consumer
  edited it), `upgrade` copies it to `.vault-framework-backup/<old-version>/` and reports it
  before overwriting. Nothing edited is silently lost.
- **User-zone absent** (older/hand-made vault) — if a vault's `CLAUDE.md` has no markers,
  `upgrade` inserts the block populated from any pre-existing "Vault-specific configuration"
  section if present, else empty; it never discards the file without backup.

## CLI commands

The existing subcommands (`scaffold`, `ingest`, `new-note`, `check`, `register`, `status`) are
preserved. New/changed:

- `vault scaffold <dir>` — create a new vault: copy payload to real paths, write
  `.vault-framework.json` stamp, create empty content dirs. (Replaces the current in-vault
  scaffold; now driven by the installed package's payload.)
- `vault upgrade <dir>` — re-lay framework-owned paths per manifest, preserve user-zones, handle
  removed-files + backup-on-drift, update the stamp. Idempotent.
- `vault check <dir>` — existing lint, plus assert `.vault-framework.json` version matches the
  installed package version and report drift (framework files edited on disk).

## Distribution / release pipeline

Consumer and maintainer runbooks (with air-gap path placeholders — `<INTERNAL_PIP_INDEX_URL>`,
`pip.ini`/`pip.conf` locations, `<GITLAB_BASE>`, upload endpoints) are documented in the
"Distribution & updates" section of `instructions.md` and are the canonical operator reference.

Summary:
1. Bump version in `pyproject.toml`; tag + push source to GitLab.
2. `python -m build` → wheel.
3. `airgap-pack dist/` → self-contained offline bundle (wheel + any deps not on the internal index).
4. One-way transfer; publish to internal PyPI/Artifactory (twine or `jf`).
5. Consumers: `pip install --upgrade vault-framework && vault upgrade <dir>`.

## Migration

- **Extract** the framework source out of the live "Moshe Vault" repo into the new
  `vault-framework` repo; refactor `scripts/vault.py` into `src/vault_framework/{cli,core}.py`;
  move `scripts/templates/*` into `src/vault_framework/payload/`.
- **The live "Moshe Vault"** becomes an ordinary consumer vault of the package (dogfood): install
  the package, run `vault upgrade .` against it, confirm no content changes.
- Existing hand-made vaults with no stamp: `vault upgrade` treats a missing
  `.vault-framework.json` as "unknown previous version" → backs up all framework files before
  overwriting, then writes a fresh stamp.

## Testing

- Unit: manifest parsing; user-zone extract/re-inject (present, absent, malformed markers);
  removed-file detection; backup-on-drift.
- Integration: `scaffold` into temp dir → assert real paths + stamp; edit content + user-zone →
  `upgrade` to a newer payload → assert content untouched, user-zone preserved, framework files
  updated, drifted file backed up.
- Air-gap smoke (reuse `airgap-pack` proof): build wheel → install from a local index with
  networking disabled → `scaffold` + `upgrade` succeed offline.

## Open questions (resolve during planning)

- Package name collision on the internal index? Confirm `vault-framework` is free / pick a
  namespaced name.
- Should `instructions.md` itself be framework-owned (overwritten) or split so consumer notes
  survive? Leaning framework-owned with a user-zone if needed.
- GitLab ownership model (central repo you control vs. per-team) — deferred; does not block the
  package design.
