# promptsmith — planned features (candidate list)

> **Renamed.** This project was `promptsmith` until 2026-09-18 and is now `guildproof`.
> This document is a record written under the old name, so it keeps the old name and the
> old `/promptsmith:*` commands. The current commands are `/guildproof:*`.

Status: **candidates, not committed.** Reviewing other projects before locking scope or
implementing. Nothing here ships until the review pass is done and each item is approved.

Guardrails for everything on this list — a candidate is rejected if it breaks any of these:
- Stays pure markdown (method + structure). No runtime, no deps, no API keys for Layer 1.
- No persistent state machine, no `.planning/`-style artifacts. promptsmith is stateless.
- No auto-update / `npx @latest` install path (known threat vector; static-copy install is a feature).
- Stays focused — four commands over one method, not a marketplace. No long onboarding.

---

## Candidate 1 — Prohibition / negative-space coverage  ⭐ top pick

**STATUS: IMPLEMENTED** (feat/planned-features-batch) — engine Step 4 now emits a prohibitions
pass; `templates/sharpened-prompt.md` has a `PROHIBITIONS` block distinct from `OUT OF SCOPE`.

**Source:** GSD `/gsd-spec-phase` ("edge + prohibition coverage").
**Idea:** the sharpen engine actively generates an explicit "must NOT do" list, not just a
passive out-of-scope note. e.g. "must not invent endpoints," "must not change auth," "must not
touch the billing schema."
**Why:** directly serves the existing pitch ("the edge cases you didn't think of"). Negative
constraints are where vague prompts most often go wrong.
**Touches:** `skills/prompt-engineering/SKILL.md` (add a gap-fill / push-back sub-step),
`templates/sharpened-prompt.md` (a Prohibitions block).
**Effort:** low. **Identity cost:** none.
**Open question:** its own template section, or fold into the existing guardrails block?

## Candidate 2 — One-step lens → fix  ⭐ removes a documented round-trip

**STATUS: IMPLEMENTED** (feat/planned-features-batch) — `/lens --fix` added: new Step 6 emits a
corrected artifact in its own form (prose/code/prompt), minimal targeted changes, injection-safe,
with a second-pass check. Default (no flag) keeps the critique-only behavior + manual-sharpen
offer. README usage updated.

**Source:** GSD `/gsd-verify-work` (auto-diagnose AND emit a fix plan, not just findings).
**Idea:** `/lens --fix` (or an auto-offer) returns a corrected draft, not only findings. Today
the README tells the user to manually re-feed lens findings into `/sharpen` — kill that hop.
**Why:** removes a friction point the README itself calls out (lens → sharpen by hand).
**Touches:** `commands/lens.md`, the engine's lens step, possibly the sharpen template reused
for the corrected output.
**Effort:** low–medium. **Identity cost:** none (stays markdown).
**Open question:** flag (`--fix`) vs always offering the corrected draft at the end.

## Candidate 7 — Voice-preservation guardrail (small)

**STATUS: IMPLEMENTED** (feat/planned-features-batch) — voice-preservation guardrail added to
`lenses/editorial.md` and strengthened in `agents/copy-rewrite.md`, explicitly framed as a
counterweight to the `ai-tells` lens (a deliberate stylistic signature is not an AI tell).
**Source:** ComposioHQ/awesome-claude-skills `content-research-writer` (verify per-skill license
before adapting any text; the principle itself is concept-only).
**Idea:** add a voice-preservation guardrail to `lenses/editorial.md` and `agents/copy-rewrite.md`:
when the author has a known voice or supplied samples, match it — enhance, don't override; suggest,
don't replace; flag where a change would alter voice. **Acts as a counterweight to the new
`ai-tells` lens**, which strips patterns aggressively and could otherwise flatten a distinctive
author into generic prose.
**Why:** prevents homogenizing the user's voice; resolves a real tension introduced by candidate 6.
**Touches:** `lenses/editorial.md`, `agents/copy-rewrite.md`.
**Effort:** low. **Identity cost:** none.
**Note:** the rest of the source skill (full long-form research/drafting workflow) is REJECTED as
scope creep — promptsmith engineers prompts/agents, it is not a writing companion.

## Candidate 6 — AI-writing-tells catalog for the editorial lens  ⭐ strong

