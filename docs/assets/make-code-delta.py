"""One-off generator for the CODE-delta proof asset (the dev-facing variant):
    docs/assets/proof-code-delta.png  — side-by-side, buggy retry fn vs safe retry fn
    docs/assets/proof-code-delta.gif  — animates the four beats

This is the outcome-first cut: it shows the ANSWER the prompt buys, for readers who want to see
the code rather than the prompt. The above-the-fold hero is the prompt delta (make-prompt-delta.py);
this one lives deeper in the README for a dev audience.

Content is drawn VERBATIM from docs/assets/proof-answer-delta.md. The "before" answer is a fair,
competent retry function with a hidden production bug (retried non-idempotent POST = double charge),
not a strawman - that fairness is the credibility. Do not dumb it down to widen the delta.

Not part of the package; run once, the image + gif are the committed artifacts."""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))

FONT_PATH = r"C:\Windows\Fonts\CascadiaMono.ttf"
FONT_BOLD_PATH = r"C:\Windows\Fonts\consolab.ttf"
FS = 15
font = ImageFont.truetype(FONT_PATH, FS)
font_b = ImageFont.truetype(FONT_BOLD_PATH, FS)
font_sm = ImageFont.truetype(FONT_PATH, 13)
font_title = ImageFont.truetype(FONT_BOLD_PATH, 17)

BG = (13, 17, 23)
PANEL = (22, 27, 34)
FG = (201, 209, 217)
DIM = (110, 118, 129)
COMMENT = (139, 148, 158)
GREEN = (63, 185, 80)
BLUE = (88, 166, 255)
YELLOW = (210, 153, 34)
RED = (248, 81, 73)
RED_BG = (45, 22, 24)
GREEN_BG = (18, 38, 24)
LINE_H = 20

NAIVE_PROMPT = "write a function to retry a failed API call"
SHARP_PROMPT = "/guildproof:sharpen write a function to retry a failed API call"

NAIVE_CODE = """\
async function retry(fn, attempts = 3, delayMs = 500) {
  let lastErr;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      await new Promise(r => setTimeout(r, delayMs * 2 ** i)); // exponential backoff
    }
  }
  throw lastErr;
}""".split("\n")

SHARP_CODE = """\
async function retry(fn, {
  maxAttempts = 4,
  deadlineMs = 10_000,
  idempotent = false,          // MUST be true (or carry a key) to retry writes
  isRetryable = defaultRetryable,
} = {}) {
  const start = Date.now();
  let attempt = 0, lastErr;
  while (attempt < maxAttempts && Date.now() - start < deadlineMs) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (!isRetryable(err) || !idempotent) throw err; // unsafe/non-retryable: stop
      const retryAfter = err.retryAfterMs ?? 0;
      const backoff = Math.min(2 ** attempt * 200, 2000);
      const jitter = backoff * (0.5 + Math.random() * 0.5); // jitter, no storm
      await new Promise(r => setTimeout(r, Math.max(retryAfter, jitter)));
      attempt++;
    }
  }
  throw lastErr;
}

function defaultRetryable(err) {
  if (err.code === 'ECONNRESET' || err.code === 'ETIMEDOUT') return true;
  const s = err.status;
  return s === 429 || (s >= 500 && s <= 599);   // never 4xx except 429
}""".split("\n")

NAIVE_BUG = [
    "Retries every failure identically - including a POST /charge that",
    "already succeeded on the server but timed out on the wire. That is a",
    "DOUBLE CHARGE. It also retries 400s and 403s that can never succeed.",
    "The prompt never said the call was safe to retry, so the model assumed.",
]
SHARP_WIN = [
    "Retries only when it is safe AND can succeed. It refused to retry a",
    "write it was never told is idempotent - and made that a required",
    "argument instead of guessing. The refusal to guess is the whole point.",
]


