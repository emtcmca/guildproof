# B2 — Specialist behaviors, small-model tier

**Date:** 2026-09-19 · **Benchmark:** [B2](../benchmarks/README.md#b2--specialist-behaviors-what-the-agent-prompts-change-about-an-answer)
· **Artifacts:** [`2026-09-19-b2-artifacts/`](2026-09-19-b2-artifacts/) (34 files, everything below is
reproducible from them)

## What was measured

For four specialists, the same user message was sent to the same model twice with the specialist
prompt (`agents/<name>.md`) as its system prompt, and twice with nothing. Each of the 16 outputs was
then scored by two independent judges against a fixed behavior checklist, with the arm labels hidden.

The checklists were committed in `evals/benchmarks/README.md` before any run. Nothing was chosen
after seeing an output.

- **Model, both arms:** `claude-haiku-4-5-20251001` (the small tier). **Judges:** Opus 5.
- **k = 2** per arm. **Judges = 2** per specialist, scoring independently.
- **Inputs:** one per specialist (B2's D-1, S-1, A-1, V-1). The second input of each pair has not run.
- **Cells:** 4 specialists × 18 behaviors total × 2 arms × 2 runs × 2 judges = 144 scorings.

## Result

Each cell is the number of times that behavior was marked PRESENT out of 4 scorings (2 runs × 2
judges).

| Specialist | Behavior | Bare | With guildproof |
|---|---|---|---|
| debugger | separates the user's claims from verified facts | 0/4 | **0/4** |
| debugger | declines to invent a reproduction | 2/4 | 4/4 |
| debugger | ranks hypotheses, each with a cheapest probe | 0/4 | 4/4 |
| debugger | separates trigger from root cause | 0/4 | 1/4 |
| debugger | no masking one-line patch handed over | 0/4 | 2/4 |
| security-review | ranks by exploitability × impact | 4/4 | 4/4 |
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

Per specialist:

| Specialist | Bare | With guildproof |
|---|---|---|
| verifier | 2/24 (8%) | 22/24 (92%) |
| security-review | 7/16 (44%) | 16/16 (100%) |
| debugger | 2/20 (10%) | 11/20 (55%) |
| api-reviewer | 6/12 (50%) | 7/12 (58%) |

**Inter-judge agreement: 69 of 72 cells, and Cohen's κ = 0.92 ("almost perfect").** The three splits
are listed below.

The κ is reported instead of the raw 96% because raw agreement is the statistic that lies. Two judges
working a corpus where almost everything is negative will agree constantly by accident: the canonical
case is Roitblat, Kershaw and Oot (JASIST 2010), where two expert teams on 5,000 documents hit 70%
raw agreement and κ = 0.238, because nearly all of it was independently agreeing that a document was
negative. **That trap does not bite this run, and the reason is checkable:** the 72 cells split almost
evenly, 35 both-present and 34 both-absent, with each judge marking present at 50-51%. Chance
agreement is therefore 0.50, not 0.90, and the observed 0.96 is a real signal. Had the cells been
skewed, the 96% would have meant nothing and this note would say so.

## The three results that cut against guildproof

Per the benchmark's house rules, these publish with the same prominence as the wins.

**1. `api-reviewer` lost two of its three behaviors.** The bare model reviewed the contract in 4 of 4
scorings against the specialist's 3 of 4, and flagged breaking changes in 2 of 4 against the
specialist's 0 of 4. The specialist won only on naming the abuse path (0/4 → 4/4). On this input, the
api-reviewer prompt is close to a wash, and it is the one specialist whose prompt should be looked at
before launch rather than advertised.

**2. The `flags breaking changes` item may be ill-posed, which means it is not evidence either way.**
One judge wrote it up unprompted: the input is a pre-release partner API, so there are arguably no
existing integrations to break, and the item admits two readings. That judge applied the more
generous one and still scored it low. An item that a careful judge has to disambiguate before scoring
is a defect in the ruler. **This row should be re-specified and re-run, not quoted.**

**3. The behavior the README leads with did not happen, in either arm.** `separates the user's claims
from verified facts` scored **0/4 with the prompt and 0/4 without it**. That behavior is the *first*
of the five things README's "Try it before you install" section tells a reader to check for. At the
small-model tier, on this input, the debugger prompt did not produce it. Both judges were explicit:
the outputs restated "3%" and "last Thursday" as established fact and then reasoned from them.

That last one is a documentation defect as much as a result. Either the README's promise gets scoped
to the model tier it holds on, or the debugger prompt needs to make the labelling step harder to
skip. It has been logged rather than quietly dropped.

## What this supports, and what it does not

**Supported.** On this input set, at the small-model tier, the specialist prompts produce their
stated behaviors far more often than the bare model does: 78% against 24%. The `verifier` gap is the
largest in the set and the most structural, 8% against 92%. Every `verifier` behavior except the
clean-axis receipt went from never happening to always happening. The bare model produced no
tri-state verdict, no BLOCKING line and no Independence line in any of its four scorings, and it
rewrote the code every time instead of reporting defects.

**Not supported.**

- **Nothing about the frontier tier.** This ran on the small model only. The 2026-09-19 self-review
  experiment already found that a frontier model closes some of these gaps on its own, so the delta
  here should be read as the small-tier delta and nothing more.
- **Nothing about answer quality.** Every item scores whether a behavior is *present*, with a quote.
  An output can hit every item and still be wrong on the substance, and the judges recorded exactly
  that in several `notable` fields: one arm-B output confidently claimed a 3% failure would surface
  "within a few requests," and one recommended `(lineItems || [])` as a guard, which is the change
  that turns a visible crash on a billing surface into an invoice silently rendered with no line
  items. Behavior compliance is not correctness.
- **One input per specialist.** Four of B2's eight inputs have not run.
- **`api-reviewer` is not shown to help.** See above.

## Method limits, stated rather than buried

- **Blinding is weaker here than in B3, structurally so.** In B2 the scored behaviors *are* output
  structure, so a judge that knows the checklist can often infer the arm: only arm B prints a
  `BLOCKING:` line. Labels were hidden to remove label bias, and that is all the blinding buys. The
  mitigation is that every PRESENT mark requires a verbatim quote, so any reader can re-check a score
  against the committed output rather than trusting the judge.
- **Redaction is enforced by promise, not by construction.** [`blind-b2.py`](2026-09-19-b2-artifacts/blind-b2.py)
  strips meta self-description from the outputs and holds the label key in a file the judges never
  read, but nothing in the harness would *fail* if a key leaked. A local review tool that releases
  labels only after a judgment is fsynced would make this structural. Recorded as the known weakness
  of this run.
- **One clause-level redaction happened and is visible in the artifact.** One arm-B verifier output
  put a sentence naming its system prompt inside its `Independence:` line, which is itself a scored
  behavior. Dropping the line would have cost arm B a point it earned; keeping it would have named
  the arm. The clause was replaced with `[clause redacted]`, which is visible in
  [`judge-in-verifier.md`](2026-09-19-b2-artifacts/judge-in-verifier.md) and logged by the script.
- **Both arms carry the same injected repo context.** Each generation agent received this repo's
  `CLAUDE.md` like any agent run here. It is identical across arms so it cannot bias the direction of
  the delta, but it may raise the bare arm's floor, which would make this delta conservative.
- **The judges are a different tier than the subjects, but the same family.** Opus judging Haiku.
- **Five scoring rows were excluded** from the totals: three where one judge filled an out-of-range
  index and wrote "no seventh checklist item exists; this entry is not scored," and two where both
  judges added an index-0 row with `evidence_kind: none`. None carried a PRESENT mark, so excluding
  them cannot flatter either arm. Both denominators are 72.

## Inter-judge splits, all three

| Specialist | Output | Arm | Behavior | Split |
|---|---|---|---|---|
| api-reviewer | W | guildproof | reviews the contract, not just the code | present / absent |
| debugger | Z | guildproof | separates trigger from root cause | present / absent |
| security-review | X | bare | names the attack, not just the weakness | present / absent |

All three splits are on arm-favourable-if-generous readings, and in each case the judge who scored it
absent wrote out their reasoning in `methodology_notes`. The `debugger` one is the most interesting:
the output names the exact defect the item describes in its hypothesis list, then contradicts itself
in its verdict section by assigning the root cause to the delivery path. Both readings are defensible
because the output holds both.

## Reproducing this

```bash
# 1. generation (16 runs) and 2. judging (8 judges) are the two committed workflow scripts
node --version   # the runs were orchestrated, not scripted; see the two .js files
python 2026-09-19-b2-artifacts/blind-b2.py   # rebuilds the judge bundles from the raw outputs
```

The raw outputs, the judge bundles, all eight judge scorecards as JSON, the label key and both
workflow scripts are in [`2026-09-19-b2-artifacts/`](2026-09-19-b2-artifacts/). The scorecards carry
every quote each judge used, so any row in the table above can be checked against the text it came
from.
