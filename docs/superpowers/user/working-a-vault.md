# Working a vault

A vault carries its own operating manual. Running Claude Code inside one loads its
`CLAUDE.md` and four skills, each backed by the deterministic CLI.

| Skill | Use it to | CLI it wraps |
|-------|-----------|--------------|
| **vault-setup** | create or air-gap-bootstrap a vault | `vault scaffold`, `vault register` |
| **vault-ingest** | turn a new `raw/` clipping into notes | `vault ingest`, `vault new-note` |
| **vault-query** | answer a question, grounded and cited | qmd / graphify |
| **vault-lint** | health-check before calling work done | `vault check` |

The split is deliberate: the CLI does everything mechanical and verifiable, the model does
only the part that needs judgment — writing note bodies from sources.

## Ingest

1. Search first (`qmd search "<title keywords>" -n 5`) — the goal is to **update an existing
   note**, not spawn a near-duplicate.
2. `vault ingest raw/<clipping>.md` stubs the summary, the registry row, and the log entry.
3. Fill `wiki/sources/<slug>.md`, then `vault new-note <slug> --source raw/<clipping>.md` per
   distinct idea. One concept per note.
4. Link the new notes from `index/_map-of-content.md`.
5. `vault check` must exit 0.
6. `qmd update && qmd embed`, then `graphify raw/ --update`.

## Query — the grounding rule

The rule that makes a vault trustworthy is in `CLAUDE.md`, and it is absolute:

> When asked any question this vault could plausibly cover, consult the vault before
> answering — never answer from prior knowledge alone. If the vault does not cover it, say so
> explicitly. Do not fill the gap from training data.

In practice: `qmd search` for keywords, `qmd query` (intent/lex/vec) for conceptual questions,
`graphify query` for multi-hop, `qmd get "#docid"` to read the full document before making a
claim, and a citation on every claim.

**Write-back:** if answering produced genuinely new cross-source synthesis, save it as
`wiki/<slug>.md` with `type: analysis`, list the source notes in `sources:`, link it from the
map of content's Analyses section, and log it. Otherwise the insight is lost when the session
ends.

## Lint

```bash
python3 scripts/vault.py check
```

Seven structural checks — broken wikilinks, orphan notes, unreferenced clippings, missing
`sources:` frontmatter, missing log entries, notes unreachable from the map of content,
duplicate stems — plus unfilled stubs and framework drift. All fail-closed.

When it fails and the fix isn't obvious inside the skill's whitelist, the instruction is to
**stop and report**, not to improvise. A vault that reports "done" while broken is worse than
one that reports failure.

## Evaluating whether it actually works

`tests/VAULT_TESTS.md` is the eval checklist: T0 lint, T1 known-answer, T2 negative controls,
T3 cross-source synthesis, T4 engine smoke tests, T5 incremental ingest.

T2 is the one that matters most. It asks about topics verified absent from the corpus, and
any fabricated answer fails the whole group — that is the direct test of the grounding rule.

`scripts/check_vault_answer.py` grades a recorded answer against the gold rows:

```bash
python3 scripts/check_vault_answer.py --list
python3 scripts/check_vault_answer.py T1 3 --answer answer.md
```

Citation and negative-control checks are deterministic and gate the exit code. The gold-fact
comparison is reported for you to judge by reading — paraphrase is legitimate, and a token
overlap score cannot decide that.
