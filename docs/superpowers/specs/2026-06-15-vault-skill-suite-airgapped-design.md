# Design — Vault skill suite for minimal, air-gapped models

> Date: 2026-06-15 · Status: approved (brainstorming) · Next: implementation plan
> Related: `instructions.md` (engine transfer runbook), `CLAUDE.md` (vault schema),
> `docs/superpowers/specs/2026-06-11-vault-improvements-and-eval-design.md` (prior pass)

## 1. Problem

The vault now has a solid schema (`CLAUDE.md`), a deterministic lint, a per-source
summary layer, and a manual eval harness. But the **operating instructions for an agent**
still live in a single user-level skill, `~/.claude/skills/obsidian_knowledge_graph_skill/`,
that is stale and partly broken:

- It predates the `CLAUDE.md` schema, the vault-grounding rule, `scripts/lint_vault.py`,
  the `eval/` harness, `wiki/sources/` summaries, and the air-gapped/minimal-model angle.
- Its `SKILL.md` frontmatter is malformed (no `---` delimiters), which hurts auto-triggering.
- It is generic prose that assumes a **capable** model can infer the whole procedure.

The target deployment is the opposite of that assumption: a **minimal, local model**
(e.g. MiniMax 2.7 behind Claude Code) in an **air-gapped** environment. A weak model is a
poor judge of open-ended work and unreliable at long multi-step reasoning, but it is fine at
running a named command and filling a clearly-marked blank.

## 2. Goals / non-goals

**Goals**
- Replace the stale skill with a **modular suite of focused, prescriptive skills**.
- Make the mechanical work **deterministic** (a CLI), so the model's surface area shrinks to
  the one irreducibly-LLM task: writing faithful note bodies.
- Add **validation that is safe on a weak model** — deterministic-first, **fail-closed**.
- Keep the whole thing **self-contained in the vault repo** so it travels as one unit.

**Non-goals (YAGNI)**
- **No agents / subagents** for orchestration (a weak model orchestrating subagents tends to
  do worse than running a tight script). graphify's own extraction subagent is unchanged.
- No new search/graph engines — reuse `qmd` and `graphify` as-is.
- The CLI does **not** re-implement graphify (extraction/labeling need the LLM); it only
  invokes the existing `/graphify` skill.
- No automated *content-correctness* grading by the weak model — that stays in the manual
  `eval/` harness.

## 3. Locked decisions

| Axis | Decision |
|------|----------|
| Deliverable shape | Modular skill suite (4 skills), **no agents** |
| Determinism | **Determinism-first**: a CLI does all mechanical work; model fills note bodies only |
| Location | **In the vault repo** — `<vault>/.claude/skills/` + `<vault>/scripts/`, committed |
| CLI shape | **Single `scripts/vault.py`**, pure stdlib, subcommand interface |
| Validation | 3 layers, deterministic-first, **fail-closed**, bounded model reactions |
| Old skill | Retire `obsidian_knowledge_graph_skill` → short deprecation pointer to the suite |
| Engine transfer | Stays in `instructions.md` Phase A bundle; `vault-setup` ties it together |

## 4. Architecture

A self-contained vault where deterministic code does the mechanical work and four thin
skills tell a weak model *which command to run and which blanks only it can fill*.

```
<vault>/
  CLAUDE.md                  # schema + grounding rule + STRICTNESS setting
  scripts/
    vault.py                 # single stdlib CLI (the deterministic engine)
    lint_vault.py            # existing lint (called by `vault check`)
  .claude/skills/
    vault-setup/SKILL.md     # bootstrap (incl. air-gapped) + register engines
    vault-ingest/SKILL.md    # raw -> stubs -> fill -> check -> graph
    vault-query/SKILL.md     # grounded answering (procedural side of the rule)
    vault-lint/SKILL.md      # run check, interpret findings, bounded fixes
  raw/ wiki/ index/ eval/
```

## 5. The CLI — `scripts/vault.py`

Pure Python stdlib (matches `lint_vault.py`), invoked as `py scripts\vault.py <cmd>` on
Windows or `python3 scripts/vault.py <cmd>` on macOS/Linux. `argparse` subcommands. Every
command validates its own output and exits non-zero with an actionable message.