def draw_code_line(d, x, y, line, base=FG):
    if "//" in line and not line.strip().startswith("//"):
        code, _, comment = line.partition("//")
        d.text((x, y), code, font=font, fill=base)
        d.text((x + font.getlength(code), y), "//" + comment, font=font, fill=COMMENT)
    elif line.strip().startswith("//"):
        d.text((x, y), line, font=font, fill=COMMENT)
    else:
        d.text((x, y), line, font=font, fill=base)


def build_png():
    COL_W = 840
    GUT = 26
    MARGIN = 26
    W = MARGIN * 2 + COL_W * 2 + GUT
    header_h = 96
    prompt_h = 58
    code_h = len(SHARP_CODE) * LINE_H + 24
    callout_h = 96
    col_h = prompt_h + code_h + callout_h
    H = header_h + col_h + 74

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((MARGIN, 22), "The answer delta", font=font_title, fill=FG)
    d.text((MARGIN, 50), "Same model. Same task. The only thing that changed is the prompt.",
           font=font_sm, fill=DIM)

    def column(x0, prompt_prefix, prompt_text, prefix_color, code, callout, accent, accent_bg, tag):
        y = header_h
        d.rounded_rectangle([x0, y, x0 + COL_W, header_h + col_h], radius=8, fill=PANEL)
        d.rounded_rectangle([x0 + 16, y + 14, x0 + 16 + font_sm.getlength(tag) + 16, y + 36],
                            radius=6, fill=accent_bg)
        d.text((x0 + 24, y + 17), tag, font=font_sm, fill=accent)
        py = y + 46
        d.text((x0 + 16, py), prompt_prefix, font=font, fill=prefix_color)
        d.text((x0 + 16 + font.getlength(prompt_prefix), py), prompt_text, font=font, fill=FG)
        cy = py + 34
        for ln in code:
            draw_code_line(d, x0 + 16, cy, ln)
            cy += LINE_H
        box_top = header_h + col_h - callout_h + 6
        d.rounded_rectangle([x0 + 12, box_top, x0 + COL_W - 12, header_h + col_h - 10],
                            radius=6, fill=accent_bg)
        ly = box_top + 12
        for i, ln in enumerate(callout):
            f = font_b if i == 0 else font_sm
            col = accent if i == 0 else FG
            d.text((x0 + 22, ly), ln, font=f, fill=col)
            ly += 18

    column(MARGIN, "$ ", NAIVE_PROMPT, DIM, NAIVE_CODE, NAIVE_BUG, RED, RED_BG,
           "what you type  ->  the answer it gets")
    column(MARGIN + COL_W + GUT, "", SHARP_PROMPT, GREEN, SHARP_CODE, SHARP_WIN, GREEN, GREEN_BG,
           "sharpened first  ->  the answer that gets")

    cap_y = H - 54
    d.text((MARGIN, cap_y),
           "The naive prompt got a function that double-charges. The sharpened prompt got one that",
           font=font_sm, fill=DIM)
    d.text((MARGIN, cap_y + 20),
           "refuses to retry a write it was never told is safe - and said so, instead of guessing.",
           font=font_sm, fill=DIM)
    d.text((W - MARGIN - font_b.getlength("guildproof"), cap_y + 10), "guildproof",
           font=font_b, fill=BLUE)

    out = os.path.join(HERE, "proof-code-delta.png")
    img.save(out)
    print("PNG:", out, img.size)


GW, GH = 1040, 720
GPAD = 22


