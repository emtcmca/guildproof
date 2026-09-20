# Using guildproof

A practical sheet for a new user — human or agent — to get value out of guildproof fast.

guildproof is prompt & context engineering delivered as a Claude Code plugin, in **two layers**:

- **Layer 1 (core)** — zero model calls, model-agnostic, paste-anywhere. Three commands that
  turn rough input into sharp output: `/sharpen`, `/forge-agent`, `/lens`.
- **Layer 2 (coordinator)** — `/orchestrate`. Dispatches live specialist subagents to handle a
  multi-domain request and synthesizes one deliverable. Needs a host that can spawn subagents
  (Claude Code).

---

## 1. Install

Three ways in. Option A is the one the README shows; B and C live here.

### Option A — as a plugin (recommended)

```
/plugin marketplace add emtcmca/guildproof
/plugin install guildproof
```
Verify: type `/guildproof` — `/guildproof:sharpen`, `:forge-agent`, `:lens`, `:orchestrate`
should autocomplete. (Plugin commands are namespaced — bare `/sharpen` only exists with the
manual/standalone install below.)

Then run `/guildproof:lens --lens skeptic` on any short paragraph. If it reports running the
`skeptic` lens, the bundled lens library resolved correctly. Autocomplete alone doesn't prove the
install — the commands can load while the files they read don't.

(For local development against a clone, add the working copy instead:
`/plugin marketplace add /path/to/your/guildproof-clone`.)

### Option B — manual (standalone, bare command names)

