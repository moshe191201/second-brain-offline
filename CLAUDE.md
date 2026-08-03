# CLAUDE.md — Framework Repo

This repo is the **framework**, not a vault. A vault is a user-owned folder the framework
writes into. `example_vault/` is the one vault that lives here, as living documentation.

> Design specs: `docs/superpowers/specs/` · Plans: `docs/superpowers/plans/`
> Vault schema (for work *inside* a vault): `example_vault/CLAUDE.md`

## Layout

```
docs/                              mkdocs site — user guide + specs/plans
example_vault/                     a real vault, built by the current payload (CI-verified)
qmd-api/                           staging + install scripts for the qmd OpenAI-backend fork
src/second_brain_vault_framework/  the pip package
  ├── core.py                      every subcommand's implementation
  ├── cli.py                       `vault` entry point (argparse only)
  ├── manifest.json                what the framework owns in a vault + user-zone markers
  └── payload/                     the files laid down into a vault
tests/                             stdlib unittest suite for the package
```

## The one rule that explains the layout

**`payload/` is the source of truth; `example_vault/` is an artifact.**

Never edit a framework-owned file inside `example_vault/` directly. Edit it in
`src/second_brain_vault_framework/payload/`, then re-lay it:

```bash
vault upgrade example_vault
```

CI enforces this: the `example-vault` stage runs `vault check example_vault` and fails if
`vault upgrade` would produce a diff. A payload edit that isn't laid down is a broken build.

Which paths are framework-owned is defined in `manifest.json` — nowhere else. Adding a file
to the payload means adding it to `owned_paths` too, or `upgrade` will never install it.

## Path mapping

`payload/dot-claude/` → `.claude/` in the vault. The rename exists because packaging backends
skip dot-directories; `core.payload_path_for()` is the only place that translation happens.

## Conventions

- **Pure stdlib.** The CLI must run inside an air gap with nothing installed. No runtime deps
  in `pyproject.toml`, ever. Docs/build extras are fine.
- **Fail closed.** `vault check` exits non-zero on any finding. Never soften it to a warning.
- **`tests/VAULT_TESTS.md` in a vault is never a qmd collection** — gold answers must not
  contaminate retrieval. `core.cmd_register` deliberately omits it.
- Version lives in `pyproject.toml` and `__init__.__version__`; `manifest.json` carries a
  copy for the vault stamp. Bump all three together.

## Before calling work done

```bash
python -m unittest discover -s tests
vault check example_vault
```