def gframe(rows, cursor=False):
    img = Image.new("RGB", (GW, GH), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, GW - 1, 34], fill=PANEL)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([GPAD + i * 22, 12, GPAD + 12 + i * 22, 24], fill=c)
    d.text((GW / 2, 17), "PowerShell", font=font, fill=DIM, anchor="mm")
    y = 34 + GPAD
    for kind, text in rows:
        if kind == "blank":
            y += LINE_H
            continue
        if kind == "prompt":
            pre = "PS C:\\dev> "
            d.text((GPAD, y), pre, font=font, fill=GREEN)
            d.text((GPAD + font.getlength(pre), y), text, font=font, fill=FG)
        elif kind == "sharp":
            pre = "PS C:\\dev> "
            d.text((GPAD, y), pre, font=font, fill=GREEN)
            d.text((GPAD + font.getlength(pre), y), text, font=font, fill=BLUE)
        elif kind == "req":
            d.text((GPAD, y), text, font=font, fill=BLUE)
        elif kind == "bug":
            d.text((GPAD, y), text, font=font_b if text and text[0] != " " else font, fill=RED)
        elif kind == "win":
            d.text((GPAD, y), text, font=font_b if text and text[0] != " " else font, fill=GREEN)
        elif kind == "comment":
            d.text((GPAD, y), text, font=font, fill=COMMENT)
        elif kind == "dim":
            d.text((GPAD, y), text, font=font, fill=DIM)
        else:
            draw_code_line(d, GPAD, y, text)
        y += LINE_H
    if cursor:
        d.rectangle([GPAD, y, GPAD + 9, y + 15], fill=FG)
    return img


def codrows(lines, kind="plain"):
    return [(kind, ln) for ln in lines]


def build_gif():
    frames, durs = [], []

    def hold(rows, ms, cursor=False):
        frames.append(gframe(rows, cursor))
        durs.append(ms)

    def type_out(kind, text, base_rows=None):
        base = base_rows or []
        typed = ""
        for ch in text:
            typed += ch
            frames.append(gframe(base + [(kind, typed)], cursor=True))
            durs.append(20)
        return base + [(kind, typed)]

    def reveal(base, rows, ms=48):
        shown = list(base)
        for r in rows:
            shown.append(r)
            if len(shown) > 30:
                shown = shown[:1] + shown[-29:]
            frames.append(gframe(shown))
            durs.append(ms)
        return shown

    base = type_out("prompt", NAIVE_PROMPT)
    hold(base, 500, cursor=True)
    after1 = reveal(base + [("blank", "")], codrows(NAIVE_CODE))
    hold(after1, 700)
    bug_rows = [("blank", "")] + [("bug", ln) for ln in
                ["This ships a bug:", "  a retried POST /charge that already succeeded = a DOUBLE CHARGE.",
                 "  The prompt never said the call was safe to retry."]]
    after2 = reveal(after1, bug_rows, ms=70)
    hold(after2, 1600)

    base3 = type_out("sharp", SHARP_PROMPT)
    hold(base3, 500, cursor=True)
    prompt_preview = [
        ("dim", "-> returns a prompt with the decisions the one-liner left unstated:"),
        ("blank", ""),
        ("req", "REQUIREMENTS:"),
        ("plain", "- Retry only retryable failures (timeouts, 429, 5xx). Never 4xx."),
        ("plain", "- Backoff WITH jitter; a total deadline, not just max attempts."),
        ("req", "PROHIBITIONS:"),
        ("plain", "- Do NOT retry a non-idempotent POST unless the caller gives a key."),
        ("req", "OPEN QUESTION:"),
        ("comment", "- Is this call idempotent? I will not guess - that is the double charge."),
    ]
    after3 = reveal(base3 + [("blank", "")], prompt_preview, ms=55)
    hold(after3, 1400)

    base4 = [("sharp", SHARP_PROMPT), ("blank", "")]
    after4 = reveal(base4, codrows(SHARP_CODE), ms=40)
    win_rows = [("blank", "")] + [("win", ln) for ln in
                ["Refuses to retry a write it was never told is safe - and says so,",
                 "instead of guessing. Same model. Same task. Only the prompt changed."]]
    after4 = reveal(after4, win_rows, ms=70)
    hold(after4, 3000)

    out = os.path.join(HERE, "proof-code-delta.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durs, loop=0, optimize=True)
    print("GIF:", out, "frames:", len(frames))


if __name__ == "__main__":
    build_png()
    build_gif()