**STATUS: IMPLEMENTED** (feat/planned-features-batch) — shipped as a dedicated `lenses/ai-tells.md`
(6-category catalog + tiered vocabulary + two-pass discipline, adapted from avoid-ai-writing with
attribution) rather than folded into editorial; `editorial.md` cross-references it; README lens
table updated. The upstream Node scoring engine was intentionally NOT ported (stays method-only).

**Source:** conorbronsdon/avoid-ai-writing (MIT — adapt catalog content with attribution).
**Idea:** enrich `lenses/editorial.md` with a structured AI-tell catalog: ~6 categories
(content / language / structure / communication / structural-detection / tool-fingerprints) and a
**tiered vocabulary** (Tier 1 always-flag e.g. leverage/delve/robust/seamless; Tier 2 flag on
clustering; Tier 3 on density). Add rhythm checks (uniform sentence length, em-dash overuse, bold
density) and a two-pass re-audit (rewrite, then re-scan for survivors).
**Why:** directly upgrades an existing lens; catches the exact tells we flagged in promptsmith's
own README (em-dash overuse, hype phrases, sycophancy, generic conclusions, `[placeholder]`
leftovers) and systematizes the brand word-bans. Pure method.
**Touches:** `lenses/editorial.md` (catalog + tiers); optionally a dedicated `--lens ai-tells`.
**Effort:** low–medium. **Identity cost:** none.
**Do NOT port:** the upstream Node scoring engine (`detector/patterns.js`) — that's a dependency.
promptsmith stays method-only; the host does the judging.
**Open question:** fold into `editorial`, or ship a separate `ai-tells` lens that `editorial`
references?

## Candidate 5 — Style-aware lenses (hard-rule vs style-preference split)  ⭐ strong

**STATUS: IMPLEMENTED** (feat/planned-features-batch) — `lenses/visual-design.md` rewritten into
hard-rules vs style-relative sections + 8 style families inline, with "establish the intended
aesthetic first, never cross-penalize." `lenses/ux-designer.md` framed as the style-independent
hard-rules lens (+ affordance, state-closure). DEFERRED: the optional `--style <family>` CLI flag
(command-surface change; lens-level family detection covers the core value for now).

**Source:** oil-oil/ui-ux-guide (Apache-2.0, markdown-only — compatible to adapt with attribution).
**Idea:** restructure the `visual-design` / `ux-designer` lenses to separate two kinds of checks:
- **Hard rules** — style-independent UX/perception facts that are always true (task priority,
  state closure, affordance, error prevention, feedback loops, consistency, CRAP, spacing rhythm,
  hint layering, UI-copy discipline). Always enforced.
- **Style-relative** — judged *within* a chosen aesthetic family (modern-minimal, editorial,
  brutal, playful, premium-luxury, etc.), never cross-penalized. A brutalist design must not be
  dinged for not being minimal.
Optionally add a `--style <family>` arg so a visual review is scored inside the intended aesthetic.
**Why:** fixes a real failure mode — a single-opinion visual lens penalizes any design that isn't
the reviewer's default taste. The hard/relative split makes the lens honest across aesthetics.
**Touches:** `lenses/visual-design.md`, `lenses/ux-designer.md`, maybe `commands/lens.md` (style arg).
**Effort:** medium (rewrite two lenses; optional style-family reference). **Identity cost:** none.
**Open question:** bake style families into the lens files, or a separate `lenses/_style-families.md`
reference the visual lenses point to?

## Candidate 4 — Evidence-separated, tri-state verdict

**STATUS: IMPLEMENTED** (feat/planned-features-batch) — `agents/verifier.md` now returns a
tri-state verdict (VERIFIED / VERIFIED WITH GAPS / NOT VERIFIED) plus an explicit BLOCKING flag,
and splits output into Observable evidence (facts) vs Assessment (judgment). Folds in the existing
"Claimed vs actual" + "Confirm-these" (the latter is now what makes a verdict WITH GAPS).
Orchestration unchanged — it keys on the BLOCKING/HIGH semantics, which are preserved. Concept only
(loki is BUSL — no code/text copied).

**Source:** loki-mode "Evidence Receipt" + verdict levels.
**Idea:** the `verifier` agent (and `/lens`) structures output as deterministic/observable
evidence vs. AI assessment, and rolls up to a single tri-state verdict:
**VERIFIED / VERIFIED WITH GAPS / NOT VERIFIED.** Today findings are per-item ✅/⚠️/❌ with no
rolled-up verdict separating "what I can point to" from "what I judge."
**Why:** extends the existing "supplied facts are not verified facts" guardrail into the output
format; makes a verdict auditable at a glance.
**Touches:** `agents/verifier.md`, `commands/lens.md`, possibly the orchestrate synthesis step.
**Effort:** low. **Identity cost:** none (pure markdown).
**License note:** loki-mode is BUSL-1.1 (source-available, not OSS). Concept-inspiration only —
do NOT copy any loki code or text.
**Open question:** is "VERIFIED WITH GAPS" distinct enough from ⚠️, or redundant?

