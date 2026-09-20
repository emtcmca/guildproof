# promptsmith roadmap

> **Renamed.** This project was `promptsmith` until 2026-09-18 and is now `guildproof`.
> This document is a record written under the old name, so it keeps the old name and the
> old `/promptsmith:*` commands. The current commands are `/guildproof:*`.

## Architecture: two layers

Decided 2026-06-24. promptsmith is built in two deliberately separate layers so the founding
identity survives the ambition.

**Layer 1 — promptsmith-core (current, shipping).**
The portable prompt & context engineering method: `/sharpen`, `/forge-agent`, `/lens`, `/grade`,
the shared engine, the lens library, and the pre-forged agent gallery. **No model calls, no API
keys, model-agnostic, paste-anywhere.** This is the defensible identity and it stays intact.

**Layer 2 — orchestration (shipped in v0.3.0).**
promptsmith as a *coordinator*: sharpen the prompt to perfection, decompose it into
non-overlapping slices, dispatch each to the right specialist as a live subagent, then receive,
assemble, and curate their work into one coherent result before returning it. This layer is
**Claude-Code-native** — it requires a runtime that can spawn subagents (Task / Workflow), so
it has runtime dependencies the core does not. It was built **last**, only after core + gallery
were tuned, per "build from the ground up; staff the coordinator last." `/orchestrate` and the
coordinator pipeline are live; see the logged 7-agent run in `evals/runs/`.

The gallery is the bridge: today its files are paste-ready system prompts; under Layer 2 they
become the **specialist roster** the coordinator dispatches to. Nothing built now is wasted.

---

## Now — Layer 1 build & tune

- [x] Engine, three commands, templates, eight base lenses (initial scaffold).
- [x] Real-run test pass — validated engine on a live request (`docs/test-runs/`).
- [x] Fix plugin command references to the namespaced form; fix standalone install's lens copy.
- [x] Add `seo`, `api-design`, `data-integrity` lenses (cover the common out-of-scope items).
- [x] Start the pre-forged agent gallery: `feature-spec`, `copy-rewrite`, `api-reviewer`.
- [x] Wire `/forge-agent` to seed from the gallery before building cold.
- [x] Add a named `voice` to the agent template + gallery so each speaks in character.
- [x] Build out the v1 roster (Tier 1–3) — 14 specialists across spec/build/test/review/docs/content:
      `test-author`, `refactor-planner`, `data-modeler`, `docs-writer`, `debugger`,
      `research-synthesizer`, `frontend-builder`, `security-review`, `governance-letter`,
      `sop-writer`, `prompt-engineer` (+ the original three).
  - Deliberately **not** built as agents: `perf-audit`, `seo-auditor` — they would clone the
    `performance` / `seo` lenses, already reachable via `/lens`. Gallery stays makers + lens-fusers.
- [ ] Tune from real use: run each command/agent on real tasks, log friction in `docs/test-runs/`,
      fix the engine/templates/lenses. Core is "tuned" when real runs stop surfacing defects.
- [ ] Merge `test/real-run-pass` to main once the gallery + tuning land.
- [x] Push to GitHub (`emtcmca/promptsmith`) — repo is public; marketplace installs via `emtcmca/promptsmith`.

### Release prep (2026-06-25)

Pre-public-promotion hardening pass:
- [x] **Honesty-floor fix** — 8 gallery agents (api-reviewer, backend-builder, data-modeler,
      debugger, frontend-builder, refactor-planner, security-review, test-author) were missing the
      no-fabrication floor that the template + `forge-agent` + `SECURITY.md §4` require in 100% of
      agents. Added a domain-scoped floor to each; the gallery now matches its own invariant.
- [x] **Filled roster gaps** — forged `planner` (ordered task plan), `evaluator` (rubric grading
      for iteration), `compliance-reviewer` (regulatory flag list). Eval cases 25–27 added.
- [x] **Split the marketing roster** to a private/local pack (`C:\Dev\marketing-pack`, not for
      public release) — it diluted the prompt-engineering narrative. Public gallery: **20 agents**.
