# Getting started

## 1. Install the framework

```bash
pip install second-brain-vault-framework
vault --version
```

Pure stdlib — no runtime dependencies, on purpose, so the same command works inside an air
gap. (Air-gapped install: see [Air-gapped install](air-gapped-install.md).)

## 2. Create a vault

```bash
vault scaffold "My Vault"
cd "My Vault"
```

You get:

```
CLAUDE.md            the schema + the rule to always ground answers in the vault
instructions.md      full build and air-gapped replication runbook
raw/  wiki/  index/  the three layers (empty, waiting for content)
tests/               VAULT_TESTS.md eval checklist — never indexed
scripts/             vault.py (CLI shim) · check_vault_answer.py
.claude/skills/      vault-setup · vault-ingest · vault-query · vault-lint
.vault-framework.json  which framework version built this vault
```

## 3. Register the search engines

Requires `qmd` on PATH (and `graphify` for graph queries).

```bash
python3 scripts/vault.py register
```

This adds `raw/`, `wiki/`, and `index/` as qmd collections and builds the index. `tests/` is
deliberately excluded — the T2 negative-control questions only prove anything if their gold
answers are not retrievable.

## 4. Add your first source

Drop a clipping (Obsidian Web Clipper output, or any markdown) into `raw/`, then:

```bash
python3 scripts/vault.py ingest "raw/My Article.md"
```

That stubs out the summary note, the source-registry row, and the log entry. The stubs carry
`<!-- TODO -->` markers, and `vault check` fails while any remain — so a half-finished ingest
can never look finished.

Fill the summary, then create one concept note per idea:

```bash
python3 scripts/vault.py new-note some-concept --source "raw/My Article.md"
```

## 5. Check before calling it done

```bash
python3 scripts/vault.py check
```

Fail-closed: non-zero on broken wikilinks, orphan notes, unreferenced clippings, missing log
entries, notes unreachable from the map of content, unfilled stubs, or framework drift.

## Doing all of this with Claude Code

Run Claude Code inside the vault and it loads `CLAUDE.md` plus the four `vault-*` skills.
Ask it to ingest a clipping and it runs the loop above, filling note bodies from the source —
that is the intended way to work. See [Working a vault](working-a-vault.md).
