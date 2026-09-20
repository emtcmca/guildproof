# guildproof — command sheet

A one-page reference. For the narrative walkthrough see [USING-GUILDPROOF.md](USING-GUILDPROOF.md).

## Install

```
/plugin marketplace add emtcmca/guildproof
/plugin install guildproof
```
Verify: type `/guildproof` → the four commands autocomplete. Plugin commands are **namespaced**
(`/guildproof:sharpen`); bare names only exist with the manual/standalone install (see README).

## Commands

| Command | Use it for | Returns |
|---|---|---|
| `/guildproof:sharpen <request>` | a rough one-off task | a complete, reviewed **prompt** |
| `/guildproof:forge-agent <description>` | a reusable assistant | a durable **system prompt** |
| `/guildproof:lens <artifact>` | critiquing something | **findings** (✅/⚠️/❌), worst-first |
| `/guildproof:lens <prompt> --grade` | scoring a prompt | a **scored verdict** + top fixes |
| `/guildproof:orchestrate <request>` | a multi-domain build | **one synthesized deliverable** |

**Pick fast:** one domain → `sharpen` (or one gallery agent). Reusable → `forge-agent`.
Critique an artifact → `lens`. Score a prompt, or compare two versions → `lens --grade`. Several
domains, one coherent result → `orchestrate`.

## Flags

| Flag | Works on | Effect |
|---|---|---|
| `--lens a,b` | sharpen, forge-agent, lens | force specific lenses (else auto-picked by topic) |
| `--deep` | sharpen, forge-agent | interview one question at a time instead of assuming |
| `--fix` | lens | also emit a corrected version of the artifact, not findings alone |
| `--grade` | lens | score a prompt against a rubric (verdict) instead of lens findings |
| `--against <p>` | lens `--grade` | score two prompts on one rubric; report deltas and regressions |
| `--rubric a,b` | lens `--grade` | grade against your own criteria instead of the defaults |
| `--dry` | orchestrate | show decomposition + routing, don't dispatch |
| `--gate` | orchestrate | always pause for approval before fan-out |
| `--no-gate` | orchestrate | run autonomously through synthesis |
| *(default)* | orchestrate | smart gate: auto-run ≤3 agents/low-risk, pause for larger |

## Lenses (auto-selected by topic, or force with `--lens`)

`visual-design` · `ux-designer` · `accessibility` · `security-reviewer` · `performance` ·
`api-design` · `data-integrity` · `seo` · `product-strategist` · `editorial` · `ai-tells` ·
`skeptic` (default) — 12 built-in

**Add your own:** a markdown file with `name:` + `applies-to:` frontmatter in
`~/.claude/guildproof-lenses/` (global) or `./.guildproof-lenses/` (project). Auto-loaded.

## Gallery (20 specialists — paste directly, or let `/orchestrate` dispatch them)

- **Build:** feature-spec · planner · data-modeler · backend-builder · frontend-builder · test-author · refactor-planner
- **Review:** api-reviewer · security-review · verifier · evaluator · compliance-reviewer · debugger
- **Write:** copy-rewrite · docs-writer · sop-writer · governance-letter
- **Meta:** research-synthesizer · prompt-engineer · mcp-integrator

Files live in `agents/`. Forge a new one with `/forge-agent` and drop it in to grow the roster.

## Common recipes

```
# Sharpen, forcing lenses and going deep
/guildproof:sharpen redesign the signup form --lens ux-designer,accessibility --deep

# Forge a specialist (seeds from the gallery if a match exists)
/guildproof:forge-agent a reviewer that critiques API endpoints for security holes

# Review a component, then get the fix — one step
/guildproof:lens (paste code) --lens accessibility,visual-design --fix

# Score a prompt, revise it, then prove the revision actually improved it
/guildproof:lens (paste a system prompt) --grade
/guildproof:lens (paste the revision) --grade --against (paste the original)

# Inspect an orchestration plan without spending fan-out
/guildproof:orchestrate build a password reset flow --dry

# Run the full coordinated build
/guildproof:orchestrate add public read-only shareable links to dashboards
```

## Eval harness (test & refine)

- Run: say **"run the guildproof evals"** (all 38 cases) or **"run eval case 17"** (one).
- Output: a dated scorecard in `evals/runs/`.
- Refine: change a lens/engine/agent → re-run the same cases → diff scorecards → keep only
  non-regressing improvements.

## Honesty guardrails (always on)

Never fabricated, always flagged: facts (provisions, numbers, dates, tech stack), sources/citations
(no retrieval → say so), MCP servers (no registry → recommend by capability + "verify exists").