## Candidate 3 — Convergence review loop  (optional, defer)

**Source:** GSD `/gsd-plan-review-convergence` / `/gsd-review` (re-review until no new findings).
**Idea:** a `--converge` mode on `/lens` (or a multi-perspective lens panel) that re-runs until a
pass surfaces nothing new — the loop-until-dry pattern.
**Why:** catches the tail of issues a single pass misses.
**Effort:** medium (adds control flow + stop condition). **Identity cost:** low, but raises
complexity — watch the "no long onboarding" guideline.
**Decision:** defer. Candidate for a v0.3 headline, not the next slice.

---

## Rejected from GSD (recorded so we don't re-litigate)

- Persistent state machine (`STATE.md`, `CONTEXT.md`, `.planning/`) — kills stateless,
  paste-anywhere identity.
- `npx @latest` auto-update installer — the threat vector the awesome-list flags; our static
  install is a selling point.
- 60-command lifecycle / milestones / versioning — violates focus + no-onboarding guidelines.
- JS/TS/shell runtime — kills zero-dep, markdown-only.

### From lackeyjb/playwright-skill — REJECTED (whole skill)

Browser automation that writes + executes Playwright code on the fly. Category mismatch and
violates every hard constraint: needs Node + Playwright + Chromium (`npm run setup`), executes
JS via `run.js`, drives real browsers to live sites. promptsmith *generates* test specs (via
forge/orchestrate); it does not *run* a browser. Nothing to port — the conceptual adjacency to
`/lens` (live UI validation vs. static review) is too shallow to justify a runtime dependency.

### From asklokesh/loki-mode — FRAMEWORK REJECTED (one concept lifted → candidate 4)

