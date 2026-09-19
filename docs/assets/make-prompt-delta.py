"""One-off generator for the prompt-delta proof asset:
    docs/assets/proof-prompt-delta.png  — the workhorse still image (skims into HN/LinkedIn/dev.to)
    docs/assets/proof-prompt-delta.gif  — animates the reveal (social / dev.to asset)

Design: three visually distinct layers.
  1. TITLE BAND (top, sans) — the header, its own band, clearly not terminal text.
  2. TERMINAL WINDOW (middle, mono) — the mock guildproof output, unchanged terminal styling.
  3. ANNOTATION BUBBLES (right gutter, sans) — margin commentary as bubbles with leader lines,
     collectively distinct from the mono terminal output.
  4. SUMMARY FOOTER BAND (bottom, sans) — the takeaway, its own band.

Each margin bubble names the decision the one-liner left unstated, so the prompt's length reads
as recovered senior judgment, not padding. The honesty-floor bubble (idempotency) is styled green.

Content faithful to docs/assets/proof-answer-delta.md (the fleshed prompt, Panel 3).
Not part of the package; run once, the image + gif are the committed artifacts."""
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))

# ---- fonts: MONO for terminal, SANS for header/footer/annotations (the visual distinction) ----
MONO = r"C:\Windows\Fonts\CascadiaMono.ttf"
SANS = r"C:\Windows\Fonts\segoeui.ttf"
SANS_B = r"C:\Windows\Fonts\segoeuib.ttf"
SANS_SB = r"C:\Windows\Fonts\seguisb.ttf"
SANS_I = r"C:\Windows\Fonts\segoeuii.ttf"

mono = ImageFont.truetype(MONO, 20)
mono_lbl = ImageFont.truetype(MONO, 14)
title_f = ImageFont.truetype(SANS_B, 34)
sub_f = ImageFont.truetype(SANS, 18)
ann_f = ImageFont.truetype(SANS_I, 18)      # annotations italic sans — reads as commentary
foot_f = ImageFont.truetype(SANS_SB, 22)
foot_sf = ImageFont.truetype(SANS, 17)

# ---- palette: three depth levels so the bands separate from the terminal ----
CANVAS = (9, 12, 16)        # darkest — the page behind everything
TERM = (14, 19, 26)         # terminal interior (mid)
CHROME = (28, 34, 42)       # terminal title bar
BAND = (24, 30, 39)         # title + footer bands (lightest) — visually distinct
FG = (201, 209, 217)
DIM = (128, 138, 150)
CREAM = (245, 240, 232)
COPPER = (184, 115, 51)
COPPER_LT = (212, 146, 74)
BLUE = (88, 166, 255)
GREEN = (80, 200, 120)
BUB_BG = (40, 29, 17)       # copper-tinted bubble
BUB_BR = (150, 96, 44)
BUBG_BG = (18, 40, 25)      # green (honesty) bubble
BUBG_BR = (54, 120, 74)

# ---- geometry ----
W = 1480
TERM_X, TERM_Y, TERM_W = 28, 150, 960
CHROME_H, PAD, LH = 42, 18, 30
CONTENT_X = TERM_X + 20
CONTENT_Y0 = TERM_Y + CHROME_H + PAD
TERM_RIGHT = TERM_X + TERM_W
BUB_X = TERM_RIGHT + 36
GUT_W = W - BUB_X - 28
TITLE_H = 128

CMD = "/guildproof:sharpen write a function to retry a failed API call"

