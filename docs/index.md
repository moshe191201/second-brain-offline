# Second Brain Vault Framework

An AI-operable knowledge vault that turns raw source clippings into atomic, cross-linked
notes — searchable, traversable, and grounded. Built to run fully offline, including
air-gapped, on minimal local models.

## Framework vs. vault

The **framework** is a pip package. A **vault** is a normal folder you own.

```bash
pip install second-brain-vault-framework
vault scaffold "My Vault"
```

The package lays framework files into the vault and replaces them wholesale on upgrade.
Your `raw/`, `wiki/`, and `index/` are never read or written by it.

## Three layers

| Layer | Folder | Rule |
|-------|--------|------|
| Source | `raw/` | Immutable clippings — the evidence layer |
| Knowledge | `wiki/` | Atomic concept notes, one idea each |
| Navigation | `index/` | Map of content, source registry, log, key takeaways |

`tests/` holds the eval checklist and is never indexed — gold answers must not contaminate
retrieval.

## Two engines, both local

- **qmd** — hybrid BM25 + vector search. *"Find me the note about X."*
- **graphify** — entity/relationship knowledge graph. *"How does X relate to Y?"*

## Where to go next

- [Getting started](superpowers/user/getting-started.md) — install, scaffold, first ingest
- [Working a vault](superpowers/user/working-a-vault.md) — the ingest / query / lint loop
- [Air-gapped install](superpowers/user/air-gapped-install.md) — one boundary crossing per release
- [Upgrading the framework](superpowers/user/upgrading.md) — what upgrade touches, and what it never touches

Design specs and implementation plans for each change are under **Design specs** and
**Implementation plans** in the nav.
