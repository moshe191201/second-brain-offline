# qmd OpenAI-Compatible Backend for the Air-Gapped Vault — Design

**Date:** 2026-07-09
**Status:** Approved pending spec review
**Fork working copy:** `~/Desktop/Code/qmd-api` (clone of `github.com/tobi/qmd`, at v2.6.3)

## Problem

The air-gapped vault deployment (see `instructions.md` Part 3) uses qmd for hybrid
search, but three failures block it inside the gap:

1. **No GPUs.** Most target machines cannot reasonably run qmd's local GGUF models
   (embeddinggemma-300M + a 1.7B query-expansion model + a 0.6B reranker on CPU).
2. **Native-module ABI breakage.** qmd depends on `better-sqlite3` and `sqlite-vec`
   (compiled native modules). Transferring qmd via git carries source but not
   binaries; inside the gap `npm install` cannot reach the registry, so the modules
   are missing or ABI-mismatched. This is also the root cause of the "qmd only works
   on Node 22" symptom — qmd itself supports Node ≥22, including the gap's Node 26.
3. **Unused infrastructure.** The gap has OpenAI-compatible endpoints
   (`/v1/embeddings`, `/v1/chat/completions`, `/v1/models`) serving an embeddings
   model, chat models, and a reranker model (served through chat/completions; there
   is **no** `/v1/rerank` endpoint). qmd cannot use any of it.

A hand-rolled Python embedding/search script works but is markedly worse than qmd
(no token-aware chunking, no hybrid fusion, no expansion/rerank, no MCP plugin).

## Decisions already made (with the user)

- **Approach:** fork qmd and add an OpenAI-compatible backend (Option A); rejected
  a pure-Python reimplementation (too much quality to rebuild) and stock-qmd-on-CPU
  (keeps the GPU pain).
- **Transfer path:** arbitrary tarballs may cross the gap (one-way inbound only —
  code written inside cannot come out; the in-gap prototype patch is re-implemented
  here, not reused).
- **Target platform:** Windows x64, Node 26. A connected Windows x64 + Node 26
  staging machine is available.
- **Feature scope:** full query pipeline via API — BM25 + vector + expansion/HyDE +
  rerank.
- **API details:** no `/v1/rerank`; reranker model invoked via chat/completions.
  API key field exists but is a dummy default — treat as optional.

## Architecture

Fork `github.com/tobi/qmd` at v2.6.3, branch `openai-backend`, developed and tested
on the connected macOS machine. Two changes only:

### 1. New backend: `src/llm-openai.ts`

Class `OpenAICompatLLM` implementing qmd's existing `LLM` interface
(`src/llm.ts` — `embed`, `embedBatch`, `generate`, `expandQuery`, `rerank`,
`modelExists`, `dispose`), using plain `fetch` (no new dependencies).

| Operation | Endpoint | Behavior |
|---|---|---|
| `embed` / `embedBatch` | `POST /v1/embeddings` | Native batching (API accepts arrays of inputs). |
| `generate` (HyDE) | `POST /v1/chat/completions` | Direct port. |
| `expandQuery` | `POST /v1/chat/completions` | Port upstream's expansion prompt (built for its fine-tuned 1.7B model) to a plain instruct prompt; parse the same `lex`/`vec`/`hyde` output structure. Parse failure → fall back to the raw query (an existing qmd code path). |
| `rerank` | `POST /v1/chat/completions` | Tiered, see below. |

**Rerank tiers** (each failure degrades to the next; search never dies):

1. `QMD_OPENAI_RERANK_MODEL` set → chat/completions against that model with the
   reranker's yes/no prompt format (Qwen3-Reranker style), requesting `logprobs`;
   score = P("yes"). If the server omits logprobs, parse the generated yes/no text.
2. No rerank model → pointwise relevance scoring with the regular chat model.
3. Failure → skip reranking; keep hybrid-fusion order.

**Tokenizer compromise:** qmd chunks documents at index time via the local model's
tokenizer (`tokenize`/`countTokens`/`detokenize`). The API backend has no local
tokenizer, so it chunks with a deterministic character-based estimate
(~4 chars/token, with a safety margin against the embedding model's context
limit). Chunk boundaries differ slightly from upstream; harmless because the index
is always built inside the gap by the same backend that queries it.

### 2. Backend selection seam

Introduce `getDefaultLLM()` returning `OpenAICompatLLM` when `QMD_LLM=openai`,
else the stock `LlamaCpp`. Replace the direct `getDefaultLlamaCpp()` call sites:

- `src/store.ts:85` (store LLM accessor) and the `llmOverride ?? getDefaultLlamaCpp()`
  sites (~store.ts:2772, 3737, 3912, 3958)