# OUTPUT prompt rows: (kind, text). kind: head=blue section label, body=FG, blank
ROWS = [
    ("head", "ROLE: a backend engineer who treats a retry as a"),
    ("body", "      correctness decision, not a loop."),
    ("head", "OBJECTIVE: retry ONLY when retrying is safe and can succeed."),
    ("blank", ""),
    ("head", "REQUIREMENTS:"),
    ("body", "- Retry only retryable failures: timeouts, 429, 5xx."),
    ("body", "  Never 4xx (except 429) - they only waste the budget."),
    ("body", "- Exponential backoff WITH jitter."),
    ("body", "- A total deadline, not just a max attempt count."),
    ("body", "- Honor a Retry-After header on 429/503."),
    ("blank", ""),
    ("head", "PROHIBITIONS (must NOT do):"),
    ("body", "- NEVER retry a non-idempotent POST unless the caller"),
    ("body", "  supplies an idempotency key."),
    ("body", "- Do NOT swallow the final error; surface what failed."),
    ("blank", ""),
    ("head", "OPEN QUESTION (answer before building):"),
    ("body", "- Is this call idempotent / does it carry a key?"),
    ("body", "  The retry is only safe if yes. I will not guess."),
]

# annotations: (ROWS index, text, is_honesty_floor)
ANNOTS = [
    (5, "you never said which failures are safe to retry", False),
    (7, "the thundering-herd storm you'd forget", False),
    (8, "attempts aren't time - one slow call runs past a count", False),
    (12, "the one line that stops a double charge", False),
    (17, "honesty floor: flags what it can't know, won't guess", True),
]

TERM_PREFIX = 2  # cmd row 0 + blank row 1 precede ROWS in the terminal


def row_y(rows_idx):
    return CONTENT_Y0 + (TERM_PREFIX + rows_idx) * LH


TERM_ROWS_TOTAL = TERM_PREFIX + len(ROWS)
TERM_H = CHROME_H + PAD + TERM_ROWS_TOTAL * LH + PAD
TERM_BOTTOM = TERM_Y + TERM_H
FOOT_Y = TERM_BOTTOM + 30
FOOT_H = 122
H = FOOT_Y + FOOT_H + 24


def draw_title_band(d):
    d.rectangle([0, 0, W, TITLE_H], fill=BAND)
    d.rectangle([0, TITLE_H - 2, W, TITLE_H], fill=COPPER)      # accent rule under the band
    d.rectangle([28, 34, 36, 94], fill=COPPER)                  # copper marker block
    d.text((52, 30), "The prompt delta", font=title_f, fill=CREAM)
    d.text((52, 82), "One line in. The prompt a senior would have written — out.",
           font=sub_f, fill=DIM)
    tag = "GUILDPROOF · /sharpen"
    d.text((W - 28 - mono_lbl.getlength(tag), 54), tag, font=mono_lbl, fill=COPPER_LT)


def draw_terminal(d, typed_cmd, n_rows):
    d.rounded_rectangle([TERM_X, TERM_Y, TERM_RIGHT, TERM_BOTTOM], radius=9, fill=TERM,
                        outline=(44, 52, 62), width=1)
    d.rounded_rectangle([TERM_X, TERM_Y, TERM_RIGHT, TERM_Y + CHROME_H], radius=9, fill=CHROME)
    d.rectangle([TERM_X, TERM_Y + CHROME_H - 9, TERM_RIGHT, TERM_Y + CHROME_H], fill=CHROME)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([TERM_X + 18 + i * 22, TERM_Y + 15, TERM_X + 30 + i * 22, TERM_Y + 27], fill=c)
    d.text((TERM_X + TERM_W / 2, TERM_Y + 21), "PowerShell", font=mono, fill=DIM, anchor="mm")
    pre = "PS C:\\dev> "
    y = CONTENT_Y0
    d.text((CONTENT_X, y), pre, font=mono, fill=GREEN)
    d.text((CONTENT_X + mono.getlength(pre), y), typed_cmd, font=mono, fill=FG)
    if n_rows == 0:
        cx = CONTENT_X + mono.getlength(pre) + mono.getlength(typed_cmd)
        d.rectangle([cx, y, cx + 11, y + 21], fill=FG)
        return
    for i, (kind, text) in enumerate(ROWS[:n_rows]):
        yy = CONTENT_Y0 + (TERM_PREFIX + i) * LH
        if kind == "head":
            d.text((CONTENT_X, yy), text, font=mono, fill=BLUE)
        elif kind == "body":
            d.text((CONTENT_X, yy), text, font=mono, fill=FG)


