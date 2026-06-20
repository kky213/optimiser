# Optimiser — Feature & Concept Reference

> How every saving mechanism works, why it exists, and when it fires.

---

## The Core Idea

Every time your AI tool (Claude Code, Cursor, Copilot) makes an API call, it sends
the **entire conversation history** to the model — every file it read, every search
result, every log line — again and again, every single turn.

Optimiser sits between your tool and the API as a local proxy on port 8787.
It intercepts each request, shrinks the payload, and forwards the smaller version.
The model never knows. Your tool never changes.

```
Your Tool (Claude Code)
        │
        │  ANTHROPIC_BASE_URL=http://127.0.0.1:8787
        ▼
┌───────────────────┐
│   OPTIMISER       │  ← compresses, caches, shapes, remembers
│   port 8787       │
└───────────────────┘
        │
        ▼
Anthropic / OpenAI / Gemini API
```

---

## Feature 1 — Content-Aware Compression (Input Tokens)

**What it solves:** Tool outputs (file reads, search results, logs) accumulate in
context and get re-sent every turn, even when the model already processed them.

**How it works:**

When a request arrives, the pipeline inspects every message block and classifies
its content type. It then routes each block to the compressor best suited for it.
This happens before the request leaves your machine — the API never sees the
original size.

```
Request message block
        │
        ▼
┌──────────────────────────────────────────────────┐
│  ContentRouter                                    │
│                                                   │
│  Magika ML detector (first)                       │
│  Regex fallback (if Magika uncertain)             │
│                                                   │
│  JSON array?  ────────► SmartCrusher (Rust)       │
│  Source code? ────────► CodeCompressor (AST)      │
│  Log output?  ────────► LogCompressor             │
│  grep/rg?     ────────► SearchCompressor          │
│  Git diff?    ────────► DiffCompressor            │
│  Plain text?  ────────► KompressML (BERT ONNX)    │
│  Mixed?       ────────► Split, route each section │
└──────────────────────────────────────────────────┘
        │
        ▼
  Compressed block (55–80% smaller)
```

---

### SmartCrusher — JSON Arrays (Rust, highest savings)

**Concept:** JSON tool outputs are almost always arrays of objects with identical
keys. Sending `{"path":"a","size":100,"type":"file"}` a thousand times is wasteful.
SmartCrusher detects the shared schema and converts the array to a compact
table format — like CSV with a header row.

**Applied:** Any tool output that is a JSON array (file listings, search results,
grep output piped through jq, API responses). Must save at least 15% to apply
(lossless threshold).

```
Before:
[
  {"path": "src/main.py", "size": 1240, "type": "file"},
  {"path": "src/utils.py", "size": 890, "type": "file"},
  ... (1000 items)
]

After:
[["path","size","type"],["src/main.py",1240,"file"],["src/utils.py",890,"file"],...]
(+ sentinel object marking that CCR can expand)
```

**Savings:** 60–80% on large JSON arrays.

---

### CodeCompressor — Source Code (AST-aware)

**Concept:** When the model has already read a file, re-sending its full body every
turn is wasteful. CodeCompressor parses the code with `tree-sitter`, identifies
functions and classes the model has seen, replaces their bodies with a
`// ... (N lines)` placeholder, and keeps only the signature and line number.

**Applied:** Only to code the model has already processed in this session.
New code is never compressed. Languages: Python, JavaScript, TypeScript, Rust,
Go, Java, C/C++, and more via tree-sitter language pack.

```
Before (turn 3, model already read this file in turn 1):
def process_drawing(path: str, config: Config) -> Result:
    data = load_file(path)
    validated = validate_schema(data, config.schema)
    ... (80 more lines)
    return Result(validated)

After:
def process_drawing(path: str, config: Config) -> Result:
    # ... (83 lines, see turn 1 read) [CCR:f3a9c1]
```

**Savings:** 40–70% on repeated file reads.

---

### LogCompressor — Build/Test Output

**Concept:** Build logs and test runners emit the same lines repeatedly (stack
frames, warnings, identical error messages). LogCompressor deduplicates them,
strips ANSI escape codes and timestamps from repeated lines, and collapses
identical stack trace runs.

**Applied:** Any tool output that looks like a build log, test run, or terminal
output — detected by patterns like timestamps, log levels (INFO/WARN/ERROR),
ANSI sequences.

```
Before:
[2026-06-20 10:01:01] WARNING: deprecated API in module X
[2026-06-20 10:01:02] WARNING: deprecated API in module X
[2026-06-20 10:01:03] WARNING: deprecated API in module X
... (47 more)

After:
WARNING: deprecated API in module X  (×50)
```

**Savings:** 50–90% on verbose test/build output.

---

### SearchCompressor — grep / ripgrep Results

**Concept:** Search results repeat the file path on every match line. When a file
has 20 matching lines, the path is sent 20 times. SearchCompressor groups matches
by file, keeps the path once as a header, and lists only the line numbers and
matched content.

**Applied:** Output that matches the pattern of `rg`, `grep`, or `find` — file
path followed by line number and matched text.

