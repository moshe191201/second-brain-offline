# qmd OpenAI-Compatible Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an OpenAI-compatible API backend to the qmd fork so the air-gapped vault can run qmd's full hybrid search (embed, expand, HyDE, rerank) against internal `/v1/embeddings` + `/v1/chat/completions` endpoints, with no local GGUF models and no GPU.

**Architecture:** New `src/llm-openai.ts` implements qmd's `LLM` interface over `fetch`; a `getDefaultLLM()` seam in `src/llm.ts` selects it when `QMD_LLM=openai`, else returns the stock `LlamaCpp` (upstream-identical default). Shared parsing helpers move to `src/llm-shared.ts` to avoid an import cycle. Fail-fast: API failures throw `OpenAIBackendError` after bounded retries — never degrade, never fall back to local models.

**Tech Stack:** TypeScript (Node ≥22, ESM), vitest, plain `fetch` (no new dependencies). Two repos: the fork at `/Users/moshe/Desktop/Code/qmd-api` (all code tasks) and the vault at `/Users/moshe/Desktop/Code/Moshe Vault` (docs tasks 11, 13).

**Spec:** `docs/superpowers/specs/2026-07-09-qmd-openai-backend-design.md`

**Conventions for every code task below:**
- Working directory: `/Users/moshe/Desktop/Code/qmd-api`, branch `openai-backend`.
- Test runner: `npx vitest run <file> --reporter=verbose` (CI=true is fine — the OpenAI backend deliberately has NO CI-mode guard; LlamaCpp's `_ciMode` guard exists to block accidental local-model loads in CI, which cannot happen with mocked `fetch`).
- The `LLM` interface, option/result types (`EmbedOptions`, `EmbeddingResult`, `GenerateOptions`, `GenerateResult`, `ModelInfo`, `Queryable`, `QueryType`, `RerankDocument`, `RerankOptions`, `RerankResult`) all live in `src/llm.ts` and are imported **type-only** from `src/llm-openai.ts`. Runtime imports flow one way: `llm.ts` → `llm-openai.ts` → `llm-shared.ts`. Never add a runtime import from `llm-openai.ts` or `llm-shared.ts` back into `llm.ts`.

---

### Task 1: Branch and baseline

**Files:** none (git + verification only)

- [ ] **Step 1: Create the branch**

```bash
cd /Users/moshe/Desktop/Code/qmd-api
git checkout -b openai-backend
node --version   # expect v26.x
npm install      # ensure node_modules is complete for this Node ABI
```

- [ ] **Step 2: Build and record the test baseline**

```bash
npm run build
npx vitest run --reporter=dot 2>&1 | tail -20
```

Expected: build succeeds; note any pre-existing failures (model-dependent tests may skip under CI=true). Everything green now must stay green at the end.

---

### Task 2: `src/llm-shared.ts` — backend switch + shared expansion parser

**Files:**
- Create: `src/llm-shared.ts`
- Modify: `src/llm.ts:1507-1542` (LlamaCpp.expandQuery — replace inline parsing), plus one import and one re-export
- Test: `test/llm-shared.test.ts` (create)

- [ ] **Step 1: Write the failing test**

```typescript
// test/llm-shared.test.ts
import { describe, test, expect, afterEach, vi } from "vitest";
import { isOpenAIBackend, parseExpansionLines } from "../src/llm-shared.js";

afterEach(() => vi.unstubAllEnvs());

describe("isOpenAIBackend", () => {
  test("false when QMD_LLM is unset", () => {
    vi.stubEnv("QMD_LLM", "");
    expect(isOpenAIBackend()).toBe(false);
  });
  test("true for QMD_LLM=openai (case/space tolerant)", () => {
    vi.stubEnv("QMD_LLM", " OpenAI ");
    expect(isOpenAIBackend()).toBe(true);
  });
  test("false for QMD_LLM=local", () => {
    vi.stubEnv("QMD_LLM", "local");
    expect(isOpenAIBackend()).toBe(false);
  });
});

describe("parseExpansionLines", () => {
  test("parses lex/vec/hyde lines", () => {
    const out = parseExpansionLines(
      "lex: kv cache memory\nvec: how the kv cache reduces recomputation\nhyde: The KV cache stores attention keys.",
      "kv cache", true);
    expect(out).toEqual([
      { type: "lex", text: "kv cache memory" },
      { type: "vec", text: "how the kv cache reduces recomputation" },
      { type: "hyde", text: "The KV cache stores attention keys." },
    ]);
  });
  test("drops lines sharing no term with the query", () => {
    const out = parseExpansionLines("lex: kv cache\nvec: unrelated bananas", "kv cache", true);
    expect(out).toEqual([{ type: "lex", text: "kv cache" }]);
  });
  test("drops unknown types and junk lines", () => {
    const out = parseExpansionLines("foo: kv cache\nno colon here\nvec: kv cache basics", "kv cache", true);
    expect(out).toEqual([{ type: "vec", text: "kv cache basics" }]);
  });
  test("excludes lex when includeLexical=false", () => {
    const out = parseExpansionLines("lex: kv cache\nvec: kv cache basics", "kv cache", false);
    expect(out).toEqual([{ type: "vec", text: "kv cache basics" }]);
  });
  test("returns fallback set when nothing parseable", () => {
    const out = parseExpansionLines("total garbage", "kv cache", true);
    expect(out).toEqual([
      { type: "hyde", text: "Information about kv cache" },
      { type: "lex", text: "kv cache" },
      { type: "vec", text: "kv cache" },
    ]);
  });
  test("fallback respects includeLexical=false", () => {
    const out = parseExpansionLines("", "kv cache", false);
    expect(out.map(q => q.type)).toEqual(["hyde", "vec"]);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run test/llm-shared.test.ts --reporter=verbose`
Expected: FAIL — cannot resolve `../src/llm-shared.js`.

- [ ] **Step 3: Create `src/llm-shared.ts`**

```typescript
/**
 * llm-shared.ts - Backend-agnostic LLM helpers shared by the llama.cpp and
 * OpenAI-compatible backends.
 *
 * IMPORTANT: only `import type` from llm.ts is allowed here (runtime imports
 * would create a cycle: llm.ts imports llm-openai.ts which imports this file).
 */
import type { Queryable, QueryType } from "./llm.js";

/** True when the OpenAI-compatible API backend is selected via QMD_LLM=openai. */
export function isOpenAIBackend(): boolean {
  return (process.env.QMD_LLM ?? "").trim().toLowerCase() === "openai";
}

/**
 * Parse "type: text" query-expansion lines into Queryables, filtering
 * hallucinated lines that share no term with the original query. Returns the
 * standard fallback set when nothing parseable survives.
 * (Extracted verbatim from LlamaCpp.expandQuery so both backends share it.)
 */
export function parseExpansionLines(result: string, query: string, includeLexical: boolean): Queryable[] {
  const lines = result.trim().split("\n");
  const queryLower = query.toLowerCase();
  const queryTerms = queryLower.replace(/[^a-z0-9\s]/g, " ").split(/\s+/).filter(Boolean);

  const hasQueryTerm = (text: string): boolean => {
    const lower = text.toLowerCase();
    if (queryTerms.length === 0) return true;
    return queryTerms.some(term => lower.includes(term));
  };

  const queryables: Queryable[] = lines.map(line => {
    const colonIdx = line.indexOf(":");
    if (colonIdx === -1) return null;
    const type = line.slice(0, colonIdx).trim();
    if (type !== 'lex' && type !== 'vec' && type !== 'hyde') return null;
    const text = line.slice(colonIdx + 1).trim();
    if (!hasQueryTerm(text)) return null;
    return { type: type as QueryType, text };
  }).filter((q): q is Queryable => q !== null);

  const filtered = includeLexical ? queryables : queryables.filter(q => q.type !== 'lex');
  if (filtered.length > 0) return filtered;

  const fallback: Queryable[] = [
    { type: 'hyde', text: `Information about ${query}` },
    { type: 'lex', text: query },
    { type: 'vec', text: query },
  ];
  return includeLexical ? fallback : fallback.filter(q => q.type !== 'lex');
}
```

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run test/llm-shared.test.ts --reporter=verbose`
Expected: PASS (10 tests).

- [ ] **Step 5: Refactor `LlamaCpp.expandQuery` to use the shared parser**

In `src/llm.ts`, add to the top-of-file imports (near line 73, after the `fs` import):

```typescript
import { isOpenAIBackend, parseExpansionLines } from "./llm-shared.js";
```

And at the bottom of the file, re-export for consumers:

```typescript
export { isOpenAIBackend, parseExpansionLines } from "./llm-shared.js";
```

Then inside `expandQuery` (currently `src/llm.ts:1507-1536`), replace this block:

```typescript
      const lines = result.trim().split("\n");
      const queryLower = query.toLowerCase();
      const queryTerms = queryLower.replace(/[^a-z0-9\s]/g, " ").split(/\s+/).filter(Boolean);

      const hasQueryTerm = (text: string): boolean => {
        const lower = text.toLowerCase();
        if (queryTerms.length === 0) return true;
        return queryTerms.some(term => lower.includes(term));
      };

      const queryables: Queryable[] = lines.map(line => {
        const colonIdx = line.indexOf(":");
        if (colonIdx === -1) return null;
        const type = line.slice(0, colonIdx).trim();
        if (type !== 'lex' && type !== 'vec' && type !== 'hyde') return null;
        const text = line.slice(colonIdx + 1).trim();
        if (!hasQueryTerm(text)) return null;
        return { type: type as QueryType, text };
      }).filter((q): q is Queryable => q !== null);

      // Filter out lex entries if not requested
      const filtered = includeLexical ? queryables : queryables.filter(q => q.type !== 'lex');
      if (filtered.length > 0) return filtered;

      const fallback: Queryable[] = [
        { type: 'hyde', text: `Information about ${query}` },
        { type: 'lex', text: query },
        { type: 'vec', text: query },
      ];
      return includeLexical ? fallback : fallback.filter(q => q.type !== 'lex');
```

with:

```typescript
      return parseExpansionLines(result, query, includeLexical);
```

- [ ] **Step 6: Typecheck + full suite still green**

Run: `npm run build && npx vitest run --reporter=dot 2>&1 | tail -5`
Expected: build OK, same pass/fail counts as the Task 1 baseline plus the new file.

- [ ] **Step 7: Commit**

```bash
git add src/llm-shared.ts src/llm.ts test/llm-shared.test.ts
git commit -m "refactor: extract backend-agnostic expansion parsing + QMD_LLM backend switch helper"
```

---

### Task 3: Model resolution + embedding formatting honor the openai backend

**Files:**
- Modify: `src/llm.ts:94-114` (formatQueryForEmbedding / formatDocForEmbedding), `src/llm.ts:273-283` (resolveEmbedModel / resolveGenerateModel / resolveRerankModel)
- Test: `test/llm-openai-resolution.test.ts` (create)

- [ ] **Step 1: Write the failing test**

```typescript
// test/llm-openai-resolution.test.ts
import { describe, test, expect, afterEach, vi } from "vitest";
import {
  resolveEmbedModel, resolveGenerateModel, resolveRerankModel,
  formatQueryForEmbedding, formatDocForEmbedding,
} from "../src/llm.js";

afterEach(() => vi.unstubAllEnvs());

function stubOpenAIEnv() {
  vi.stubEnv("QMD_LLM", "openai");
  vi.stubEnv("QMD_OPENAI_EMBED_MODEL", "my-embed");
  vi.stubEnv("QMD_OPENAI_CHAT_MODEL", "my-chat");
}

describe("model resolution under QMD_LLM=openai", () => {
  test("resolveEmbedModel returns the openai embed model", () => {
    stubOpenAIEnv();
    expect(resolveEmbedModel()).toBe("my-embed");
  });
  test("resolveGenerateModel returns the openai chat model", () => {
    stubOpenAIEnv();
    expect(resolveGenerateModel()).toBe("my-chat");
  });
  test("resolveRerankModel prefers QMD_OPENAI_RERANK_MODEL, falls back to chat model", () => {
    stubOpenAIEnv();
    expect(resolveRerankModel()).toBe("my-chat");
    vi.stubEnv("QMD_OPENAI_RERANK_MODEL", "my-reranker");
    expect(resolveRerankModel()).toBe("my-reranker");
  });
  test("openai resolution ignores config/local env overrides", () => {
    stubOpenAIEnv();
    vi.stubEnv("QMD_EMBED_MODEL", "hf:local/model.gguf");
    expect(resolveEmbedModel({ embed: "hf:cfg/model.gguf" })).toBe("my-embed");
  });
  test("unset openai model names resolve to a visible placeholder", () => {
    vi.stubEnv("QMD_LLM", "openai");
    expect(resolveEmbedModel()).toBe("unset (QMD_OPENAI_EMBED_MODEL)");
    expect(resolveGenerateModel()).toBe("unset (QMD_OPENAI_CHAT_MODEL)");
  });
  test("local resolution is unchanged when QMD_LLM is unset", () => {
    vi.stubEnv("QMD_LLM", "");
    expect(resolveEmbedModel({ embed: "hf:cfg/model.gguf" })).toBe("hf:cfg/model.gguf");
  });
});

describe("embedding formatting under QMD_LLM=openai", () => {
  test("query text is passed through raw", () => {
    stubOpenAIEnv();
    expect(formatQueryForEmbedding("kv cache")).toBe("kv cache");
  });
  test("doc text is raw, title prepended when present", () => {
    stubOpenAIEnv();
    expect(formatDocForEmbedding("body text")).toBe("body text");
    expect(formatDocForEmbedding("body text", "My Title")).toBe("My Title\nbody text");
  });
  test("gemma-style formatting is unchanged when QMD_LLM is unset", () => {
    vi.stubEnv("QMD_LLM", "");
    expect(formatQueryForEmbedding("kv cache", "hf:ggml-org/embeddinggemma-300M-GGUF/x.gguf"))
      .toBe("task: search result | query: kv cache");
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run test/llm-openai-resolution.test.ts --reporter=verbose`
Expected: FAIL — openai cases return gguf defaults / gemma-formatted strings.

- [ ] **Step 3: Implement**

In `src/llm.ts`, replace the three resolvers (lines 273-283):

```typescript
export function resolveEmbedModel(config?: ModelResolutionConfig): string {
  if (isOpenAIBackend()) {
    return process.env.QMD_OPENAI_EMBED_MODEL?.trim() || "unset (QMD_OPENAI_EMBED_MODEL)";
  }
  return config?.embed || process.env.QMD_EMBED_MODEL || DEFAULT_EMBED_MODEL;
}

export function resolveGenerateModel(config?: ModelResolutionConfig): string {
  if (isOpenAIBackend()) {
    return process.env.QMD_OPENAI_CHAT_MODEL?.trim() || "unset (QMD_OPENAI_CHAT_MODEL)";
  }
  return config?.generate || process.env.QMD_GENERATE_MODEL || DEFAULT_GENERATE_MODEL;
}

export function resolveRerankModel(config?: ModelResolutionConfig): string {
  if (isOpenAIBackend()) {
    return process.env.QMD_OPENAI_RERANK_MODEL?.trim()
      || process.env.QMD_OPENAI_CHAT_MODEL?.trim()
      || "unset (QMD_OPENAI_CHAT_MODEL)";
  }
  return config?.rerank || process.env.QMD_RERANK_MODEL || DEFAULT_RERANK_MODEL;
}
```

And add the openai branch at the top of both format functions (lines 94-114):

```typescript
export function formatQueryForEmbedding(query: string, modelUri?: string): string {
  if (isOpenAIBackend()) return query;
  const uri = modelUri ?? resolveEmbedModel();
  if (isQwen3EmbeddingModel(uri)) {
    return `Instruct: Retrieve relevant documents for the given query\nQuery: ${query}`;
  }
  return `task: search result | query: ${query}`;
}

export function formatDocForEmbedding(text: string, title?: string, modelUri?: string): string {
  if (isOpenAIBackend()) return title ? `${title}\n${text}` : text;
  const uri = modelUri ?? resolveEmbedModel();
  if (isQwen3EmbeddingModel(uri)) {
    // Qwen3-Embedding: documents are raw text, no task prefix
    return title ? `${title}\n${text}` : text;
  }
  return `title: ${title || "none"} | text: ${text}`;
}
```

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run test/llm-openai-resolution.test.ts test/llm.test.ts --reporter=verbose`
Expected: new tests PASS; existing llm tests unchanged.

- [ ] **Step 5: Commit**

```bash
git add src/llm.ts test/llm-openai-resolution.test.ts
git commit -m "feat: resolve model names and embedding formats from QMD_OPENAI_* under the openai backend"
```

---

### Task 4: `src/llm-openai.ts` — config, error type, request core, embeddings

**Files:**
- Create: `src/llm-openai.ts`
- Test: `test/llm-openai.test.ts` (create)

- [ ] **Step 1: Write the failing test**

```typescript
// test/llm-openai.test.ts
import { describe, test, expect, afterEach, beforeEach, vi } from "vitest";
import {
  OpenAICompatLLM, OpenAIBackendError, readOpenAIConfigFromEnv,
} from "../src/llm-openai.js";

const CFG = {
  baseUrl: "http://gap-api/v1",
  embedModel: "my-embed",
  chatModel: "my-chat",
} as const;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status, headers: { "content-type": "application/json" },
  });
}

beforeEach(() => vi.useRealTimers());
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("readOpenAIConfigFromEnv", () => {
  test("reads a complete config, trimming and stripping trailing slash", () => {
    vi.stubEnv("QMD_OPENAI_BASE_URL", "http://gap-api/v1/");
    vi.stubEnv("QMD_OPENAI_EMBED_MODEL", " my-embed ");
    vi.stubEnv("QMD_OPENAI_CHAT_MODEL", "my-chat");
    vi.stubEnv("QMD_OPENAI_API_KEY", "");
    const cfg = readOpenAIConfigFromEnv();
    expect(cfg.baseUrl).toBe("http://gap-api/v1");
    expect(cfg.embedModel).toBe("my-embed");
    expect(cfg.apiKey).toBeUndefined();
  });
  test("throws naming every missing env var", () => {
    vi.stubEnv("QMD_OPENAI_BASE_URL", "");
    vi.stubEnv("QMD_OPENAI_EMBED_MODEL", "");
    vi.stubEnv("QMD_OPENAI_CHAT_MODEL", "");
    expect(() => readOpenAIConfigFromEnv()).toThrowError(
      /QMD_OPENAI_BASE_URL.*QMD_OPENAI_EMBED_MODEL.*QMD_OPENAI_CHAT_MODEL/s);
  });
});

describe("embedBatch", () => {
  test("posts to /v1/embeddings with model + input array, maps by index", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      data: [
        { index: 1, embedding: [0.4, 0.5] },
        { index: 0, embedding: [0.1, 0.2] },
      ],
    }));
    vi.stubGlobal("fetch", fetchMock);
    const llm = new OpenAICompatLLM(CFG);
    const results = await llm.embedBatch(["a", "b"]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("http://gap-api/v1/embeddings");
    expect(JSON.parse(init.body)).toEqual({ model: "my-embed", input: ["a", "b"] });
    expect(results).toEqual([
      { embedding: [0.1, 0.2], model: "my-embed" },
      { embedding: [0.4, 0.5], model: "my-embed" },
    ]);
  });
  test("sends Authorization header when apiKey configured", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ data: [{ index: 0, embedding: [1] }] }));
    vi.stubGlobal("fetch", fetchMock);
    const llm = new OpenAICompatLLM({ ...CFG, apiKey: "sekret" });
    await llm.embed("a");
    expect(fetchMock.mock.calls[0]![1].headers.authorization).toBe("Bearer sekret");
  });
  test("embed returns the single result", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      jsonResponse({ data: [{ index: 0, embedding: [9] }] })));
    const llm = new OpenAICompatLLM(CFG);
    expect(await llm.embed("a")).toEqual({ embedding: [9], model: "my-embed" });
  });
  test("empty input short-circuits without a network call", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    expect(await new OpenAICompatLLM(CFG).embedBatch([])).toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("fail-fast + retry", () => {
  test("retries 5xx up to 3 attempts then throws OpenAIBackendError", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockResolvedValue(new Response("boom", { status: 503 }));
    vi.stubGlobal("fetch", fetchMock);
    const llm = new OpenAICompatLLM(CFG);
    const pending = llm.embed("a");
    const guard = expect(pending).rejects.toThrowError(OpenAIBackendError);
    await vi.runAllTimersAsync();
    await guard;
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
  test("does NOT retry 4xx (except 429) — single attempt, clear error", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("bad model", { status: 400 }));
    vi.stubGlobal("fetch", fetchMock);
    const llm = new OpenAICompatLLM(CFG);
    await expect(llm.embed("a")).rejects.toThrowError(/embeddings.*http:\/\/gap-api\/v1\/embeddings.*400/s);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  test("retries network errors and succeeds on a later attempt", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new Error("ECONNREFUSED"))
      .mockResolvedValueOnce(jsonResponse({ data: [{ index: 0, embedding: [1] }] }));
    vi.stubGlobal("fetch", fetchMock);
    const llm = new OpenAICompatLLM(CFG);
    const pending = llm.embed("a");
    await vi.runAllTimersAsync();
    expect(await pending).toEqual({ embedding: [1], model: "my-embed" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
  test("error message includes the env-var hint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("x", { status: 400 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(new OpenAICompatLLM(CFG).embed("a"))
      .rejects.toThrowError(/QMD_OPENAI_BASE_URL/);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run test/llm-openai.test.ts --reporter=verbose`
Expected: FAIL — cannot resolve `../src/llm-openai.js`.

- [ ] **Step 3: Create `src/llm-openai.ts`**

```typescript
/**
 * llm-openai.ts - OpenAI-compatible API backend for QMD.
 *
 * Selected via QMD_LLM=openai (see getDefaultLLM in llm.ts). Routes
 * embeddings, generation, query expansion and reranking to an
 * OpenAI-compatible server (/v1/embeddings, /v1/chat/completions,
 * /v1/models). This module must never import node-llama-cpp, and may only
 * `import type` from llm.ts (runtime imports would create a cycle).
 *
 * Fail-fast policy (spec 2026-07-09): any API failure — after bounded
 * retries on 429/5xx/network errors — throws OpenAIBackendError. No silent
 * degradation, no fallback to local models.
 */
import { parseExpansionLines } from "./llm-shared.js";
import type {
  LLM, EmbedOptions, EmbeddingResult, GenerateOptions, GenerateResult,
  ModelInfo, Queryable, RerankDocument, RerankOptions, RerankResult,
} from "./llm.js";

const CHARS_PER_TOKEN = 4;
const TOKEN_SLICE_RE = new RegExp(`[\\s\\S]{1,${CHARS_PER_TOKEN}}`, "g");
const EMBED_TIMEOUT_MS = 60_000;
const CHAT_TIMEOUT_MS = 120_000;
const MAX_ATTEMPTS = 3;
const RETRY_BASE_DELAY_MS = 1_000;
const RERANK_CONCURRENCY = 8;
const RERANK_MAX_DOC_CHARS = 6_000;

export class OpenAIBackendError extends Error {
  constructor(operation: string, url: string, detail: string, hint?: string) {
    super(
      `qmd openai backend: ${operation} failed against ${url}: ${detail}\n` +
      (hint ?? "Check QMD_OPENAI_BASE_URL and that the endpoint is reachable.")
    );
    this.name = "OpenAIBackendError";
  }
}

export type OpenAIBackendConfig = {
  /** e.g. https://host/v1 — trailing slash is stripped */
  baseUrl: string;
  apiKey?: string;
  embedModel: string;
  chatModel: string;
  /** Optional dedicated reranker, served via chat/completions */
  rerankModel?: string;
  /** Overrides both per-operation timeout defaults when set */
  timeoutMs?: number;
};

export function readOpenAIConfigFromEnv(): OpenAIBackendConfig {
  const baseUrl = (process.env.QMD_OPENAI_BASE_URL ?? "").trim().replace(/\/+$/, "");
  const embedModel = (process.env.QMD_OPENAI_EMBED_MODEL ?? "").trim();
  const chatModel = (process.env.QMD_OPENAI_CHAT_MODEL ?? "").trim();
  const missing = [
    !baseUrl && "QMD_OPENAI_BASE_URL",
    !embedModel && "QMD_OPENAI_EMBED_MODEL",
    !chatModel && "QMD_OPENAI_CHAT_MODEL",
  ].filter((v): v is string => Boolean(v));
  if (missing.length > 0) {
    throw new OpenAIBackendError(
      "configuration", baseUrl || "(QMD_OPENAI_BASE_URL unset)",
      `missing required env: ${missing.join(", ")}`,
      "QMD_LLM=openai requires QMD_OPENAI_BASE_URL, QMD_OPENAI_EMBED_MODEL and QMD_OPENAI_CHAT_MODEL."
    );
  }
  const timeoutRaw = (process.env.QMD_OPENAI_TIMEOUT_MS ?? "").trim();
  const timeoutParsed = timeoutRaw ? Number(timeoutRaw) : NaN;
  return {
    baseUrl, embedModel, chatModel,
    apiKey: (process.env.QMD_OPENAI_API_KEY ?? "").trim() || undefined,
    rerankModel: (process.env.QMD_OPENAI_RERANK_MODEL ?? "").trim() || undefined,
    timeoutMs: Number.isFinite(timeoutParsed) && timeoutParsed > 0 ? timeoutParsed : undefined,
  };
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function safeBodySnippet(response: Response): Promise<string> {
  try {
    return (await response.text()).slice(0, 300);
  } catch {
    return "(unreadable body)";
  }
}

type ChatResponse = {
  choices?: {
    message?: { content?: string };
    logprobs?: {
      content?: {
        token: string;
        logprob: number;
        top_logprobs?: { token: string; logprob: number }[];
      }[];
    };
    finish_reason?: string;
  }[];
};

export class OpenAICompatLLM implements LLM {
  private config: OpenAIBackendConfig | null;

  /** Config is read lazily from env so that constructing the singleton is
   *  safe on pure-BM25 code paths that never call the API. */
  constructor(config?: OpenAIBackendConfig) {
    this.config = config ?? null;
  }

  private cfg(): OpenAIBackendConfig {
    this.config ??= readOpenAIConfigFromEnv();
    return this.config;
  }

  private async request<T>(
    operation: string,
    path: string,
    init: { method: string; body?: unknown },
    defaultTimeoutMs: number
  ): Promise<T> {
    const cfg = this.cfg();
    const url = `${cfg.baseUrl}${path}`;
    const headers: Record<string, string> = { "content-type": "application/json" };
    if (cfg.apiKey) headers.authorization = `Bearer ${cfg.apiKey}`;
    const timeoutMs = cfg.timeoutMs ?? defaultTimeoutMs;

    let lastDetail = "no attempt made";
    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
      try {
        const response = await fetch(url, {
          method: init.method,
          headers,
          body: init.body === undefined ? undefined : JSON.stringify(init.body),
          signal: AbortSignal.timeout(timeoutMs),
        });
        if (response.ok) return await response.json() as T;
        lastDetail = `HTTP ${response.status}: ${await safeBodySnippet(response)}`;
        const retryable = response.status === 429 || response.status >= 500;
        if (!retryable) break;
      } catch (error) {
        lastDetail = error instanceof Error ? error.message : String(error);
      }
      if (attempt < MAX_ATTEMPTS) await sleep(RETRY_BASE_DELAY_MS * 2 ** (attempt - 1));
    }
    throw new OpenAIBackendError(operation, url, lastDetail);
  }

  private chat(operation: string, body: Record<string, unknown>): Promise<ChatResponse> {
    return this.request<ChatResponse>(operation, "/chat/completions", { method: "POST", body }, CHAT_TIMEOUT_MS);
  }

  // ==========================================================================
  // Embeddings
  // ==========================================================================

  async embed(text: string, options: EmbedOptions = {}): Promise<EmbeddingResult | null> {
    const [result] = await this.embedBatch([text], options);
    return result ?? null;
  }

  // Note: options.model is intentionally ignored — the endpoint's embed model
  // is fixed by QMD_OPENAI_EMBED_MODEL, and resolveEmbedModel() already
  // resolves to the same name under this backend.
  async embedBatch(texts: string[], _options: EmbedOptions = {}): Promise<(EmbeddingResult | null)[]> {
    if (texts.length === 0) return [];
    const model = this.cfg().embedModel;
    type EmbeddingsResponse = { data?: { index: number; embedding: number[] }[] };
    const response = await this.request<EmbeddingsResponse>(
      "embeddings", "/embeddings",
      { method: "POST", body: { model, input: texts } },
      EMBED_TIMEOUT_MS
    );
    const byIndex = new Map((response.data ?? []).map(d => [d.index, d.embedding]));
    return texts.map((_, i) => {
      const embedding = byIndex.get(i);
      return embedding ? { embedding, model } : null;
    });
  }

  // ==========================================================================
  // Generation / expansion / rerank — implemented in Tasks 5-6
  // ==========================================================================

  async generate(_prompt: string, _options: GenerateOptions = {}): Promise<GenerateResult | null> {
    throw new Error("not implemented yet (Task 5)");
  }

  async expandQuery(
    _query: string,
    _options: { context?: string; includeLexical?: boolean; intent?: string } = {}
  ): Promise<Queryable[]> {
    throw new Error("not implemented yet (Task 5)");
  }

  async rerank(
    _query: string,
    _documents: RerankDocument[],
    _options: RerankOptions = {}
  ): Promise<RerankResult> {
    throw new Error("not implemented yet (Task 6)");
  }

  async modelExists(_model: string): Promise<ModelInfo> {
    throw new Error("not implemented yet (Task 5)");
  }

  async dispose(): Promise<void> {
    // Nothing to release — connections are per-request.
  }
}
```

(The `parseExpansionLines`, `TOKEN_SLICE_RE`, `RERANK_*` imports/constants are used in Tasks 5-7; TypeScript's `noUnusedLocals` is not enabled in this repo, so they compile now.)

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run test/llm-openai.test.ts --reporter=verbose`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add src/llm-openai.ts test/llm-openai.test.ts
git commit -m "feat: OpenAI-compatible backend core — config, fail-fast request layer, embeddings"
```

---

### Task 5: generate, modelExists/listModels, expandQuery

**Files:**
- Modify: `src/llm-openai.ts` (replace the Task-5 stubs)
- Test: `test/llm-openai.test.ts` (append)

- [ ] **Step 1: Append the failing tests**

```typescript
// append to test/llm-openai.test.ts
describe("generate", () => {
  test("posts chat completion and returns text", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      choices: [{ message: { content: "hello world" }, finish_reason: "stop" }],
    }));
    vi.stubGlobal("fetch", fetchMock);
    const llm = new OpenAICompatLLM(CFG);
    const result = await llm.generate("say hello", { maxTokens: 50, temperature: 0.1 });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("http://gap-api/v1/chat/completions");
    const body = JSON.parse(init.body);
    expect(body.model).toBe("my-chat");
    expect(body.messages).toEqual([{ role: "user", content: "say hello" }]);
    expect(body.max_tokens).toBe(50);
    expect(body.temperature).toBe(0.1);
    expect(result).toEqual({ text: "hello world", model: "my-chat", done: true });
  });
  test("done=false when finish_reason is length", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({
      choices: [{ message: { content: "trunc" }, finish_reason: "length" }],
    })));
    const result = await new OpenAICompatLLM(CFG).generate("x");
    expect(result?.done).toBe(false);
  });
});

describe("modelExists / listModels", () => {
  test("GETs /v1/models and matches by id", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      data: [{ id: "my-embed" }, { id: "my-chat" }],
    }));
    vi.stubGlobal("fetch", fetchMock);
    const llm = new OpenAICompatLLM(CFG);
    expect(await llm.modelExists("my-chat")).toEqual({ name: "my-chat", exists: true });
    expect(await llm.modelExists("nope")).toEqual({ name: "nope", exists: false });
    expect(fetchMock.mock.calls[0]![0]).toBe("http://gap-api/v1/models");
    expect(fetchMock.mock.calls[0]![1].method).toBe("GET");
  });
});

describe("expandQuery (openai)", () => {
  test("sends system+user messages and parses lex/vec/hyde output", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({
      choices: [{ message: { content: "lex: kv cache memory\nvec: kv cache reuse\nhyde: The kv cache stores keys." } }],
    }));
    vi.stubGlobal("fetch", fetchMock);
    const llm = new OpenAICompatLLM(CFG);
    const out = await llm.expandQuery("kv cache", { intent: "understand memory use" });
    const body = JSON.parse(fetchMock.mock.calls[0]![1].body);
    expect(body.messages[0].role).toBe("system");
    expect(body.messages[1].content).toContain("Expand this search query: kv cache");
    expect(body.messages[1].content).toContain("Query intent: understand memory use");
    expect(out).toEqual([
      { type: "lex", text: "kv cache memory" },
      { type: "vec", text: "kv cache reuse" },
      { type: "hyde", text: "The kv cache stores keys." },
    ]);
  });
  test("malformed output falls back to raw-query queryables (not an error)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({
      choices: [{ message: { content: "I cannot help with that." } }],
    })));
    const out = await new OpenAICompatLLM(CFG).expandQuery("kv cache");
    expect(out).toEqual([
      { type: "hyde", text: "Information about kv cache" },
      { type: "lex", text: "kv cache" },
      { type: "vec", text: "kv cache" },
    ]);
  });
  test("API failure throws — no fallback (fail-fast)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("x", { status: 400 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(new OpenAICompatLLM(CFG).expandQuery("kv cache"))
      .rejects.toThrowError(OpenAIBackendError);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run test/llm-openai.test.ts --reporter=verbose`
Expected: new tests FAIL with "not implemented yet".

- [ ] **Step 3: Implement — replace the three stubs in `src/llm-openai.ts`**

```typescript
  private static readonly EXPANSION_SYSTEM_PROMPT = [
    "You expand a search query into retrieval variants for a hybrid search engine.",
    "Output 3 to 6 lines and nothing else. Each line has the form `type: text` where type is one of:",
    "lex — exact keywords for BM25 full-text search (terms likely to appear verbatim in documents)",
    "vec — a semantic paraphrase for embedding search",
    "hyde — a one-sentence hypothetical document passage that would answer the query",
    "Every line must share at least one word with the original query.",
    "No markdown, no numbering, no commentary.",
  ].join("\n");

  async generate(prompt: string, options: GenerateOptions = {}): Promise<GenerateResult | null> {
    const model = this.cfg().chatModel;
    const response = await this.chat("generate", {
      model,
      messages: [{ role: "user", content: prompt }],
      max_tokens: options.maxTokens ?? 600,
      temperature: options.temperature ?? 0.3,
    });
    const choice = response.choices?.[0];
    return {
      text: choice?.message?.content ?? "",
      model,
      done: choice?.finish_reason !== "length",
    };
  }

  async expandQuery(
    query: string,
    options: { context?: string; includeLexical?: boolean; intent?: string } = {}
  ): Promise<Queryable[]> {
    const includeLexical = options.includeLexical ?? true;
    const user = options.intent
      ? `Expand this search query: ${query}\nQuery intent: ${options.intent}`
      : `Expand this search query: ${query}`;
    const response = await this.chat("expandQuery", {
      model: this.cfg().chatModel,
      messages: [
        { role: "system", content: OpenAICompatLLM.EXPANSION_SYSTEM_PROMPT },
        { role: "user", content: user },
      ],
      max_tokens: 600,
      temperature: 0.7,
    });
    const text = response.choices?.[0]?.message?.content ?? "";
    return parseExpansionLines(text, query, includeLexical);
  }

  async listModels(): Promise<string[]> {
    type ModelsResponse = { data?: { id: string }[] };
    const response = await this.request<ModelsResponse>(
      "models", "/models", { method: "GET" }, EMBED_TIMEOUT_MS);
    return (response.data ?? []).map(m => m.id);
  }

  async modelExists(model: string): Promise<ModelInfo> {
    const models = await this.listModels();
    return { name: model, exists: models.includes(model) };
  }
```

(Place `EXPANSION_SYSTEM_PROMPT` as a static field at the top of the class body. Keep the `rerank` stub for Task 6.)

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run test/llm-openai.test.ts --reporter=verbose`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/llm-openai.ts test/llm-openai.test.ts
git commit -m "feat: openai backend generate, model listing, query expansion (fail-fast)"
```

---

### Task 6: rerank via chat/completions with yes/no logprob scoring

**Files:**
- Modify: `src/llm-openai.ts` (replace the rerank stub)
- Test: `test/llm-openai.test.ts` (append)

- [ ] **Step 1: Append the failing tests**

```typescript
// append to test/llm-openai.test.ts
function rerankResponse(topLogprobs: { token: string; logprob: number }[]): Response {
  return jsonResponse({
    choices: [{
      message: { content: "yes" },
      logprobs: { content: [{ token: "yes", logprob: -0.1, top_logprobs: topLogprobs }] },
    }],
  });
}

describe("rerank (openai)", () => {
  test("scores docs by P(yes) from top_logprobs and sorts descending", async () => {
    const fetchMock = vi.fn()
      // doc A: strongly yes
      .mockResolvedValueOnce(rerankResponse([
        { token: "yes", logprob: -0.05 }, { token: "no", logprob: -3.0 },
      ]))
      // doc B: strongly no
      .mockResolvedValueOnce(rerankResponse([
        { token: "yes", logprob: -4.0 }, { token: "no", logprob: -0.02 },
      ]));
    vi.stubGlobal("fetch", fetchMock);
    const llm = new OpenAICompatLLM({ ...CFG, rerankModel: "my-reranker" });
    const result = await llm.rerank("kv cache", [
      { file: "a.md", text: "kv cache doc" },
      { file: "b.md", text: "unrelated doc" },
    ]);
    expect(result.model).toBe("my-reranker");
    const body = JSON.parse(fetchMock.mock.calls[0]![1].body);
    expect(body.model).toBe("my-reranker");
    expect(body.max_tokens).toBe(1);
    expect(body.logprobs).toBe(true);
    expect(body.messages[1].content).toContain("<Query>: kv cache");
    expect(result.results[0]).toMatchObject({ file: "a.md", index: 0 });
    expect(result.results[1]).toMatchObject({ file: "b.md", index: 1 });
    expect(result.results[0]!.score).toBeGreaterThan(0.9);
    expect(result.results[1]!.score).toBeLessThan(0.1);
  });
  test("falls back to yes/no text when logprobs are absent", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(jsonResponse({ choices: [{ message: { content: "Yes" } }] }))
      .mockResolvedValueOnce(jsonResponse({ choices: [{ message: { content: "no" } }] })));
    const llm = new OpenAICompatLLM(CFG);
    const result = await llm.rerank("q terms", [
      { file: "a.md", text: "t1" }, { file: "b.md", text: "t2" },
    ]);
    expect(result.results.find(r => r.file === "a.md")!.score).toBe(1);
    expect(result.results.find(r => r.file === "b.md")!.score).toBe(0);
  });
  test("uses chat model when no rerank model configured", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ choices: [{ message: { content: "yes" } }] }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await new OpenAICompatLLM(CFG).rerank("q", [{ file: "a.md", text: "t" }]);
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body).model).toBe("my-chat");
    expect(result.model).toBe("my-chat");
  });
  test("identical doc texts are scored once (deduplicated)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ choices: [{ message: { content: "yes" } }] }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await new OpenAICompatLLM(CFG).rerank("q", [
      { file: "a.md", text: "same" }, { file: "b.md", text: "same" },
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(result.results).toHaveLength(2);
  });
  test("API failure on any doc fails the whole rerank (fail-fast)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("x", { status: 400 })));
    await expect(new OpenAICompatLLM(CFG).rerank("q", [{ file: "a.md", text: "t" }]))
      .rejects.toThrowError(OpenAIBackendError);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run test/llm-openai.test.ts --reporter=verbose`
Expected: rerank tests FAIL with "not implemented yet".

- [ ] **Step 3: Implement — replace the rerank stub**

```typescript
  // Qwen3-Reranker prompt format: the reranker is a causal LM that answers
  // strictly "yes"/"no"; relevance = P(yes) read from logprobs.
  private static readonly RERANK_SYSTEM_PROMPT =
    'Judge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be "yes" or "no".';

  private async scoreDocument(query: string, text: string, model: string): Promise<number> {
    const user =
      `<Instruct>: Given a web search query, retrieve relevant passages that answer the query\n` +
      `<Query>: ${query}\n<Document>: ${text}`;
    const response = await this.chat("rerank", {
      model,
      messages: [
        { role: "system", content: OpenAICompatLLM.RERANK_SYSTEM_PROMPT },
        { role: "user", content: user },
      ],
      max_tokens: 1,
      temperature: 0,
      logprobs: true,
      top_logprobs: 20,
    });
    const choice = response.choices?.[0];
    const top = choice?.logprobs?.content?.[0]?.top_logprobs;
    if (top && top.length > 0) {
      let yesLogprob: number | undefined;
      let noLogprob: number | undefined;
      for (const entry of top) {
        const token = entry.token.trim().toLowerCase();
        if (token === "yes" && yesLogprob === undefined) yesLogprob = entry.logprob;
        if (token === "no" && noLogprob === undefined) noLogprob = entry.logprob;
      }
      if (yesLogprob !== undefined || noLogprob !== undefined) {
        const yes = Math.exp(yesLogprob ?? -100);
        const no = Math.exp(noLogprob ?? -100);
        return yes / (yes + no);
      }
    }
    // Server returned no usable logprobs: coarse text fallback (capability
    // adaptation per spec — NOT a failure path; API errors already threw).
    const answer = (choice?.message?.content ?? "").trim().toLowerCase();
    return answer.startsWith("yes") ? 1 : 0;
  }

  async rerank(
    query: string,
    documents: RerankDocument[],
    _options: RerankOptions = {}
  ): Promise<RerankResult> {
    const model = this.cfg().rerankModel ?? this.cfg().chatModel;
    // Char-based truncation (no local tokenizer) + dedup of identical
    // effective texts — same rationale as the llama.cpp backend.
    const truncated = documents.map(doc =>
      doc.text.length > RERANK_MAX_DOC_CHARS ? doc.text.slice(0, RERANK_MAX_DOC_CHARS) : doc.text);
    const uniqueTexts = Array.from(new Set(truncated));
    const scores = new Map<string, number>();
    for (let i = 0; i < uniqueTexts.length; i += RERANK_CONCURRENCY) {
      const batch = uniqueTexts.slice(i, i + RERANK_CONCURRENCY);
      const batchScores = await Promise.all(
        batch.map(text => this.scoreDocument(query, text, model)));
      batch.forEach((text, j) => scores.set(text, batchScores[j]!));
    }
    const results = documents
      .map((doc, index) => ({ file: doc.file, score: scores.get(truncated[index]!) ?? 0, index }))
      .sort((a, b) => b.score - a.score);
    return { results, model };
  }
```

- [ ] **Step 4: Run to verify pass**

Run: `npx vitest run test/llm-openai.test.ts --reporter=verbose`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/llm-openai.ts test/llm-openai.test.ts
git commit -m "feat: openai backend rerank — yes/no logprob scoring via chat/completions"
```

---

### Task 7: Tokenizer shims, singleton, `ChunkingLLM` + `getDefaultLLM()` seam

**Files:**
- Modify: `src/llm-openai.ts` (add tokenizer methods + singleton)
- Modify: `src/llm.ts` (add `ChunkingLLM` interface + `getDefaultLLM()`, near `getDefaultLlamaCpp` at line ~2049)
- Test: `test/llm-openai.test.ts` (append)

- [ ] **Step 1: Append the failing tests**

```typescript
// append to test/llm-openai.test.ts
import { getDefaultLLM } from "../src/llm.js";
import { getDefaultOpenAILLM, setDefaultOpenAILLMForTest } from "../src/llm-openai.js";

describe("tokenizer shims (char-based, ~4 chars/token)", () => {
  const llm = new OpenAICompatLLM(CFG);
  test("countTokens is ceil(len/4)", async () => {
    expect(await llm.countTokens("")).toBe(0);
    expect(await llm.countTokens("abcd")).toBe(1);
    expect(await llm.countTokens("abcde")).toBe(2);
  });
  test("tokenize/detokenize round-trips and slices are token-count consistent", async () => {
    const text = "The quick brown fox jumps over the lazy dog.";
    const tokens = await llm.tokenize(text);
    expect(tokens.length).toBe(await llm.countTokens(text));
    expect(await llm.detokenize(tokens)).toBe(text);
    expect(await llm.detokenize(tokens.slice(0, 2))).toBe("The quic");
  });
});

describe("getDefaultLLM seam", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    setDefaultOpenAILLMForTest(null);
  });
  test("returns the OpenAI singleton when QMD_LLM=openai", () => {
    vi.stubEnv("QMD_LLM", "openai");
    const llm = getDefaultLLM();
    expect(llm).toBeInstanceOf(OpenAICompatLLM);
    expect(getDefaultLLM()).toBe(llm); // singleton
    expect(llm).toBe(getDefaultOpenAILLM());
  });
  test("returns LlamaCpp when QMD_LLM is unset", () => {
    vi.stubEnv("QMD_LLM", "");
    expect(getDefaultLLM()).not.toBeInstanceOf(OpenAICompatLLM);
  });
  test("constructing the openai singleton does not require QMD_OPENAI_* env (lazy config)", () => {
    vi.stubEnv("QMD_LLM", "openai");
    vi.stubEnv("QMD_OPENAI_BASE_URL", "");
    expect(() => getDefaultLLM()).not.toThrow();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run test/llm-openai.test.ts --reporter=verbose`
Expected: FAIL — `tokenize`, `getDefaultLLM`, `getDefaultOpenAILLM` missing.

- [ ] **Step 3: Add tokenizer methods + singleton to `src/llm-openai.ts`**

Inside the class:

```typescript
  // ==========================================================================
  // Tokenizer shims — deterministic char-based estimate (~4 chars/token).
  // Used only for chunk sizing at index time; the index is always built and
  // queried by the same backend, so exact model tokenization is unnecessary.
  // ==========================================================================

  async tokenize(text: string): Promise<readonly string[]> {
    return text.match(TOKEN_SLICE_RE) ?? [];
  }

  async detokenize(tokens: readonly string[]): Promise<string> {
    return tokens.join("");
  }

  async countTokens(text: string): Promise<number> {
    return Math.ceil(text.length / CHARS_PER_TOKEN);
  }
```

At module bottom:

```typescript
// =============================================================================
// Default instance management
// =============================================================================

let defaultOpenAILLM: OpenAICompatLLM | null = null;

/** Get (or lazily create) the default OpenAI-backend instance. Construction
 *  never touches env or network — config is validated on first API call. */
export function getDefaultOpenAILLM(): OpenAICompatLLM {
  defaultOpenAILLM ??= new OpenAICompatLLM();
  return defaultOpenAILLM;
}

export function setDefaultOpenAILLMForTest(llm: OpenAICompatLLM | null): void {
  defaultOpenAILLM = llm;
}
```

- [ ] **Step 4: Add `ChunkingLLM` + `getDefaultLLM()` to `src/llm.ts`**

Add the runtime import at the top of `src/llm.ts` (next to the llm-shared import from Task 2 — this direction is cycle-safe because llm-openai.ts only type-imports from llm.ts):

```typescript
import { getDefaultOpenAILLM } from "./llm-openai.js";
```

Add directly after the `LLM` interface (line ~553):

```typescript
/**
 * The full backend surface qmd's store/chunker/session layers need beyond the
 * base LLM interface. Both LlamaCpp and OpenAICompatLLM satisfy it.
 * tokenize/detokenize use `readonly any[]` because token representations are
 * backend-opaque (LlamaToken[] vs char-slice strings); callers only ever
 * count, slice, and pass tokens back to the same backend's detokenize.
 */
export interface ChunkingLLM extends LLM {
  embedBatch(texts: string[], options?: EmbedOptions): Promise<(EmbeddingResult | null)[]>;
  tokenize(text: string): Promise<readonly any[]>;
  countTokens(text: string): Promise<number>;
  detokenize(tokens: readonly any[]): Promise<string>;
}
```

Add directly after `getDefaultLlamaCpp` (line ~2060):

```typescript
/**
 * Backend seam: the default LLM for all qmd operations.
 * QMD_LLM=openai selects the OpenAI-compatible API backend; anything else
 * (including unset) preserves upstream behavior exactly (local llama.cpp).
 */
export function getDefaultLLM(): ChunkingLLM {
  return isOpenAIBackend() ? getDefaultOpenAILLM() : getDefaultLlamaCpp();
}
```

- [ ] **Step 5: Run to verify pass**

Run: `npm run build && npx vitest run test/llm-openai.test.ts test/esm-ambiguous-module.test.ts --reporter=verbose`
Expected: build OK (no cycle errors), tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/llm-openai.ts src/llm.ts test/llm-openai.test.ts
git commit -m "feat: char-based tokenizer shims, openai singleton, getDefaultLLM backend seam"
```

---

### Task 8: Wire all call sites through `getDefaultLLM` + no-llama regression tests

**Files:**
- Modify: `src/llm.ts` (session layer: lines ~1741-1920)
- Modify: `src/store.ts` (lines 24, 85, 1274, 2772, 3732-3737, 3892-3912, 3933-3958)
- Test: `test/llm-openai-isolation.test.ts` (create)

- [ ] **Step 1: Write the failing test**

```typescript
// test/llm-openai-isolation.test.ts
import { describe, test, expect, afterEach, vi } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

afterEach(() => vi.unstubAllEnvs());

describe("openai backend never touches node-llama-cpp", () => {
  test("llm-openai.ts and llm-shared.ts have no node-llama-cpp reference at all", () => {
    for (const file of ["llm-openai.ts", "llm-shared.ts"]) {
      const source = readFileSync(join(process.cwd(), "src", file), "utf-8");
      expect(source).not.toContain("node-llama-cpp");
    }
  });
  test("store.ts and cli/qmd.ts route default-LLM access through getDefaultLLM", () => {
    const store = readFileSync(join(process.cwd(), "src", "store.ts"), "utf-8");
    expect(store).not.toContain("getDefaultLlamaCpp()");
    const llm = readFileSync(join(process.cwd(), "src", "llm.ts"), "utf-8");
    // the session-manager default must use the seam:
    expect(llm).toContain("const llm = getDefaultLLM();");
  });
  test("chunking works end-to-end with the openai backend selected and fetch disabled", async () => {
    vi.stubEnv("QMD_LLM", "openai");
    vi.stubGlobal("fetch", vi.fn(() => { throw new Error("network must not be touched by chunking"); }));
    const { chunkDocumentByTokens } = await import("../src/store.js");
    const chunks = await chunkDocumentByTokens("word ".repeat(2000), 100, 10, 50);
    expect(chunks.length).toBeGreaterThan(1);
    for (const chunk of chunks) expect(chunk.tokens).toBeLessThanOrEqual(100);
    vi.unstubAllGlobals();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `npx vitest run test/llm-openai-isolation.test.ts --reporter=verbose`
Expected: FAIL — `getDefaultLlamaCpp()` still present in store.ts; chunking test may crash trying to init llama.

- [ ] **Step 3: Widen the session layer in `src/llm.ts`**

All in `src/llm.ts` (types only — method name `getLlamaCpp` is kept to minimize rebase churn):

1. `LLMSessionManager` (line ~1741): change `private llm: LlamaCpp;` → `private llm: ChunkingLLM;`, constructor parameter `constructor(llm: ChunkingLLM)`, and `getLlamaCpp(): LlamaCpp` → `getLlamaCpp(): ChunkingLLM`.
2. `getSessionManager()` (line ~1914): change `const llm = getDefaultLlamaCpp();` → `const llm = getDefaultLLM();`.
3. `withLLMSessionForLlm` (line ~1954): change parameter `llm: LlamaCpp` → `llm: ChunkingLLM`.

- [ ] **Step 4: Rewire `src/store.ts`**

1. Line 24 imports: replace `getDefaultLlamaCpp,` with `getDefaultLLM,` and add `type ChunkingLLM,` to the same import list from `"./llm.js"`.
2. Line ~85: `function getLlm(store: Store): LlamaCpp { return store.llm ?? getDefaultLlamaCpp(); }` → `function getLlm(store: Store): ChunkingLLM { return store.llm ?? getDefaultLLM(); }` (update the doc comment above it: "LlamaCpp instance" → "LLM backend").
3. Line ~1274 (`Store` type): `llm?: LlamaCpp;` → `llm?: ChunkingLLM;`.
4. Line ~2772 (`chunkDocumentByTokens`): `const llm = getDefaultLlamaCpp();` → `const llm = getDefaultLLM();`.
5. Line ~3732 (`getEmbedding`): parameter `llmOverride?: LlamaCpp` → `llmOverride?: ChunkingLLM`; line ~3737 `(llmOverride ?? getDefaultLlamaCpp())` → `(llmOverride ?? getDefaultLLM())`.
6. Line ~3892 (`expandQuery`): parameter `llmOverride?: LlamaCpp` → `llmOverride?: ChunkingLLM`; line ~3912 `llmOverride ?? getDefaultLlamaCpp()` → `llmOverride ?? getDefaultLLM()`.
7. Line ~3933 (`rerank`): parameter `llmOverride?: LlamaCpp` → `llmOverride?: ChunkingLLM`; line ~3958 `llmOverride ?? getDefaultLlamaCpp()` → `llmOverride ?? getDefaultLLM()`.
8. If `LlamaCpp` is now unused in store.ts imports, remove it.

- [ ] **Step 5: Run to verify pass + full suite**

Run: `npm run build && npx vitest run test/llm-openai-isolation.test.ts --reporter=verbose && npx vitest run --reporter=dot 2>&1 | tail -5`
Expected: isolation tests PASS; suite matches the Task 1 baseline (plus all new tests).

- [ ] **Step 6: Commit**

```bash
git add src/llm.ts src/store.ts test/llm-openai-isolation.test.ts
git commit -m "feat: route store/session/chunker through getDefaultLLM backend seam"
```

---

### Task 8b: Wire the SDK's `createStore()` (and thus `qmd mcp`) through `getDefaultLLM`

**Discovered during Task 8's code-quality review, not in the original spec.** `src/store.ts`'s
internal store (used by the CLI's `search`/`embed`/etc. commands) now correctly falls through to
`getDefaultLLM()` via `getLlm(store)`. But the SDK's public `createStore()` in `src/index.ts` —
which `src/mcp/server.ts`'s `startMcpServer()`/`startMcpHttpServer()` call, which is what `qmd mcp`
actually runs — unconditionally constructs `new LlamaCpp({...})` and assigns it to
`internal.llm`, bypassing the backend seam entirely. Since `getLlm()` only falls through to
`getDefaultLLM()` when `store.llm` is unset, any consumer going through `index.ts`'s `createStore()`
(the MCP server included) never honors `QMD_LLM=openai` — it always loads a local GGUF model
regardless of configuration. This directly threatens the fork's purpose for its most likely
production path (`qmd mcp`, the mode the Claude Code qmd plugin invokes).

**Files:**
- Modify: `src/index.ts:68-70` (llm.js import), `src/index.ts:375-384` (`createStore`'s LlamaCpp
  construction + assignment), `src/index.ts:541-547` (`close()`'s disposal)
- Test: `test/llm-openai-sdk-isolation.test.ts` (create)

- [ ] **Step 1: Write the failing test**

```typescript
// test/llm-openai-sdk-isolation.test.ts
import { describe, test, expect, afterEach, vi } from "vitest";
import { mkdtempSync, rmSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("SDK createStore() honors QMD_LLM=openai", () => {
  test("does not construct a LlamaCpp, and never touches the network, under the openai backend", async () => {
    vi.stubEnv("QMD_LLM", "openai");
    vi.stubEnv("QMD_OPENAI_BASE_URL", "http://sdk-isolation-test/v1");
    vi.stubEnv("QMD_OPENAI_EMBED_MODEL", "embed-model");
    vi.stubEnv("QMD_OPENAI_CHAT_MODEL", "chat-model");
    vi.stubGlobal("fetch", vi.fn(() => {
      throw new Error("network must not be touched by createStore() itself");
    }));

    const { createStore } = await import("../src/index.js");
    const { OpenAICompatLLM } = await import("../src/llm-openai.js");
    const dir = mkdtempSync(join(tmpdir(), "qmd-sdk-isolation-"));
    const dbPath = join(dir, "test.sqlite");
    try {
      const store = await createStore({
        dbPath,
        config: { collections: {} },
      });
      // No per-store LlamaCpp was constructed: internal.llm is either unset,
      // or (if ever set) must not be a LlamaCpp instance.
      expect(store.internal.llm).not.toBeInstanceOf(
        (await import("../src/llm.js")).LlamaCpp
      );
      await store.close(); // must not throw even with no per-store llm to dispose
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test("still constructs a per-store LlamaCpp when QMD_LLM is unset (local backend unchanged)", async () => {
    vi.stubEnv("QMD_LLM", "");
    const { createStore } = await import("../src/index.js");
    const { LlamaCpp } = await import("../src/llm.js");
    const dir = mkdtempSync(join(tmpdir(), "qmd-sdk-isolation-local-"));
    const dbPath = join(dir, "test.sqlite");
    try {
      const store = await createStore({
        dbPath,
        config: { collections: {} },
      });
      expect(store.internal.llm).toBeInstanceOf(LlamaCpp);
      await store.close();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /Users/moshe/Desktop/Code/qmd-api && CI=true npx vitest run test/llm-openai-sdk-isolation.test.ts --reporter=verbose`
Expected: FAIL on the first test — `store.internal.llm` IS a `LlamaCpp` instance (constructed
unconditionally), so `not.toBeInstanceOf` fails. The second test should already pass (it's today's
existing behavior) — confirms the test file itself is well-formed before the fix.

- [ ] **Step 3: Implement — guard the LlamaCpp construction in `src/index.ts`**

Add `isOpenAIBackend` to the existing `llm.js` import (`src/index.ts:68-70`):

```typescript
import {
  LlamaCpp,
  isOpenAIBackend,
} from "./llm.js";
```

Replace the unconditional construction (`src/index.ts:375-384`):

```typescript
  // Create a per-store LlamaCpp instance — lazy-loads models on first use,
  // auto-unloads after 5 min inactivity to free VRAM.
  const llm = new LlamaCpp({
    embedModel: config?.models?.embed,
    generateModel: config?.models?.generate,
    rerankModel: config?.models?.rerank,
    inactivityTimeoutMs: 5 * 60 * 1000,
    disposeModelsOnInactivity: true,
  });
  internal.llm = llm;
```

with:

```typescript
  // Create a per-store LlamaCpp instance for the local backend — lazy-loads
  // models on first use, auto-unloads after 5 min inactivity to free VRAM.
  // Under QMD_LLM=openai, skip this: leave internal.llm unset so getLlm()
  // (store.ts) falls through to the shared getDefaultLLM() singleton, which
  // is stateless (per-request fetch calls) and has no per-store lifecycle to
  // manage. Per-store config.models.* overrides are local-backend-only —
  // resolveEmbedModel()/etc. already ignore them under the openai backend
  // (Task 3), so there is nothing to preserve here for that path.
  const llm = isOpenAIBackend() ? undefined : new LlamaCpp({
    embedModel: config?.models?.embed,
    generateModel: config?.models?.generate,
    rerankModel: config?.models?.rerank,
    inactivityTimeoutMs: 5 * 60 * 1000,
    disposeModelsOnInactivity: true,
  });
  if (llm) internal.llm = llm;
```

Update `close()` (`src/index.ts:541-547`) to only dispose a per-store `llm` if one was created:

```typescript
    close: async () => {
      if (llm) await llm.dispose();
      internal.close();
      if (hasYamlConfig || options.config) {
        setConfigSource(undefined); // Reset config source
      }
    },
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /Users/moshe/Desktop/Code/qmd-api && CI=true npx vitest run test/llm-openai-sdk-isolation.test.ts --reporter=verbose`
Expected: PASS (2/2).

- [ ] **Step 5: Confirm existing SDK/MCP tests are unaffected**

Run: `cd /Users/moshe/Desktop/Code/qmd-api && CI=true npx vitest run test/sdk.test.ts test/mcp.test.ts --reporter=verbose`
Expected: same pass/fail counts as before this change (these tests monkeypatch
`store.internal.llm` directly after `createStore()` returns, so they're unaffected either way —
confirm this holds, don't just assume it).

- [ ] **Step 6: Full suite**

Run: `cd /Users/moshe/Desktop/Code/qmd-api && npm run build && CI=true npx vitest run --reporter=dot`
Expected: prior baseline count + 2 new tests, only the same 9 pre-existing `test/cli.test.ts`
failures. If a run shows an unexpected extra failure or takes far longer than ~60-100s, rerun once
before concluding there's a real regression (a one-off environmental flake has been observed
before in this plan's execution — see Task 8's notes).

- [ ] **Step 7: Commit**

```bash
git add src/index.ts test/llm-openai-sdk-isolation.test.ts
git commit -m "fix: route SDK createStore() (and qmd mcp) through getDefaultLLM backend seam"
```

---

### Task 9: CLI — `qmd doctor` reachability check and `qmd status` backend line

**Files:**
- Modify: `src/cli/qmd.ts:83` (imports), `src/cli/qmd.ts:466` (showStatus), `src/cli/qmd.ts:3748` (runDoctorDeviceChecks)
- Test: manual CLI verification (CLI has no unit-test harness for these output paths; `test/cli.test.ts` covers arg parsing only)

- [ ] **Step 1: Add imports**

In the `src/cli/qmd.ts:83` import from `"../llm.js"`, add `isOpenAIBackend`. Add a new import line below it:

```typescript
import { getDefaultOpenAILLM, readOpenAIConfigFromEnv } from "../llm-openai.js";
```

- [ ] **Step 2: `showStatus` backend line**

At the top of `showStatus()` (line ~466, immediately after `const db = getDb();`):

```typescript
  if (isOpenAIBackend()) {
    try {
      const cfg = readOpenAIConfigFromEnv();
      console.log(`${c.bold}LLM backend:${c.reset} openai (${cfg.baseUrl})`);
    } catch (error) {
      console.log(`${c.bold}LLM backend:${c.reset} openai — MISCONFIGURED: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
```

- [ ] **Step 3: `runDoctorDeviceChecks` openai branch**

At the top of `runDoctorDeviceChecks(nextSteps: string[])` (line ~3748), before the `configuredGpuModeLabel()` call:

```typescript
  if (isOpenAIBackend()) {
    try {
      const cfg = readOpenAIConfigFromEnv();
      const models = await getDefaultOpenAILLM().listModels();
      const expected = [cfg.embedModel, cfg.chatModel, ...(cfg.rerankModel ? [cfg.rerankModel] : [])];
      const missing = expected.filter(m => !models.includes(m));
      doctorCheck("openai backend", missing.length === 0,
        missing.length === 0
          ? `reachable at ${cfg.baseUrl}; models available: ${expected.join(", ")}`
          : `reachable at ${cfg.baseUrl}, but /v1/models does not list: ${missing.join(", ")}. Next: verify the QMD_OPENAI_*_MODEL names (some servers hide models from the listing)`);
      if (missing.length > 0) {
        nextSteps.push("Verify QMD_OPENAI_EMBED_MODEL / QMD_OPENAI_CHAT_MODEL / QMD_OPENAI_RERANK_MODEL against the server's /v1/models.");
      }
    } catch (error) {
      doctorCheck("openai backend", false, error instanceof Error ? error.message : String(error));
      nextSteps.push("Fix the QMD_OPENAI_* environment configuration and rerun `qmd doctor`.");
    }
    return; // GPU/llama.cpp probes are meaningless under the API backend
  }
```

- [ ] **Step 4: Manual verification**

```bash
npm run build
# Misconfigured: doctor reports the missing env vars and exits without a GPU probe
QMD_LLM=openai node bin/qmd doctor 2>&1 | grep -A1 "openai backend"
# Local mode untouched:
node bin/qmd doctor 2>&1 | grep "device mode"
# Status line appears:
QMD_LLM=openai QMD_OPENAI_BASE_URL=http://localhost:9 QMD_OPENAI_EMBED_MODEL=e QMD_OPENAI_CHAT_MODEL=cc node bin/qmd status 2>&1 | grep "LLM backend"
```

Expected: first command shows a failing "openai backend" check naming `QMD_OPENAI_BASE_URL`; second shows the normal device-mode line; third prints `LLM backend: openai (http://localhost:9)`.

- [ ] **Step 5: Commit**

```bash
git add src/cli/qmd.ts
git commit -m "feat: qmd doctor/status report openai backend reachability instead of GPU probe"
```

---

### Task 10: Full suite, build artifacts, fork bookkeeping

**Files:**
- Modify: `CHANGELOG.md` (fork entry), `README.md` (env var section)

- [ ] **Step 1: Full verification**

```bash
cd /Users/moshe/Desktop/Code/qmd-api
npm run build && npx vitest run --reporter=dot 2>&1 | tail -5
```

Expected: build clean; all tests pass (same baseline failures as Task 1, if any, and nothing new).

- [ ] **Step 2: Document the fork surface**

Add to `CHANGELOG.md` under `## [Unreleased]`:

```markdown
### Added (fork: openai-backend)

- `QMD_LLM=openai` selects a new OpenAI-compatible API backend (`src/llm-openai.ts`)
  that routes embeddings, query expansion, HyDE generation, and reranking to an
  OpenAI-compatible server. Configured via `QMD_OPENAI_BASE_URL`,
  `QMD_OPENAI_API_KEY` (optional), `QMD_OPENAI_EMBED_MODEL`,
  `QMD_OPENAI_CHAT_MODEL`, `QMD_OPENAI_RERANK_MODEL` (optional),
  `QMD_OPENAI_TIMEOUT_MS` (optional). With `QMD_LLM` unset, behavior is
  byte-identical to upstream. Under the API backend, node-llama-cpp is never
  imported, no GGUF models are needed, and any API failure fails the operation
  loudly (bounded retries on 429/5xx/network errors) — no local fallback.
```

Append these rows to `README.md`'s existing environment-variable table (same `| Variable | Description |` columns it already uses):

```markdown
| `QMD_LLM` | Backend selector. `openai` routes all model work to an OpenAI-compatible API; unset/`local` uses local GGUF models (default). |
| `QMD_OPENAI_BASE_URL` | Base URL of the OpenAI-compatible server, e.g. `https://host/v1`. Required when `QMD_LLM=openai`. |
| `QMD_OPENAI_EMBED_MODEL` | Embeddings model name on the server. Required when `QMD_LLM=openai`. |
| `QMD_OPENAI_CHAT_MODEL` | Chat model name used for expansion/HyDE (and rerank fallback). Required when `QMD_LLM=openai`. |
| `QMD_OPENAI_RERANK_MODEL` | Optional dedicated reranker (served via chat/completions, scored by yes/no logprobs). |
| `QMD_OPENAI_API_KEY` | Optional bearer token for the API. |
| `QMD_OPENAI_TIMEOUT_MS` | Optional request timeout override (defaults: embeddings 60s, chat 120s). |
```

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md README.md
git commit -m "docs: document QMD_LLM=openai backend configuration"
```

---

### Task 11: Vault docs — instructions.md API-backend variant + vault-setup skill

**Files (vault repo `/Users/moshe/Desktop/Code/Moshe Vault`):**
- Modify: `instructions.md` (Part 2 qmd table, Part 3 Phases A/B, §4 troubleshooting)
- Modify: `.claude/skills/vault-setup/SKILL.md` (air-gapped bootstrap section)

- [ ] **Step 1: instructions.md — Part 2 qmd table**

In the "qmd (search engine)" table, append a row:

```markdown
| ⚡ API backend (fork) | The `qmd-api` fork adds `QMD_LLM=openai`, routing all model work to an OpenAI-compatible endpoint. Under this backend **no GGUF models and no GPU are needed** — skip the `qmd-models.tgz` artifact entirely. Env vars: `QMD_OPENAI_BASE_URL` (required), `QMD_OPENAI_EMBED_MODEL` (required), `QMD_OPENAI_CHAT_MODEL` (required), `QMD_OPENAI_API_KEY` / `QMD_OPENAI_RERANK_MODEL` / `QMD_OPENAI_TIMEOUT_MS` (optional). API failures fail the operation loudly — no local fallback. |
```

- [ ] **Step 2: instructions.md — Part 3 Phase A/B variant**

After the Phase A command blocks, add:

```markdown
#### Phase A variant — API backend (no GPU, no model transfer)

When the closed environment has an OpenAI-compatible inference endpoint, stage the
`qmd-api` fork instead of stock qmd. **The staging machine must match the target's
OS, CPU architecture, and Node major version** (native better-sqlite3/sqlite-vec
binaries are captured from the staging machine's install tree).

macOS / Linux (bash):
​```bash
git clone <qmd-api fork> && cd qmd-api && git checkout openai-backend
npm install && npm run build && npm install -g .
qmd --version                          # sanity: fork installed
tar czf qmd-install-tree.tgz -C "$(npm prefix -g)" .
# A3 (model pre-pull) is NOT needed — skip qmd-models.tgz entirely.
​```
Windows (PowerShell):
​```powershell
git clone <qmd-api fork>; cd qmd-api; git checkout openai-backend
npm install; npm run build; npm install -g .
qmd --version
tar czf qmd-install-tree.tgz -C "$(npm prefix -g)" .
​```

#### Phase B variant — API backend

After unpacking the install tree (B2), set the backend env vars machine-wide
(e.g. /etc/profile.d/qmd.sh, or the Windows system environment):

​```
QMD_LLM=openai
QMD_OPENAI_BASE_URL=https://<internal-endpoint>/v1
QMD_OPENAI_EMBED_MODEL=<embeddings model name>
QMD_OPENAI_CHAT_MODEL=<chat model name>
QMD_OPENAI_RERANK_MODEL=<reranker model name>   # optional
QMD_OPENAI_API_KEY=<key>                        # optional
​```

Skip B3 (model cache restore). Verify with `qmd doctor` — the "openai backend"
check must report the endpoint reachable and the configured models present.
```

(Remove the `​` zero-width guards around the inner code fences when inserting — they exist only to nest fences in this plan.)

- [ ] **Step 3: instructions.md — §4 troubleshooting rows**

Append to the troubleshooting table:

```markdown
| `qmd` fails after transfer: `better_sqlite3.node` missing / wrong ABI ("was compiled against a different Node.js version") | qmd carried across the gap as source (git) — native modules never compiled, or compiled for a different Node ABI | Carry the **install tree** built on a staging machine matching OS/arch/Node major (Phase A/A-variant), never bare source |
| `qmd embed`/`query` fails with `qmd openai backend: ... failed against <url>` | API backend is fail-fast by design — endpoint down, wrong base URL, or wrong model name | Fix `QMD_OPENAI_*` env; verify with `qmd doctor`. Do NOT expect fallback to local models |
```

- [ ] **Step 4: vault-setup SKILL.md — air-gapped bootstrap env checklist**

In the "Air-gapped bootstrap" section, insert after step 1:

```markdown
1b. **API backend (no-GPU environments):** if qmd is the `qmd-api` fork, confirm the
    machine-wide env is set: `QMD_LLM=openai`, `QMD_OPENAI_BASE_URL`,
    `QMD_OPENAI_EMBED_MODEL`, `QMD_OPENAI_CHAT_MODEL` (+ optional
    `QMD_OPENAI_RERANK_MODEL`, `QMD_OPENAI_API_KEY`). Run `qmd doctor` — the
    "openai backend" check must pass before registering collections. API failures
    fail loudly by design; there is no local-model fallback.
```

- [ ] **Step 5: Commit (vault repo)**

```bash
cd "/Users/moshe/Desktop/Code/Moshe Vault"
git add instructions.md .claude/skills/vault-setup/SKILL.md
git commit -m "docs: air-gap runbook variant for qmd-api OpenAI backend (no GPU, no model transfer)"
```

---

### Task 12: Local end-to-end verification against a real OpenAI-compatible server

**Files:** none (verification only). Requires a local OpenAI-compatible server; use Ollama (or LM Studio at `http://localhost:1234/v1` — adjust base URL/model names accordingly).

- [ ] **Step 1: Start the server and pull models**

```bash
ollama pull nomic-embed-text && ollama pull qwen2.5:3b
curl -s http://localhost:11434/v1/models | head -c 400   # confirm OpenAI-compat endpoint
```

- [ ] **Step 2: Point a fresh, isolated qmd index at the vault via the fork**

```bash
cd /Users/moshe/Desktop/Code/qmd-api && npm run build
export QMD_LLM=openai \
       QMD_OPENAI_BASE_URL=http://localhost:11434/v1 \
       QMD_OPENAI_EMBED_MODEL=nomic-embed-text \
       QMD_OPENAI_CHAT_MODEL=qwen2.5:3b \
       XDG_CACHE_HOME=/tmp/qmd-openai-it/cache \
       QMD_CONFIG_DIR=/tmp/qmd-openai-it/config
QMD=/Users/moshe/Desktop/Code/qmd-api/bin/qmd
cd "/Users/moshe/Desktop/Code/Moshe Vault"
node $QMD collection add ./raw   --name sources
node $QMD collection add ./wiki  --name concepts
node $QMD collection add ./index --name indices
node $QMD update
node $QMD embed          # all embeddings via /v1/embeddings — watch for API errors
node $QMD doctor         # "openai backend" check must pass
```

Expected: embed completes with no `OpenAIBackendError`; doctor green.

- [ ] **Step 3: Acceptance queries (from instructions.md §Step 7)**

```bash
node $QMD search "GRPO critic length bias" -n 3
node $QMD query $'intent: find the concept note about GRPO\nlex: GRPO critic\nvec: why GRPO removes the critic model' -n 3
```

Expected: `concepts/grpo-and-variants.md` is the top hit for both; `query` exercises expansion + embedding + rerank through the API.

- [ ] **Step 4: The no-llama proof on a real install tree**

```bash
cd /Users/moshe/Desktop/Code/qmd-api
mv node_modules/node-llama-cpp node_modules/node-llama-cpp.bak
cd "/Users/moshe/Desktop/Code/Moshe Vault"
node $QMD query $'intent: kv cache\nlex: kv cache\nvec: kv cache memory' -n 3   # must succeed
cd /Users/moshe/Desktop/Code/qmd-api
mv node_modules/node-llama-cpp.bak node_modules/node-llama-cpp
```

Expected: the query succeeds with node-llama-cpp physically absent.

- [ ] **Step 5: Clean up**

```bash
rm -rf /tmp/qmd-openai-it
unset QMD_LLM QMD_OPENAI_BASE_URL QMD_OPENAI_EMBED_MODEL QMD_OPENAI_CHAT_MODEL XDG_CACHE_HOME QMD_CONFIG_DIR
```

---

### Task 13: Windows staging checklist (executed later by the user on the staging machine)

**Files (vault repo):**
- Create: `airgap-build/windows/QMD-API-STAGING.md`

- [ ] **Step 1: Write the checklist**

```markdown
# Staging qmd-api for the air gap (Windows x64, Node 26)

Run on the connected Windows x64 staging machine (PowerShell 7+).

1. Prereqs: Node 26.x (`node --version`), git, network access.
2. Build and install the fork globally:
   git clone <qmd-api fork url>; cd qmd-api; git checkout openai-backend
   npm install; npm run build; npm install -g .
   qmd --version        # expect the fork's version string
3. Smoke-test without any model (BM25 only):
   New-Item -ItemType Directory -Force $env:TEMP\qmd-smoke | Out-Null
   '# hello world test note' | Out-File -Encoding utf8 $env:TEMP\qmd-smoke\test.md
   qmd collection add $env:TEMP\qmd-smoke --name smoke
   qmd update
   qmd search "hello world" -n 1          # must return the note
4. Prove the native modules match this ABI:
   node -e "require('$(npm prefix -g)\node_modules\@tobilu\qmd\node_modules\better-sqlite3')" ; echo OK
   (Adjust the path if `npm ls -g better-sqlite3` shows a different layout.)
5. Capture the install tree:
   tar czf qmd-install-tree.tgz -C "$(npm prefix -g)" .
6. Transfer manifest: qmd-install-tree.tgz ONLY — no qmd-models.tgz needed.
7. Inside the gap (per instructions.md Phase B variant):
   tar xzf qmd-install-tree.tgz -C "$(npm prefix -g)"
   Set machine-wide env: QMD_LLM=openai, QMD_OPENAI_BASE_URL, QMD_OPENAI_EMBED_MODEL,
   QMD_OPENAI_CHAT_MODEL (+ optional QMD_OPENAI_RERANK_MODEL, QMD_OPENAI_API_KEY).
   Verify: qmd --version; qmd doctor (openai backend check green).
```

- [ ] **Step 2: Commit (vault repo)**

```bash
cd "/Users/moshe/Desktop/Code/Moshe Vault"
git add airgap-build/windows/QMD-API-STAGING.md
git commit -m "docs: Windows staging checklist for qmd-api fork"
```

---

## Spec coverage self-check

| Spec requirement | Task |
|---|---|
| `OpenAICompatLLM` implementing `LLM` over fetch, no new deps | 4-7 |
| Backend seam `getDefaultLLM()`, default = local, upstream-identical | 7, 8 |
| node-llama-cpp never imported under openai | 8 (tests), 12 (install-tree proof) |
| Env-var configuration incl. optional key/rerank/timeout | 4 |
| embed/embedBatch → /v1/embeddings, batched | 4 |
| generate (HyDE) → chat/completions | 5 |
| expandQuery ported prompt, lex/vec/hyde parse, raw-query fallback on malformed output only | 2, 5 |
| Rerank: configured reranker via chat/completions + logprobs; chat-model fallback tier; text fallback when logprobs absent | 6 |
| Char-based chunking (~4 chars/token) | 7, 8 (chunker test) |
| Fail-fast: API failure fails query, bounded retries 429/5xx/network, clear errors naming env var | 4-6 |
| `qmd embed` visible failure / non-zero exit | 4 (embedBatch throws → CLI `exitWithError`) |
| `qmd doctor`/`status` backend section, /v1/models reachability + model-name check | 9 |
| BM25 `qmd search` works without API | 13 step 3 (smoke), 4 (lazy config) |
| Unit tests: mocked fetch, fail-fast, rerank config selection, chunker | 4-8 |
| Integration test on this Mac, GRPO known-answer acceptance | 12 |
| Upstream suite green with QMD_LLM unset | 1, 10 |
| Packaging: Windows x64/Node 26 install-tree tarball, no models tarball | 13 |
| instructions.md + vault-setup skill updates | 11 |