def draw_bubbles(d, n_prompt_rows, shown):
    """Annotation bubbles (sans) in the gutter with leader lines to their terminal line.
    Declutters vertically so adjacent bubbles never overlap."""
    last_bottom = TITLE_H + 10
    for idx, (r_idx, text, honesty) in enumerate(ANNOTS):
        if idx not in shown or r_idx >= n_prompt_rows:
            continue
        anchor_y = row_y(r_idx) + 11
        lines = textwrap.wrap(text, 44) or [text]
        bh = len(lines) * 24 + 20
        bw = min(GUT_W, max(ann_f.getlength(l) for l in lines) + 32)
        top = max(anchor_y - bh / 2, last_bottom + 12)
        center = top + bh / 2
        bg, br, fg = (BUBG_BG, BUBG_BR, GREEN) if honesty else (BUB_BG, BUB_BR, COPPER_LT)
        d.ellipse([TERM_RIGHT - 4, anchor_y - 4, TERM_RIGHT + 4, anchor_y + 4], fill=br)
        d.line([TERM_RIGHT + 4, anchor_y, BUB_X, center], fill=br, width=2)
        d.rounded_rectangle([BUB_X, top, BUB_X + bw, top + bh], radius=11, fill=bg, outline=br, width=1)
        ty = top + 10
        for l in lines:
            d.text((BUB_X + 16, ty), l, font=ann_f, fill=fg)
            ty += 24
        last_bottom = top + bh


def draw_footer(d, show_text):
    d.rectangle([0, FOOT_Y, W, FOOT_Y + FOOT_H], fill=BAND)
    d.rectangle([0, FOOT_Y, W, FOOT_Y + 2], fill=COPPER)        # accent rule above the band
    if not show_text:
        return
    d.rectangle([28, FOOT_Y + 30, 36, FOOT_Y + 92], fill=GREEN)  # green marker block
    d.text((52, FOOT_Y + 24), "THE POINT", font=mono_lbl, fill=GREEN)
    d.text((52, FOOT_Y + 46),
           "Same one-liner. The scaffolding a senior adds — named, so you don't have to remember to, every time.",
           font=foot_f, fill=CREAM)
    d.text((52, FOOT_Y + 82),
           "It never invents the answer to “is this idempotent?” — it flags it. That refusal to guess is the point.",
           font=foot_sf, fill=DIM)


def scene(typed_cmd, n_rows, shown_bubbles, footer_text):
    img = Image.new("RGB", (W, H), CANVAS)
    d = ImageDraw.Draw(img)
    draw_title_band(d)
    draw_footer(d, footer_text)
    draw_terminal(d, typed_cmd, n_rows)
    draw_bubbles(d, n_rows, shown_bubbles)
    return img


def build_png():
    img = scene(CMD, len(ROWS), set(range(len(ANNOTS))), True)
    out = os.path.join(HERE, "proof-prompt-delta.png")
    img.save(out)
    print("PNG:", out, img.size)


def build_gif():
    frames, durs = [], []

    def add(img, ms):
        frames.append(img)
        durs.append(ms)

    typed = ""
    for ch in CMD:
        typed += ch
        add(scene(typed, 0, set(), False), 20)
    add(scene(CMD, 0, set(), False), 650)
    for n in range(1, len(ROWS) + 1):
        add(scene(CMD, n, set(), False), 55)
    add(scene(CMD, len(ROWS), set(), False), 700)
    shown = set()
    for idx in range(len(ANNOTS)):
        shown = set(shown) | {idx}
        add(scene(CMD, len(ROWS), set(shown), False), 110)
        add(scene(CMD, len(ROWS), set(shown), False), 600)
    add(scene(CMD, len(ROWS), set(range(len(ANNOTS))), True), 3200)

    out = os.path.join(HERE, "proof-prompt-delta.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durs, loop=0, optimize=True)
    print("GIF:", out, "frames:", len(frames))


if __name__ == "__main__":
    build_png()
    build_gif()
