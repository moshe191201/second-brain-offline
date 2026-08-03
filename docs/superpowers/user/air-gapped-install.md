# Air-gapped install

The framework is designed around **one boundary crossing per release**, after which everything
inside the gap is a normal `pip install` over the LAN.

`example_vault/instructions.md` is the canonical, step-by-step runbook — it is shipped inside
every vault and is the operator reference. This page is the map of it.

## Why the framework has no dependencies

`vault` is pure stdlib. That is a hard constraint, not a preference: a CLI with a dependency
tree needs that tree resolvable inside the gap, and every added package is another artifact to
transfer and another version to keep in sync. The one thing that must always work — laying
down and checking a vault — works with nothing but Python.

## Per release: staging side

1. Bump the version in `pyproject.toml`, `__init__.__version__`, and `manifest.json`; tag and
   push.
2. `python -m build` → wheel.
3. `airgap-pack dist/` → a self-contained offline bundle (wheel + anything not already on the
   internal index).
4. One-way transfer.
5. Publish to the internal PyPI/Artifactory (`twine` or `jf`).

## Per release: gap side

```bash
pip install --upgrade second-brain-vault-framework
vault upgrade <your-vault>
```

That is the whole update path. No cloning, no copying files by hand, no knowledge of the
framework's internal structure. See [Upgrading](upgrading.md) for exactly what `upgrade`
touches.

## The engines

The vault CLI is only one of the artifacts that has to cross. The other two:

**qmd** — search. Native modules (`better-sqlite3`, `sqlite-vec`) are compiled per
platform+ABI, so the staging machine must match the target's OS, CPU architecture, and Node
major version. `qmd-api/` covers the OpenAI-backend fork, which is the right choice when the
gap has an internal OpenAI-compatible endpoint and no GPU: it loads no local GGUF models, so
there is no multi-hundred-megabyte model tarball to carry.

**graphify** — the knowledge graph. Ships as Python wheels; vendor them the same way.

The one rule both share: **build once where there's real internet, then ship the
already-compiled result.** A fresh `npm install` inside the gap cannot succeed, and
`--ignore-scripts` doesn't fix it — it converts a loud failure into a silent one. See
[`qmd-api/README.md`](https://gitlab.example.com/) in the repo for the full explanation.

## Verifying the bootstrap

```bash
python3 scripts/vault.py check   # must exit 0
qmd collection list              # tests/ must NOT appear
qmd doctor                       # openai backend check green, if using the API fork
```

Then run the `tests/VAULT_TESTS.md` checklist (T0–T4) for a behavioral check rather than a
structural one. A vault that lints clean but hallucinates on T2 is not bootstrapped.
