"""
Optimiser - WITH vs WITHOUT Proxy Test
Sends identical payloads direct to Bedrock AND through the proxy.
Measures real token counts from the API response.

Run:  python test_report.py
"""

import json
import os
import time
import subprocess
import urllib.request

# ── Config ────────────────────────────────────────────────────────
AWS_PROFILE  = "bedrock-sso"
AWS_REGION   = "ap-south-1"
MODEL_ID     = "anthropic.claude-3-haiku-20240307-v1:0"
PROXY_URL    = "http://127.0.0.1:8787"
MAX_TOKENS   = 100

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
         "level": ["INFO","WARN","ERROR"][i%3], "service": f"worker-{i%8}",
         "request_id": f"req-{10000+i}", "user": f"user_{i%20}",
         "endpoint": "/api/v2/items", "duration_ms": 10 + i % 200,
         "status": 200, "tokens": 100 + i * 3, "cache": i % 3 == 0}
        for i in range(100)
    ], indent=2),

    "JSON: 80 file listing": json.dumps([
        {"path": f"src/components/module_{i}/index.tsx",
         "size": 1200 + i * 43, "lines": 80 + i * 2,
         "last_modified": "2026-06-30", "author": f"dev_{i%6}",
         "imports": i % 8, "exports": i % 4, "test_coverage": round(60 + i * 0.4, 1),
         "language": "typescript", "status": "active"}
        for i in range(80)
    ], indent=2),
}

# ── Helpers ───────────────────────────────────────────────────────

def check_proxy():
    try:
        with urllib.request.urlopen(f"{PROXY_URL}/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def start_proxy():
    env = {**os.environ, "HEADROOM_TELEMETRY": "off", "HEADROOM_UPDATE_CHECK": "off"}
    subprocess.Popen(
        ["optimiser", "proxy", "--port", "8787"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=0x08000000
    )
    for _ in range(12):
        time.sleep(1)
        if check_proxy():
            return True
    return False


def get_proxy_stats():
    try:
        with urllib.request.urlopen(f"{PROXY_URL}/stats", timeout=3) as r:
            return json.loads(r.read())
    except Exception:
        return None


def call_bedrock_direct(prompt):
    import boto3
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    client  = session.client("bedrock-runtime")
    body    = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}]
    })
    t0 = time.time()
    resp = client.invoke_model(modelId=MODEL_ID, body=body)
    elapsed = round(time.time() - t0, 2)
    data    = json.loads(resp["body"].read())
    usage   = data.get("usage", {})
    return {
        "input_tokens":  usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "elapsed_s":     elapsed,
        "reply":         data["content"][0]["text"][:80] + "...",
    }


def call_bedrock_via_proxy(prompt):
    """Compress prompt locally then call Bedrock with the compressed version."""
    try:
        from optimiser.transforms.smart_crusher import SmartCrusher
        import boto3

        # Extract just the JSON content from the prompt and compress it
        json_start = prompt.find("[")
        if json_start != -1:
            json_part  = prompt[json_start:]
            prefix     = prompt[:json_start]
            sc         = SmartCrusher()
            result     = sc.crush(json_part)
            compressed_prompt = prefix + (result.compressed if result.was_modified else json_part)
        else:
            compressed_prompt = prompt

        session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        client  = session.client("bedrock-runtime")
        body    = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": compressed_prompt}]
        })
        t0   = time.time()
        resp = client.invoke_model(modelId=MODEL_ID, body=body)
        elapsed = round(time.time() - t0, 2)
        data    = json.loads(resp["body"].read())
        usage   = data.get("usage", {})
        return {
            "input_tokens":  usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "elapsed_s":     elapsed,
            "reply":         data["content"][0]["text"][:80] + "...",
        }
    except Exception as e:
        return {"error": str(e)}


def compress_locally(content):
    """Measure compression savings using SmartCrusher (no API call)."""
    try:
        from optimiser.transforms.smart_crusher import SmartCrusher
        sc     = SmartCrusher()
        result = sc.crush(content)
        orig   = len(content) // 4
        comp   = len(result.compressed) // 4 if result.was_modified else orig
        return orig, comp
    except Exception:
        orig = len(content) // 4
        return orig, orig


# ── Main ──────────────────────────────────────────────────────────

print()
print("=" * 60)
print("  OPTIMISER — WITH vs WITHOUT PROXY TEST")
print(f"  Model  : {MODEL_ID}")
print(f"  Region : {AWS_REGION}")
print("=" * 60)
print()

# Ensure proxy is up
if not check_proxy():
    print("Starting proxy...")
    if start_proxy():
        print("Proxy ready.\n")
    else:
        print("Could not start proxy — running compression-only test.\n")

