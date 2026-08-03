# qmd-api

Getting the **OpenAI-backend fork of qmd** into an air-gapped, no-GPU environment that has an
internal OpenAI-compatible inference endpoint (`/v1/embeddings` + `/v1/chat/completions`).

Under this backend qmd loads no GGUF models — no `qmd-models.tgz` to carry, no GPU in the gap.

| File | Side of the gap | What it does |
|------|-----------------|--------------|
| [`QMD-API-STAGING.md`](QMD-API-STAGING.md) | connected staging machine | build the fork, prove the native modules match this ABI, capture the install tree |
| [`install-qmd-api.sh`](install-qmd-api.sh) | inside the gap | unpack that tree into the global npm prefix and verify it loads |

## The rule everything here follows

**Build once where there's real internet, then ship the already-compiled result.**

`better-sqlite3`'s install script is `prebuild-install || node-gyp rebuild`. Both halves need
network egress the gap doesn't have, even when Artifactory is reachable. `--ignore-scripts`
doesn't fix that — it turns a crash into a silent gap, because nothing produced
`build/Release/better_sqlite3.node` either way. A fresh `npm install` inside the gap
structurally cannot work; don't try to make it.

## Inside the gap

```bash
./install-qmd-api.sh qmd-install-tree.tgz
```

The script extracts, then checks the `qmd` binary and that `better-sqlite3` actually loads
under this machine's Node ABI — the check that catches a staging/target Node major mismatch
before it turns into a confusing runtime failure. Run `./install-qmd-api.sh --verify` to
re-run those checks against an existing install without touching it.

Then set the `QMD_OPENAI_*` env vars machine-wide, confirm `qmd doctor` shows the
`openai backend` check green, and register your vault's collections.

`QMD-API-STAGING.md` also documents the Artifactory variant, for orgs whose policy is that
everything installs *through* the registry rather than from a raw tarball.
