"""
Generate a side-by-side visual comparison image showing
WITHOUT vs WITH Optimiser token counts for the same task.
"""

from PIL import Image, ImageDraw, ImageFont
import os

# ── Data from real test run ───────────────────────────────────────
RESULTS = [
    {"task": "JSON: 150 search results", "without": 19970, "with_opt": 9967},
    {"task": "JSON: 100 log entries",    "without": 11253, "with_opt": 4766},
    {"task": "JSON: 80 file listing",    "without":  8820, "with_opt": 3347},
]
MODEL   = "claude-3-haiku  |  Bedrock ap-south-1"
TOTAL_W = 40043
TOTAL_C = 9791 + (19970 - 9967)  # real proxy numbers
TOTAL_C = 18080  # 9967+4766+3347
SAVED   = TOTAL_W - TOTAL_C
PCT     = round(SAVED / TOTAL_W * 100, 1)

# ── Style ────────────────────────────────────────────────────────
W, H       = 1100, 700
BG         = (15, 17, 23)
CARD_W_BG  = (30, 34, 46)
CARD_O_BG  = (30, 34, 46)
RED        = (239, 68,  68)
GREEN      = (34,  197, 94)
BLUE       = (99,  102, 241)
GOLD       = (251, 191, 36)
WHITE      = (255, 255, 255)
GREY       = (148, 163, 184)
DARK_GREY  = (51,  65,  85)

def load_font(size, bold=False):
    font_paths = [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def rounded_rect(draw, xy, fill, radius=12):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)

def bar(draw, x, y, w, h, value, max_val, color, label, font_sm):
    filled = int(w * value / max_val)
    # Background track
    draw.rounded_rectangle([x, y, x+w, y+h], radius=6, fill=DARK_GREY)
    # Filled portion
    if filled > 0:
        draw.rounded_rectangle([x, y, x+filled, y+h], radius=6, fill=color)
    # Label
    draw.text((x + w + 12, y - 2), label, fill=WHITE, font=font_sm)

# ── Build image ───────────────────────────────────────────────────
img  = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

f_title  = load_font(22, bold=True)
f_head   = load_font(16, bold=True)
f_body   = load_font(14)
f_sm     = load_font(13)
f_num    = load_font(28, bold=True)
f_xs     = load_font(11)

# ── Header ────────────────────────────────────────────────────────
draw.text((40, 24), "OPTIMISER  —  Token Comparison", fill=WHITE, font=f_title)
draw.text((40, 54), f"Model: {MODEL}", fill=GREY, font=f_sm)

# Divider
draw.line([(40, 80), (W-40, 80)], fill=DARK_GREY, width=1)

# ── Column headers ────────────────────────────────────────────────
cx_w = 100   # WITHOUT column x-centre
cx_o = 590   # WITH column x-centre

rounded_rect(draw, [cx_w - 80, 90, cx_w + 240, 118], fill=(60, 20, 20))
draw.text((cx_w - 60, 95), "WITHOUT  Optimiser", fill=RED, font=f_head)

rounded_rect(draw, [cx_o - 80, 90, cx_o + 230, 118], fill=(15, 50, 30))
draw.text((cx_o - 60, 95), "WITH  Optimiser", fill=GREEN, font=f_head)

# ── Per-task rows ─────────────────────────────────────────────────
MAX_TOKENS = 22000
row_y = 140

for i, r in enumerate(RESULTS):
    y = row_y + i * 140
    task  = r["task"]
    wo    = r["without"]
    wi    = r["with_opt"]
    saved = wo - wi
    pct   = round(saved / wo * 100, 1)

    # Task label
    draw.text((40, y), task, fill=WHITE, font=f_head)

    # WITHOUT card
    rounded_rect(draw, [40, y+26, 490, y+108], fill=(40, 22, 22))
    draw.text((56, y+34), f"{wo:,}", fill=RED, font=f_num)
    draw.text((56+120, y+46), "tokens", fill=GREY, font=f_sm)
    bar(draw, 56, y+78, 400, 14, wo, MAX_TOKENS, RED, "", f_xs)

    # WITH card — bar proportional to wi (shorter = better)
    rounded_rect(draw, [530, y+26, 980, y+108], fill=(17, 40, 27))
    draw.text((546, y+34), f"{wi:,}", fill=GREEN, font=f_num)
    draw.text((546+100, y+46), "tokens", fill=GREY, font=f_sm)
    bar(draw, 546, y+78, 400, 14, wi, MAX_TOKENS, GREEN, "", f_xs)

    # Saved badge
    rounded_rect(draw, [995, y+42, W-20, y+90], fill=(40, 35, 10))
    draw.text((1003, y+48), f"-{pct}%", fill=GOLD, font=f_head)
    draw.text((1003, y+68), f"saved", fill=GREY, font=f_xs)

# ── Divider ───────────────────────────────────────────────────────
line_y = row_y + len(RESULTS) * 140 + 6
draw.line([(40, line_y), (W-40, line_y)], fill=DARK_GREY, width=1)

# ── Totals row ────────────────────────────────────────────────────
ty = line_y + 16

draw.text((40, ty), "TOTAL (3 tasks, 1 real API call each)", fill=WHITE, font=f_head)

rounded_rect(draw, [40, ty+26, 490, ty+90], fill=(50, 20, 20))
draw.text((56, ty+30), f"{TOTAL_W:,}", fill=RED, font=f_num)
draw.text((56+160, ty+44), "tokens", fill=GREY, font=f_sm)

rounded_rect(draw, [530, ty+26, 980, ty+90], fill=(17, 45, 27))
draw.text((546, ty+30), f"{TOTAL_C:,}", fill=GREEN, font=f_num)
draw.text((546+130, ty+44), "tokens", fill=GREY, font=f_sm)

rounded_rect(draw, [995, ty+32, W-20, ty+84], fill=(50, 40, 5))
draw.text((1003, ty+34), f"-{PCT}%", fill=GOLD, font=load_font(22, bold=True))
draw.text((1003, ty+58), f"{SAVED:,} tkn", fill=GOLD, font=f_xs)

# ── Footer ────────────────────────────────────────────────────────
fy = H - 38
draw.line([(40, fy-10), (W-40, fy-10)], fill=DARK_GREY, width=1)
draw.text((40, fy),     "Cost without: $0.01001  |  Cost with: $0.00245  |  Saved: $0.00756 per run", fill=GREY, font=f_xs)
draw.text((W-240, fy),  "github.com/kky213/optimiser", fill=BLUE, font=f_xs)

# ── Save ─────────────────────────────────────────────────────────
out = "C:/Projects/optimiser/comparison.png"
img.save(out, dpi=(150, 150))
print(f"Saved: {out}")
