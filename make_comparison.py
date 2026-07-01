"""
Generate comparison chart from test_report_result.json.
100% local — no internet, no API.

Run:  python make_comparison.py
"""

import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Load results ──────────────────────────────────────────────────
RESULT = Path(__file__).parent / "test_report_result.json"
if not RESULT.exists():
    print("Run test_report.py first to generate results.")
    raise SystemExit(1)

data    = json.loads(RESULT.read_text(encoding="utf-8"))
tests   = [t for t in data["tests"] if not t.get("direct_error")]
summary = data["summary"]

# Up to 4 tests shown in chart
tests = tests[:4]

# ── Style ─────────────────────────────────────────────────────────
W, H  = 1100, 160 + len(tests) * 140 + 120
BG         = (15, 17, 23)
DARK_GREY  = (51,  65,  85)
WHITE      = (255, 255, 255)
GREY       = (148, 163, 184)
RED        = (239,  68,  68)
GREEN      = (34,  197,  94)
GOLD       = (251, 191,  36)
BLUE       = (99,  102, 241)


def load_font(size):
    for p in ("C:/Windows/Fonts/consola.ttf",
              "C:/Windows/Fonts/cour.ttf",
              "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def rr(draw, xy, fill, r=10):
    draw.rounded_rectangle(xy, radius=r, fill=fill)


# ── Build image ───────────────────────────────────────────────────
img  = Image.new("RGB", (W, H), BG)
d    = ImageDraw.Draw(img)

f_title = load_font(22)
f_head  = load_font(16)
f_body  = load_font(14)
f_sm    = load_font(13)
f_num   = load_font(28)
f_xs    = load_font(11)

# Header
d.text((40, 22), "OPTIMISER — Token Compression Benchmark",
       fill=WHITE, font=f_title)
d.text((40, 52), "100% local  |  no API calls  |  no internet  |  pure SmartCrusher",
       fill=GREY, font=f_sm)
d.line([(40, 78), (W-40, 78)], fill=DARK_GREY, width=1)

# Column headers
rr(d, [20, 88, 500, 116], (60, 20, 20))
d.text((36, 94), "WITHOUT  Optimiser", fill=RED, font=f_head)
rr(d, [520, 88, 1000, 116], (15, 50, 30))
d.text((536, 94), "WITH  Optimiser", fill=GREEN, font=f_head)

MAX_T = max(t["direct_in"] for t in tests) * 1.05

row_y = 138
for i, t in enumerate(tests):
    y   = row_y + i * 140
    wo  = t["direct_in"]
    wi  = t["comp_local_in"]
    pct = t["saved_pct"]

    d.text((40, y), t["name"], fill=WHITE, font=f_head)

    # WITHOUT card
    rr(d, [20, y+26, 490, y+108], (40, 22, 22))
    d.text((36, y+32), f"{wo:,}", fill=RED, font=f_num)
    d.text((36 + 130, y+44), "tokens", fill=GREY, font=f_sm)
    fw = int(400 * wo / MAX_T)
    d.rounded_rectangle([36, y+78, 36+400, y+92], radius=5, fill=DARK_GREY)
    if fw: d.rounded_rectangle([36, y+78, 36+fw, y+92], radius=5, fill=RED)

    # WITH card
    rr(d, [510, y+26, 980, y+108], (17, 40, 27))
    d.text((526, y+32), f"{wi:,}", fill=GREEN, font=f_num)
    d.text((526 + 100, y+44), "tokens", fill=GREY, font=f_sm)
    cw = int(400 * wi / MAX_T)
    d.rounded_rectangle([526, y+78, 526+400, y+92], radius=5, fill=DARK_GREY)
    if cw: d.rounded_rectangle([526, y+78, 526+cw, y+92], radius=5, fill=GREEN)

    # Badge
    rr(d, [990, y+42, W-10, y+90], (40, 35, 10))
    d.text((998, y+46), f"-{pct:.0f}%", fill=GOLD, font=f_head)
    d.text((998, y+68), "saved",        fill=GREY, font=f_xs)

# Divider + totals
ty   = row_y + len(tests) * 140 + 8
d.line([(40, ty), (W-40, ty)], fill=DARK_GREY, width=1)
ty  += 14

tw = summary["total_direct_tokens"]
tc = summary["total_compressed_tokens"]
tp = summary["savings_pct"]
cs = summary["input_cost_saved_usd"]

d.text((40, ty), f"TOTAL ({len(tests)} tasks)", fill=WHITE, font=f_head)

rr(d, [20, ty+26, 490, ty+88], (50, 20, 20))
d.text((36, ty+30), f"{tw:,}", fill=RED, font=f_num)
d.text((36+160, ty+44), "tokens", fill=GREY, font=f_sm)

rr(d, [510, ty+26, 980, ty+88], (17, 45, 27))
d.text((526, ty+30), f"{tc:,}", fill=GREEN, font=f_num)
d.text((526+130, ty+44), "tokens", fill=GREY, font=f_sm)

rr(d, [990, ty+30, W-10, ty+88], (50, 40, 5))
d.text((998, ty+32), f"-{tp:.0f}%",     fill=GOLD, font=load_font(22))
d.text((998, ty+56), f"~${cs:.5f} saved", fill=GOLD, font=f_xs)

# Footer
fy = H - 36
d.line([(40, fy-10), (W-40, fy-10)], fill=DARK_GREY, width=1)
d.text((40, fy),    "Local build — no telemetry, no API, no cloud", fill=GREY, font=f_xs)
d.text((W-280, fy), "github.com/kky213/optimiser",                  fill=BLUE, font=f_xs)

# Save
out = Path(__file__).parent / "comparison.png"
img.save(str(out), dpi=(150, 150))
print(f"Chart saved: {out}")
