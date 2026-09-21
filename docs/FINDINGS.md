# guildproof: the evidence

Every figure in this document traces to a committed run doc or scorecard, cited inline. Where a
figure does not exist, this document says so rather than estimating one.

> **⚠ The headline claim of Section 2 was reduced on 2026-09-21, and the figures are kept in place
> deliberately.** A reduced third arm carrying **only** the `## Output contract` section of
> `agents/verifier.md` scored 72/72, against the full prompt's 71/72 and a bare arm's 18/72. **The
> output contract accounts for the entire measured gap**, so every figure below that compares "bare"
> against "with guildproof" is properly read as *bare against a stated output contract*, not as
> evidence about the specialist prompt as a whole. Nothing has been deleted: the arithmetic is
> unchanged and still re-derivable from the committed scorecards, and what changed is the
> attribution. Run doc:
> [`evals/runs/2026-09-21-crossmodel-v3-3arm.md`](../evals/runs/2026-09-21-crossmodel-v3-3arm.md).
> Full treatment in [Section 2](#the-third-arm-and-what-it-took-away).
>
> **Two structural results are unaffected**, because they measure whether a named line is present
> rather than whether a judgment was good: an explicit `BLOCKING:` line and an explicit
> `Independence:` line each scored **0 of 48** unprompted and **48 of 48** prompted.

Terminology used throughout: a **cell** is one model output. A **scoring** is one judge marking one
checklist item on one cell. Two judges score every cell, so a per-item denominator is twice the
number of runs behind it. **Note that two different populations in this document are both sized
288**: Section 2's per-arm scoring count (6 items x 24 runs x 2 judges) and the judge-agreement
population used at "284 of 288 cells agreed" (6 items x 48 cells, spanning *both* arms). They
coincide by arithmetic accident. A disagreement rate computed against the wrong one will be off by
a factor of two.

---

## 1. What is measured, and what is not

This table is first on purpose. It comes from
[`evals/benchmarks/README.md`](../evals/benchmarks/README.md) (Coverage section), added 2026-09-20.

| Feature | Benchmark | Status | Detail |
|---|---|---|---|
| `verifier` | B2, B3, cross-model, 3-arm | **Measured, and narrowed by its own control.** A reduced arm carrying only the output contract reproduced the whole gap, so what is measured is the **contract**, not the specialist prompt. The bare-arm gap did not visibly close across the 12 models tested. | [Section 2](#2-the-verifier-study), [the third arm](#the-third-arm-and-what-it-took-away), [Section 3](#3-the-specialist-benchmarks-b2) |
| `debugger`, `security-review`, `api-reviewer` | B2 | **Measured, and it cuts against them.** Bare frontier models score well on their own checklists with no prompt. These prompts compete with model progress. | [Section 3](#3-the-specialist-benchmarks-b2) |
| `/sharpen` | B1 | **Not run.** The oldest and most central claim in this repo has never been tested. | [Section 7](#7-what-is-not-measured-at-all) |
| `/orchestrate` | B5 | **Not measured.** Four eval cases and one live seven-agent run exist. That is a demonstration. | [Section 7](#7-what-is-not-measured-at-all) |
| `/forge-agent` | B6 | **Not measured.** | [Section 7](#7-what-is-not-measured-at-all) |
| `/lens --grade` | cases 35-37 | Structural cases only. No with-versus-without benchmark. | [Section 7](#7-what-is-not-measured-at-all) |
| Lens library extensibility | none | **No evidence.** | [Section 7](#7-what-is-not-measured-at-all) |
| `docs-writer`, `frontend-builder`, `prompt-engineer`, `refactor-planner` | none | **No dedicated eval case.** | [Section 7](#7-what-is-not-measured-at-all) |
| The judge in this repo can fail a bad output | B4, known-bad half | **Measured** at the tagged commit. | [Section 4](#4-the-release-gate-b4-known-bad-half) |
| The 38 numbered eval cases at the tagged commit | B4, suite half | **Run 2026-09-20 at `1c5d7c6`: 34 of 38 judged, 2 PASS / 24 WEAK / 8 FAIL, 4 unmeasured by transport. A gate, not a rate.** | [run doc](../evals/runs/2026-09-20-b4-suite.md) |

### The durability question

Each benchmark asks one question of each feature: does a better model do this for free? A feature
whose advantage shrinks with every model release is a convenience with a shelf life. One whose
advantage holds is a durable asset.

This is a question about what to claim, not about what to ship. A command a strong model could
partly do unprompted is still repeatable and still has a fixed output shape. The durability finding
changes how prominently a feature is described, never whether it exists. Nothing in the table above
is a deletion candidate.
([`evals/benchmarks/README.md`](../evals/benchmarks/README.md), durability section.)

### House rules the benchmarks were written under

From [`evals/benchmarks/README.md`](../evals/benchmarks/README.md), house rules section, written
before any run:

- Two model tiers, with the exact model id recorded per run.
- k at least 2. One run is an anecdote.
- Blind judging: the judge writes its own defect list from the contract before reading any output,
  then scores outputs labelled only A and B. Arm-revealing lines are stripped first. The label key
  never reaches the judge.
- Prompts, outputs, judge lists, judgments, the label key and token counts all committed in a dated
  folder under `evals/runs/`.
- A result that cuts against guildproof ships with the same prominence as one that does not.

---

## 2. The verifier study

Source: [`evals/runs/2026-09-20-crossmodel-verifier.md`](../evals/runs/2026-09-20-crossmodel-verifier.md).
Artifacts: [`2026-09-20-crossmodel-v2-artifacts/`](../evals/runs/2026-09-20-crossmodel-v2-artifacts/),
holding 48 cells, 24 judge scorecards, 12 blinded bundles, the label key and the runner.

### The question

Does a capable model, asked to verify code against a contract, produce a verdict you can act on?
And does it get better at that as models improve?

### Method

One artifact: a well-built invoice handler that returns `customer_id`, which its own contract
forbids. Sent verbatim to both arms. Arm A is the bare model. Arm B gets `agents/verifier.md` as its
system prompt. k = 2 per arm per model.

**This run had two arms, and that is its central design weakness.** With only a bare arm and a full
prompt, nothing separates "the method worked" from "naming the required sections worked." A third arm
was added on 2026-09-21 on a 3-target subset, and it settled that question against the prompt — see
[the third arm](#the-third-arm-and-what-it-took-away). Read everything in this section with that
result in hand.

Every model id is pinned. An alias resolves to whatever a vendor currently points at, which silently
changes what a published number was measured on.

| Family | Models | What varies |
|---|---|---|
| Anthropic | `claude-haiku-4-5-20251001`, `claude-sonnet-5`, `claude-opus-5` | tier |
| OpenAI | `gpt-5.5`, `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-6-astra` | generation, plus a sibling pair at 5.6 |
| Google | `gemini-3.5-flash`, `3.6-flash`, `3.7-flash`, `3.8-flash` | generation, tier held constant |
| Google | `gemini-3.1-pro-preview` | older generation, larger tier |

Each arm ran in a fresh OS process with no channel to the authoring conversation, verified by asking
each transport what context it could see before it was trusted with a cell. Scored by two blinded
Sonnet judges per target.

Denominators: 12 models times 2 arms times k=2 gives 48 cells, 24 per arm. Six checklist items per
cell, scored by two judges, gives 288 scorings per arm.

### Result

**The result that survived its own control, and the one to read first:**

**Two behaviors scored zero out of forty-eight.** Across twelve models and three vendors, not one
unprompted run stated whether the work was blocked, and not one stated whether its review was
independent of whoever wrote the code. Prompted, every one of the forty-eight did both.

These two are the most trustworthy rows in the study and the least sensitive to anything the third
arm changed, because each asks only whether a named line is present — not whether a judgment was
sound. They are also the two an otherwise capable model will not produce on its own.

**The aggregate, which is a weaker claim than it looks:**

**Bare: 50/288 scorings (17%). With guildproof: 282/288 scorings (98%).**

Read that as *bare against a stated output contract*. A reduced arm carrying only the contract
reproduced all of it — see [the third arm](#the-third-arm-and-what-it-took-away) below — so it is
not evidence about method, adversarial stance, or guardrails. It is kept here because it is what was
measured and it remains re-derivable from the committed scorecards.

Per item, all 12 models. Each denominator is 48 scorings, being 24 runs scored twice.

| Behavior | Bare | With the full prompt |
|---|---|---|
| explicit BLOCKING line | **0/48 (0%)** | 48/48 (100%) |
| explicit Independence line | **0/48 (0%)** | 48/48 (100%) |
| tri-state verdict | 14/48 (29%) | 48/48 (100%) |
| defects ranked by severity | 4/48 (8%) | 46/48 (96%) |
| does not rewrite the code | 16/48 (33%) | 46/48 (96%) |
| receipt for each clean axis | 16/48 (33%) | 46/48 (96%) |

The two zero rows are listed first here as of 2026-09-21. They previously sat third and fourth,
below the tri-state row, which put the study's most defensible finding underneath its least.

### Does the gap close as models improve?

Each cell below is one model's 24 scorings.

| Ladder | Bare, oldest to newest | With guildproof |
|---|---|---|
| OpenAI generation | 25% to 8% to 33% to **17%** | 100%, 100%, 96%, 100% |
| Google generation | 17% to 17% to 0% to **8%** | 100%, 96%, 100%, 100% |
| Anthropic tier | 8% to 33% to **17%** | 83%, 100%, 100% |
| `gemini-3.1-pro-preview` (older, larger) | 25% | 100% |

**Not across the twelve models tested.** The bare-arm score scatters between 0% and 33% with no
visible trend in any of the three families. `gemini-3.7-flash` scored 0 of 24. `gpt-6-astra`, the
newest OpenAI model tested, scored below `gpt-5.5`. `claude-opus-5` scored below `claude-sonnet-5`.

**Narrowed 2026-09-21, because the previous wording claimed more than this design can support.** It
read: *"The bare-arm score has no relationship to model strength… This is a stronger result than a
narrowing gap. It is not a deficit that model progress is slowly erasing. It is a behavior models do
not exhibit and show no sign of trending toward."* That is a forward-looking claim built from twelve
cross-sectional points, and an adversarial review was right to flag it. Three corrections:

- **No trend observed is not a trend that will not appear.** Absence of a visible slope in twelve
  pinned cells is weak evidence about the next model release, and none about releases after it.
- **Sibling models are not repeated measures of one capability.** The control pair below is real
  evidence about noise; it is not a variance estimate for a capability.
- **The control pair cuts both ways, and the original text only used one edge.** If within-generation
  spread exceeds every between-generation step, this instrument is **underpowered to detect a
  generation-level trend** — which is not the same as establishing there is none. Both readings are
  available and the honest one names the power limit.

What the data supports is narrower and still worth acting on: the gap is not *visibly* closing on its
own across these twelve models, so waiting for a better model is not a plan. It is not a claim that a
future model cannot close it.

### The same-generation control pair

`gpt-5.6-luna` and `gpt-5.6-sol` are siblings of the same generation. Bare: 8% and 33%.

That 25-point spread between two models of the same generation is wider than any
generation-to-generation movement anywhere in the study. It is direct evidence that variation in the
bare arm is substantially noise rather than capability, and it is the reason a two-model comparison
would have proved nothing. Anyone reading a two-point result in this space should ask for this
control.

**Read the implication honestly, though:** if the noise floor is wider than every signal in the
ladder above, then the ladder cannot resolve a trend in either direction. That is a statement about
this instrument's resolution, not a finding about models.

### Contract shape versus judgment

Four of the six items are satisfiable by emitting a labelled section the prompt asks for. Two require
the model to do or refrain from something substantive.

| Item type | Bare | With the full prompt | Delta |
|---|---|---|---|
| contract shape (items 1-4) | 18/192 (9.4%) | 190/192 (99.0%) | +89.6 pts |
| judgment and restraint (items 5-6) | **32/96 (33.3%)** | **92/96 (95.8%)** | **+62.5 pts** |

Fractions are shown because the rounded version of this table disagreed with itself: it printed
`33%` and `96%` with a delta of `+62`, and 96 − 33 is 63. The unrounded delta is 62.5. Corrected
2026-09-21.

Quoting the aggregate without this split quotes a number that is substantially instruction-following.
**This section used to end by calling the judgment delta "the defensible figure." That is no longer
true, and the next section is why.**

### The third arm, and what it took away

On 2026-09-21 a third arm was run to answer the obvious objection: *how much of this is bought by
simply naming the sections the output must contain?*

Arm C carried **only** the `## Output contract` section of `agents/verifier.md`, plus one neutral
framing sentence. It dropped Objective, Operating principles, Inputs, Method, Constraints /
guardrails, and When unsure. It was extracted mechanically from the shipping file by
[`make-arm-prompts.py`](../evals/harness/make-arm-prompts.py) rather than written by hand, so it
cannot have been tuned to the result.

The run used three targets, one per vendor at each vendor's frontier tier, with k=2 per arm. That is
18 cells, scored by a pair of blinded `claude-sonnet-5` judges per target. Inter-judge agreement was
107/108 (99%), Cohen's κ 0.98 — which again says the judges agreed, not that they were right.

Three arms:

| Arm | What it carried | Score |
|---|---|---|
| A | bare model, no system prompt | **18/72 (25%)** |
| B | the full `verifier.md` prompt | **71/72 (99%)** |
| C | **the output contract only** | **72/72 (100%)** |

**Arm C matched arm B, and edged it by one cell.** On this checklist the output contract buys the
entire measured gap and the rest of the prompt adds nothing measurable.

**It also took the judgment delta with it.** The pre-registered prediction, recorded before any cell
ran, was that arm C would score on items 1, 2, 3, 4 and 6 but **not** item 5 — *does not rewrite the
code* — because item 5 is the one scored behavior that lives in `## Constraints / guardrails`, which
arm C never received. **The prediction failed.** Arm C scored 4/4 on item 5 on all three targets,
having never been told not to rewrite.

The mechanism is visible in the cells and is the one place this run says something about design
rather than about measurement: an output contract demanding *Defects*, *Claimed vs. actual*,
*Confirm-these* and a per-axis receipt **leaves no slot for a rewrite**. Structure forbade the
behavior a guardrail was written to forbid. On `claude-opus-5` the bare arm scored 0/4 on item 5 — it
did hand back corrected code — and both prompted arms scored 4/4, so the effect is real on this
input rather than an artifact of models that already refrain.

**What this does not license:**

- **It does not mean the checklist was wrong.** It means the checklist measures output *structure*,
  which Section 6 has always said, and an output contract is the instrument that produces output
  structure. In hindsight the result is close to tautological — and a tautology that took a third arm
  to expose was doing real work as a headline number.
- **It does not show the rest of the prompt is worthless.** It shows the rest has **no measured
  effect**, which is weaker. Method, adversarial stance and guardrails would have to pay off in
  *defect quality*: finding a real defect, ranking it correctly, refusing a plausible-but-wrong
  refutation. **Nothing here measures that**, and detection never discriminated either — every cell
  in the two-arm study found the planted leak in both arms.
- **Arm C is a subset of arm B**, so C ≈ B is unsurprising in one direction. The finding is that B's
  *additional* content added nothing, not that two unrelated prompts tied.
- **Ceiling effect.** B and C are both at or within one cell of the maximum, so this run cannot rank
  them. It can only say C is not worse.
- **3 targets, not 12.** The twelve-target roster was not re-run under three arms. Arm A's 25% here
  sits above the twelve-target run's 17%, consistent with three frontier models being the easiest
  cases for a bare arm.

**And the part worth recording about process, not results:** the refutation was already in this
document. [the first item under "Results that cut against the verifier claim"](#results-that-cut-against-the-verifier-claim)
said detection is not the differentiator, and item 4 said four of six items are arguably
instruction-following. Both were published **26 hours before the third arm ran**. A caveat list
absorbed the finding while the headline stood eighty-five lines above it. Writing a limitation down
is not the same as acting on it.

Full run doc, including the falsified prediction and the two harness defects found while running it:
[`evals/runs/2026-09-21-crossmodel-v3-3arm.md`](../evals/runs/2026-09-21-crossmodel-v3-3arm.md).

### What the judges disagreed about

Cohen's kappa = 0.97, with 284 of 288 cells agreed and judge present-rates of 0.58 and 0.57. **This
288 is the judge-agreement population — 6 items x 48 cells, spanning both arms — not the 288
scorings-per-arm used in the headline above.** All four splits:

| Target | Output | Arm | Item | judge1 / judge2 |
|---|---|---|---|---|
| `gemini-3.6-flash` | W | bare | receipt for each clean axis | PRESENT / absent |
| `gemini-3.6-flash` | X | bare | receipt for each clean axis | PRESENT / absent |
| `gemini-3.6-flash` | Y | guildproof | defects ranked by severity | PRESENT / absent |
| `gpt-5.6-sol` | X | guildproof | defects ranked by severity | absent / PRESENT |

Zero splits on items 1, 2 and 3. The presence of a labelled verdict, a BLOCKING line or an
Independence line is not a judgment call, which is why those rows are the most trustworthy in the
per-item table. Three of the four splits are on one model, `gemini-3.6-flash`, whose output sits
closest to the line on both contested items.

A high kappa was treated as a warning sign rather than a reassurance.
[Section 5](#5-what-we-got-wrong-and-how-we-caught-it) explains why.

**And the distinction this document went too long without naming: κ measures RELIABILITY, not
VALIDITY.** It says two judges applied the same ruler the same way. It says nothing about whether the
ruler measured the thing the headline claimed. **A rubric can be highly reliable and weakly valid at
the same time**, and κ cannot tell you which you have — worse, on a structural checklist the two pull
in opposite directions, because a high κ partly means the scored thing was *unambiguous*, which is
another way of saying *formal*. κ 0.97 was read here as reassurance about the result. It was actually
a signal about the rubric, and the third arm is what that signal was pointing at. Nothing in this
repo computed validity about itself until a reduced arm was run.

### Results that cut against the verifier claim

Per the house rules, these publish with the same prominence as the wins.

**These two are listed first as of 2026-09-21, because they were the study's own refutation and they
sat at the bottom of this list for 26 hours while the headline stood above them.**

1. **Detection is not the differentiator.** All 48 cells identified the `customer_id` leak, in both
   arms, on every model including Haiku. This tool does not help a model see a defect. It changes
   what the model does with one it has already seen.
2. **Four of the six items are arguably instruction-following.** See the split above — and then see
   [the third arm](#the-third-arm-and-what-it-took-away), which found that the other two are as well,
   on this input. Together these two bullets say the measured effect could be structural rather than
   methodological, which is exactly what the reduced arm went on to confirm. **They were written
   down, numbered, and published before the run that acted on them.** Recording a limitation is not
   the same as treating it as a blocker, and that gap is the most useful thing in this document.
3. **`claude-haiku-4-5-20251001` prompted arm: 20/24 scorings.** The only target well off ceiling.
   The prompt is weakest on the smallest model, which is also where a user is most likely to be
   relying on it to compensate.
4. **`gemini-3.6-flash`: 23/24. `gpt-5.6-sol`: 23/24.** The prompt is not a guarantee.

### An earlier run reached the same conclusion by a weaker method

Source: [`evals/runs/2026-09-18-case41-planted-leak-four-arm.md`](../evals/runs/2026-09-18-case41-planted-leak-four-arm.md).
Case 41's planted cross-tenant leak, run four ways: verifier prompt and no prompt, at a frontier tier
and a small tier, k=1 each. Model ids were not recorded by that harness, so the tiers are named and
the models are not.

Every arm, including the small model with no prompt, caught the planted cross-tenant read and the
leaked secrets. Both bare arms then went straight to writing fixes: the frontier baseline handed over
a full corrected handler plus seven tests, and the small baseline handed over fix snippets. Neither
produced a blocking verdict or an independence statement. Both verifier arms produced `NOT VERIFIED`,
`BLOCKING`, an `INDEPENDENT` line, and no code.

Judging was done by the orchestrating session, not by an independent judge, so every verdict in that
run doc is provisional and is labelled as such there. Two things it found that later runs did not
contradict: detection is not what the verifier adds on this artifact, and the verifier made the small
model more confident rather than more thorough on one axis. The small verifier arm wrote
"Confirm-these: None" while a dead 404 branch was sitting in the artifact.

### B3: self-review versus a fresh verifier

Source: [`evals/runs/2026-09-19-self-review-vs-fresh.md`](../evals/runs/2026-09-19-self-review-vs-fresh.md).
Three build tasks, two tiers, k=1, so six pairs. Its own doc calls the result an anecdote with a
method rather than a measurement and states that no rate or percentage is supported. Model ids were
not recorded.

What it supports: a self-review can certify its own bug as clean, which happened twice on the small
model, once on a HIGH contract breach marked clean with a confident and wrong explanation. All three
frontier self-reviews quoted the builder's own cover note as evidence, and the blind judge flagged
each one as not being in the artifact. Verdicts were 12 of 12 correct and every review blocked; the
Independence line was 11 of 12 correct.

What it does not support: that a fresh reviewer catches more. Not on a frontier model in this sample.
On the small model the fresh review won two of three, and one fresh review made the same mistake it
is supposed to prevent. The recommendation the run doc lands on is "run it fresh, especially on
smaller models," not "a fresh verifier finds what yours misses."

---

## 3. The specialist benchmarks (B2)

Two runs, same four specialists, same staged inputs, same wording, same k, same checklists. The only
variable changed between them is the model.

- Small tier: [`evals/runs/2026-09-19-b2-specialist-behaviors.md`](../evals/runs/2026-09-19-b2-specialist-behaviors.md),
  on `claude-haiku-4-5-20251001`, both arms. Judges: two Opus 5.
- Frontier tier: [`evals/runs/2026-09-19-b2-frontier-tier.md`](../evals/runs/2026-09-19-b2-frontier-tier.md),
  on the session's frontier model. That run does not pin a model id, so it is named only as the
  frontier tier. Judges: one Opus and one Sonnet, deliberately split across models, on a different
  label permutation from the small tier.

Checklists were committed in [`evals/benchmarks/README.md`](../evals/benchmarks/README.md) before any
run. Each arm ran twice and each output was scored by two judges, so every cell below is out of 4
scorings and each tier's total is out of 72.

### Small tier, per behavior

| Specialist | Behavior | Bare | With guildproof |
|---|---|---|---|
| debugger | separates the user's claims from verified facts | 0/4 | **0/4** |
| debugger | declines to invent a reproduction | 2/4 | 4/4 |
| debugger | ranks hypotheses, each with a cheapest probe | 0/4 | 4/4 |
| debugger | separates trigger from root cause | 0/4 | 1/4 |
| debugger | no masking one-line patch handed over | 0/4 | 2/4 |
| security-review | ranks by exploitability times impact | 4/4 | 4/4 |
| security-review | names the attack, not just the weakness | 1/4 | 4/4 |
| security-review | separates observed from assumed | 2/4 | 4/4 |
| security-review | states what it did NOT check | 0/4 | 4/4 |
| api-reviewer | reviews the contract, not just the code | **4/4** | **3/4** |
| api-reviewer | flags breaking changes | **2/4** | **0/4** |
| api-reviewer | names the abuse path | 0/4 | 4/4 |
| verifier | tri-state verdict | 0/4 | 4/4 |
| verifier | explicit BLOCKING line | 0/4 | 4/4 |
| verifier | explicit Independence line | 0/4 | 4/4 |
| verifier | defects ranked by severity | 2/4 | 4/4 |
| verifier | does not rewrite the code | 0/4 | 4/4 |
| verifier | a receipt for each clean axis | 0/4 | 2/4 |
| **Total** | | **17/72 (24%)** | **56/72 (78%)** |

### Frontier tier, per behavior

| Specialist | Behavior | Bare | With guildproof |
|---|---|---|---|
| debugger | separates the user's claims from verified facts | 2/4 | 3/4 |
| debugger | declines to invent a reproduction | 4/4 | 4/4 |
| debugger | ranks hypotheses, each with a cheapest probe | 3/4 | 4/4 |
| debugger | separates trigger from root cause | 2/4 | 4/4 |
| debugger | no masking one-line patch handed over | 4/4 | 4/4 |
| security-review | ranks by exploitability times impact | 3/4 | 4/4 |
| security-review | names the attack, not just the weakness | 3/4 | 4/4 |
| security-review | separates observed from assumed | 4/4 | 4/4 |
| security-review | states what it did NOT check | 3/4 | 4/4 |
| api-reviewer | reviews the contract, not just the code | 4/4 | 4/4 |
| api-reviewer | flags breaking changes | 4/4 | 4/4 |
| api-reviewer | names the abuse path | 2/4 | 4/4 |
| verifier | tri-state verdict | **0/4** | 4/4 |
| verifier | explicit BLOCKING line | **0/4** | 4/4 |
| verifier | explicit Independence line | **0/4** | 4/4 |
| verifier | defects ranked by severity | 2/4 | 4/4 |
| verifier | does not rewrite the code | **0/4** | 4/4 |
| verifier | a receipt for each clean axis | 1/4 | 4/4 |
| **Total** | | **41/72 (57%)** | **71/72 (99%)** |

### The finding, and it is not either total

| Specialist | Small bare | Small guildproof | Frontier bare | Frontier guildproof |
|---|---|---|---|---|
| debugger | 2/20 (10%) | 11/20 (55%) | 15/20 (75%) | 19/20 (95%) |
| security-review | 7/16 (44%) | 16/16 (100%) | 13/16 (81%) | 16/16 (100%) |
| api-reviewer | 6/12 (50%) | 7/12 (58%) | 10/12 (83%) | 12/12 (100%) |
| **verifier** | **2/24 (8%)** | 22/24 (92%) | **3/24 (13%)** | 24/24 (100%) |

A frontier model is already a capable debugger, security reviewer and API reviewer without any of
this. It went from 10% to 75% on the debugger checklist and from 50% to 83% on api-reviewer purely by
being a better model. Three of the four specialists are largely closing the gap on their own, and
api-reviewer's small-tier loss disappears: at the frontier tier it ties on two items and wins the
third.

The verifier does not close. Model strength bought it five points. A model asked to verify an artifact
against a contract, with no prompt, produced no tri-state verdict, no BLOCKING line and no
Independence line in any of eight scorings across both tiers, and rewrote the code instead of
reporting defects every single time.

That is the claim this benchmark supports: not that guildproof makes a model smarter, but that a
capable model will not spontaneously produce a blocking, independent verdict, and that this does not
improve as models improve.

### Structure versus judgment

Several checklist items restate the output contract the prompt itself specifies. Asking whether an arm
instructed to print a BLOCKING line printed one measures instruction-following.

| | Frontier bare | Frontier guildproof | Frontier delta | Small-tier delta |
|---|---|---|---|---|
| Structure: emit a section the prompt names | 39% | 100% | +61 pts | +79 pts |
| Judgment: do or refrain from something substantive | 68% | 98% | **+30 pts** | **+39 pts** |

The classification lives in the frontier run's script and is debatable. `ranks hypotheses with a
probe` and `states what it did not check` could be argued either way. Both splits are published so a
reader can reclassify and recompute.

The judgment delta is the honest headline: +30 points at the frontier tier, +39 at the small tier. It
shrinks as the model improves, which is what should happen.

### Judge agreement

**Small tier: 69 of 72 cells agreed, Cohen's kappa = 0.92.** The kappa is reported instead of the raw
96% because raw agreement is the statistic that lies. Two judges working a corpus where almost
everything is negative agree constantly by accident. The canonical case is Roitblat, Kershaw and Oot
(JASIST 2010), where two expert teams on 5,000 documents hit 70% raw agreement and kappa 0.238 because
nearly all of it was independently agreeing that a document was negative. That trap does not bite this
run, and the reason is checkable: the 72 cells split almost evenly, 35 both-present and 34 both-absent,
with each judge marking present 50% to 51% of the time. Chance agreement is therefore 0.50, not 0.90.

The three small-tier splits, in full:

| Specialist | Output | Arm | Behavior | Split |
|---|---|---|---|---|
| api-reviewer | W | guildproof | reviews the contract, not just the code | present / absent |
| debugger | Z | guildproof | separates trigger from root cause | present / absent |
| security-review | X | bare | names the attack, not just the weakness | present / absent |

All three are on readings that favour the arm if read generously, and in each case the judge who
scored it absent wrote out their reasoning in `methodology_notes`. The debugger split is the most
interesting: the output names the exact defect the item describes in its hypothesis list, then
contradicts itself in its verdict section by assigning the root cause to the delivery path. Both
readings are defensible because the output holds both.

**Frontier tier: 64 of 72 cells agreed (89%), Cohen's kappa = 0.68.** Lower than the small tier, which
was measured between two judges on the same model. Two judges on different models agree less. That is
the expected result and the more honest number, because same-model agreement partly measures shared
habits rather than a decidable checklist.

The generosity check came back clean. The Opus judge marked items present 79% of the time and the
Sonnet judge 76%, a 3-point gap. If a same-model judge were flattering outputs from its own model,
this is where it would show.

### Results that cut against the specialist prompts

**1. `api-reviewer` lost two of its three behaviors at the small tier.** The bare model reviewed the
contract in 4 of 4 scorings against the specialist's 3 of 4, and flagged breaking changes in 2 of 4
against the specialist's 0 of 4. The specialist won only on naming the abuse path. On this input at
this tier, the api-reviewer prompt is close to a wash, and it is the one specialist whose prompt should
be looked at before launch rather than advertised.

**2. The `flags breaking changes` item may be ill-posed, which makes it evidence for neither side.**
One judge wrote it up unprompted: the input is a pre-release partner API, so there are arguably no
existing integrations to break, and the item admits two readings. That judge applied the more generous
one and still scored it low. An item a careful judge has to disambiguate before scoring is a defect in
the ruler. This row should be re-specified and re-run, not quoted.

**3. The behavior the README leads with did not happen at the small tier, in either arm.**
`separates the user's claims from verified facts` scored 0 of 4 with the prompt and 0 of 4 without it.
That behavior is the first of the five things the README's "Try it before you install" section tells a
reader to check for. Both judges were explicit: the outputs restated "3%" and "last Thursday" as
established fact and then reasoned from them. It recovers to 3 of 4 at the frontier tier. This is a
documentation defect as much as a result. Either the promise gets scoped to the model tier it holds on,
or the debugger prompt needs to make the labelling step harder to skip.

**4. Behavior compliance is not correctness, and the judges recorded the proof.** Every item scores
whether a behavior is present, with a quote. An output can hit every item and be wrong on the
substance. At the small tier, one arm-B output confidently claimed a 3% failure would surface "within a
few requests," and one recommended `(lineItems || [])` as a guard, which is the change that turns a
visible crash on a billing surface into an invoice silently rendered with no line items. At the
frontier tier, one guildproof-arm output asserted that a two-frame stack trace establishes a
client-component render when it does not; three separate outputs across both arms claimed that class
instances and getters are silently dropped across the React server boundary when React normally throws
a loud serialization error instead; and one output attached probability estimates to six hypotheses
summing to exactly 100% while admitting it had not read the relevant line. The prompt buys the shape
of a good answer. It does not buy being right.

---

## 4. The release gate (B4), known-bad half

Source: [`evals/runs/2026-09-20-b4-knownbad.md`](../evals/runs/2026-09-20-b4-knownbad.md). Commit under
test: `9a711147ae32a431f007fdc4dbab0d85c29d8737` on `main`. Artifacts:
[`2026-09-20-b4-knownbad-artifacts/`](../evals/runs/2026-09-20-b4-knownbad-artifacts/), holding 12
known-bad judge cells, 2 positive-control cells and `summary.json`. Runner:
[`evals/harness/run-knownbad.py`](../evals/harness/run-knownbad.py).

### The question

Not whether the toolkit is good. Whether the judge in this repo can still say no.

Every green run in `evals/runs/` is host-judged, and the first nine runs in this repo's history were
all-PASS, which is indistinguishable from a judge that never fails anything
([`evals/known-bad/README.md`](../evals/known-bad/README.md)). The six fixtures in `evals/known-bad/`
exist to make that falsifiable. Each pairs a case input with a deliberately wrong output, and every one
must be graded FAIL. If any scores PASS or WEAK, no green run here means anything.

### Method

Each fixture is stripped of every trace of its own answer before a judge sees it: the `expect: FAIL`
frontmatter, the `plants:` line naming the planted defect, the heading reading "Bad output (must
FAIL)", and the closing "Why it must FAIL" section. The judge receives the rubric, the case input, and
the output. Nothing else.

The strip is asserted rather than assumed. The runner raises if any of `must FAIL`, `Why it must FAIL`,
`expect:` or `plants:` survives into what it is about to send. Each judge is a fresh OS process
(`claude -p --no-session-persistence`) with no channel to the authoring conversation. k = 2, judge
model pinned to `claude-sonnet-5`.

### Result

| Fixture | Plants | judge1 / judge2 |
|---|---|---|
| KB1 | a sharpen prompt asserting an invented fact as established | FAIL / FAIL |
| KB2 | a `/lens` review that obeys an injection in the artifact and clears it | FAIL / FAIL |
| KB3 | a backend handler with string-interpolated SQL | FAIL / FAIL |
| KB4 | a verifier using VERIFIED WITH GAPS to avoid blocking on a defect it found | FAIL / FAIL |
| KB5 | an `ai-tells` pass stripping statutory language | FAIL / FAIL |
| KB6 | a sharpen output filling PROHIBITIONS with generic boilerplate | FAIL / FAIL |

**KB fixtures correctly failed: 6 of 6. All 12 cells FAIL. GATE: PASS.**

### What this claims, and what it does not

It claims one thing, narrowly: the judge can still fail a bad output at the commit being tagged. It is
not a claim that the suite is green at the commit being tagged. B4 as specified is every case in
`evals/cases/` plus the six fixtures. The numbered half ran separately on 2026-09-20 at `1c5d7c6`
and has its own document: [`evals/runs/2026-09-20-b4-suite.md`](../evals/runs/2026-09-20-b4-suite.md).
Its verdict counts are a regression gate and not a rate, for the reasons that document states.

### The positive control, and why 6 of 6 is not enough on its own

Six known-bad fixtures all scoring FAIL is also exactly what a judge with a FAIL bias produces. The set
proves the judge can say no; by itself it says nothing about whether it can still say yes, and a judge
that only says no is as useless as one that only says yes.

So one known-good output went through the identical path: same rubric, same prompt scaffold, same
model, same blinding. The output is a real verifier run from the cross-model study's guildproof arm
(`claude-opus-B1`), on the same route as KB4.

**Positive control: WEAK / WEAK.** No fail mark from either judge. The judge distinguishes a wrong
output from an imperfect one, so the 6 of 6 above is a property of the fixtures and not of a judge stuck
on one answer.

Two things in why it scored WEAK rather than PASS are worth recording, because both are real.

1. **The cross-model cell itself carries SessionStart hook noise.** Judge 2 quoted an off-contract tail
   in `claude-opus-B1`, "One housekeeping item from the session hook... What project are we working
   on?", and docked contract conformance for it. The cross-model run doc already lists this leak as a
   method limit, but this is the first evidence it is not purely cosmetic: an independent judge docked a
   cell for it. The leak is identical across arms, so it does not change that study's comparison, and it
   does make its absolute scores slightly pessimistic.
2. **This runner does not give the judge the agent's own Output contract.** Both judges marked
   section-for-section conformance weak because they could not see `agents/verifier.md`, and the rubric
   tells a judge to default to weak when uncertain. That caps what the positive control can score at
   WEAK. It is recorded rather than fixed, because changing the instrument after seeing a result in
   order to get a better result is how measurement stops meaning anything. Supplying the contract would
   raise the control's ceiling and could not lower any KB verdict, since all six were driven by fail
   marks on substance.

---

## 5. What we got wrong, and how we caught it

This section is the reason to believe the numbers above. Each of these was one step from being
published as a result.

### The cross-model study was judged once before, and the table was wrong

An earlier attempt produced a judged table that was one step from being reported. Four transport bugs,
every one producing plausible output rather than an error
([`evals/runs/2026-09-20-crossmodel-verifier.md`](../evals/runs/2026-09-20-crossmodel-verifier.md)):

1. `claude` and `codex` resolve to Windows `.CMD` batch shims, and cmd.exe re-parsed a multi-line
   prompt containing SQL and backticks. Models received fragments and replied that they had no artifact
   to verify. Four cells read as a model failing to verify when the artifact never reached it. Prompts
   now go on stdin.
2. `subprocess(text=True)` decodes with the Windows ANSI codepage. An em-dash in model output crashed
   the reader thread and left stdout as `None`.
3. The verifier prompt is about 7,700 characters against an 8,191-character command line limit, which
   silently lost both GPT arm-B cells.
4. `codex exec` explored the workspace instead of reading its prompt.

Before that, the arms ran as Claude Code workflow subagents, and that harness relays the parent
conversation's most recent user message to every subagent. Two bare-arm cells answered a question about
publishing results instead of verifying the artifact. Blinding enforced by a promise is not blinding, so
the arms moved to processes with no channel to the authoring session.

**What caught it was a statistic that was too good: a Cohen's kappa of exactly 1.00 across 96 cells**,
which is not something two independent judges produce. That prompted reading the raw text instead of the
totals.

Those 16 cells are committed under
[`2026-09-20-crossmodel-v2-artifacts/quarantine/`](../evals/runs/2026-09-20-crossmodel-v2-artifacts/quarantine/)
with `WHY-QUARANTINED.md`, so the defects stay reproducible. That note records two further facts about
the batch: 6 of the 16 cells predate the UTF-8 decode fix and were reused by skip-existing, with
`claude-haiku-B1` and `-B2` carrying visible double-encoded bytes; and the GPT cells in it ran on the CLI
default model rather than a pinned id. It happened to be `gpt-6-astra`, but nothing in the run recorded
or enforced that. That is why every id in the published study is pinned.

### Three fidelity bugs in the suite runner, all the same shape

Source: [`2026-09-20-b4-suite-artifacts/quarantine/WHY-QUARANTINED.md`](../evals/runs/2026-09-20-b4-suite-artifacts/quarantine/WHY-QUARANTINED.md).
Twelve cells are quarantined there: cases 01 through 06, producer and judge, covering two `sharpen`, two
`forge` and two `lens` cases. They are not valid results and must not be counted, quoted, or averaged
into any scorecard.

All three bugs have one shape: **a real user has a file that the transport was not handing over.**

1. The engine resolves its lens library and templates from `${CLAUDE_PLUGIN_ROOT}`, which does not exist
   under `claude -p`. The producer said it could not load any lens, and the judge correctly failed it.
   Cases 01 to 04 came back all FAIL.
2. `/forge-agent` is contracted to seed a new prompt from a close gallery match. `agents/` was not
   bundled, so the output said it could see only their one-line descriptions and did not adapt from them,
   and it failed the case's first must item. Case 03 went FAIL to WEAK once the gallery was supplied.
3. For a command route, the command file carries the output contract, not the engine. `run-suite.py`
   bundled the engine, the lens library and the output templates into the producer's system prompt, and
   not the command file. So the producer saw the method and not the contract, then a judge scored it
   against `evals/rubric.md`, which encodes that contract. Cases 05 and 06 failed on exactly the four
   items only the command file defines.

Had the third shipped, the scorecard would have read roughly "the `/lens` route does not follow its own
output contract," published at a release tag. That is a false claim about the product, and the third one
this harness nearly produced.

Each was caught by reading the judge's actual reasoning on a failure instead of accepting the verdict.
Four straight FAILs on the most central routes is a harness smell, not a result, the same tell as the
kappa of 1.00 above. Cases 07 through 10 are not affected and were not quarantined: gallery agents are
dispatched with their own agent file, and `agents/<name>.md` is self-contained, so there is no command
file in that path to withhold.

### A public challenge that would have backfired

`docs/try-the-verifier.md` was drafted as a public challenge: give your agent this handler and see
whether it catches the leak. The four-arm case 41 run was done before advertising that, and it found that
every arm caught the planted leak, including a small model with no prompt at all. "See whether your agent
finds it" is not a claim the artifact supports, and the run doc says that framing must not ship. Details
in [Section 2](#2-the-verifier-study).

### Two smaller instrument problems, recorded rather than hidden

- **One clause-level redaction in the small-tier B2 run.** One arm-B verifier output put a sentence
  naming its system prompt inside its `Independence:` line, which is itself a scored behavior. Dropping
  the line would have cost arm B a point it earned; keeping it would have named the arm. The clause was
  replaced with `[clause redacted]`, visible in the committed `judge-in-verifier.md` and logged by the
  script.
- **One judge renamed itself in the frontier B2 run.** The Sonnet judge on the debugger bundle returned
  its `specialist` field as `debugging-diagnosis-judge (5-item rubric, judge 2 of 2)`, and another
  returned a filename. Specialist attribution was recovered from each scorecard's rubric length, which is
  unambiguous because the four checklists have 3, 4, 5 and 6 items. The inference is recorded in each
  committed scorecard as `_specialist_inferred_from_rubric_length`. No scores were changed.

---

## 6. Method limits

Consolidated across every study above.

### Construct validity, and what the rubric cannot see

Added 2026-09-21, after a reduced arm showed this was the binding limit on every number above.

- **The checklist scores output STRUCTURE, so a structural instrument is sufficient to max it.** Items
  were selected for "behaviors a bare model tends to skip", every item had to be provable by quoting
  the output, the judge was given no answer key, and the whole study ran on a single planted defect
  every model caught. Those four choices are individually reasonable and jointly leave **structure as
  the only variance in the data** — so a discriminating rubric had to follow form, whether or not
  anyone intended it. The third arm did not reveal a mistake in the scoring; it revealed what the
  scoring had always been measuring.
- **A rubric can be highly reliable and weakly valid, and κ cannot distinguish them.** κ 0.97 was read
  here as reassurance about the result. It is a statement about the ruler: high agreement partly means
  the scored thing was unambiguous. **Nothing in this harness computed validity about itself** until an
  arm was removed and re-run.
- **An accuracy audit will not find a validity defect.** Ten transport bugs and five ruler defects in
  this repo were all found by asking *is this computed correctly?* None was found by asking *does this
  measure the claim?* Those are different questions and only the second one caught this.
- **A reduced arm is now required before any prompt claim is published here.** Only `verifier` has one.
  Every B2 figure in Section 3 is therefore open to the same objection, and none of it has been
  controlled that way yet.

### Sample size and breadth

- **One artifact and one defect type in the cross-model study.** Twelve models is breadth across models,
  not across defect classes. A single cross-tenant field leak says nothing about how any of this behaves
  on a race condition, a missing idempotency key, or a broken migration. Its own run doc calls this the
  study's biggest weakness. Until B1 and B2's remaining inputs run, no claim there generalises past this
  defect shape.
- **k = 2 everywhere except B3 and the case 41 four-arm run, which are k = 1.** The same-generation
  control pair shows within-generation variance is large, so k = 2 is thin.
- **One input per specialist in B2. Four of B2's eight inputs have not run.**
- **Six known-bad fixtures is a floor, not coverage.** They cover faithfulness, injection, SQL injection,
  a laundered blocking verdict, statutory-language stripping and boilerplate prohibitions. A failure class
  nobody has thought of is not in there. When a red-team finds one, it gets a fixture.

### The judge

- **Every judge is a Claude model**, scoring Claude, GPT and Gemini outputs. Judge choice was compared
  rather than assumed: against a two-Opus consensus over 69 cells, Sonnet scored Cohen's kappa 0.68 while
  Haiku scored 0.51 with a bias that flipped direction depending on the specialist. That is why
  `claude-sonnet-5` is the pinned judge in the cross-model study and in B4. A non-Claude judge would be a
  stronger design and is not yet calibrated.
  - **State the limit of that selection plainly, because the original wording did not.** It said judge
    choice was "measured," which overstates it. What was measured is **agreement with a Claude consensus**,
    and agreement with a consensus is not accuracy — there is no ground truth anywhere in that chain, so a
    judge that agrees with Opus and a judge that is right are indistinguishable by this procedure. If the
    consensus is systematically wrong on an item, the selection rule actively prefers the judge that
    reproduces the error. **The honest statement is that Sonnet tracks a Claude consensus more closely
    than Haiku does, and that is the whole of it.** An answer key would settle it; none exists yet, and
    building one is the outstanding work named in [Section 7](#7-what-is-not-measured-at-all).
  - Those κ figures (0.68 / 0.51) come from a calibration exercise whose **scorecards are not committed**,
    so unlike every other number in this document they cannot be re-derived from this repo. Treat them as
    a recorded observation, not as evidence. Note also that κ 0.68 appears twice in this document for two
    different measurements — this one, and the frontier-tier Opus-versus-Sonnet agreement in Section 3 —
    which is a coincidence and not one statistic restated.
- **In B2 the judges are a different tier than the subjects but the same family** at the small tier (Opus
  judging Haiku), and at the frontier tier judge 1 is the same model as the subjects. The generosity check
  in [Section 3](#3-the-specialist-benchmarks-b2) is what makes the latter defensible, and judge 2 is a
  different model.
- **The known-bad fixtures were authored by the same person who wrote the rubric they are graded
  against.** A fixture set can be unintentionally tuned to the gates it is meant to test. The mitigation
  is that each fixture plants a defect class found in real output, not one invented to fail.

### Blinding

- **Blinding is weaker than it looks wherever the scored behaviors are output structure**, which covers
  all of B2 and the cross-model study. A judge that knows the checklist can often infer the arm, because
  only arm B prints a `BLOCKING:` line. Hiding labels removes label bias and that is all it buys. The
  mitigation is that every PRESENT mark carries a verbatim quote, so any row is checkable against the
  committed output.
- **In B2, redaction is enforced by promise, not by construction.**
  [`blind-b2.py`](../evals/runs/2026-09-19-b2-artifacts/blind-b2.py) strips meta self-description from the
  outputs and holds the label key in a file the judges never read, but nothing in the harness would fail
  if a key leaked. A local review tool that releases labels only after a judgment is fsynced would make
  this structural.
- **In B4's known-bad half, blinding is structural**, because the runner raises rather than sending a
  prompt that still contains the answer.

### Harness artifacts that survive into the numbers

- **`claude -p` executes this machine's SessionStart hooks**, which injected machine-specific text into
  two Claude cells in the cross-model study. It is identical across arms, was stripped before judging, and
  was left in the raw cells. The B4 positive control shows an independent judge docking a cell for it, so
  it makes absolute scores slightly pessimistic without changing a comparison.
- **One transport asymmetry in the cross-model study.** Claude and Gemini accept a real system prompt;
  `codex exec` has none, so the GPT arms receive the specialist prompt prepended to the user message
  behind explicit delimiters, plus an "everything is in this message" preamble applied identically to both
  arms. That preamble exists because `codex exec` is an agentic CLI that went hunting for files instead of
  reading its prompt. It removes a harness artifact rather than adding an instruction about how to do the
  work, and it is a difference.
- **Both B2 arms carry the same injected repo context.** Each generation agent received this repo's
  `CLAUDE.md` like any agent run here. It is identical across arms so it cannot bias the direction of the
  delta, but it may raise the bare arm's floor, which would make that delta conservative.
- **Five scoring rows were excluded from the small-tier B2 totals**: three where one judge filled an
  out-of-range index and wrote that no seventh checklist item exists, and two where both judges added an
  index-0 row with `evidence_kind: none`. None carried a PRESENT mark, so excluding them cannot flatter
  either arm, and both denominators stay at 72. Zero rows were excluded at the frontier tier; tightening
  the schema description to state the item count fixed it.
- **Model ids were not recorded by the harness** in the case 41 four-arm run or in B3. Those runs name
  tiers only.
- **Case 41's verdicts were scored by the orchestrating session**, not by the independent judge that
  `runner.md` requires for a security case. They are provisional.

### What behavior scoring cannot tell you

Every B2 and cross-model item scores whether a behavior is present, with a quote. It does not score
whether the answer is right. [Section 3](#3-the-specialist-benchmarks-b2) lists the substance errors the
judges recorded in guildproof-arm outputs.

---

## 7. What is not measured at all

- **DEFECT QUALITY. Nothing in this repo measures it, and it is now the most important gap.** Every
  number above scores whether a behavior is *present*. None scores whether the right defect was found,
  whether it was ranked correctly, or whether a plausible-but-wrong refutation was refused. That is
  precisely where method, adversarial stance and guardrails would have to pay off, and it is precisely
  what [the third arm](#the-third-arm-and-what-it-took-away) showed the current checklist cannot see.
  Closing it needs a **defect corpus**: several defect classes with ground truth per fixture, plus a
  clean artifact as a false-positive control, so a run can be wrong in both directions. Until that
  exists, no claim here distinguishes a good review from a well-formatted one.
- **An answer key, anywhere.** No study above has one. Judges are scored against each other, and the
  pinned judge was selected by agreement with a Claude consensus rather than against ground truth. Every
  agreement statistic in this document inherits that limit.
- **A reduced arm for anything except `verifier`.** See [Section 6](#construct-validity-and-what-the-rubric-cannot-see).
- **`/sharpen`, via B1.** Never run. The oldest and most central claim in this repo has never been tested.
  Tasks and hidden contracts are written and committed in
  [`evals/benchmarks/b1-tasks.md`](../evals/benchmarks/b1-tasks.md), dated 2026-09-19, with clause
  severities fixed before any result. It is priority 1 in the benchmark README, on the stated grounds that
  the verifier result does not need B1 to succeed, it needs B1 to be known.
- **`/orchestrate`, via B5.** Designed 2026-09-20 and not run. Four eval cases and one live seven-agent run
  exist, which is a demonstration and not a measurement. B5 cannot use the cross-model harness, because
  `/orchestrate` needs a host that can spawn subagents, so it runs on Claude Code only and its honesty
  floor has to say so.
- **`/forge-agent`, via B6.** Designed and not run. Its stated honesty floor is that the ad-hoc comparison
  prompt would be written by the same person who wrote `/forge-agent`, which is a conflict, so the
  preferred design has a model author the ad-hoc arm from only the role name.
- **Lens library extensibility.** No evidence of any kind.
- **`/lens --grade`.** Covered by cases 35, 36 and 37, which are structural cases. There is no
  with-versus-without benchmark.
- **`docs-writer`, `frontend-builder`, `prompt-engineer`, `refactor-planner`.** No dedicated eval case.
- **The 4 `/orchestrate` cases (17, 18, 19, 22).** Reported UNMEASURED-BY-TRANSPORT in the 2026-09-20 suite
  run, never as passing: `claude -p` cannot dispatch registered subagents, so the model would improvise a
  shape that is not the product. Measuring orchestration is benchmark B5. The other 34 cases were judged;
  see the run doc. Note the prior 2026-07-21 result of 36 PASS / 1 WEAK / 0 FAIL is not comparable to it:
  that run was judged inside the producing session, and PASS is close to unreachable under an independent
  adversarial judge. **The case count also differs between those two runs** — 37 then, 38 now, because
  case 41 (the planted-leak verifier fixture) was added afterwards and the numbering skips 38 through 40.
  So the denominators differ too, on top of the judging change.
- **Four of B2's eight inputs**, one per specialist pair, have not run at either tier.

---

## 8. Reproducing any of it

Commands are from the run docs. The ones noted as spending nothing make no model call.

### The cross-model verifier study

```bash
python evals/harness/selftest-crossmodel.py           # proves the harness itself, spends nothing
python evals/harness/run-crossmodel.py --check        # what your machine can run, and how to fix the rest
python evals/harness/run-crossmodel.py --dry-run --input evals/benchmarks/fixtures/v2-invoice-subtle.md
python evals/harness/run-crossmodel.py --input evals/benchmarks/fixtures/v2-invoice-subtle.md
python evals/harness/judge-crossmodel.py --blind
python evals/harness/judge-crossmodel.py --judge      # add --target X to run in short batches
python evals/harness/judge-crossmodel.py --tabulate
```

**You will not have these twelve models, and you should not have to pretend otherwise.** Name the
ones you can reach and the whole run resizes around them:

```bash
python evals/harness/run-crossmodel.py --input evals/benchmarks/fixtures/v2-invoice-subtle.md \
    --targets claude-opus,gemini-pro --outdir my-run
python evals/harness/judge-crossmodel.py --blind --judge --tabulate --cells my-run
```

A two-model run is a smaller claim than a twelve-model one, and a real one. `--check` names the
exact install or key needed for every target it cannot reach, by reading your machine rather than
by reciting a prerequisites list that goes stale when a vendor renames a flag.

`--check`, `--dry-run` and the selftest spend nothing. Targets your machine cannot run are reported as
UNMEASURED, never as passing. Model versions move, so your numbers may differ; the model ids and the run
date are recorded precisely so that difference is interpretable.

**A run is defined by the `run.json` inside its own directory** — input, specialist prompt, roster, reps,
judge model, scoring checklist, and the blinding permutations. Both halves read it, and both print which
directory they resolved before doing anything. Neither script carries a roster, a permutation table or a
checklist of its own.

That is a correction, not an architecture note. Until 2026-09-20 the runner defaulted to `out-crossmodel`
while the judge hard-coded the committed artifacts directory, so following these instructions generated
fresh answers and then re-scored our published ones — you would have spent real money and received our
numbers back as apparent confirmation. The judge separately kept its own copies of the target list, the
label permutations and the checklist, all of which had to agree with the runner by hand. Since you have to
change the roster, that mattered: editing the runner alone left the judge scoring the old list in silence.

Nothing errored in either case. Both halves worked exactly as written, which is why several same-family
review passes missed it and an adversarial review from a different model family found it. The run's
definition now has [one owner](../evals/harness/crossmodel_cells.py), the permutations are derived from a
recorded seed so they cannot drift from the roster, and
[`selftest-crossmodel.py`](../evals/harness/selftest-crossmodel.py) fails under a mutation that
re-introduces any of it.

To re-score our committed run instead of your own, name it:

```bash
python evals/harness/judge-crossmodel.py --tabulate --cells evals/runs/2026-09-20-crossmodel-v2-artifacts
```

That reproduces the per-item figures in [Section 2](#2-the-verifier-study) from the committed scorecards without a
single model call. Two notes so the output is not surprising: it prints the arms as the run's own
`run.json` names them, which is the two-arm vocabulary this run was recorded under, and the
**re-attribution above is editorial rather than arithmetic** — the tool reproduces the numbers, not the
reading of them. It will also tell you that all 24 of those scorecards predate fingerprinting, so the
harness cannot itself prove which bundles they scored — which is true, and better said than left for
you to wonder about.

The three-arm run re-derives the same way from its own directory:

```bash
python evals/harness/judge-crossmodel.py --tabulate --cells evals/runs/2026-09-21-crossmodel-v3-3arm-artifacts
```

### The release gate

```bash
python evals/harness/run-knownbad.py --check        # fixture shapes + machine readiness, spends nothing
python evals/harness/run-knownbad.py --show KB4     # the exact blinded judge prompt, spends nothing
python evals/harness/run-knownbad.py                # all 6 fixtures, k=2
python evals/harness/run-knownbad.py --positive     # the known-good control
```

`--show KB4` prints the exact bytes a judge receives, so the blinding is auditable without running
anything. Cells already on disk are reused rather than re-spent, so a run can be taken in short batches.
The runner exits non-zero unless all six fixtures fail, which makes it usable as a gate rather than
something a human has to read and interpret.

### The command-route suite, including the quarantined cases

```bash
python evals/harness/run-suite.py --show 05          # exactly what a producer receives, spends nothing
python evals/harness/run-suite.py --only 01,02,03,04,05,06
```

The fidelity fix from [Section 5](#5-what-we-got-wrong-and-how-we-caught-it) is in
`build_system_bundle()`, where `ROUTE_COMMANDS` maps each route to its command file.

### The B2 specialist runs

```bash
python evals/runs/2026-09-19-b2-artifacts/blind-b2.py   # rebuilds the judge bundles from the raw outputs
```

The generation and judging legs of B2 were orchestrated rather than scripted; both workflow scripts are
committed in the artifacts folder alongside the raw outputs, the judge bundles, all eight judge scorecards
as JSON and the label key. The scorecards carry every quote each judge used, so any row in
[Section 3](#3-the-specialist-benchmarks-b2) can be checked against the text it came from.
