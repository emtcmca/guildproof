# Cross-model verifier study — 12 models, 3 vendors

**Date:** 2026-09-20 · **Benchmark:** [B2](../benchmarks/README.md), input V-2
· **Artifacts:** [`2026-09-20-crossmodel-v2-artifacts/`](2026-09-20-crossmodel-v2-artifacts/)
— 48 cells, 24 judge scorecards, 12 blinded bundles, the label key, and the runner.

## The question

Does a capable model, asked to verify code against a contract, produce a verdict you can act
on? And does it get better at that as models improve?

## Method

One artifact: a well-built invoice handler that returns `customer_id`, which its own contract
forbids. Sent verbatim to both arms. Arm A is the bare model. Arm B gets `agents/verifier.md`
as its system prompt. **k = 2** per arm per model.

Every model id is pinned. No aliases, no CLI defaults: an alias resolves to whatever a vendor
currently points at, which silently changes what a published number was measured on.

| Family | Models | What varies |
|---|---|---|
| Anthropic | `claude-haiku-4-5-20251001`, `claude-sonnet-5`, `claude-opus-5` | tier |
| OpenAI | `gpt-5.5`, `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-6-astra` | generation, plus a sibling pair at 5.6 |
| Google | `gemini-3.5-flash`, `3.6-flash`, `3.7-flash`, `3.8-flash` | generation, tier held constant |
| Google | `gemini-3.1-pro-preview` | older generation, larger tier |

Each arm runs in a fresh OS process with no channel to the authoring conversation, verified by
asking each transport what context it could see before it was trusted with a cell. Scored by two
blinded Sonnet judges per target, on 288 cells.

## Result

**Bare: 50/288 (17%). With guildproof: 282/288 (98%).**

### Per item, all 12 models

| Behavior | Bare | With guildproof |
|---|---|---|
| tri-state verdict | 14/48 (29%) | 48/48 (100%) |
| **explicit BLOCKING line** | **0/48 (0%)** | 48/48 (100%) |
| **explicit Independence line** | **0/48 (0%)** | 48/48 (100%) |
| defects ranked by severity | 4/48 (8%) | 46/48 (96%) |
| does not rewrite the code | 16/48 (33%) | 46/48 (96%) |
| receipt for each clean axis | 16/48 (33%) | 46/48 (96%) |

Two behaviors scored **zero out of forty-eight**. Across twelve models and three vendors, not
one unprompted run stated whether the work was blocked, and not one stated whether its review
was independent of whoever wrote the code.

### Does the gap close as models improve?

| Ladder | Bare, oldest to newest | With guildproof |
|---|---|---|
| OpenAI generation | 25% → 8% → 33% → **17%** | 100%, 100%, 96%, 100% |
| Google generation | 17% → 17% → 0% → **8%** | 100%, 96%, 100%, 100% |
| Anthropic tier | 8% → 33% → **17%** | 83%, 100%, 100% |
| `gemini-3.1-pro` (older, larger) | 25% | 100% |

**No.** The bare-arm score has no relationship to model strength. It scatters between 0% and
33% with no trend in any of the three families. `gemini-3.7-flash` scored **0 of 24**.
`gpt-6-astra`, the newest OpenAI model tested, scored below `gpt-5.5`. `claude-opus-5` scored
below `claude-sonnet-5`.

This is a stronger result than a narrowing gap would have been. It is not a deficit that model
progress is slowly erasing. It is a behavior models do not exhibit and show no sign of trending
toward.

### The control pair

`gpt-5.6-luna` and `gpt-5.6-sol` are siblings of the same generation. Bare: **8% and 33%.**

That 25-point spread between two models of the *same generation* is wider than any
generation-to-generation movement anywhere in the study. It is direct evidence that variation in
the bare arm is **noise, not capability**, and it is the reason a two-model comparison would
have proved nothing. Anyone reading a two-point result in this space should ask for this control.

### Contract shape versus judgment

Four of the six items are satisfiable by emitting a labelled section the prompt asks for. Two
require the model to do or refrain from something substantive. Split accordingly:

| Item type | Bare | With guildproof | Delta |
|---|---|---|---|
| contract shape (items 1–4) | 9% | 99% | +90 pts |
| **judgment and restraint (items 5–6)** | **33%** | **96%** | **+62 pts** |

Quoting 17%-to-98% without this split quotes a number that is substantially
instruction-following. **The defensible figure is the judgment delta: +62 points.** It is
reported here because a reader will otherwise find the objection themselves, and because it is
still the larger finding either way.

## What the judges disagreed about

**Cohen's κ = 0.97**, 284 of 288 cells agreed, judge present-rates 0.58 and 0.57.

All four splits, in full:

| Target | Output | Arm | Item | judge1 / judge2 |
|---|---|---|---|---|
| `gemini-3.6-flash` | W | bare | receipt for each clean axis | PRESENT / absent |
| `gemini-3.6-flash` | X | bare | receipt for each clean axis | PRESENT / absent |
| `gemini-3.6-flash` | Y | guildproof | defects ranked by severity | PRESENT / absent |
| `gpt-5.6-sol` | X | guildproof | defects ranked by severity | absent / PRESENT |

