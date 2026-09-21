# Three-arm verifier study: how much of the gap is the output contract?

**Run 2026-09-21. 3 targets, 3 arms, k=2, 18 cells, 2 blinded `claude-sonnet-5` judges per target.**
Artifacts: [`2026-09-21-crossmodel-v3-3arm-artifacts/`](2026-09-21-crossmodel-v3-3arm-artifacts/).
Re-derive with no model call:

```bash
python evals/harness/judge-crossmodel.py --tabulate --cells evals/runs/2026-09-21-crossmodel-v3-3arm-artifacts
```

## Why this ran

The [2026-09-20 two-arm study](2026-09-20-crossmodel-verifier.md) measured a bare model (17%)
against `agents/verifier.md` (98%) on a six-item checklist. The strongest objection to that result
is not about blinding or sample size. It is that **most of the gap might be bought by simply naming
the sections the output must contain** — no method, no adversarial stance, no guardrails. If so, the
honest claim shrinks from "this prompt changes how a model reviews work" to "telling a model which
headings to emit makes it emit those headings."

Arm C tests exactly that. It is the `## Output contract` section of `agents/verifier.md` and
nothing else, extracted mechanically by
[`make-arm-prompts.py`](../harness/make-arm-prompts.py) rather than written by hand, plus one
neutral framing sentence. It drops Objective, Operating principles, Inputs, Method,
Constraints / guardrails, and When unsure.

Proposed independently by the first Codex adversarial review.

## Result

| Arm | What it carried | Score |
|---|---|---|
| A | bare model, no system prompt | **18/72 = 25%** |
| B | the full `verifier.md` prompt | **71/72 = 99%** |
| C | **the output contract only** | **72/72 = 100%** |

Inter-judge agreement 107/108 (99%), Cohen's κ 0.98.

**Arm C matched arm B. On this checklist, the output contract buys the entire measured gap, and the
rest of the prompt adds nothing.** Not "most of it" — all of it, with C one cell ahead of B.

Per target, out of 24:

| Target | A bare | B full | C contract only |
|---|---|---|---|
| `claude-opus-5` | 4/24 | 24/24 | 24/24 |
| `gpt-6-astra` | 8/24 | 23/24 | 24/24 |
| `gemini-3.1-pro-preview` | 6/24 | 24/24 | 24/24 |

## The pre-registered prediction was wrong, and that is the interesting part

Before any cell ran, recorded in `make-arm-prompts.py`:

> Arm C scores high on items 1, 2, 3, 4 and 6, and NOT on item 5.

The reasoning was that item 5 — *does not rewrite the code* — is the one scored behavior that lives
in `## Constraints / guardrails`, which arm C does not receive. **It failed.** Arm C scored 4/4 on
item 5 on all three targets, having never been told not to rewrite.

The mechanism is visible in the cells and is worth stating, because it is the one place this run
says something about design rather than about measurement: an output contract that demands
*Defects*, *Claimed vs. actual*, *Confirm-these* and a per-axis receipt leaves no slot for a
rewrite. **Structure forbade the behavior that a guardrail was written to forbid.** On
`claude-opus-5` the bare arm scored 0/4 on item 5 — it did hand back corrected code — and both
prompted arms scored 4/4. So the effect is real on this input, not an artifact of models that
already refrain.

## What this does and does not license

**It does not mean the checklist was wrong.** It means the checklist measures *output structure*,
which was always disclosed, and an output contract is the instrument that produces output
structure. The result is close to tautological in hindsight. That is not a reason to bury it; a
tautology that took a third arm to expose was doing real work as a headline number.

**It does not show the rest of the prompt is worthless.** It shows the rest of the prompt has **no
measured effect**, which is a different and weaker statement. Method, adversarial stance and
guardrails would have to pay off in *defect quality* — finding a real defect, ranking it correctly,
refusing a plausible-but-wrong refutation — and **nothing here measures that.** Every cell in the
two-arm study already found the planted leak in both arms, so detection never discriminated either.

**It does mean the published claim has to shrink.** The defensible sentence is now about the
contract, not the prompt:

> A short output contract reliably produces a tri-state verdict, a BLOCKING line, an independence
> statement, severity-ranked defects and a receipt per clean axis. Bare models produce those about
> a quarter of the time. The rest of the specialist prompt showed no measured effect on that
> checklist.

## Accuracy boundary

- **3 targets, not 12.** One per vendor, frontier tier of each. The two-arm run's twelve targets
  were not re-run under three arms; that costs 72 producer calls and this pilot was run first
  precisely because it might change the claim, which it did.
- **Arm C is a subset of arm B.** C ≈ B is therefore unsurprising in one direction. The finding is
  that B's *additional* content did not add anything, not that two unrelated prompts tied.
- **One artifact, one defect type**, the same `v2-invoice-subtle.md` as the two-arm run. A wider
  defect corpus is the outstanding gap and is the reason not to over-read this.
- **k=2, single input, one judge model.** κ 0.98 says the two judges agreed, not that they were
  right.
- **Ceiling effect.** B and C are at or within one cell of 24/24, so this run cannot rank them.
  It can only say C is not worse.
- Arm A's 25% here is above the 17% of the twelve-target run, consistent with three frontier models
  being the easiest cases for a bare arm.

## Two harness defects found while running this

Both would have produced plausible output rather than an error, which is the failure shape this
harness keeps hitting.

1. **The generated arm-C prompt carried its own experiment metadata.** The first version of
   `make-arm-prompts.py` wrote a `<!-- GENERATED ... Why: isolates how much of arm B's advantage
   is bought by naming the headings -->` header into the prompt file, and the runner sends that
   file verbatim as the system prompt. The model would have been told it was a reduced arm in an
   experiment about its own prompt. Caught before any cell was generated; provenance now lives in
   a sibling `.provenance.json` and the generator refuses to emit a prompt containing experiment
   words.
2. **The judge's own prompt said "four unlabeled outputs".** With three arms a bundle holds six,
   and the judge would have been told the wrong count. Now derived from the manifest. Also fixed:
   the fingerprint sidecars matched the scorecard glob, so the provenance line reported "12
   scorecards, 6 provably scored" for a 6-scorecard run and listed the six sidecars as
   unfingerprinted evidence. No tally was affected; the count was still twice the truth.
