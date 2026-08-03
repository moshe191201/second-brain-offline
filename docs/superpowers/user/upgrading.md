# Upgrading the framework

```bash
pip install --upgrade second-brain-vault-framework
vault upgrade <your-vault>
```

Idempotent — running it twice changes nothing the second time.

## What upgrade owns

`manifest.json`, shipped inside the package and stamped into each vault as
`.vault-framework.json`, is the single source of truth for what the framework owns.

| Tier | Paths | On upgrade |
|------|-------|------------|
| **Framework-owned** | `CLAUDE.md`, `instructions.md`, `.claude/skills/vault-*/SKILL.md`, `scripts/vault.py`, `scripts/check_vault_answer.py`, `tests/VAULT_TESTS.md` | Overwritten wholesale from the payload. Read-only by convention. |
| **User zone** | the marked block inside `CLAUDE.md` | Extracted before the overwrite, re-injected after — preserved verbatim. |
| **Content** | everything else: `raw/`, `wiki/`, `index/`, `graphify-out/`, `.obsidian/`, `.qmd/` | Never read, never written. |

Content is not "carefully merged" — it is never touched at all. That is the property the whole
design exists to guarantee, and it is why the framework ships as a package instead of a git
remote you merge from.

## The user zone

One editable region survives upgrades, at the bottom of `CLAUDE.md`:

```markdown
<!-- USER ZONE START -->
Your vault-specific conventions, domain notes, and local overrides go here.
<!-- USER ZONE END -->
```

Put vault-specific configuration there and nowhere else in the file. Anything you write
outside the markers is a framework-owned line and will be replaced.

`instructions.md` has **no** user zone by design. The `vault-*` skills gate on reading it
before acting, so it must never be stale or hand-edited — the canonical version always wins.

## If you edited a framework file anyway

Nothing is silently lost. Before overwriting, `upgrade` compares each framework file against
the payload it shipped with; anything that differs is copied to
`.vault-framework-backup/<old-version>/` and reported by name. You get the new version and
your old file, and you decide what to carry across — usually by moving it into the user zone.

## Removed files

If a release stops shipping a framework file, `upgrade` deletes it from your vault — but only
by diffing your vault's **stamped manifest** against the new one. It never scans the
filesystem for deletion candidates, so a content file can't be caught by that pass no matter
what it's named.

## Vaults with no stamp

A hand-made vault, or one predating stamping, has no `.vault-framework.json`. That's treated
as "unknown previous version": every framework file is backed up before being overwritten,
then a fresh stamp is written. It is never an error.

## Checking for drift

```bash
vault check <your-vault>
```

Beyond the structural lint, `check` compares the vault's stamped version against the installed
package and fails if they differ — so "I upgraded the package but forgot to upgrade the vault"
surfaces as a failing check rather than as confusing behavior weeks later.