| Subcommand | Behavior | LLM? |
|---|---|---|
| `scaffold <name>` | Stamp out the full layout above, including `CLAUDE.md`, `vault.py` itself, the four skills, and the `eval/` template. **Self-replicating; idempotent.** | No |
| `ingest raw/<file>.md` | Parse the clipping frontmatter (title/author/date/source); write the **one** `wiki/sources/<slug>.md` summary stub with **valid frontmatter and a `<!-- TODO: ... -->` body**; add the `index/source-registry.md` row; append the `index/log.md` entry; print the blanks to fill and instruct the model to create one concept note per durable concept via `new-note`. **Re-runnable** — never clobbers a filled note. | No |
| `new-note <slug> --source raw/<file>.md` | Create `wiki/<slug>.md` (concept) with **valid frontmatter (incl. `sources:`) and a `<!-- TODO -->` body** and a placeholder MOC link. The model decides *which* notes to create and their slugs; the CLI guarantees each is created *correctly*. Idempotent. | No |
| `check` | Run `lint_vault.py` **plus** a structural eval: every raw clipping has a summary + a log entry + is reachable from the MOC; no orphan notes; **no leftover `<!-- TODO -->` stubs**; frontmatter present/valid; wikilinks resolve. Exit code is the gate (0 = pass). | No |
| `register` | Add qmd collections `raw`/`wiki`/`index` (**never `eval/`**), then `qmd update && qmd embed`. | No |
| `status` | Per-raw-file table: stub-created / body-filled / registered / graphed. | No |

Design notes:
- `ingest` is the keystone for minimal models: it converts "write notes from scratch"
  (open-ended) into "fill these N marked blanks" (bounded). Frontmatter, provenance,
  registry, and log are all machine-written and therefore always correct.
- `check`'s **stub-completion checks** are a deterministic *proxy* for "did the model do its
  job": code cannot judge whether a body is *correct*, but it can prove a body was *written*
  (no TODO marker), is non-trivial (min length), and is well-formed (frontmatter + links).
- All commands are idempotent / re-runnable so a mid-run stop can be safely resumed.

## 6. The four skills

Each `SKILL.md` has **correct YAML frontmatter** (`---` delimited `name` + `description`),
is short and imperative, carries a TodoWrite-style checklist, and exposes two explicit
paths so capability is declared, not guessed.

- **`vault-setup`** — bootstrap a new or air-gapped vault: run `vault scaffold`, follow the
  `instructions.md` Phase A/B dependency runbook to install the engines, then `vault register`.
- **`vault-ingest`** — the ingest loop (see §7). Minimal/capable paths; fail-closed.
- **`vault-query`** — the procedural side of the `CLAUDE.md` grounding rule: qmd first,
  graphify for multi-hop, cite the note/raw source, and say explicitly when the vault does
  not cover the question (never fill the gap from training data).
- **`vault-lint`** — run `vault check`, interpret findings, apply only the whitelisted fixes.

Skill skeleton (every skill follows this shape):

```
## Minimal-model path (default)
1. Run: <exact command>
2. Fill ONLY the blanks it names.
3. Run: vault check
   - exit 0   -> done
   - exit !=0 -> do exactly what the message says, or STOP and report.
   Do NOT free-form "fix". Do NOT edit raw/.

## Capable-model path (opt-in)
   ...adds the Layer-3 faithfulness self-review before `vault check`.
```

The active path is governed by a `STRICTNESS` setting in `CLAUDE.md` (default `MINIMAL`),
which `vault scaffold` emits.

## 7. Data flow — ingest

```
raw/x.md (immutable)
  -> vault ingest raw/x.md        # summary stub + registry row + log entry (deterministic)
  -> model identifies the durable concepts in x.md
  -> vault new-note <slug> --source raw/x.md   # one per concept (deterministic stub)
  -> model fills ONLY named blanks (the summary + concept note bodies)
  -> [capable path only] faithfulness self-review (bounded; whitelist reactions)
  -> vault check                  # deterministic gate
       exit 0   -> continue
       exit !=0 -> whitelisted fix OR STOP + report
  -> /graphify . --update          # LLM extraction via existing skill
  -> vault register                # qmd collections + update + embed
  -> done
```