```
Before:
src/proxy/server.py:142: from optimiser.config import
src/proxy/server.py:143: from optimiser.config import
src/proxy/handlers/anthropic.py:88: from optimiser.config import

After:
src/proxy/server.py [lines 142-143]: from optimiser.config import
src/proxy/handlers/anthropic.py [line 88]: from optimiser.config import
```

**Savings:** 30–60% on large grep outputs.

---

### KompressML — Plain Text (BERT ONNX)

**Concept:** For plain prose, documentation, or unstructured text, a fine-tuned
BERT model (all-MiniLM-L6-v2, ~86MB ONNX) scores each sentence by importance.
Low-scoring sentences are dropped. The model receives only the high-signal content.

**Applied:** Any text block that doesn't match the structural patterns above.
Requires `pip install optimiser-ai[ml]`. Without `[ml]`, this layer is skipped
and the content passes through unchanged.

**Savings:** 15–40% on prose and documentation.

---

## Feature 2 — CCR (Compress-Cache-Retrieve)

**What it solves:** Lossless compression means some information is removed. What
if the model actually needs that information later?

**Concept:** CCR makes compression *reversible on demand*. When content is
compressed, the original is stored in a local SQLite database keyed by SHA-256
hash. A short sentinel marker replaces the removed content. A retrieval tool
(`headroom_retrieve`) is injected into the request. If the model determines it
needs the full content, it calls the tool with the hash — the proxy intercepts
that call and returns the original from SQLite. The model only pays the token
cost if it genuinely needs the data.

```
Turn 1 — File read (5 000 tokens):

  Proxy compresses → 800 tokens
  Stores original in ~/.optimiser/ccr.db  (key: f3a9c1...)
  Injects marker:  "... [CCR:f3a9c1] ..."
  Injects tool:    headroom_retrieve(hash) → available to model

  Model sees 800 tokens.

Turn 2 — Model needs full file:

  Model calls: headroom_retrieve(hash="f3a9c1")
  Proxy intercepts (never reaches Anthropic API)
  Proxy returns original 5 000 tokens from SQLite
  Model continues with full content

Turn 3+ — Model doesn't need it again:

  Only the 800-token compressed version stays in context
```

**CCR Learning (our addition):** Every retrieval is logged to
`~/.optimiser/ccr_retrievals.jsonl`. This builds a dataset of which compressions
the model had to undo, enabling future threshold tuning — content types that get
retrieved often should be compressed less aggressively.

**Savings:** Reduces baseline context by 60–80%. The retrieve cost only occurs
when the model actually needs expansion.

---

## Feature 3 — Output Shaping (Output Tokens)

**What it solves:** Output tokens cost 5× more than input tokens on Claude.
Agentic tools like Claude Code pin `effort=xhigh` on every single turn — even
trivial mechanical steps like reading a file or running a test that passed.

**Concept:** Output shaping works on two levers, both applied to the *request*
(never to the response — the proxy never generates tokens):

### Lever A — Verbosity Steering

A deterministic instruction block is appended to the tail of the system prompt,
*after* any `cache_control` breakpoint so the provider's prefix cache is
preserved. Five levels:

| Level | Instruction |
|---|---|
| 1 | No preamble or postamble — start with the substance |
| 2 | + Never restate code/files already in context, reference by path |
| 3 | + Conclusions only, omit rationale unless asked |
| 4 | + Minimum tokens, fragments acceptable |
| 5 | Full caveman mode |

Default in Optimiser: **Level 2** (safe, no information loss).

### Lever B — Effort Routing

Every turn is classified structurally (no content regex):

```
Last message is a clean tool_result (file read, passing test)?
  → MECHANICAL_CONTINUATION  → lower effort: xhigh → medium

Last message contains error indicators?
  → ERROR_CONTINUATION       → leave effort alone (errors need thinking)

Last message is a human turn?
  → NEW_USER_ASK             → leave effort alone
```

This means routine steps in a long agentic loop cost 60–70% less thinking tokens.
The proxy only *lowers* an effort value the client already sent — it never
injects effort where the client didn't include it (would cause a 400 on some models).

**Savings:** 20–40% on output tokens across a long session.

---

## Feature 4 — Prefix Cache Protection

**What it solves:** Anthropic's prompt cache gives a 90% discount on input tokens
for messages it has seen before. But cache hits require the prefix to be byte-for-byte
identical. One UUID, one timestamp, one rotating JWT in the system prompt — and
every turn is a cache miss, paying the full write penalty.

**Two components work together:**

### CacheAligner — Volatile Content Detector

Scans the system prompt for content that changes every request:

- **UUIDs** — detected via `uuid.UUID()` parse, not regex (avoids false positives on MD5 hashes)
- **ISO 8601 timestamps** — detected via `datetime.fromisoformat()`
- **JWTs** — detected by `xxxxx.yyyyy.zzzzz` three-part base64 structure
- **Rotating tokens** — detected by entropy analysis

When found, the aligner flags the span so the compressor knows the prefix is
unstable. Future versions will canonicalise (replace with stable placeholders).

