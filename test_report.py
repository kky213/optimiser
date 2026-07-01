"""
Optimiser - Local Compression Benchmark
100% offline. No API calls, no AWS, no internet.
Measures token savings using SmartCrusher locally.

Run:  python test_report.py
"""
# Force UTF-8 output on Windows
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import json
import time
from pathlib import Path

# ── Test payloads ─────────────────────────────────────────────────
TESTS = {
    "JSON: 150 search results": json.dumps([
        {"id": i, "file": f"src/module_{i}.py", "line": i * 3,
         "match": f"def process_item_{i}(data, config, timeout=30):",
         "score": round(0.99 - i * 0.001, 3), "size": 1000 + i * 7,
         "type": "function", "module": "core.processor",
         "tags": ["api", "v2"], "status": "active", "owner": f"team_{i%5}"}
        for i in range(1, 151)
    ], indent=2),

    "JSON: 100 log entries": json.dumps([
        {"timestamp": f"2026-07-01T10:{i//60:02d}:{i%60:02d}Z",
         "level": ["INFO", "WARN", "ERROR"][i % 3], "service": f"worker-{i%8}",
         "request_id": f"req-{10000+i}", "user": f"user_{i%20}",
         "endpoint": "/api/v2/items", "duration_ms": 10 + i % 200,
         "status": 200, "tokens": 100 + i * 3, "cache": i % 3 == 0}
        for i in range(100)
    ], indent=2),

    "JSON: 80 file listing": json.dumps([
        {"path": f"src/components/module_{i}/index.tsx",
         "size": 1200 + i * 43, "lines": 80 + i * 2,
         "last_modified": "2026-06-30", "author": f"dev_{i%6}",
         "imports": i % 8, "exports": i % 4,
         "test_coverage": round(60 + i * 0.4, 1),
         "language": "typescript", "status": "active"}
        for i in range(80)
    ], indent=2),

    "JSON: 60 git commits": json.dumps([
        {"hash": f"a{i:06x}", "author": f"dev_{i%5}@company.com",
         "date": f"2026-06-{(i%28)+1:02d}",
         "message": f"fix(module-{i%10}): resolve edge case in processor pipeline step {i}",
         "files_changed": i % 8 + 1, "insertions": i * 4, "deletions": i * 2,
         "branch": f"feature/ticket-{1000+i}", "reviewed": i % 3 != 0}
        for i in range(60)
    ], indent=2),
}

MODEL = "local (no API calls)"
HAIKU_PRICE_PER_1K = 0.00025  # $0.25 per 1M input tokens


def compress_locally(content: str):
    """
    Compress JSON using SmartCrusher.
    SmartCrusher only works on raw JSON, so extract the JSON part from a prompt.
    Returns (original_tokens, compressed_tokens).
    """
    try:
        from optimiser.transforms.smart_crusher import SmartCrusher
        sc = SmartCrusher()

        # Find the start of the JSON array or object
        json_start = -1
        for ch, idx in [(c, i) for i, c in enumerate(content)]:
            if ch in ('[', '{'):
                json_start = idx
                break

        if json_start != -1:
            prefix      = content[:json_start]
            json_part   = content[json_start:]
            result      = sc.crush(json_part)
            if result.was_modified:
                compressed  = prefix + result.compressed
                orig_tok    = len(content) // 4
                comp_tok    = len(compressed) // 4
                return orig_tok, comp_tok
        # Fallback: try full content
        result = sc.crush(content)
        orig_tok = len(content) // 4
        if result.was_modified:
            return orig_tok, len(result.compressed) // 4
        return orig_tok, orig_tok
    except Exception as e:
        print(f"  Warning: SmartCrusher unavailable ({e})")
        orig_tok = len(content) // 4
        return orig_tok, orig_tok


# ── Run ───────────────────────────────────────────────────────────

print()
print("=" * 62)
print("  OPTIMISER - LOCAL COMPRESSION BENCHMARK")
print("  100% offline  |  no API  |  no internet")
print("=" * 62)
print()

rows = []
total_orig = total_comp = 0

for name, content in TESTS.items():
    prompt = f"Summarise this data in one sentence:\n\n{content}"
    t0 = time.perf_counter()
    orig_tok, comp_tok = compress_locally(prompt)
    elapsed = round(time.perf_counter() - t0, 4)

    saved_tok = orig_tok - comp_tok
    saved_pct = round(saved_tok / max(orig_tok, 1) * 100, 1)
    total_orig += orig_tok
    total_comp += comp_tok

    rows.append({
        "name":          name,
        "direct_in":     orig_tok,
        "direct_out":    0,
        "direct_s":      elapsed,
        "comp_local_in": comp_tok,
        "saved_tok":     saved_tok,
        "saved_pct":     saved_pct,
        "proxy_in":      comp_tok,
        "direct_error":  None,
    })

    bar_len  = 36
    bar_fill = int(bar_len * comp_tok / max(orig_tok, 1))
    bar_str  = "#" * bar_fill + "-" * (bar_len - bar_fill)
    print(f"  {name}")
    print(f"    Original  : {orig_tok:>7,} tokens")
    print(f"    Compressed: {comp_tok:>7,} tokens  ({saved_pct:.1f}% saved)")
    print(f"    [{bar_str}]")
    print()

# ── Summary ───────────────────────────────────────────────────────
total_saved = total_orig - total_comp
total_pct   = round(total_saved / max(total_orig, 1) * 100, 1)
cost_orig   = total_orig / 1000 * HAIKU_PRICE_PER_1K
cost_comp   = total_comp / 1000 * HAIKU_PRICE_PER_1K
cost_saved  = round(cost_orig - cost_comp, 6)

print("=" * 62)
print("  TOTALS")
print("=" * 62)
print(f"  {'Test':<34} {'Before':>8} {'After':>8} {'Saved%':>7}")
print(f"  {'-'*58}")
for r in rows:
    print(f"  {r['name']:<34} {r['direct_in']:>8,} {r['comp_local_in']:>8,} {r['saved_pct']:>6.1f}%")
print(f"  {'-'*58}")
print(f"  {'TOTAL':<34} {total_orig:>8,} {total_comp:>8,} {total_pct:>6.1f}%")
print()
print(f"  Tokens saved       : {total_saved:,}")
print(f"  Cost without (est.): ${cost_orig:.5f}")
print(f"  Cost with (est.)   : ${cost_comp:.5f}")
print(f"  Cost saved (est.)  : ${cost_saved:.5f}  per identical run")
print()
print("  Note: cost estimate uses Haiku pricing ($0.25/1M input).")
print("        Actual savings depend on your model + backend.")
print("=" * 62)
print()

# ── Save report ───────────────────────────────────────────────────
report = {
    "model": MODEL,
    "tests": rows,
    "summary": {
        "total_direct_tokens":           total_orig,
        "total_compressed_tokens":       total_comp,
        "tokens_saved":                  total_saved,
        "savings_pct":                   total_pct,
        "input_cost_direct_usd":         round(cost_orig,  6),
        "input_cost_with_optimiser_usd": round(cost_comp,  6),
        "input_cost_saved_usd":          cost_saved,
    },
}
out = Path(__file__).parent / "test_report_result.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"  Report saved: {out}")
print()