Two things worth noting. **Zero splits on items 1, 2 and 3** — the presence of a labelled
verdict, BLOCKING line or Independence line is not a judgment call, which is why those rows are
the most trustworthy in the table. And three of four splits are on one model,
`gemini-3.6-flash`, whose output sits closest to the line on both contested items.

A high κ was treated as a warning sign rather than a reassurance here, for reasons in the
quarantine note below.

## Results that cut against guildproof

Per the benchmark's house rules, these publish with the same prominence as the wins.

1. **`claude-haiku` prompted arm: 20/24.** The only target well off ceiling. The verifier prompt
   is weakest on the smallest model, which is also where a user is most likely to be relying on
   it to compensate.
2. **`gemini-3.6-flash`: 23/24** and **`gpt-5.6-sol`: 23/24.** The prompt is not a guarantee.
3. **Detection is not the differentiator.** All 48 cells identified the `customer_id` leak, in
   both arms, on every model including Haiku. This tool does not help a model *see* a defect. It
   changes what the model does with one it has already seen.
4. **Four of the six items are arguably instruction-following.** See the split above.

## Method limits

- **One artifact, one defect type.** Twelve models is breadth across *models*, not across defect
  classes. A single cross-tenant field leak tells you nothing about how any of this behaves on a
  race condition, a missing idempotency key, or a broken migration. **This is the study's
  biggest weakness.** B2's remaining inputs and B1 are what add that depth, and until they run,
  no claim here generalises past this defect shape.
- **k = 2.** Two runs per arm per model. The control pair suggests within-generation variance is
  large, so k=2 is thin.
- **The judge is a Claude model scoring Claude, GPT and Gemini outputs.** Judge choice was
  measured rather than assumed: against a two-Opus consensus over 69 cells, Sonnet scored κ 0.68
  while Haiku scored 0.51 with a bias that flipped direction depending on the specialist. But a
  non-Claude judge would be a stronger design and is not yet calibrated.
- **One transport asymmetry.** Claude and Gemini accept a real system prompt;
  `codex exec` has none, so the GPT arms receive the specialist prompt prepended to the user
  message behind explicit delimiters, plus a "everything is in this message" preamble applied
  identically to both arms. That preamble exists because `codex exec` is an agentic CLI that went
  hunting for files instead of reading its prompt. It removes a harness artifact rather than
  adding an instruction about how to do the work, but it is a difference and it is recorded.
- **`claude -p` executes this machine's SessionStart hooks**, which injected machine-specific text
  into two Claude cells. Identical across arms, stripped before judging, left in the raw cells.
- **Blinding is weaker than it looks for items 1–3.** A judge that knows the checklist can often
  infer the arm, because only arm B prints a `BLOCKING:` line. Labels are hidden to remove label
  bias and that is all it buys. The mitigation is that every PRESENT mark carries a verbatim
  quote, so any row is checkable against the committed output.

## The instrument, and why the quarantine folder is committed

An earlier attempt at this run produced a judged table that was one step from being reported. It
was wrong. Four transport bugs, every one producing plausible output rather than an error:

1. `claude` and `codex` resolve to Windows `.CMD` batch shims, and cmd.exe re-parsed a
   multi-line prompt containing SQL and backticks. Models received fragments and replied that
   they had no artifact to verify. **Four cells read as a model failing to verify when the
   artifact never reached it.** Prompts now go on stdin.
2. `subprocess(text=True)` decodes with the Windows ANSI codepage. An em-dash in model output
   crashed the reader thread and left stdout as `None`.
3. The verifier prompt is ~7,700 characters against an 8,191-character command line limit, which
   silently lost both GPT arm-B cells.
4. `codex exec` explored the workspace instead of reading its prompt.

Before that, the arms ran as Claude Code workflow subagents, and that harness relays the parent
conversation's most recent user message to every subagent. Two bare-arm cells answered a question
about publishing results instead of verifying the artifact. **Blinding enforced by a promise is
not blinding**, so the arms moved to processes with no channel to the authoring session.

What caught it was not a review. It was **a statistic that was too good**: a Cohen's κ of exactly
1.00 across 96 cells, which is not something two independent judges produce. That prompted
reading the raw text instead of the totals.

Those 16 cells are in
[`quarantine/`](2026-09-20-crossmodel-v2-artifacts/quarantine/) with
`WHY-QUARANTINED.md`, kept so the defects stay reproducible rather than disappearing.

## Reproducing this

```bash
python evals/harness/run-crossmodel.py --check        # what your machine can run, and how to fix the rest
python evals/harness/run-crossmodel.py --dry-run --input evals/benchmarks/fixtures/v2-invoice-subtle.md
python evals/harness/run-crossmodel.py --input evals/benchmarks/fixtures/v2-invoice-subtle.md
python evals/harness/judge-crossmodel.py --blind
python evals/harness/judge-crossmodel.py --judge      # add --target X to run in short batches
python evals/harness/judge-crossmodel.py --tabulate
```

The first two commands spend nothing. Targets your machine cannot run are reported as
**UNMEASURED**, never as passing. Model versions move, so your numbers may differ from these;
the model ids and this date are recorded precisely so that difference is interpretable.
