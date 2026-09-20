---
description: "Turn a rough request into a sharpened, gap-filled, professionally-reviewed prompt ready to paste into any agent."
usage: "/guildproof:sharpen <rough request> [--lens name,name] [--deep] — e.g. /guildproof:sharpen update the dashboard to feel calmer and more authoritative --lens ux-designer,visual-design"
category: "dev"
---

Sharpen a one-off task request into a complete, executable prompt. Model-agnostic — the
output is plain text you can paste into any agent or chat.

## Step 1 — Load the engine

Read `${CLAUDE_PLUGIN_ROOT}/skills/prompt-engineering/SKILL.md` in full. It defines the
pipeline. This command runs that pipeline on the **SHARPEN** path.

> **Paths.** `${CLAUDE_PLUGIN_ROOT}` is this plugin's install directory, substituted
> automatically — never a literal folder in the user's project. If guildproof was installed
> standalone (README Option B, no plugin root), read from `~/.claude/` instead:
> `~/.claude/skills/…`, `~/.claude/guildproof-templates/`, `~/.claude/guildproof-lenses/`,
> `~/.claude/guildproof-agents/`. Never resolve these against the user's working directory.

## Step 2 — Parse arguments

Parse `$ARGUMENTS`:
- `--lens <a,b>` — explicit lenses to apply. If absent, auto-pick by topic (engine Step 5).
- `--deep` — run the interactive interview instead of assuming (engine Step 7). Ask the
  open questions one at a time, wait for answers, then synthesize.
- Everything else = the rough request to sharpen.

If the request is empty, ask the user what they want to sharpen and stop.

## Step 3 — Run the engine

Execute engine Steps 2–7 with route = SHARPEN:
1. Extract goal, audience, tone/feel/theme, constraints, success criteria, format, scope.
2. Gap-fill with labeled assumptions (unless `--deep`, then ask).
3. Red-team the request; turn findings into guardrails.
4. Load and apply the selected lenses (built-in + user dirs).
5. Synthesize using `${CLAUDE_PLUGIN_ROOT}/templates/sharpened-prompt.md`.

## Step 4 — Output

Lead with the **Prompt** block in a copy-pasteable code fence. Then, separated below it:
the assumptions you made, the 1–2 push-backs worth hearing, and the open questions —
ending with an offer to rerun with `--deep` for a deeper pass.

No preamble. The artifact comes first.