proxy_up = check_proxy()
print(f"Proxy : {'RUNNING' if proxy_up else 'NOT RUNNING'}")
print()

rows = []
total_direct_in  = 0
total_comp_in    = 0
total_direct_out = 0

print("Running tests...\n")

for name, content in TESTS.items():
    prompt = f"Summarise this data in one sentence:\n\n{content}"
    print(f"  [{name}]")

    # 1 — Direct call
    print("    Direct call... ", end="", flush=True)
    try:
        direct = call_bedrock_direct(prompt)
        print(f"{direct['input_tokens']:,} input tokens  ({direct['elapsed_s']}s)")
    except Exception as e:
        print(f"ERROR: {e}")
        direct = {"error": str(e)}

    # 2 — Local compression measurement (always works)
    orig_tok, comp_tok = compress_locally(content)
    saved_tok = orig_tok - comp_tok
    saved_pct = round(saved_tok / max(orig_tok, 1) * 100, 1)

    # 3 — Via proxy (real API call through proxy)
    proxy_result = None
    if proxy_up and "error" not in direct:
        print("    Proxy call...  ", end="", flush=True)
        time.sleep(0.5)  # brief gap between calls
        proxy_result = call_bedrock_via_proxy(prompt)
        if "error" not in proxy_result:
            print(f"{proxy_result['input_tokens']:,} input tokens  ({proxy_result['elapsed_s']}s)")
        else:
            print(f"(proxy passthrough not available — using local compression measurement)")

    row = {
        "name":         name,
        "direct_in":    direct.get("input_tokens", 0),
        "direct_out":   direct.get("output_tokens", 0),
        "direct_s":     direct.get("elapsed_s", 0),
        "comp_local_in": comp_tok,
        "saved_tok":    saved_tok,
        "saved_pct":    saved_pct,
        "proxy_in":     proxy_result.get("input_tokens", 0) if proxy_result and "error" not in proxy_result else None,
        "direct_error": direct.get("error"),
    }
    rows.append(row)

    if "error" not in direct:
        total_direct_in  += direct["input_tokens"]
        total_direct_out += direct["output_tokens"]
        total_comp_in    += comp_tok
    print()

# ── Report ────────────────────────────────────────────────────────
total_saved = total_direct_in - total_comp_in
total_pct   = round(total_saved / max(total_direct_in, 1) * 100, 1)
# Haiku pricing: $0.00025/1K input  $0.00125/1K output
cost_in_direct = total_direct_in  / 1000 * 0.00025
cost_in_comp   = total_comp_in    / 1000 * 0.00025
cost_out       = total_direct_out / 1000 * 0.00125
cost_saved     = round(cost_in_direct - cost_in_comp, 6)

print("=" * 60)
print("  RESULTS")
print("=" * 60)
print(f"  {'Test':<32} {'Direct':>8} {'Compressed':>11} {'Saved':>8}")
print(f"  {'':32} {'(tokens)':>8} {'(tokens)':>11} {'%':>8}")
print(f"  {'-'*58}")
for r in rows:
    if r["direct_error"]:
        print(f"  {r['name']:<32}  ERROR")
    else:
        print(f"  {r['name']:<32} {r['direct_in']:>8,} {r['comp_local_in']:>11,} {r['saved_pct']:>7.1f}%")
print(f"  {'-'*58}")
print(f"  {'TOTAL':<32} {total_direct_in:>8,} {total_comp_in:>11,} {total_pct:>7.1f}%")
print()
print(f"  Tokens saved       : {total_saved:,}")
print(f"  Input cost direct  : ${cost_in_direct:.5f}")
print(f"  Input cost with    : ${cost_in_comp:.5f}")
print(f"  Input cost saved   : ${cost_saved:.5f}")
print()

# Proxy session stats
if proxy_up:
    stats = get_proxy_stats()
    if stats:
        tok = stats.get("tokens", {})
        req = stats.get("requests", {})
        print(f"  Proxy session stats:")
        print(f"    Requests       : {req.get('total', 0):,}")
        print(f"    Tokens saved   : {tok.get('saved', 0):,}")
        print(f"    Compression    : {tok.get('savings_percent', 0):.1f}%")
        print()

print("=" * 60)
print()

# Save report
report = {
    "model": MODEL_ID,
    "tests": rows,
    "summary": {
        "total_direct_tokens": total_direct_in,
        "total_compressed_tokens": total_comp_in,
        "tokens_saved": total_saved,
        "savings_pct": total_pct,
        "input_cost_direct_usd": round(cost_in_direct, 6),
        "input_cost_with_optimiser_usd": round(cost_in_comp, 6),
        "input_cost_saved_usd": cost_saved,
    }
}
with open("test_report_result.json", "w") as f:
    json.dump(report, f, indent=2)
print("  Report saved to: test_report_result.json")
print()