- `src/llm.ts:1915` (chunker)
- `src/cli/qmd.ts:3764` (device info for `qmd status`/`doctor` — see Error handling)

**Default stays `local`.** With `QMD_LLM` unset the fork behaves identically to
upstream — keeps rebases trivial and lets one artifact serve both worlds. Because
node-llama-cpp is lazily loaded, selecting `openai` means it is **never imported**:
no GPU probe, no GGUF models, no model-cache transfer.

### Configuration (env vars only)

```
QMD_LLM=openai                    # backend switch; unset/local = upstream behavior
QMD_OPENAI_BASE_URL=https://…/v1  # required when QMD_LLM=openai
QMD_OPENAI_API_KEY=…              # optional (endpoint accepts a dummy default)
QMD_OPENAI_EMBED_MODEL=<name>     # required
QMD_OPENAI_CHAT_MODEL=<name>      # required (expansion/HyDE/fallback rerank)
QMD_OPENAI_RERANK_MODEL=<name>    # optional (enables rerank tier 1)
QMD_OPENAI_TIMEOUT_MS=…           # optional (defaults: embed 60s/batch, chat 120s)
```

## Error handling & operations

- **Unreachable endpoint / non-200:** fail with a message naming the operation, the
  URL, and the env var to check — never a raw stack trace.
- **`qmd doctor` / `qmd status`:** when `QMD_LLM=openai`, replace the GPU/VRAM probe
  with a backend section — reports `backend: openai`, performs a live
  `GET /v1/models` reachability check, and verifies the configured model names
  appear in the list.
- **`qmd embed` resilience:** per-batch retry with backoff (3 attempts); chunks that
  still fail are reported and skipped; re-running `qmd embed` picks them up (qmd
  embeds only missing vectors — already incremental).
- **Query-time degradation:** expansion or rerank failure never kills a query;
  worst case is BM25 + vector with fusion order.

## Testing

1. **Unit tests** (in the fork, alongside upstream's suite): mocked `fetch` for all
   four operations, the rerank/expansion fallback chains, error mapping, and the
   char-based chunker.
2. **No-llama regression test:** with `QMD_LLM=openai`, run index + search + query
   in an install tree where `node_modules/node-llama-cpp` is renamed away. Proves
   the local runtime is never touched — the guarantee that "no GPU needed"
   survives future changes.
3. **Integration test (this Mac):** local OpenAI-compatible server (Ollama or
   LM Studio serving an embed + chat model); run the full vault workflow against
   this repo: `qmd collection add / update / embed / search / query`.
   Acceptance: the known-answer check from `instructions.md`
   (`qmd search "GRPO critic length bias"` → `grpo-and-variants.md` as top hit)
   passes via the API backend.
4. **Upstream suite still green with `QMD_LLM` unset** (protects rebasing).

## Packaging & air-gap delivery

On the connected Windows x64 + Node 26 staging machine:

1. Clone the fork; `npm install && npm run build`; `npm install -g .` — native
   modules are built/fetched for win32-x64 + Node 26 ABI (permanently fixes the
   better-sqlite3 breakage and the Node-22 symptom).
2. Smoke-test there: `qmd --version`; `qmd update` on a sample folder (BM25 needs
   no model); `qmd embed` with `QMD_LLM=openai` against a mock or real endpoint.
3. `tar czf qmd-install-tree.tgz -C "$(npm prefix -g)" .` and carry it in — the
   Phase A pattern from `instructions.md`, **minus `qmd-models.tgz`, which is no
   longer needed**.
4. Inside the gap: untar into the npm global prefix; set `QMD_OPENAI_*` env vars
   machine-wide; `qmd doctor` to verify; `python3 scripts/vault.py register`.

## Repo-side documentation updates (this vault)

- `instructions.md` Parts 2–3: add the API-backend variant — env-var table, staging
  steps without the models tarball, updated troubleshooting rows (ABI root cause).
- `.claude/skills/vault-setup/SKILL.md`: air-gapped bootstrap section gains the
  `QMD_OPENAI_*` env-var checklist and the `qmd doctor` verification step.

The fork lives in its own repo (`qmd-api`); this vault only documents consumption.

## Out of scope

- Upstreaming the backend to `tobi/qmd` (possible later; the seam is designed to
  make a PR easy, but not part of this effort).
- Any change to graphify (already API/host-LLM driven, no GPU dependency).
- Migrating existing in-gap indexes (embedding model changes → re-embed fresh;
  `qmd embed` inside the gap rebuilds vectors anyway).
- The Claude Code qmd plugin: unchanged — its MCP server runs `qmd mcp` from PATH,
  so it picks up the fork automatically.