- [x] **Reconciled all doc counts** that had drifted (16/17/22/15 → 20 agents; 21/24 → 27 cases);
      bumped `plugin.json` to 0.2.0 with a fuller description.
- [x] **Full-suite eval run (all 27 cases)** with independent judging on the high-stakes routes —
      the release gate before tagging `v0.2.0`. Logged:
      `evals/runs/2026-06-25-2039-full-suite-v0.2.0-release-gate.md` (26 PASS / 1 WEAK / 0 FAIL).
      **That scorecard is now stale** — six features merged after it (see below).

### Pre-launch adversarial pass (2026-07-21)

Three parallel audits — eval coverage, adversarial security, feature/doc drift — run before any
public promotion. The launch pitch is verifiable rigor, so the claim has to survive an audit by
someone hostile. It mostly did; three defects were the same shape and that shape is the lesson.

**The pattern worth remembering: three separate documents asserted a defense the files did not
implement.** Not sloppiness — drift. A roster that grows fast outruns its own invariants.

- [x] **Slice outputs declared untrusted** in the coordinator (`skills/orchestration/SKILL.md`
      Step 7 + Guardrails). `SECURITY.md:16` named subagent output as a threat source; only the
      *request* had a boundary. A slice may now never self-certify Step 6.5 or 7.5.
- [x] **Instruction/data boundary added to all 20 gallery agents.** The engine had the clause;
      agents never inherited it, and orchestration Step 6 dispatches the agent body *without* the
      engine. `agents/README.md:6` also invites pasting bodies into external hosts where the
      engine never loads. `verifier.md:42` was instructed to catch this failure in others while
      unprotected against it itself.
- [x] **Lens shadowing closed in `commands/lens.md`.** `SECURITY.md:26-28` claimed project-local
      lenses could not shadow `security-reviewer`; the engine implemented it, the command that
      actually resolves lenses did not, and the two disagreed in the same run.
- [x] **Intent gate extended to `--fix`.** `--fix` turned `/lens` from critic into producer
      without inheriting the gate — it would have improved a credential-harvesting page.
- [x] **Second-order injection broadened** beyond text that addressed the reviewer, to payloads
      aimed at the *next* model to consume the artifact.
- [x] **Approval-gate risk test made non-inferential** — content-derived thresholds let content
      lower the bar.
- [x] **`research-synthesizer` supplied-citation clause added.** `SECURITY.md:37-39` listed it as
      a supplied-facts defender; the clause was absent.
- [x] **Independent-judge list replaced with a rule** (`rubric.md`, `runner.md`) — the enumeration
      predated cases 22–27, so the intent-refusal, injection, and compliance-reviewer cases were
      self-grading, which `runner.md` itself calls "not a valid result."
- [x] **`ai-tells` voice counterweight + carve-outs.** Commit `208e2f8` claimed to resolve the
      ai-tells ↔ voice-preservation tension; it never touched `lenses/ai-tells.md`. `--lens
      ai-tells` alone ran the stripping lens with no counterweight, and had no carve-out for
      quotations, statutory terms of art, or domain terminology.

### Clean-install smoke test (2026-07-21)

Ran before touching the delivery shell, because nothing had ever verified the plugin works as
*installed* rather than as a repo. Findings:

- **Root cause of the blind spot:** `known_marketplaces.json` had promptsmith registered as
  `source: directory → C:\Dev\promptsmith`. Every run in the project's history had cwd == plugin
  root, so every bare relative path resolved by coincidence. A dev-loop install is structurally
  incapable of surfacing this class of bug.
- **Packaging is fine** — a fresh GitHub clone carries all 22 agent files, both templates, and all
  12 lenses. (The 0.1.0 plugin cache missing `agents/` was a stale artifact: it was built 38
  minutes *before* the gallery was first committed at `94cb9cb`. Not a packaging defect.)
- **15 bare relative paths** across 4 commands + 2 skills resolved against the user's cwd. From a
  clean project directory all six probe paths missed.
- **`${CLAUDE_PLUGIN_ROOT}` is the supported fix** — the plugins reference lists "Skill and agent
  content / Anywhere the placeholder appears." Verified against the doc directly after a subagent
  gave contradictory guidance on it.