## 8. Validation model (the core safety design)

Three layers; only the safe ones are on by default. Principle: **a weak model is a bad judge
but a fine button-presser** — validation must be *deterministic code the model obeys*, not
*output the model eyeballs and "fixes."*

1. **CLI self-validation (deterministic, always on).** Each subcommand checks its own output
   and exits non-zero with an actionable message. The model reads only the exit code. Cannot
   degrade the result; can only catch breakage.
2. **Stub-completion checks (deterministic proxy, always on).** `vault check` flags leftover
   `<!-- TODO -->` placeholders, empty/malformed frontmatter, missing thesis line, unresolved
   wikilinks, under-length bodies — catching the most common minimal-model failures without
   any model judgment.
3. **Bounded faithfulness self-review (model, opt-in).** The one thing code cannot verify —
   whether the body is faithful to the source — is **off by default** for minimal models.
   When on, the model's allowed reactions to *any* failure are a fixed whitelist:
   (a) re-run the named fix command, (b) fill a specifically-named blank, or
   (c) **stop and report**. Never free-form fixes; never edit `raw/`.

**Fail closed.** If a weak model hits something it cannot resolve via the whitelist, it
**STOPS and hands back to the human** rather than pushing a broken vault to "done." A loud,
honest halt is strictly better than a confident wrong result. Validation therefore converts
*silent corruption* into a *visible stop* — it protects the result more on a weak model, not
less.

## 9. Testing strategy

Neither tier relies on a capable model.

- **CLI self-test (deterministic).** On a tiny throwaway fixture vault: `scaffold` →
  `ingest` a fixture clipping → fill stubs with canned text → `check` passes; then tamper one
  file (delete a log line / leave a TODO / break a wikilink) → `check` fails with the right
  message. This proves the deterministic layer regardless of which model runs it.
- **Manual `eval/` harness (content correctness).** The existing `eval/VAULT_TESTS.md`
  (T1 recall, T2 no-fabrication, T3 synthesis) runs after ingest. The weak model never grades
  itself; the human (or a separate capable session) runs the checklist.

## 10. Migration

- Retire `~/.claude/skills/obsidian_knowledge_graph_skill/`: replace its body with a short
  deprecation pointer to the in-repo `vault-*` suite (and fix the malformed frontmatter so the
  pointer itself triggers correctly). Its three reference files are superseded by `CLAUDE.md`
  + the new skills.
- Existing vaults adopt the suite by running `vault scaffold` in-place (idempotent — it adds
  the CLI + skills without touching `raw/` or filled notes).

## 11. Air-gapped transfer integration

The **vault repo is the transfer unit**: `vault.py`, the four skills, and `CLAUDE.md` are
committed, so copying/zipping the vault carries the entire operating manual. The **engines**
(qmd, graphify, embedding model, the `graphify` skill, the qmd plugin) still transfer via the
`instructions.md` Phase A staging bundle — `vault-setup` is the skill that walks an operator
(or agent) through tying the two together inside the air gap.

## 12. Risks / open questions

- **qmd cache path on Windows** is unverified (`%USERPROFILE%\.cache` vs `%LOCALAPPDATA%`);
  `vault register`/`vault-setup` must confirm via `qmd status` rather than assume.
- **graphify still needs the LLM**, so a truly minimal model may produce a thinner graph;
  acceptable — the graph is a synthesis aid, and qmd retrieval is the primary path.
- **Concept-note identification stays with the model.** `ingest` cannot know how many concept
  notes a clipping warrants, so it deterministically creates only the single source-summary
  stub; the model identifies the concepts and creates each via `vault new-note`. This keeps
  note *creation* deterministic (correct frontmatter/provenance every time) while leaving note
  *identification* — a genuinely-LLM judgment — to the model. A weak model that under- or
  over-splits is caught indirectly by the manual `eval/` harness, not by `vault check`.
```
