# Staging `qmd-api` for the air gap (Windows x64, Node 26)

Stage the OpenAI-backend fork of qmd for an air-gapped, **no-GPU** target that has an
internal OpenAI-compatible inference endpoint (`/v1/embeddings` + `/v1/chat/completions`).
Under this backend qmd loads **no GGUF models** — so there is no `qmd-models.tgz` to carry,
and no GPU is required in the gap.

Run every step on the **connected Windows x64 staging machine** (PowerShell 7+).

> ⚠ The staging machine **must match the target's OS, CPU architecture, and Node major
> version**. qmd's native modules (`better-sqlite3`, `sqlite-vec`) ship compiled per
> platform+ABI and are captured from this machine's install tree — a mismatch is exactly
> the `better_sqlite3.node ... compiled against a different Node.js version` failure the
> API-backend variant exists to avoid.

## 1. Prerequisites

```powershell
node --version   # must be 26.x (same major as the target)
git --version
```

## 2. Build and install the fork globally

```powershell
git clone <qmd-api fork url>
cd qmd-api
git checkout openai-backend
npm install
npm run build
npm install -g .
qmd --version    # prints the qmd version (2.6.x — the fork keeps upstream's version string)
```

## 3. Smoke-test without any model (BM25 only — proves the binary + native modules work)

```powershell
New-Item -ItemType Directory -Force $env:TEMP\qmd-smoke | Out-Null
'# hello world test note' | Out-File -Encoding utf8 $env:TEMP\qmd-smoke\test.md
qmd collection add $env:TEMP\qmd-smoke --name smoke
qmd update
qmd search "hello world" -n 1          # must return the note
```

`qmd search` (BM25) needs no model and never calls the API, so it works here even without
any `QMD_OPENAI_*` config — a clean check that the native SQLite modules are intact.

## 4. Prove the native modules match this ABI

```powershell
$root = npm prefix -g
node -e "require('$root\node_modules\@tobilu\qmd\node_modules\better-sqlite3'); console.log('better-sqlite3 OK')"
```

(If the path differs, resolve it with `npm ls -g @tobilu/qmd`.) A clean `OK` here is what
guarantees the transferred tree will load in the gap.

## 5. Capture the install tree

```powershell
tar czf qmd-install-tree.tgz -C "$(npm prefix -g)" .
```

## 6. Transfer manifest

- `qmd-install-tree.tgz` — **the only qmd artifact needed.**
- **No `qmd-models.tgz`** — the OpenAI backend loads no local models.

## 7. Inside the gap (see `instructions.md` → Phase B variant)

```powershell
tar xzf qmd-install-tree.tgz -C "$(npm prefix -g)"
qmd --version
```

Set the backend env vars **machine-wide** (Windows system environment, or a login profile):

```
QMD_LLM=openai
QMD_OPENAI_BASE_URL=https://<internal-endpoint>/v1
QMD_OPENAI_EMBED_MODEL=<embeddings model name>
QMD_OPENAI_CHAT_MODEL=<chat model name>
QMD_OPENAI_RERANK_MODEL=<reranker model name>   # optional
QMD_OPENAI_API_KEY=<key>                         # optional
```

> **Model names must match the endpoint's `/v1/models` list exactly**, including any tag
> suffix (e.g. some servers list `nomic-embed-text:latest`, not `nomic-embed-text`).
> `qmd doctor` cross-checks the configured names against that list and flags any mismatch.

Verify:

```powershell
qmd doctor    # the "openai backend" check must be green: reachable + all configured models present
```

A failing `openai backend` check names the cause — missing `QMD_OPENAI_*` env, an unreachable
`QMD_OPENAI_BASE_URL`, or a model name absent from `/v1/models` — with the fix in the next
step line. Once it's green, proceed to `python3 scripts/vault.py register` per the vault-setup
skill's air-gapped bootstrap.
