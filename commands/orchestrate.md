---
description: "Coordinate multiple specialist agents on a multi-domain request — sharpen, decompose, dispatch the gallery, resolve seams, and synthesize one deliverable. (Layer 2 — requires a host that can spawn subagents.)"
usage: "/guildproof:orchestrate <multi-domain request> [--dry] [--no-gate] — e.g. /guildproof:orchestrate add public read-only shareable links to user dashboards"
category: "dev"
---

Run the guildproof coordinator on a request that spans more than one specialist. Output is a
single synthesized deliverable plus the decomposition, seam owners, resolved conflicts, and any
coverage gaps. **Layer 2** — this dispatches live subagents, so it needs a host that can spawn
them (Claude Code). For a single-domain task, use `/guildproof:sharpen` instead.

## Step 1 — Load the engine

Read `${CLAUDE_PLUGIN_ROOT}/skills/orchestration/SKILL.md` in full. It defines the coordinator
pipeline. (That engine itself loads the Layer 1 `prompt-engineering` skill in its Step 1.)

> **Paths.** `${CLAUDE_PLUGIN_ROOT}` is this plugin's install directory, substituted
> automatically — never a literal folder in the user's project. If guildproof was installed
> standalone (README Option B, no plugin root), read from `~/.claude/` instead:
> `~/.claude/skills/…`, `~/.claude/guildproof-templates/`, `~/.claude/guildproof-lenses/`,
> `~/.claude/guildproof-agents/`. Never resolve these against the user's working directory.

## Step 2 — Parse arguments

Parse `$ARGUMENTS`:
- `--dry` — stop after the decomposition + plan (Step 5). Show slices, slice→agent map, seams,
  conflicts, coverage gaps, and fan-out size. Do **not** dispatch. Useful for inspecting routing.
- `--gate` — always pause for approval before fan-out (override the smart threshold).
- `--no-gate` — never pause for *approval*; run autonomously through dispatch + synthesis. **Does
  not** waive the intent gate (Step 0) or the adversarial-verify gate (Step 6.5) — those always apply.
- (default) — **smart threshold**: auto-run small/low-risk plans (≤ 3 agents, nothing
  irreversible); gate larger or risky fan-outs. See engine Step 5.
- Everything else = the multi-domain request to coordinate.

If the request is empty, ask what to coordinate and stop.

## Step 3 — Run the pipeline

Execute the orchestration pipeline (engine Steps 0–8):
0. Gate — if it's really single-domain, fall back to `/guildproof:sharpen` or the one agent.
1. Sharpen the query (Layer 1 engine).
2. Decompose into non-overlapping slices.
3. Route slices to gallery agents; log uncovered slices as coverage gaps.
4. Identify seams + conflicts; assign owners; resolve or flag conflicts.
5. Approval gate (unless `--no-gate`).
6. Dispatch each slice's agent as a subagent (parallel where independent).
7. Assemble + curate into one coherent deliverable.
8. Report.

## Step 4 — Output

Lead with the **synthesized deliverable**. Then, below it: decomposition, seams + owners,
conflicts resolved, coverage gaps (with new-agent suggestions), and per-agent contributions.

No preamble. The deliverable comes first.