- [x] **Delivery shell, part 1 — functional breaks:**
  - [x] All 15 references now use `${CLAUDE_PLUGIN_ROOT}`, each with the standalone (Option B)
        fallback path stated alongside it.
  - [x] **`description:` added to all 20 gallery agents.** They shipped with `name`/`role`/`voice`/
        `lenses`, of which the host only recognizes `name` — so all 20 rendered as the identical
        label "Agent from promptsmith plugin" and **could not be auto-selected by task context**.
        The marquee feature was reachable only by explicit name. `role`/`voice`/`lenses` retained
        for paste-anywhere use. Template, `/forge-agent`, and the gallery format spec updated so
        newly forged agents carry one.
  - [x] **Phantom agents removed** — `agents/README.md` → `docs/agent-gallery.md`,
        `agents/coverage-gaps.md` → `docs/coverage-gaps.md`. Both lacked frontmatter yet loaded as
        invokable agents (`promptsmith:README`, `promptsmith:coverage-gaps`), confirmed in a live
        session roster. `agents/` now holds 20 files, all real agents.
  - [x] **Coverage-gap log redirected** to `~/.claude/promptsmith-coverage-gaps.md` — it is
        written to, and `${CLAUDE_PLUGIN_ROOT}` is a cache wiped on update. Now asks before
        creating, consistent with the stateless identity.

- [x] **Delivery shell, part 2 — docs + metadata:**
  - [x] Hero GIF tracked (`docs/assets/`) — the README referenced it while it was untracked, so
        the image was broken on GitHub.
  - [x] Option B rewritten as a 5-row table including `templates/` and `agents/`, each with what
        breaks if you skip it. It previously omitted both, then claimed "that's the full
        footprint."
  - [x] Install verification now includes an actual functional check (`--lens skeptic` must
        report running), not just command autocomplete — autocomplete would have passed on every
        broken install described above.
  - [x] `plugin.json` advertised `/lens-review`; the command is `/lens`. That string renders in
        marketplace listings. Also added "Eval-backed."
  - [x] Doc drift: lens count 11 → 12 (`ai-tells` was missing from both guides), "all three
        commands" → four, repo layout omitted `/orchestrate`, `/orchestrate` was marketed as
        "planned" 200 lines after its own live run, and `USING-PROMPTSMITH.md` +
        `COMMAND-SHEET.md` still taught the manual round-trip that `--fix` deleted.
  - [x] Uninstall footprint now names the one file promptsmith can write
        (`~/.claude/promptsmith-coverage-gaps.md`) rather than claiming it writes nothing.
  - [x] `voice:` added to frontmatter on `api-reviewer`, `copy-rewrite`, `feature-spec` (it was
        only in their bodies). All 20 agents now carry name/description/role/voice/lenses.
  - [x] README's "8-agent run" reworded to "7 specialists plus 1 independent verifier, 8 in
        total" — the claim was accurate against the run file but read as contradicting its own
        evidence filename, which is the first thing a skeptic checks.

Verified after this slice: 20 agents · 12 lenses · 27 cases · 4 commands, and every count claim
in README / USING-PROMPTSMITH / COMMAND-SHEET / plugin.json reconciles against `ls`.
### `/grade` — the user-facing eval loop (2026-07-21)

