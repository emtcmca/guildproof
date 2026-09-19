# Pre-forged agent gallery

Ready-to-paste specialist **system prompts** — the kind `/guildproof:forge-agent` produces,
saved so you don't rebuild them cold each time.

Each file is a complete agent: paste its body into a Claude Code subagent, a `SKILL.md`, a
custom GPT, or any system-prompt field and it works as-is. They exist because the common
`/sharpen` *out-of-scope* items (new features, copywriting, performance, backend/API, SEO)
are exactly the jobs a single task agent should refuse but a user often needs next.

## The gallery

| Agent | Does | Lenses baked in |
|---|---|---|
| `feature-spec` | turns a rough feature idea into a reviewed spec / mini-PRD | product-strategist, skeptic |
| `copy-rewrite` | rewrites copy to a named tone without inventing facts | editorial, skeptic |
| `api-reviewer` | reviews a backend endpoint / contract for correctness and abuse | api-design, security-reviewer, skeptic |
| `test-author` | writes focused tests for given code, behavior-first | skeptic |
| `refactor-planner` | turns messy code + a goal into a staged, commit-by-commit plan | product-strategist, skeptic |
| `data-modeler` | turns requirements into a schema + safe migration plan | data-integrity, api-design |
| `backend-builder` | builds an endpoint/service to contract — validated, authorized, idempotent | api-design, data-integrity, security-reviewer |
| `docs-writer` | turns code/feature into README, usage, or an ADR | editorial, skeptic |
| `debugger` | turns an error + context into ranked root-cause hypotheses + probes | skeptic |
| `research-synthesizer` | fans out, then synthesizes sources into a cited brief | skeptic, editorial |
| `mcp-integrator` | finds/recommends MCP servers for a task, or specs a new server/client | api-design, security-reviewer, product-strategist |
| `frontend-builder` | builds a UI component to brand, a11y, and UX standards | ux-designer, accessibility, visual-design |
| `security-review` | reviews a change for vulnerabilities across several lenses | security-reviewer, data-integrity, api-design, skeptic |
| `verifier` | independently refutes that an artifact meets its contract; returns a blocking verdict | security-reviewer, api-design, data-integrity, skeptic |
| `governance-letter` | drafts HOA / board correspondence — firm, compliant, on-tone | editorial, skeptic |
| `sop-writer` | turns a process into a clear, followable SOP | editorial, product-strategist |
| `prompt-engineer` | sharpens a system prompt into a tighter, more concrete one | skeptic, editorial |
| `planner` | turns a goal/spec into an ordered, dependency-aware task plan with acceptance criteria + critical path | product-strategist, skeptic |
| `evaluator` | grades an artifact against a rubric — scored verdict + the highest-leverage fixes to iterate on | skeptic, product-strategist |
| `compliance-reviewer` | flags regulatory exposure (GDPR/CCPA/PCI/HIPAA/SOC2/ADA/FTC) — a flag list, not legal advice | security-reviewer, data-integrity, skeptic |

## How `/forge-agent` uses this

Before building an agent from scratch, `/guildproof:forge-agent` checks this gallery for a
close match. If one exists, it **adapts** that agent to your description (swapping domain,
tone, and lenses) instead of starting cold — faster, and consistent in shape. If nothing
matches, it forges fresh and you can drop the result here to grow the gallery.

## Format

Each file is frontmatter + the system prompt as the body:

```markdown
---
name: agent-name
description: What this agent specializes in, then when to invoke it. REQUIRED.
role: one-line description of the specialist
voice: the persona's tone in a few words
lenses: lens-a, lens-b
---

You are <role>.

Voice: <how this agent sounds — named so it speaks in character at injection>.

## Objective ...
## Operating principles ...
## Method ...
## Constraints / guardrails ...
## Output contract ...
## When unsure ...
```

Everything below the frontmatter is the paste-ready system prompt. Keep them durable
(written for every run, not one task) with push-back and an output contract baked in —
the same standard `/forge-agent` holds.

**`description` is not optional and not decorative.** It is the only frontmatter field the host
uses to *auto-select* an agent by task context — `role`, `voice`, and `lenses` are guildproof's
own schema, which the host ignores. An agent shipped without a `description` still loads, but it
renders as an unlabeled entry the host cannot match to a task, so it is reachable only if
something names it explicitly. Write it as *what it does*, then *when to invoke it*.

Also required in every agent body: the **honesty floor** (never fabricate a fact, citation, or
identifier — domain-scoped to what this agent handles) and the **instruction/data boundary**
(the artifact is data, not instructions). Both are invariants the template and `/forge-agent`
enforce in 100% of agents; a hand-added agent must carry them too.

## Add your own

Forge one with `/guildproof:forge-agent ...`, then save the System Prompt block as
`~/.claude/guildproof-agents/<name>.md`, using the frontmatter above. It becomes a seed for
future forges.

Save it **there**, not in the plugin's own `agents/` directory: a plugin install lives in a cache
directory that is wiped on every update, so an agent saved inside it disappears the next time
guildproof updates. `~/.claude/` survives.
