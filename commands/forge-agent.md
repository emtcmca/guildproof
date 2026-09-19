---
description: "Author a complete, reusable agent system prompt from a short description — role, objective, method, guardrails, output contract, and baked-in push-back."
usage: "/guildproof:forge-agent <description of the agent you want> [--lens name,name] [--deep] — e.g. /guildproof:forge-agent a reviewer that critiques HOA letters for tone and compliance"
category: "dev"
---

Turn a short description into a complete, reusable agent system prompt. Output is plain
text you can drop into a subagent, a skill, a custom GPT, or any system-prompt field.

## Step 1 — Load the engine

Read `${CLAUDE_PLUGIN_ROOT}/skills/prompt-engineering/SKILL.md` in full. This command runs the
**FORGE** path.

> **Paths.** `${CLAUDE_PLUGIN_ROOT}` is this plugin's install directory, substituted
> automatically — never a literal folder in the user's project. If guildproof was installed
> standalone (README Option B, no plugin root), read from `~/.claude/` instead:
> `~/.claude/skills/…`, `~/.claude/guildproof-templates/`, `~/.claude/guildproof-lenses/`,
> `~/.claude/guildproof-agents/`. Never resolve these against the user's working directory.

## Step 2 — Parse arguments

Parse `$ARGUMENTS`:
- `--lens <a,b>` — lenses to bake into the agent's standing behavior. If absent, auto-pick
  the lens(es) that match the agent's domain (e.g. an editor agent → `editorial`).
- `--deep` — interview one question at a time instead of assuming (engine Step 7).
- Everything else = the description of the agent to build.

If the description is empty, ask what agent to build and stop.

## Step 3 — Seed from the gallery (if a match exists)

Before building cold, check the gallery at `${CLAUDE_PLUGIN_ROOT}/agents/` for a specialist whose
role is close to the request (the roster index is `${CLAUDE_PLUGIN_ROOT}/docs/agent-gallery.md`).
If one matches, **read it and
adapt it** — swap domain, tone, and lenses to fit the description — rather than starting from
a blank page. If nothing is close, forge fresh. Either way, the output meets the same bar.

## Step 4 — Run the engine

Execute engine Steps 2–7 with route = FORGE. Key differences from SHARPEN:
- **Durable, not one-off.** Write for *every* future run, not one task. Avoid task-specific detail.
- **Bake in the lens.** The selected lens(es) become standing operating principles, not a
  one-time pass — the agent should always think like that professional.
- **Bake in push-back.** Include an explicit self-challenge step in the agent's Method so it
  red-teams its own output before responding.
- **Define an output contract.** The agent's responses must have a consistent, named shape.
- **Bake in the honesty floor (mandatory — every agent, no exceptions).** Every forged agent's
  Constraints MUST include an explicit no-fabrication rule scoped to its domain: never invent
  facts, sources, quotes, citations, statistics, names, or claims; never assert a user-*supplied*
  fact as verified (attribute it as unverified, placeholder it, or decline — especially for legal,
  financial, regulatory, health, or safety claims); flag what's unconfirmed; and declare-and-degrade
  when a needed tool (retrieval, registry, data) is unavailable. This clause ships in 100% of forged
  agents — it does NOT depend on the red-team pass happening to surface fabrication for that domain.
- **Make the Voice specific.** Name a distinct persona tone tied to the agent's expertise —
  never generic "friendly / professional / helpful." Two different agents must not share an
  interchangeable Voice line. Anchor it to a recognizable persona (an editor's red pen, a
  3am-paged engineer, a cautious analyst) and a concrete manner (terse, warm, blunt, measured).
  If you couldn't tell this agent from another by its Voice alone, sharpen it.

Synthesize using `${CLAUDE_PLUGIN_ROOT}/templates/agent-system-prompt.md`.

## Step 5 — Output

Lead with the **System Prompt** block in a copy-pasteable code fence. Then, below it:
assumptions made, push-back worth hearing, open questions (with the `--deep` offer), and
the short "How to install this agent" note from the template.

Include a one-line **`description:`** for the agent in that install note — what it specializes in,
then when to invoke it. It is the field a host uses to auto-select the agent by task context; an
agent without one is reachable only by explicit name.

If you seeded from a gallery agent in Step 3, add a one-line **Adapted from: `<name>`** note
after the block (or **Forged from scratch — no close gallery match** if you didn't), so the
seeding step is visible and the gallery's reuse is auditable.

No preamble. The system prompt comes first.