Copy five things into your `~/.claude/` directory (Windows: `C:\Users\<you>\.claude\`):

| Copy this | To here | Needed for |
|---|---|---|
| `commands/` | `~/.claude/commands/` | the four commands |
| `skills/` | `~/.claude/skills/` | the engine + coordinator |
| `lenses/` | `~/.claude/guildproof-lenses/` | the lens pass |
| `templates/` | `~/.claude/guildproof-templates/` | `/sharpen`, `/forge-agent`, `/lens --grade` output |
| `agents/` | `~/.claude/guildproof-agents/` | gallery seeding + `/orchestrate` routing |

Installed this way the commands are bare — `/sharpen`, `/forge-agent`, `/lens`, `/orchestrate` —
because standalone commands aren't namespaced.

Skip any row and that capability degrades: no `lenses/` and the lens step has nothing to load;
no `templates/` and the synthesis step has no skeleton; no `agents/` and `/forge-agent` can't
seed from the gallery while `/orchestrate` has no roster to route to.

### Option C — any other agent

The commands and the orchestrator are Claude Code features, but the prompts underneath are not.
All of them are published as plain skills:

```bash
npx skills add emtcmca/guildproof-skills
```

That installs 22 skills into any agent that reads `SKILL.md`: the engine
(`prompt-engineering`), all twenty gallery specialists, and a standalone `prompt-grader`
extracted from the engine's grading route. No plugin, no dependencies, no API keys.

What you give up: the four slash commands and `/orchestrate`, which dispatches subagents from a
plugin-bundled gallery and cannot run from a plain skills install. No gallery agent is left out.
What you keep: the same prompt bodies, generated from this repo and stamped with the commit they
came from.

Source and provenance: [emtcmca/guildproof-skills](https://github.com/emtcmca/guildproof-skills).

### Uninstall

If you installed as a plugin (Option A):

```
/plugin uninstall guildproof
/plugin marketplace remove emtcmca/guildproof
```

If you installed manually (Option B), delete what you copied:

- `~/.claude/commands/sharpen.md`, `forge-agent.md`, `lens.md`, `orchestrate.md`
- `~/.claude/skills/prompt-engineering/` and `~/.claude/skills/orchestration/`
- `~/.claude/guildproof-lenses/`, `~/.claude/guildproof-templates/`,
  `~/.claude/guildproof-agents/`

That's the full footprint. guildproof writes exactly one file on its own, and only after asking:
`~/.claude/guildproof-coverage-gaps.md`, the log `/orchestrate` appends to when a request slice
falls outside every agent's purview. Delete it too if you created one. Nothing else is written
and no state is left behind.

---

## 2. Which command do I use?

| You have… | Use | You get back |
|---|---|---|
| a rough one-off task | `/guildproof:sharpen` | a complete, gap-filled, reviewed **prompt** |
| an assistant you want to reuse | `/guildproof:forge-agent` | a durable **system prompt** |
| something to critique (code, prompt, UI, draft) | `/guildproof:lens` | **findings**, worst-first |
| a prompt to *score* (or two to compare) | `/guildproof:lens --grade` | a **scored verdict** + top fixes |
| a multi-domain build/task | `/guildproof:orchestrate` | **one synthesized deliverable** |

Rule of thumb: one domain → a core command (or one gallery agent). More than one domain that
must end as a single coherent result → `/orchestrate`.

---

## 3. The core commands

### `/guildproof:sharpen <rough request>`
Turns a vague ask into an executable prompt: role, objective, context, requirements (with the
tone adjectives named), guardrails from a red-team pass, success criteria, output format, and
out-of-scope — then the assumptions it made, the push-back worth hearing, and open questions.
```
/guildproof:sharpen make the settings page feel calmer and more trustworthy
/guildproof:sharpen draft a violation notice for a fence dispute --lens editorial --deep
```
- `--lens a,b` — force specific lenses (else it auto-picks by topic).
- `--deep` — interview you one question at a time instead of assuming.

### `/guildproof:forge-agent <description>`
Turns "an agent that reviews HOA letters for tone" into a complete, reusable system prompt —
role, a named **voice**, operating principles, method (with a baked-in self-challenge step),
guardrails, and an output contract. It seeds from the gallery when a close match exists and
states what it adapted from.
```
/guildproof:forge-agent a reviewer that critiques API endpoints for security holes
```

### `/guildproof:lens <artifact> [--lens a,b] [--fix]`
Reviews an existing prompt/page/component/draft through expert lenses and returns findings
(✅ checked / ⚠️ weak / ❌ failing), worst-first, with the top-3 fixes. By default it critiques
and does not rewrite. Add `--fix` and it emits a corrected version of the artifact in its own
form — prose stays prose, code stays code, a prompt comes back sharpened — making the minimal
targeted change that resolves each finding.
```
/guildproof:lens (paste a React component) --lens accessibility,visual-design
/guildproof:lens (paste a React component) --lens accessibility --fix
```

### `/guildproof:lens <prompt> --grade [--against <v2>] [--rubric a,b]`
The same command, in **grade mode**: instead of lens findings it *scores a prompt* — a PASS /
WEAK / FAIL verdict, the nine concerns a complete prompt resolves marked ✅/⚠️/❌, an adversarial
quality pass, and the 2–3 fixes that raise the score most. It grades **coverage, not
conformance** — a prompt that resolves a concern in one fluent sentence passes, and is never
penalized for not looking like guildproof output.

`--against` scores two versions on the same rubric and reports per-dimension deltas, **naming any
dimension that regressed even when the revision wins overall**. That is what eyeballing a rewrite
misses, and it's the same score → change → re-score → keep-only-what-didn't-regress loop the
project runs on itself in `evals/`.
```
/guildproof:lens (paste a system prompt) --grade
/guildproof:lens (paste the revision) --grade --against (paste the original)
```

**Plain `/lens` vs `/lens --grade`:** default `/lens` answers *what's wrong with this?* through a
professional's checklist, on any artifact. `--grade` answers *how good is this prompt, and did my
change help?* Findings versus a measurement — one flag apart. (To score a *doc, UI, or plan*
against criteria rather than a prompt, use the `evaluator` gallery agent.)

---

## 4. Lenses

A lens is a professional's checklist in a markdown file. The 12 built-ins: `visual-design`,
`ux-designer`, `accessibility`, `security-reviewer`, `performance`, `api-design`,
`data-integrity`, `seo`, `product-strategist`, `editorial`, `ai-tells`, `skeptic` (applied by
default).

**Add your own** (no fork): drop a markdown file with `name:` + `applies-to:` frontmatter into
`~/.claude/guildproof-lenses/` (everywhere) or `./.guildproof-lenses/` (one project). It's
auto-loaded and selectable by `--lens <name>` or by topic.

---

## 5. The agent gallery (20 specialists)

`agents/` holds ready-to-paste **specialist system prompts** — each with a named voice and a
self-challenge step. Two ways to use them:

- **Directly:** open `agents/<name>.md` and paste its body into a subagent, a skill, or any
  system-prompt field.
- **Via `/orchestrate`:** the coordinator dispatches them for you.

Roster: **Build** — feature-spec, planner, data-modeler, backend-builder, frontend-builder,
test-author, refactor-planner · **Review** — api-reviewer, security-review, verifier, evaluator,
compliance-reviewer, debugger · **Write** — copy-rewrite, docs-writer, sop-writer,
governance-letter · **Meta** — research-synthesizer, prompt-engineer, mcp-integrator.

Forge a new one with `/forge-agent` and drop it in `agents/` to grow the roster.

---

## 6. Orchestration — `/guildproof:orchestrate <multi-domain request>`

For work that spans several specialists. The coordinator:
1. **Gates** — declines if it's really single-domain (routes you to one command instead).
2. **Sharpens** the request, then **decomposes** it into non-overlapping slices.
3. **Routes** each slice to the best gallery agent; **logs any slice no agent covers** as a
   coverage gap (a `/forge-agent` candidate).
4. **Owns the seams** — assigns one owner to every shared decision; resolves cross-agent
   conflicts, or **escalates** product/risk calls to you.
5. **Dispatches** the agents as live subagents (parallel where independent).
6. **Synthesizes** one coherent deliverable — not a pile of agent outputs.

```
/guildproof:orchestrate add public read-only shareable links to user dashboards
```
- **Smart approval gate:** small/low-risk plans (≤3 agents) auto-run; larger ones pause for your
  approval first. `--gate` forces the pause; `--no-gate` runs autonomously; `--dry` shows the
  decomposition + routing without dispatching.

What you get: the deliverable first, then the decomposition, seam owners, resolved conflicts,
coverage gaps, and what each agent contributed.

---

## 7. For agents using guildproof

- Invoke a command via the Skill tool with the namespaced name (e.g. `guildproof:sharpen`),
  passing the request as args.
- The engines are plain method + structure (`skills/prompt-engineering/SKILL.md` for Layer 1,
  `skills/orchestration/SKILL.md` for Layer 2) — an agent can read and run them directly.
- Honesty guardrails are baked in and must be respected: never invent facts (provisions, numbers,
  stacks), sources, or MCP servers; flag them as assumptions/verify-items instead.

---

## 8. Testing & refining (the eval harness)

`evals/` is a host-judged harness: structural invariants + an adversarial skeptic rubric over 38
cases. Run it by saying **"run the guildproof evals"** (all) or **"run eval case 17"** (one).
It writes a dated scorecard to `evals/runs/`. To refine: change a lens/engine/agent, re-run the
same cases, diff the scorecards, keep only non-regressing improvements.

---

## Quick start (60 seconds)

1. `/plugin marketplace add emtcmca/guildproof` → `/plugin install guildproof`
2. `/guildproof:sharpen <your vaguest current task>` — see it filled in.
3. Multi-part task? `/guildproof:orchestrate <it>` and watch it decompose.
4. Want a reusable assistant? `/guildproof:forge-agent <what it should do>`.
