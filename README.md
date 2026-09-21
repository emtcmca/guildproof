# guildproof

**A guild of specialist agents, and an inspector that can stop the job.** A Claude Code plugin.

[![fresh-machine](https://github.com/emtcmca/guildproof/actions/workflows/fresh-machine.yml/badge.svg)](https://github.com/emtcmca/guildproof/actions/workflows/fresh-machine.yml)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

![`/guildproof:sharpen` turning a one-line request into a full prompt. A terminal-styled
animation drawn frame by frame from the text of a real run, not a screen recording.](docs/assets/sharpen-demo.gif)

---

## What this is

Ask a coding agent to review work and you get prose: some observations, some rewritten code, no
verdict. It does not say whether the work is blocked, and it does not say whether the review was
independent of whoever wrote the code. guildproof ships that missing reviewer as an independent
verifier that returns a blocking verdict, a guild of 20 specialist agents to dispatch, four
commands that turn a rough request into a complete prompt instead of a guess, and 12 review lenses.
No dependencies, no API keys, and no model calls inside the plugin: it is pure method and
structure, and your agent does the reasoning.

The measured part of that is narrower than the pitch, and this page says so in detail below: what
has been tested is that **a short output contract reliably produces a blocking, independent
verdict** where bare models produce one about a quarter of the time. The rest ships because the
prompts are complete and inspectable, not because a number vouches for them.

---

## Install

```
/plugin marketplace add emtcmca/guildproof
/plugin install guildproof
```

Verify, in order:

1. Type `/guildproof` and confirm all four autocomplete: `/guildproof:sharpen`,
   `/guildproof:forge-agent`, `/guildproof:lens`, `/guildproof:orchestrate`.
2. Run `/guildproof:lens --lens skeptic` on any short paragraph. If it reports running the
   `skeptic` lens, the bundled lens library resolved correctly. That is the check that actually
   proves the install, not the autocomplete.

(For local development against a clone, add the working copy instead:
`/plugin marketplace add /path/to/your/guildproof-clone`.)

**Not on Claude Code?** All twenty gallery specialists plus the engine and a grading skill, 22 in
total, ship as host-agnostic skills you can install into Codex, Copilot, or anything else that
reads `SKILL.md`: `npx skills add emtcmca/guildproof-skills`.

The other install paths moved to the how-to so this page stays short:
[Option B, manual standalone with bare command names](docs/USING-GUILDPROOF.md#option-b--manual-standalone-bare-command-names)
· [Option C, any other agent](docs/USING-GUILDPROOF.md#option-c--any-other-agent)
· [Uninstall](docs/USING-GUILDPROOF.md#uninstall).

---

## What's measured, and why it matters to you

Twelve models. Three vendors. One piece of well-built code that leaks a field its contract
forbids. Each model saw it twice with no instructions and twice with `agents/verifier.md` as its
system prompt, scored by two blinded judges against a checklist written before any run.

**Nothing unprompted stated whether the work was blocked, or whether its review was independent.**
Both behaviors scored **0 of 48**, across twelve models and three vendors. Prompted, **48 of 48**.

What that means for you: a review with no verdict is a review you have to re-read yourself, and a
review that never says who wrote the code cannot be told apart from self-approval. Those two lines
are what turn a wall of prose into something a build can stop on, and they are the two a capable
model will not write on its own.

### The number that got smaller, and why it is still on this page

An earlier version of this section led with an aggregate: **17%** of scorings bare against **98%**
prompted. That arithmetic was never wrong, and it is no longer the claim, because a later run took
it apart.

A third arm carried **only the `## Output contract` section** of `agents/verifier.md` — the list of
sections an answer must contain. No method, no adversarial stance, no guardrails, none of the rest
of the prompt. It scored **72/72**, against the full prompt's **71/72** and a bare arm's **18/72**.

**The output contract buys the entire measured gap.** On this checklist the rest of the prompt adds
nothing measurable, so the honest claim is about the contract, not about the specialist prompt:

> A short output contract reliably produces a tri-state verdict, a BLOCKING line, an independence
> statement, severity-ranked defects, and a receipt per clean axis. Bare models produce those about
> a quarter of the time.

Two things are easy to get wrong about that result:

- **"No measured effect" is not "no effect."** Arm C *is* guildproof content, so the benefit was
  localized, not removed. Method, stance and guardrails would have to pay off in **defect quality** —
  finding a real defect, ranking it correctly, refusing a plausible-but-wrong refutation — and
  nothing here measures that. Detection never discriminated either: every cell found the planted
  defect in both arms.
- **The checklist was not wrong, it was narrow.** It scores output *structure*, which this page has
  always said, and an output contract is precisely the instrument that produces output structure.
  In hindsight the result is close to tautological. It still took a third arm to see it, which is
  the argument for running one.

The reduced arm was extracted mechanically from the shipping file rather than written by hand, and
it falsified a prediction registered before any cell ran. Full run:
[`evals/runs/2026-09-21-crossmodel-v3-3arm.md`](evals/runs/2026-09-21-crossmodel-v3-3arm.md).

**Bare performance did not track model recency, across the models tested.** The unprompted score
scatters between 0% and 33% with no trend across four consecutive Gemini generations, three OpenAI
generations and three Claude tiers. One Gemini generation scored **zero of 24**, and it was the
third of four, not the newest.

Stated carefully, because an earlier version of this paragraph overreached: **no trend observed is
not a trend that will not appear.** Two models of the *same* OpenAI generation scored 8% and 33%, a
wider spread than any generation-to-generation change here, and sibling models are not repeated
measures of one capability. What the data supports is that the gap is not *visibly* closing on its
own — not that a future release cannot close it.

**The suite ships six fixtures it must always fail.** Each pairs a case input with a deliberately
wrong output: an invented fact asserted as established, a review that obeys an injection planted in
the artifact and clears it, a handler with interpolated SQL, a verifier laundering a defect it
found into "gaps". The gate fails unless a blinded judge marks all six FAIL, and it ran at the
commit behind this release: **6 of 6**, plus a known-good output through the same path to show the
judge is not simply failing everything. What that means for you: the first nine runs in this repo's
history produced **not one FAIL between them**, which is indistinguishable from a judge that cannot
say no. These fixtures are what make every other number here falsifiable, and they are why the
losses above are published at all.
Gate: [`evals/runs/2026-09-20-b4-knownbad.md`](evals/runs/2026-09-20-b4-knownbad.md).

### Four things this does not claim

- **It will not help a model see a bug.** Every run found the defect, in both arms, on all twelve
  models. Detection is the model's job. This changes what the model *does* with a defect it
  already found.
- **It does not show the specialist prompt beats a bare output contract.** The third arm above is
  the reason. Anything this page says about method, adversarial stance or guardrails is a design
  argument, not a measured one.
- **It measures output structure, not review quality.** Nothing here scores whether a defect was
  ranked correctly or whether a wrong refutation was refused. A defect corpus with ground truth per
  fixture is the outstanding gap, and it is the reason not to over-read any of this.
- **One defect type, one artifact.** Breadth across models is not breadth across bugs.

**And one thing κ does not tell you.** Inter-judge agreement on the cross-model run was κ 0.97,
which says the two blinded judges agreed — not that they were right. High agreement partly means
the scored thing was unambiguous, which for a structural checklist is expected. Reliability is not
validity, and reading κ as reassurance is part of how the aggregate headline above survived as long
as it did.

### Scope of the benchmarks

**Everything measured on this page is about one agent out of twenty.** `verifier` is the headline
because it is the piece nothing else ships, and because it is the only one with a cross-model run
behind it. It is not evidence about the rest of the guild, and this page should not be read as if it
were.

**Four of the twenty have a bare-versus-prompted benchmark on file**, on one input each, at two
model tiers: `verifier`, `debugger`, `security-review` and `api-reviewer`. The other sixteen are
not benchmarked, and neither `/sharpen` nor `/orchestrate` is. They ship because they are complete
prompts, not because a number says they help. If you want the gallery judged, judge it on the
prompts themselves — they are all plain markdown in [`agents/`](agents/), and
[the gallery table below](#the-gallery) says what each one is for.

`api-reviewer` is the one that came back mixed, and per this repo's own rule it publishes here with
the rest. At the small tier the bare model reviewed the contract in 4 of 4 scorings against the
prompt's 3 of 4, and flagged breaking changes in 2 of 4 against the prompt's 0 of 4. The prompt won
only on naming the abuse path, 0 of 4 to 4 of 4. At the frontier tier that reverses: it ties the
first two at 4 of 4 and wins the third. `verifier` is the one that does not close with model
strength: 8% bare at the small tier and 13% bare at the frontier tier, against 92% and 100%
prompted.

Every table, every judge quote, the method limits, and a section on the bugs found in the
measuring instrument itself: **[`docs/FINDINGS.md`](docs/FINDINGS.md)**. Raw cross-model run, with
all 48 outputs and all 24 judge scorecards:
[`evals/runs/2026-09-20-crossmodel-verifier.md`](evals/runs/2026-09-20-crossmodel-verifier.md).
The three-arm run that reduced the claim:
[`evals/runs/2026-09-21-crossmodel-v3-3arm.md`](evals/runs/2026-09-21-crossmodel-v3-3arm.md).

Re-derive the published tables with **no model call**, straight from the committed scorecards:

```
python evals/harness/judge-crossmodel.py --tabulate \
  --cells evals/runs/2026-09-20-crossmodel-v2-artifacts
```

Run it against your own models: `python evals/harness/run-crossmodel.py --check`

---

## Try it before you install

Because there is no runtime, you can run a piece of this by hand right now, with no install, no
plugin and no API key, in whatever chat you already have open.

**1.** Open **[`agents/debugger.md`](https://raw.githubusercontent.com/emtcmca/guildproof/main/agents/debugger.md)** and copy the whole file. It's one self-contained file, about 60 lines.

**2.** Paste it as the **first message** in a new conversation with any capable model.

**3.** Send your actual problem as the **second message**. If you don't have one handy:

```text
Here is the failure:

TypeError: Cannot read properties of undefined (reading 'map')
    at renderInvoiceLines (invoice-table.tsx:88)
    at InvoiceTable (invoice-table.tsx:41)

It hits about 3% of invoice page loads. I think it started last Thursday, around when we
moved the invoice fetch into a server component. I don't have a reproduction.
```

### What you should see

Check for these five. They are what the prompt asks for, and this exact input is what benchmark
B2 measures it with, so the measured rates are printed below the list rather than left to your
impression:

- **Your claims come back labelled as yours.** The "last Thursday," the refactor, and the 3%
  should be flagged as unverified input rather than absorbed as fact. All three are doing most
  of the work in any ranking, and none are confirmed.
- **It refuses to invent a reproduction** and says so, instead of producing a plausible one.
- **Ranked hypotheses, each with the cheapest probe that would kill it**: a specific observation
  and a rough cost, not a list of things to try.
- **Trigger separated from root cause.** The server-component move is the trigger; the root cause
  is code treating an optional field as guaranteed.
- **No one-line patch handed over.** It should note that `?? []` stops the crash while telling you
  nothing about whether those 3% of invoices are *supposed* to have line items, and that if they
  are, the guard turns a loud crash into silent under-billing.

### How often those five actually happen

B2 sent this exact input to both arms twice and had two judges score each output. On the debugger
checklist the prompt scored **11 of 20 against 2 of 20 bare** at the small tier
(`claude-haiku-4-5-20251001`), and **19 of 20 against 15 of 20 bare** at the frontier tier.

Two results in that set you should know before you paste anything:

- **The first bullet did not happen at the small tier, in either arm.** `separates the user's
  claims from verified facts` scored **0 of 4 with the prompt and 0 of 4 without it**. Both judges
  found the outputs restating "3%" and "last Thursday" as established fact and reasoning from
  them. At the frontier tier it scored 3 of 4 with the prompt against 2 of 4 bare. On a small
  model, expect to have to ask for that labelling yourself.
- **The fourth and fifth bullets are partial at the small tier**, 1 of 4 and 2 of 4 with the
  prompt against 0 of 4 bare for both. The single mark on the fourth is one judge disagreeing with
  the other on one run, so read it as thin. At the frontier tier both are 4 of 4.

The two that hold at both tiers are the reproduction refusal and the ranked hypotheses with a
probe each. That second one is the largest single gain in the set: 0 of 4 bare to 4 of 4 with the
prompt at the small tier.

Per-behavior tables, every judge quote, and the note that the frontier run does not pin a model id:
[`docs/FINDINGS.md`, section 3](docs/FINDINGS.md#3-the-specialist-benchmarks-b2).

**No reduced arm was run here.** The verifier result above showed that a bare output contract can
account for a whole measured gap, and nothing rules that out for this benchmark either — so read
these as "the prompt produced this", not "the method produced this". Running the control on the
other benchmarks is open work, and it is now a precondition in this repo for any new claim about a
prompt.

That is one of twenty gallery agents, run the hard way. The plugin is the same prompts with the
dispatch, the lens library, and the orchestration around them, but you should not have to take
that on faith before installing anything.

---

## What you get

| Command | You give it | You get back |
|---|---|---|
| `/sharpen` | a rough task request | a complete, gap-filled, reviewed **prompt** to paste into any agent |
| `/forge-agent` | a short description of an assistant | a complete, reusable **system prompt** |
| `/lens` | an existing prompt / page / draft | **findings** from expert lenses, or with `--grade`, a **scored verdict** on a prompt |
| `/orchestrate` | a multi-domain request | **one synthesized deliverable**, the gallery coordinated *(Layer 2)* |

The first three run with zero model calls and paste anywhere. `/orchestrate` needs a host that can
spawn subagents (Claude Code). Every run is hybrid: it returns a finished draft immediately, lists
the assumptions it had to make, and offers a `--deep` interview to resolve them one question at a
time. Flags, recipes and every route in one page:
[`docs/COMMAND-SHEET.md`](docs/COMMAND-SHEET.md). Longer how-to, including which command to reach
for: [`docs/USING-GUILDPROOF.md`](docs/USING-GUILDPROOF.md).

### What `/sharpen` actually adds

Same request in; the scaffolding *named* on the way out:

![Prompt delta: the one-line request "write a function to retry a failed API call" expanded into a full prompt — role, retryable-only requirements, jitter, a total deadline, a prohibition on retrying non-idempotent POSTs, and an open question about idempotency the tool refuses to guess](docs/assets/proof-prompt-delta.png)

Every margin note is a decision a rushed one-liner forgets: which failures are safe to retry, the
jitter that avoids a thundering herd, the prohibition that stops a double charge. The last line is
the honesty floor. It flags the one fact it *can't* know (*is this call idempotent?*) instead of
guessing it.

<details>
<summary><b>Prefer to see the code it buys you?</b> (the same task, answer-vs-answer)</summary>

<br>

The naive request gets a competent, backoff-aware retry function that **silently retries a
`POST /charge` which already succeeded but timed out on the wire, a double charge.** The sharpened
prompt gets one that retries only what's safe and *refuses to retry a write it was never told is
idempotent*:

![Answer delta: a buggy retry function that double-charges a non-idempotent POST, beside a safe one that refuses the unsafe retry](docs/assets/proof-code-delta.png)

</details>

The full four-beat walk-through is in [`docs/assets/proof-answer-delta.md`](docs/assets/proof-answer-delta.md).

### The gallery

A roster of 20 specialists across spec → plan → build → test → review → document, each a
ready-to-paste system prompt with a named **voice**:

- **Build:** `feature-spec`, `planner`, `data-modeler`, `backend-builder`, `frontend-builder`, `test-author`, `refactor-planner`
- **Review:** `api-reviewer`, `security-review`, `verifier`, `evaluator`, `compliance-reviewer`, `debugger`
- **Write:** `copy-rewrite`, `docs-writer`, `sop-writer`, `governance-letter`
- **Meta:** `research-synthesizer`, `prompt-engineer`, `mcp-integrator`

`/guildproof:forge-agent` checks this gallery first and **adapts** a close match instead of
starting cold. Forge your own, then drop it in `agents/` to grow the roster. Per-agent detail and
the file format: [`docs/agent-gallery.md`](docs/agent-gallery.md).

The gallery is also the dispatch roster for `/orchestrate`. On a live run of 7 specialists plus 1
independent verifier against "add public read-only shareable links to user dashboards", the
coordinator caught a three-way disagreement on link expiry between the spec, the schema and the
security slice and settled it, escalated the TTL value to the user instead of guessing, and then
the independent `verifier` found a HIGH data-exposure defect the builder's own allow-list DTO had
missed, so the pipeline halted rather than synthesizing a vouched-for-but-unverified build. That is
one logged run in `evals/runs/`, a demonstration and not a measurement, and
[FINDINGS says so](docs/FINDINGS.md#7-what-is-not-measured-at-all).

### Expert lenses

A lens is a professional's checklist in a markdown file, applied to the draft before you ever see
it. The 12 built-in lenses cover `ux-designer`, `visual-design`, `accessibility`,
`security-reviewer`, `performance`, `api-design`, `data-integrity`, `seo`, `product-strategist`,
`editorial`, `ai-tells`, and `skeptic` (the "push back on me" red-team lens, applied by default).

Add your own with no fork needed. Drop a markdown file into `~/.claude/guildproof-lenses/`
(everywhere) or `./.guildproof-lenses/` (one project); it loads automatically and overrides a
built-in of the same name.

```markdown
---
name: my-lens
applies-to: comma, separated, topics, that, auto-select, this, lens
---

# My Lens
- A specific check the agent runs the draft against.
- Another check. Keep them concrete and answerable.
```

---

## Honest limits

- **The checklist measures output structure, so a structural instrument is enough to max it.** That
  is what the third arm showed, and it is the largest limit on this page. A prompt claim in this
  repo now requires a reduced arm before it is published; only `verifier` has one so far.
- **A rubric can be highly reliable and weakly valid, and κ cannot tell you which.** κ 0.97 means
  the judges agreed. It says nothing about whether the checklist measured the thing the headline
  claimed.
- **One artifact and one defect type in the cross-model study.** Twelve models is breadth across
  models, not across defect classes.
- **Four of the twenty gallery agents carry a benchmark.** `/sharpen` (B1), `/orchestrate` (B5)
  and `/forge-agent` (B6) carry none. `/sharpen` is the oldest and most central claim in this repo
  and has never been tested.
- **`api-reviewer` lost two of its three behaviors at the small tier.** Figures above. Its 3 of 4
  is one judge disagreeing rather than a lost run, and the run doc records that the
  `flags breaking changes` item admits two readings on this input and is queued to be
  re-specified, so that row is unsettled rather than a loss.
- **k = 2 for the cross-model study and the known-bad gate; k = 1 for the numbered suite, B3 and
  the case 41 four-arm run.** k = 1 is thin for anything that reads as a recall miss.
- **Every judge is a Claude model**, scoring Claude, GPT and Gemini outputs.
- **Behavior compliance is not correctness.** Every item scores whether a behavior is present,
  with a quote. An output can hit every item and be wrong on the substance, and the judges
  recorded cases where it was.
- **The numbered eval suite is a regression gate, not a score, and its verdict counts are not a
  rate.** 34 of the 38 cases were re-judged on 2026-09-20 (2 PASS, 24 WEAK, 8 FAIL; the 4
  `/orchestrate` cases need a host that can dispatch subagents, so they are unmeasured rather
  than passing). Do not read that as a 6% pass rate. PASS requires zero ⚠️ marks across roughly
  15 to 20 marks per case, under a judge told to default to ⚠️ when uncertain, and the suite has
  no bare arm to cancel judge harshness against. The bare-versus-prompted numbers above are at
  least comparisons against a control; these are absolutes and are not.
  [`evals/runs/2026-09-20-b4-suite.md`](evals/runs/2026-09-20-b4-suite.md) has the 8 failures,
  each named, and the four rubric defects the run found in its own measuring instrument.

The full list, with the blinding limits and the harness artifacts that survive into the numbers:
[`docs/FINDINGS.md`, section 6](docs/FINDINGS.md#6-method-limits) and
[section 7](docs/FINDINGS.md#7-what-is-not-measured-at-all).

---

## How it works (the engine)

All four commands run one method, defined in
[`skills/prompt-engineering/SKILL.md`](skills/prompt-engineering/SKILL.md):

1. **Route** — sharpen / forge / lens.
2. **Extract** — goal, audience, tone/feel/theme, constraints, success criteria, format, scope.
3. **Gap-fill** — make explicit, labeled, reversible assumptions (so the draft is usable now).
4. **Push-back** — red-team the request; turn weaknesses into guardrails.
5. **Lens pass** — run the draft against the selected professional checklists.
6. **Synthesize** — emit via the matching template.
7. **Surface + offer depth** — list assumptions and open questions; offer the `--deep` interview.

There is no LLM call inside the plugin. The host agent reads the skill and performs the reasoning,
which is what makes it model-agnostic and zero-cost. The two-layer split follows from that: Layer 1
(`/sharpen`, `/forge-agent`, `/lens`) stays portable, while Layer 2 (`/orchestrate`) needs a host
that can spawn subagents. Honesty guardrails run through both. It is written not to fabricate a fact, a
citation, or an MCP server it can't verify, and it shows its work with evals in `evals/runs/`.

---

## Repo layout

```
guildproof/
  .claude-plugin/      plugin.json + marketplace.json (install metadata)
  commands/            /sharpen, /forge-agent, /lens, /orchestrate
  skills/
    prompt-engineering/SKILL.md   Layer 1 engine (sharpen / forge / lens)
    orchestration/SKILL.md        Layer 2 coordinator (orchestrate)
  lenses/              12 built-in expert lenses
  agents/              the 20-agent gallery / dispatch roster — agent files only
  templates/           output skeletons for sharpen + forge
  evals/               host-judged eval harness (rubric, runner, cases, runs)
  docs/                FINDINGS.md (the evidence), guides, agent-gallery.md,
                       coverage-gaps.md, test-run records, README assets
```

---

## Docs

- [FINDINGS.md](docs/FINDINGS.md) — the complete evidence record: what is measured, what is not,
  every table, every result that cuts against the tool, and the method limits.
- [USING-GUILDPROOF.md](docs/USING-GUILDPROOF.md) — the full how-to (human or agent): all install
  options, command chooser, every command, lenses, the gallery, orchestration, the eval harness.
- [COMMAND-SHEET.md](docs/COMMAND-SHEET.md) — one-page reference: commands, flags, lenses, gallery,
  recipes.
- [docs/SECURITY.md](docs/SECURITY.md) — threat model + the guardrails (untrusted-input boundary,
  intent gate, supplied-fact verification, independent verification).
- [SECURITY.md](SECURITY.md) — how to **report** a vulnerability, and what is in and out of scope.
  The threat model above is the reasoning; this is the channel.
- [CONTRIBUTING.md](CONTRIBUTING.md) — where changes go, and what a prompt change has to say for
  itself. · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [CHANGELOG.md](CHANGELOG.md) — including which published claims have been narrowed, and why.
- [ROADMAP.md](ROADMAP.md) — the two-layer architecture and what's next.

---

## License

Apache-2.0 © 2026 Eric Tetzlaff