Autonomous SDLC framework (GSD's category, heavier). Rejected whole: needs Bun/npm/Python/Docker,
dual bash+TS runtime, `.loki/` state + 3-tier memory, a localhost dashboard server. Also
**BUSL-1.1 (source-available, not OSS)** — no code/text may be copied into Apache-2.0 promptsmith;
concept-inspiration only.
Already covered by promptsmith (convergent, nothing to build): independent verifier that ignores
producer narration (= Loki "blind review"), refuse-to-ship-on-unverified (= orchestrate halt +
escalate), skeptic lens + `--deep` (= `loki grill` devil's advocate / anti-sycophancy).
Lifted as concept → **Candidate 4** (evidence-separated tri-state verdict).

### From AlmogBaku/debug-skill — TOOL REJECTED (method already covered)

A `dap` CLI (Go binary + auto-starting daemon) wrapping the Debug Adapter Protocol, plus a skill
teaching structured debugging. License clean (MIT). Tool half is execution-bound — Go binary,
daemon, requires language debugger backends (debugpy/dlv/js-debug/lldb) — promptsmith can't drive
a live debugger, so it fails markdown-only/zero-dep. The debugging *method* (hypothesis-driven, not
print-guessing) is real but already encoded in promptsmith's `agents/debugger.md` gallery
specialist. Nothing to port.

### From agent-sh/agnix — REJECTED AS PORT (recommended as a dev-time tool)

Rust linter + LSP that validates AI-agent config files (CLAUDE.md, SKILL.md, AGENTS.md, MCP,
plugin configs) — 430+ rules, npm/brew/cargo binary, WASM, IDE plugins. License clean (MIT OR
Apache-2.0). Execution-bound (Rust binary/LSP) — nothing markdown-portable, reject as a feature.
BUT it lints exactly the files promptsmith ships and targets the "skill silently never triggers"
failure mode. RECOMMENDATION (not a feature): run `agnix .` on the promptsmith repo as a
pre-submission QA pass to catch a malformed SKILL.md / plugin.json before reviewers do.

### From framix-team/skill-email-html-mjml — REJECTED (compiler dep + narrow domain)

Generates email-client-safe HTML by compiling MJML. License clean (MIT). Two strikes: needs the
MJML/Node compiler (`npx mjml`) — a runtime dependency — and it's a single-domain content
generator (email templates), where promptsmith is domain-general method. The `editorial` lens
already covers email copy; `/forge-agent` covers building an email specialist on demand. Nothing
to port.

### From raphaelchristi/harness-evolver — FRAMEWORK REJECTED (eval-rubric sub-note)

Evolves agent codebases via a 7-stage evolution loop with LangSmith-backed evals. License clean
(MIT). Reject whole: Python, LangSmith API key, git-worktree code mutation, network calls beyond
Anthropic — execution framework, not method. SUB-NOTE (low priority, not a numbered candidate):
its eval discipline — justification-before-score, pairwise comparison, an anti-gaming critic that
checks the judge itself — could refine `evals/rubric.md` later. Our known-bad fixtures already
guard judge integrity, so this is a polish item, not a feature.

### From luoyuctl/agenttrace (agenttrace-session-audit) — REJECTED (binary wrapper, out of domain)

A skill that drives the `agenttrace` Go binary/TUI to audit agent session logs (token cost,
latency, tool-failure rate, health scoring). License clean (MIT). SKILL.md states it runs the
binary/Go runtime, not markdown-only — fails zero-dep. Domain is session telemetry/observability,
orthogonal to prompt/agent-quality engineering; the "method" is just run-binary-then-format. Its
worst-first report ordering is already how `/lens` ranks findings. Nothing to port.

### From TheQmaks/crowdcast — REJECTED (passes guardrails, wrong domain)

Multi-agent social simulation skill (spawn 50+ persona agents, simulate reactions/narratives,
report). Notable: it's the first reject that PASSES every hard guardrail — markdown-only, zero
external deps, no network beyond Claude's API, MIT. Rejected purely on domain/scope: it's a
simulation engine, not prompt/agent-quality engineering, and it uses persistent
`.crowdcast/simulations/` state + resume (already ruled out). One marginal concept — "hybrid agent
depth" (deep reasoning for key actors, batch for the crowd) — is already covered for our ~7-agent
gallery by per-agent effort/model tiering. Not a candidate.

### From takechanman1228/claude-persona — REJECTED (Python deps + wrong domain)

Synthetic persona panels for marketing/UX research. License MIT. Two strikes: Python +
pandas/matplotlib/seaborn + `claude -p` subprocesses (fails zero-dep), and domain is customer
research, not prompt/agent-quality engineering (same family as crowdcast). Its persona-isolation
idea (each agent in a `--safe-mode` subprocess, no cross-bias / no context leakage) is already
embodied conceptually in promptsmith's blind verifier (can't see producer narration); the
mechanism itself is CLI-flag execution, not markdown-portable. Not a candidate.

---

## Still to review (before implementing anything)

Other repos Eric wants to compare first. Add findings here as a new "Candidate N" or "Rejected"
entry per repo, with source attribution.

- [x] GSD / gsd-core — DONE (candidates 1–3 above)
- [x] lackeyjb/playwright-skill — DONE (rejected, see below)
- [x] asklokesh/loki-mode — DONE (framework rejected; candidate 4 lifted as concept only)
- [x] AlmogBaku/debug-skill — DONE (tool rejected; method already covered)
- [x] oil-oil/ui-ux-guide — DONE (candidate 5 — style-aware lenses)
- [x] agent-sh/agnix — DONE (rejected as port; recommended as a dev-time QA linter)
- [x] framix-team/skill-email-html-mjml — DONE (rejected — compiler dep + narrow domain)
- [x] raphaelchristi/harness-evolver — DONE (framework rejected; eval-rubric sub-note recorded)
- [x] luoyuctl/agenttrace (session-audit skill) — DONE (rejected — binary wrapper, out of domain)
- [x] TheQmaks/crowdcast — DONE (rejected — passes guardrails but wrong domain/scope)
- [x] takechanman1228/claude-persona — DONE (rejected — Python deps + wrong domain)
- [x] conorbronsdon/avoid-ai-writing — DONE (candidate 6 — AI-tells catalog for editorial lens)
- [x] ComposioHQ/.../content-research-writer — DONE (workflow rejected; candidate 7 — voice preservation)
- [ ] _next repo — pending_

---

## Implementation order (tentative, once review is done)

1. Candidate 1 (prohibitions) — smallest change, biggest sharpen-quality gain.
2. Candidate 2 (lens → fix) — UX win, removes a known round-trip.
3. Candidate 3 (convergence) — deferred / v0.3.