### PrefixCacheTracker — Freeze Already-Cached Messages

After each API response, the proxy reads the `cache_read_input_tokens` field.
On the next turn it freezes exactly that many messages — skips them in the
compression pipeline entirely — so the cached prefix is never modified.

```
Turn 1:  Send 3 000 tokens. API reports 2 800 tokens cached.
Turn 2:  Proxy freezes the first 2 800 tokens (don't touch them).
         Only compresses the new 200 tokens added this turn.
         Cache hit: those 2 800 tokens cost 10% of normal price.
```

**Savings:** Cache hits cost 10% vs 125% (write penalty) — a 12× cost difference.
Worth protecting aggressively.

---

## Feature 5 — Memory (Cross-Session Context)

**What it solves:** Every new session starts blank. The model re-reads the same
files, re-learns the same project structure, repeats the same reasoning from
yesterday.

**Concept:** The memory system stores important context from each session in a
local SQLite vector database. At the start of each new request, the proxy does a
semantic similarity search against stored memories and injects the top-10 most
relevant results into the system prompt — before the model ever sees the request.

```
Session A (yesterday):
  Model learned: "DrawOps uses Next.js 14 app router, client files
                  are under /app/(clients)/[clientId]/"
  → Stored in ~/.optimiser/memory.db as an embedding vector

Session B (today):
  User asks: "add a new page for client files"
  Proxy:  embeds the query → semantic search → finds yesterday's memory
          → injects: "[Memory: DrawOps uses Next.js 14 app router...]"
          → model already knows the architecture without re-reading files
```

**Embedder:** `all-MiniLM-L6-v2` ONNX model (~86MB, runs locally, no API call).

**Async lookup (our addition):** Memory search fires as a background async task
the moment the request arrives — in parallel with the compression pipeline. By the
time compression finishes, the memory result is already ready. Zero added latency.

**Backends:** Local SQLite (default, no setup), Qdrant, Neo4j, Mem0.

**Savings:** Entire tool_result blocks (Read, Glob, Grep) never enter context
for information the model already knows.

---

## How All Layers Stack in a Real Request

Here is what happens for a single turn in a typical Claude Code session:

```
1. Request arrives at port 8787
   └─ Contains: system prompt + 15 turns of history + new user message

2. PrefixCacheTracker
   └─ Identifies first 12 messages as cached prefix → marks them FROZEN

3. Memory lookup fires (async, background)
   └─ Embeds the new user message → queries vector DB

4. ContentRouter compresses unfrozen messages (turns 13–15)
   ├─ Turn 13: JSON file listing → SmartCrusher → 71% smaller
   ├─ Turn 14: Python source → CodeCompressor → 58% smaller  
   └─ Turn 15: Test log output → LogCompressor → 83% smaller

5. Memory result arrives (was computing in background)
   └─ 2 relevant memories found → injected into system prompt tail

6. CCR
   └─ Compressed turns 13–15 stored in SQLite with hash sentinels
   └─ headroom_retrieve tool injected into request tools list

7. Output Shaper
   ├─ Turn 15 was a clean tool_result → MECHANICAL_CONTINUATION
   ├─ effort: xhigh → medium (60% less thinking tokens)
   └─ Verbosity level 2 instruction appended to system prompt

8. Request forwarded to Anthropic (12× cheaper on cached prefix,
   compressed new content, shaped output)

9. Response streams back through proxy unchanged
   └─ CCR context tracker updated for next turn
```

**Net result for this turn:**
- Input tokens: ~72% reduction on new content, 90% discount on cached prefix
- Output tokens: ~35% reduction from effort routing
- Session memory: model skips 2 file reads it would have done otherwise

---

## Quick Reference — Which Feature Saves What

| Scenario | Feature | Typical Saving |
|---|---|---|
| Large JSON tool output (search, ls) | SmartCrusher | 60–80% |
| Same file read twice | CodeCompressor + CCR | 55–70% |
| Verbose test failure log | LogCompressor | 50–90% |
| grep across large codebase | SearchCompressor | 30–60% |
| Model re-doing yesterday's work | Memory | Entire tool calls skipped |
| Every turn in long agentic loop | Prefix Cache Freeze | 90% cost on cached messages |
| Mechanical steps (file reads, passing tests) | Effort Routing | 20–40% output tokens |
| Model narrating what it's about to do | Verbosity Steering | 15–30% output tokens |
| Model needs compressed content back | CCR Retrieve | One-time cost, on demand only |

---

## Configuration Reference

All features are **ON by default** in Optimiser. Override via environment variables:

```bash
# Disable specific features
OPTIMISER_INTERCEPT_ENABLED=0    # Turn off all input compression
HEADROOM_OUTPUT_SHAPER=0         # Turn off output shaping
OPTIMISER_MEMORY=0               # Turn off cross-session memory
HEADROOM_VERBOSITY_LEVEL=1       # Set verbosity (1–5, default 2)

# Start with features selectively off
optimiser start --no-memory --no-output-shaping

# Check what's running
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/stats
```