The asymmetry that motivated it: promptsmith ran a rigorous measured-iteration loop (score →
change one thing → re-score → keep only what didn't regress) and a rubric-bound `evaluator`
agent — **on itself only**. Users got none of it for their own prompts.

- [x] **`/grade` command** (5th command, `commands/grade.md`) — scored verdict on a prompt, or
      `--against` to compare two versions.
      **⤷ Superseded 2026-07-21 (same session, pre-promotion): merged into `/lens --grade`.** The
      standalone command was removed before a single external install. See the merge note below.
- [x] **GRADE route in the engine** (Step 8) — states its rubric before scoring, runs a coverage
      pass over the nine concerns, an adversarial quality pass, hard gates, then leverage-ranked
      fixes. Grades **coverage, not conformance**: a prompt resolving a concern in prose scores
      ✅ and is never docked for lacking promptsmith's headings.
- [x] **`templates/graded-prompt.md`** — output skeleton, verdict-first, with a comparison mode.
- [x] Reports ✅/⚠️/❌ counts, never a numeric score — a host-judged rubric doesn't support
      "73/100", and fake precision invites tracking a trend that isn't real.
- [x] **`--against` names regressions even when the revision wins overall.** That is the whole
      reason to measure instead of eyeball, and it's what a one-shot rewrite hides.
- [x] Hard-gated: refuses to grade a harmful prompt (grading it is helping it), and treats the
      graded prompt as untrusted data — a prompt steering its own grader is a *plausible* input
      here, not an exotic attack.

### Merge `/grade` → `/lens --grade` (2026-07-21, pre-promotion)

Two adversarial launch reviews (GTM + cold-user) independently flagged that `/lens` and `/grade`
overlap enough to confuse — the docs needed three separate "which do I use" paragraphs, and the
`evaluator` gallery agent already overlapped `/grade`. When a distinction needs three paragraphs
to defend, it's a product smell. Merged, in the only clean window: **before a single external
install**, so the public never sees the 5-command surface get unwound.

- [x] `/grade` deleted as a standalone command; folded into `/lens` as **`--grade`** (verdict
      mode) + **`--against`** (comparison) + **`--rubric`**. Command surface: **5 → 4**.
- [x] The GRADE engine route (Step 8), `templates/graded-prompt.md`, and the untrusted-input /
      refuse-harmful / coverage-not-conformance / regression-honesty guarantees all **carried over
      unchanged** — only the entry point moved. Reached via `/lens --grade`; there is no `/grade`.
- [x] Reconciled every surface: `commands/lens.md` (grade mode section), engine routing,
      template next-step, README, USING-PROMPTSMITH, COMMAND-SHEET, `plugin.json`, eval cases
      35–37, and the `evals/README.md` route table. Command count back to **four** everywhere.
- [x] Re-eval the grade path blind on the new `/lens --grade` surface (cases 35–37): all correct —
      35 FAIL on Grounded, 36 names the Bounded regression under B's win, 37 flags the self-grading
      injection. Producer confirmed `--grade` routing was unambiguous from `lens.md` + engine Step 8.
- [x] Clean-install re-verify on the 4-command surface: PASS (all paths resolve, no standalone
      `/grade`, `graded-prompt.md` still shipped).

**Identity note:** this is the 5th command against a stated "four commands, not a marketplace"
guardrail. Accepted deliberately — it is the feature that makes the eval-harness framing literally
true on product surfaces rather than only in the launch narrative (see `docs/launch-plan.md`).

### Eval coverage — closing the six-feature gap (2026-07-21)

Suite grew **27 → 37 cases** and **3 → 6 known-bad fixtures**. Every feature that shipped after
the v0.2.0 gate now has a dedicated case, and the audit's structural blind spot is closed.

- [x] **`rubric.md` fixed: 8 → 9 SHARPEN blocks.** PROHIBITIONS was invisible to the only
      deterministic check in the harness, so a regression that dropped it scored a clean ✅.
      Added the PROHIBITIONS-vs-OUT-OF-SCOPE distinction as an invariant.
- [x] **GRADE route added to `rubric.md`** — structural invariants + quality dimensions, with
      coverage-not-conformance, regression-honesty, and not-steerable as hard gates.
- [x] New cases: **28** prohibitions · **29** brutalist style-relative (a full revert of the
      visual split would have scored green before this) · **30** ai-tells tiering · **31** the
      voice-preservation collision, which makes the ai-tells↔voice tension *falsifiable* rather
      than asserted · **32** `--fix` minimality · **33** `--fix` second-order injection ·
      **34** verifier `VERIFIED WITH GAPS` · **35–37** grade, comparison, injection resistance.
- [x] New known-bad: **KB4** verifier laundering a demonstrated defect into "gaps" · **KB5**
      ai-tells stripping statutory language from a quoted provision · **KB6** a PROHIBITIONS
      block that is structurally valid but boilerplate — it passes the structural check, which
      is exactly why the fixture is needed.
- [x] `evals/README.md` coverage restated **per route** instead of per case, removing the prose
      enumeration that had already drifted.
- [ ] **Case 24 still asserts the pre-tri-state verifier contract** (`Verdict: FAIL`). Case 34
      covers the new middle state; 24 needs its vocabulary reconciled on the next pass.

### Eval run 2026-07-21 — partial; does NOT clear the v0.3.0 gate

Logged: `evals/runs/2026-07-21-post-adversarial-pass.md`.

- [x] **Known-bad calibration: 3/3 correctly FAILED.** Strongest signal in the run — those judges
      got an artifact and a rubric with no criteria to game and refused to pass a planted defect.
      A harness whose judges cannot say no is not a harness.
- [x] **Blind cases: 33 PASS (security gate), 36 PASS, 32 WEAK.**
- [~] **Cases 28, 29, 30, 31, 34, 35, 37 — PASS but provisional.** A methodology defect made wave 1
      non-blind (below). Re-run before treating as gate results.
- [ ] **Cases 01–27 not run.** This branch touched all 20 agents, the lens command, the coordinator,
      and the rubric — regressions are plausible, not theoretical. **The suite is not green.**

**Methodology defect (ours, not the repo's).** Wave-1 producers were told to read only a case's
`## Input` section, but `Read` returns the whole file, so they saw the Must / Must-not lists first.
Two of nine disclosed it unprompted; the rest can't be reconstructed. A producer holding the
must-not list can satisfy it without the behavior being right — the exact bias the harness exists
to remove. Fixed by extracting all 37 inputs to standalone files and passing them inline with a
prohibition on reading anything under `evals/`.

**New findings from the run:**
- [x] **`commands/lens.md` Step 6 minimality under-specified — FIXED.** The rule now lives in the
      command text as a mechanical test ("every change must trace to a finding you stated in
      Step 4; walk your diff and name the finding each change answers"), with the two honest
      escape hatches — add it as a finding first, or surface it as an unfixed observation — and a
      requirement that the change-summary name a finding per change. No longer relies on the eval
      case to carry the constraint.
- [x] **`lenses/ai-tells.md` ↔ `commands/lens.md` rewrite-by-default conflict — FIXED.** The lens
      no longer mandates emitting a rewrite; its two-pass discipline runs as internal validation,
      and a new "What gets emitted depends on the invoking route — this lens never decides that
      for itself" block defers to the command: findings-only by default, corrected artifact under
      `--fix`, folded-in requirements on SHARPEN/FORGE.
- [x] **Case 36's fixture was miscalibrated** — B dropped both safety rules while gaining only
      formatting, so a correct producer judged A stronger and the case never exercised
      "regression beneath a win." Rebalanced; calibration note in the case file. The fixture was
      wrong, not the implementation.

### Exposed-subset sweep (2026-07-21, blind) — gate cleared

After the two spec fixes, the exposed subset of cases 01–27 ran **blind** (inputs from extracted
files, no `evals/` access): the 12 gallery agents this branch edited plus both security gates and
both legal-surface agents.

- [x] **12/12 exposed legacy cases PASS blind:** 05, 06, 13, 14, 15, 16, 20, 21, 22, 23, 24, 27.
- [x] Both **security gates** hold blind (22 intent-refusal, 23 injection-resistance).
- [x] Both **legal-surface agents** hold blind (13 governance-letter, 27 compliance-reviewer) — no
      fabricated statute, disclaimers present, flag-and-route only.
- [x] **Tri-state verifier** confirmed blind (24 `NOT VERIFIED`, 34 `VERIFIED WITH GAPS`), with the
      Observable-evidence / Assessment split intact and the KB4 laundering pattern refused.
- [x] **Honesty floor** holds on the two highest-fabrication-risk agents blind: 14
      (declare-and-degrade, refused a Sources list) and 21 (refused to assert unverified package
      names, typosquat warning present).

### Full-suite blind run complete (2026-07-21) — SUITE GREEN

Every one of the 37 cases ran **blind** (three sittings; wave-1 contamination re-run, then the
untouched legacy cases, then the pre-existing known-bad fixtures re-confirmed).

**Final scorecard: 36 PASS · 1 WEAK (fixed `62a9a39`) · 0 FAIL. Calibration 6/6 correctly FAILED.**
Logged in full at `evals/runs/2026-07-21-post-adversarial-pass.md`.

- [x] Cases 28–37 re-run **blind** — all 7 wave-1 provisionals converted, no verdict moved.
- [x] Untouched legacy cases (01–04, 07–12, 17–19, 25, 26) run blind — all PASS.
- [x] All 6 known-bad fixtures (KB1–6) confirmed correctly FAILING under the revised rubric.
- [x] Case 24's stale fixture vocabulary reconciled (`Verdict: FAIL` → `NOT VERIFIED`).
- [x] **Two of the branch's own fixes validated inside the run:** case 31 named a finding per change
      (the minimality fix on the voice path); cases 03/04 emitted the `description:` frontmatter +
      `~/.claude/promptsmith-agents/` save warning, so `/forge-agent` cannot reproduce the
      descriptionless agent the gallery originally shipped.

### Step 7 — clean-install re-verify (2026-07-21) — PASS

Simulated a real install: `git archive HEAD` into a plugin-root dir (tracked files only, i.e. what
ships), cwd set to an empty project dir (the failure mode the path bug caused). Verified:

- [x] **All 8 `${CLAUDE_PLUGIN_ROOT}/…` references resolve** against the install image from a
      non-repo cwd — the bare-path bug that only ever worked under a dev-install is closed.
- [x] `plugin.json` valid; advertises all five commands; **no `/lens-review`** (the retired name).
- [x] All 5 command files ship with frontmatter.
- [x] **All 20 agents load** (name + description present); **no phantom agents** — `README.md` /
      `coverage-gaps.md` are absent from `agents/` (now in `docs/`).
- [x] 12 lenses present; `skeptic` (the default lens) loads.
- [x] **`plugin.json` bumped 0.2.0 → 0.3.0** so the manifest matches the tag (the exact drift this
      whole pass fought).

**All seven Phase-0 steps complete. Ready to tag v0.3.0 after merge to main.**

## Now in progress — Layer 2 orchestration (Claude-Code-native)

**Status (2026-06-25):** coordinator v0 built on branch `feat/layer2-orchestration` —
`skills/orchestration/SKILL.md` (the pipeline) + `commands/orchestrate.md` (the `/orchestrate`
command) + `docs/coverage-gaps.md` (the gap log). The pipeline encodes gate → sharpen →
decompose → route → seams/conflicts → approval gate → dispatch (subagents) → assemble/curate →
report. **Not yet merged** (awaits review). Open mechanism decisions remain (below). Acceptance
target is eval case 17.

- [x] Coordinator pipeline (decompose / route / seams / synthesize) specified as runnable protocol.
- [x] Coverage-gap detection + log (now `~/.claude/promptsmith-coverage-gaps.md`) feeding `/forge-agent`.
- [x] Approval gate before fan-out (default ON; `--no-gate` to waive); `--dry` to inspect routing.
- [x] First live multi-agent run: case 17 PASS via real 4-agent dispatch; guardrail cases 18
  (overkill-fallback) + 19 (coverage-gap) PASS; D6 applied (catch agent-emergent conflicts).
- [x] Full live re-run (2026-06-25): case 17 as a real **7-agent build + independent verifier**
  (runs/2026-06-25-2101-orchestration-case17-live-7agent.md). Caught a 3-way expiry conflict,
  assigned the unowned `expires_at`-enforcement seam, and Step 6.5's verifier caught a HIGH
  `widgets` over-serialization defect → synthesis halted + escalated. The regression anchor now
  has a non-simulated PASS.
- [ ] Continue tuning from real runs (more domains, larger fan-out, the deferred slices).
- [x] Forge `backend-builder` to fill the API-maker gap (gallery now 15 agents).
- [x] Mechanism decisions resolved (2026-06-25): dispatch = **subagents** (Workflow later only
  if fan-out demands); agent form = **inline-prompt** (single source of truth, portable);
  approval gate = **smart threshold** (auto ≤3 agents/low-risk, gate larger; `--gate`/`--no-gate`
  override); command name = `/orchestrate`; specialist selection = roster/lens match.

The hard, failure-prone parts — design these hardest:

- **Decomposition.** Split the sharpened prompt into specialist slices with no overlap and no
  gaps. Decide who owns each seam.
- **Dispatch.** Route each slice to the right gallery specialist as a live subagent; run
  independent slices in parallel.
- **Assembly + curation.** Merge conflicting outputs into one voice — dedup, resolve
  contradictions, enforce consistent tone/format. This synthesis step is the real moat (cf.
  Auris coordinator synthesis). A pile of subagent outputs is not a deliverable.
- **Guardrails.** Detect when orchestration is overkill (a single agent does it better) and
  fall back to plain `/sharpen`. Cap fan-out. Surface what each specialist did.
- **Coverage-gap detection → gallery growth.** When part of a request falls outside every
  existing agent's purview, the coordinator must not silently drop it or fake-cover it. It
  **logs the unmet slice** (what was asked, why no agent fits), surfaces it to the user, and
  feeds it back to the gallery: a recurring gap becomes the spec for a new agent forged via
  `/forge-agent` and dropped into `agents/`. This is the feedback loop that makes the roster
  grow from real demand instead of guesswork — orchestration and the gallery improving each other.
- **Agent tool / source access.** Some specialists are only fully useful with live tools —
  `research-synthesizer` needs web/retrieval; others may need a database, a file reader, or a
  code runner. The orchestration runtime is where agents get scoped tool access. Until then,
  affected agents must **degrade honestly** (D5: declare no-source, label training knowledge,
  never fabricate citations). Phase-2 task: a way to grant an agent the tools it needs.
  - **`mcp-integrator` is the front half of this.** When the coordinator hits a slice that needs
    a tool/data source, it routes to `mcp-integrator` to recommend an existing MCP server or spec a
    new one (adopt-before-build, least-privilege) **and emit the wiring recipe** (`claude mcp add` /
    config). It advises and hands off the runnable steps; it does not auto-connect. The remaining
    Phase-2 piece is the **runtime that actually applies the wiring** (approval-gated) and attaches
    the MCP to the agent's session.

### Worked example: shareable dashboard links

A manual stand-in-coordinator run of *"Add public, read-only shareable links to user
dashboards"* (eval case 17) decomposed to feature-spec, data-modeler, security-review, and
frontend-builder. Run in isolation, the agents exposed exactly the failure modes Layer 2 must
own:

- **Unowned seam.** `expires_at`: data-modeler *stores* it, security-review *demands enforcement*,
  the API slice would *check* it — and in isolation each assumes another owns it. Nobody enforces.
  → The coordinator must assign every seam an explicit owner.
- **Overlap / duplication.** feature-spec and security-review both raise "public = data exposure";
  data-modeler and security-review both opine on token randomness. → Dedup the concern to one voice.
- **Direct conflict.** feature-spec's "no expiry in the MVP cut line" contradicts security-review's
  "expiry is mandatory." → The coordinator resolves it before output; it doesn't paste both.
- **Pile, not deliverable.** Four output contracts, four personas. → Synthesis to one voice is the moat.

This is the acceptance bar encoded in case 17: decompose-without-overlap, seam-ownership,
conflict-resolution, single-voice synthesis, domain completeness.

Resolved (2026-06-25):
- Host mechanism → **subagents** (Agent/Task); Workflow revisited only if fan-out outgrows it.
- Specialist selection → **roster/lens match** against `docs/agent-gallery.md`.
- Approval point → **smart-threshold gate** before fan-out (Step 5).
- Conflict handling → coordinator **resolves within authority, escalates product/risk calls** (D6).

Still open (deferred, not blocking):
- Promote gallery agents to first-class Claude Code subagent definitions (agentType)? — kept
  inline-prompt for now (single source of truth, portable).
- Workflow harness for very large / pipelined fan-outs.
