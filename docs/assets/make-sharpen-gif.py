"""One-off generator for docs/assets/sharpen-demo.gif — a real /guildproof:sharpen run,
typed out terminal-style. Not part of the package; run once, gif is the committed artifact."""
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))

FONT_PATH = r"C:\Windows\Fonts\CascadiaMono.ttf"
FONT_BOLD_PATH = r"C:\Windows\Fonts\consolab.ttf"
FONT_SIZE = 15
W, H = 1000, 640
BG = (13, 17, 23)
FG = (201, 209, 217)
DIM = (110, 118, 129)
GREEN = (63, 185, 80)
BLUE = (88, 166, 255)
YELLOW = (210, 153, 34)
PAD = 22
LINE_H = 20

font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
font_bold = ImageFont.truetype(FONT_BOLD_PATH, FONT_SIZE)

PROMPT = "/guildproof:sharpen update the settings page to feel calmer and more trustworthy"

BODY = """\
```
ROLE: Act as a senior frontend/UI engineer with a visual-design and
accessibility lens applied.

OBJECTIVE: Restyle the existing settings page so it reads as calm
and trustworthy, without changing what any control does.

REQUIREMENTS:
- Translate "calm": generous whitespace, muted palette, low-contrast
  motion, restrained decoration.
- Translate "trustworthy": consistent iconography, clear hierarchy,
  predictable microcopy, strong affordance on every control.
- Preserve every existing state (empty, loading, error, disabled).

GUARDRAILS (from red-team pass):
- "Calm" must never drop below WCAG AA contrast (4.5:1 text, 3:1 UI).
- If styled component-by-component with no shared tokens, fix at the
  token layer -- not by hand-patching each component.

PROHIBITIONS:
- Don't invent brand colors or tokens that don't exist -- flag
  [brand tokens?] if unsupplied.
- Don't touch settings logic, stored values, or control behavior.
- Don't exceed scope: no new sections, no framework migration.

SUCCESS CRITERIA:
- Passes WCAG AA contrast on all text and UI.
- No functional regression in settings behavior.
```

Assumptions made: audience = general end users * modern-minimal style
family fits "calm + trustworthy" * this is a restyle, not new settings.

Push-back: "calm and trustworthy" gets two different results from two
engineers unless the mechanics are pinned now -- confirm the
translations above before this gets built.

Open questions: What's the actual component stack? Do design tokens
already exist, or does this restyle need to establish them?

(2 open questions -- run with --deep to resolve them first)
"""

body_lines = []
for raw_line in BODY.split("\n"):
    if not raw_line:
        body_lines.append("")
        continue
    wrapped = textwrap.wrap(raw_line, width=78) or [""]
    body_lines.extend(wrapped)

frames = []
durations = []


def render(lines, cursor=False):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, 34], fill=(22, 27, 34))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([PAD + i * 22, 12, PAD + 12 + i * 22, 24], fill=c)
    d.text((W / 2, 17), "PowerShell", font=font, fill=DIM, anchor="mm")
    y = 34 + PAD
    for kind, text in lines:
        color = FG
        f = font
        if kind == "prompt":
            d.text((PAD, y), "PS C:\\dev\\guildproof>", font=font, fill=GREEN)
            offset = font.getlength("PS C:\\dev\\guildproof> ")
            d.text((PAD + offset, y), text, font=font, fill=FG)
            y += LINE_H
            continue
        if kind == "fence":
            color = YELLOW
        elif kind == "req":
            color = BLUE
        elif kind == "dim":
            color = DIM
        d.text((PAD, y), text, font=f, fill=color)
        y += LINE_H
    if cursor:
        d.rectangle([PAD, y, PAD + 9, y + 15], fill=FG)
    return img


def classify(line):
    if line.strip().startswith("```"):
        return "fence"
    if line.strip().startswith(("ROLE:", "OBJECTIVE:", "REQUIREMENTS:", "GUARDRAILS", "PROHIBITIONS:", "SUCCESS CRITERIA:")):
        return "req"
    if line.strip().startswith(("Assumptions", "Push-back", "Open questions", "(2 open")):
        return "dim"
    return "plain"


# Phase 1: type the command
typed = ""
for ch in PROMPT:
    typed += ch
    frames.append(render([("prompt", typed)], cursor=False))
    durations.append(18)
frames.append(render([("prompt", typed)], cursor=False))
durations.append(600)

# Phase 2: reveal output, line by line, command stays pinned at top
shown = [("prompt", typed)]
for line in body_lines:
    shown.append((classify(line), line))
    if len(shown) > 30:
        shown = [shown[0]] + shown[-29:]
    frames.append(render(shown))
    durations.append(45)

frames.append(render(shown))
durations.append(2500)

frames[0].save(
    os.path.join(HERE, "sharpen-demo.gif"),
    save_all=True,
    append_images=frames[1:],
    duration=durations,
    loop=0,
    optimize=True,
)
print("frames:", len(frames))
