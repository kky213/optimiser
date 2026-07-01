"""
Optimiser Compression Test — no API call needed
Tests compression locally and shows before/after token savings.
Run: python test_report.py
"""

import sys
import os
import json
import time
import urllib.request

PROXY_URL = "http://127.0.0.1:8787"

# ── Test payloads (real-world shapes) ────────────────────────────

TESTS = {
    "JSON tool output (200 search results)": json.dumps([
        {"id": i, "file": f"src/module_{i}.py", "line": i * 3,
         "match": f"def process_item_{i}(data, config, timeout=30):",
         "score": round(0.99 - i * 0.001, 3), "size": 1000 + i * 7,
         "type": "function", "module": "core.processor",
         "tags": ["api", "v2"], "status": "active"}
        for i in range(1, 201)
    ], indent=2),

    "Python source file (large)": "\n".join([
        f"""
class Processor_{i}:
    def __init__(self, config):
        self.config = config
        self.id = {i}

    def process(self, data):
        result = []
        for item in data:
            if item.get('active'):
                result.append({{'id': item['id'], 'value': item['value'] * {i}}})
        return result

    def validate(self, data):
        return all(k in data for k in ['id', 'value', 'active'])
""" for i in range(1, 31)
    ]),

    "Log output (500 lines)": "\n".join([
        f"2026-07-01 10:{i//60:02d}:{i%60:02d} INFO  [worker-{i%8}] "
        f"Processing request id={10000+i} user=user_{i%50} "
        f"endpoint=/api/v2/items duration={10+i%200}ms status=200 "
        f"tokens_used={100+i*3} cache={'hit' if i%3==0 else 'miss'}"
        for i in range(500)
    ]),

    "Git diff (large PR)": "\n".join([
        f"""diff --git a/src/module_{i}.py b/src/module_{i}.py
index abc{i:04d}..def{i:04d} 100644
--- a/src/module_{i}.py
+++ b/src/module_{i}.py
@@ -{i*10},{i*10+8} +{i*10},{i*10+10} @@
-    old_value_{i} = compute(x, {i})
-    return old_value_{i}
+    new_value_{i} = compute_optimized(x, {i}, cache=True)
+    logger.debug(f"computed {{new_value_{i}}}")
+    return new_value_{i}
"""
        for i in range(1, 41)
    ]),
}


def estimate_tokens(text):
    return len(text) // 4


def compress_via_proxy(content):
    """Call the proxy's MCP compress endpoint."""
    try:
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "headroom_compress",
                "arguments": {"content": content}
            },
            "id": 1
        }).encode()

        req = urllib.request.Request(
            f"{PROXY_URL}/mcp",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            result = data.get("result", {})
            if isinstance(result, dict):
                content_list = result.get("content", [])
                if content_list:
                    text = content_list[0].get("text", "")
                    parsed = json.loads(text)
                    return {
                        "compressed": parsed.get("compressed", ""),
                        "original_tokens": parsed.get("original_tokens", 0),
                        "compressed_tokens": parsed.get("compressed_tokens", 0),
                        "savings_percent": parsed.get("savings_percent", 0),
                    }
    except Exception:
        pass
    return None


def compress_local(content):
    """Compress using SmartCrusher (JSON) or raw token estimate for other types."""
    try:
        orig_tokens = estimate_tokens(content)

        from optimiser.transforms.smart_crusher import SmartCrusher
        sc = SmartCrusher()
        result = sc.crush(content)
        if result and result.was_modified:
            comp_tokens = estimate_tokens(result.compressed)
        else:
            comp_tokens = orig_tokens
        saved = orig_tokens - comp_tokens
        return {
            "compressed": result.compressed if result else content,
            "original_tokens": orig_tokens,
            "compressed_tokens": comp_tokens,
            "savings_percent": round(saved / max(orig_tokens, 1) * 100, 1),
        }
    except Exception as e:
        return {"error": str(e)}


def check_proxy():
    try:
        with urllib.request.urlopen(f"{PROXY_URL}/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def get_proxy_stats():
    try:
        with urllib.request.urlopen(f"{PROXY_URL}/stats", timeout=2) as r:
            return json.loads(r.read())
    except Exception:
        return None


def run_test(name, content):
    orig_tokens = estimate_tokens(content)
    t0 = time.time()
    result = compress_local(content)
    elapsed = round(time.time() - t0, 3)

    if "error" in result:
        return {"name": name, "error": result["error"]}

    comp_tokens = result["compressed_tokens"]
    saved = orig_tokens - comp_tokens
    pct = result["savings_percent"]

    return {
        "name": name,
        "original_tokens": orig_tokens,
        "compressed_tokens": comp_tokens,
        "tokens_saved": saved,
        "savings_pct": pct,
        "elapsed_s": elapsed,
    }


# ── Main ─────────────────────────────────────────────────────────

print()
print("=" * 56)
print("   OPTIMISER COMPRESSION TEST")
print("=" * 56)
print()

proxy_up = check_proxy()
print(f"  Proxy status : {'RUNNING' if proxy_up else 'NOT RUNNING (local compress only)'}")
print(f"  Mode         : Local compression library")
print()

results = []
total_orig = 0
total_comp = 0

for name, content in TESTS.items():
    print(f"  Testing: {name}...")
    r = run_test(name, content)
    results.append(r)
    if "error" not in r:
        total_orig += r["original_tokens"]
        total_comp += r["compressed_tokens"]

total_saved = total_orig - total_comp
total_pct   = round(total_saved / max(total_orig, 1) * 100, 1)
cost_before = round(total_orig / 1_000_000 * 3.0, 5)   # $3/1M tokens (Haiku)
cost_after  = round(total_comp / 1_000_000 * 3.0, 5)
cost_saved  = round(cost_before - cost_after, 5)

print()
print("=" * 56)
print("  RESULTS")
print("=" * 56)
print(f"  {'Test':<34} {'Before':>7} {'After':>7} {'Saved%':>7}")
print(f"  {'-'*54}")
for r in results:
    if "error" in r:
        print(f"  {r['name']:<34} ERROR: {r['error'][:20]}")
    else:
        print(f"  {r['name']:<34} {r['original_tokens']:>7,} {r['compressed_tokens']:>7,} {r['savings_pct']:>6.1f}%")

print(f"  {'-'*54}")
print(f"  {'TOTAL':<34} {total_orig:>7,} {total_comp:>7,} {total_pct:>6.1f}%")
print()
print(f"  Tokens saved  : {total_saved:,}")
print(f"  Cost without  : ${cost_before:.5f}")
print(f"  Cost with     : ${cost_after:.5f}")
print(f"  Cost saved    : ${cost_saved:.5f}  (per this test run)")
print()

# Proxy session stats
if proxy_up:
    stats = get_proxy_stats()
    if stats:
        tok = stats.get("tokens", {})
        req = stats.get("requests", {})
        print(f"  Proxy session total:")
        print(f"    Requests     : {req.get('total', 0):,}")
        print(f"    Tokens saved : {tok.get('saved', 0):,}")
        print(f"    Compression  : {tok.get('savings_percent', 0):.1f}%")
        print()

print("=" * 56)
print()

# Save JSON report
report = {
    "tests": results,
    "summary": {
        "total_original_tokens": total_orig,
        "total_compressed_tokens": total_comp,
        "total_tokens_saved": total_saved,
        "savings_pct": total_pct,
        "cost_before_usd": cost_before,
        "cost_after_usd": cost_after,
        "cost_saved_usd": cost_saved,
    }
}
with open("test_report_result.json", "w") as f:
    json.dump(report, f, indent=2)
print(f"  Report saved to: test_report_result.json")
print()
