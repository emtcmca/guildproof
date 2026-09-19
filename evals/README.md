# guildproof evals

A light, host-judged harness to test and refine guildproof. Lives here, **not** loaded as a
plugin component (`evals/` isn't a scanned dir), so the plugin surface stays clean.

## Why it's shaped this way

guildproof is zero-call and model-agnostic — the host model does the reasoning, so two runs
of `/sharpen` are never byte-identical. You can't assert `expected == actual`. So the harness
judges in two passes:

1. **Structural invariants** — deterministic checks (sections present, assumptions labeled,
   ✅/⚠️/❌ used). Catch format regressions. No judgment needed.
2. **Quality rubric** — the host scores each output against a skeptic-framed rubric, per
   dimension, ✅/⚠️/❌ + a one-line reason. The judge is told to *break* the output, not bless it.

Fittingly, guildproof judges itself: the `skeptic` lens and `prompt-engineer` agent are the
judges.

## Layout

```
evals/
  README.md     this file
  rubric.md     structural invariants + quality dimensions per route, and the scoring scale
  runner.md     the protocol the host follows: run case → check → judge → write scorecard
  cases/        37 input fixtures (one per file): the input + case-specific must / must-not
  runs/         dated scorecards — the regression trail, committed
  known-bad/    6 negative fixtures the harness MUST FAIL — the test of the test (calibration)
```

### Coverage by route

Stated per route rather than per case, so it doesn't go stale every time a case is added:

| Route | Cases |
|---|---|
| `sharpen` | 01, 02, 28 |
| `forge-agent` | 03, 04 |
| `lens` (critique) | 05, 06, 23, 29, 30 |
| `lens --fix` | 31, 32, 33 |
| `lens --grade` | 35, 36, 37 |
| `orchestrate` | 17, 18, 19, 22 |
| gallery agents | 07–16, 20, 21, 24–27, 34 |

**Judge independence.** The harness is host-judged, which risks a producer grading its own work
(the first 9 runs were all-PASS). The judge must be a **separate invocation** from the producer
whenever a case tests a security gate, a legal/regulatory output, a code artifact, an
artifact-producing route (including any `--fix`), or orchestration — the rule lives in
`rubric.md`, deliberately as a rule and not a case list, because the list went stale once already.
The `known-bad/` fixtures must periodically FAIL — a judge that can't say no isn't judging.

## How to run

Tell Claude Code: **"run the guildproof evals"** (all cases) or **"run eval case 02"**.
It follows `runner.md`: executes each case the way a user would, checks invariants, judges the
rubric adversarially, and writes a scorecard to `runs/`.

## The refinement loop

1. Baseline run → commit the scorecard in `runs/`.
2. Change a lens / the engine / an agent.
3. Re-run the same cases.
4. Diff against the last run: keep the change only if the target dimension rose **and** nothing
   else regressed. Revert if it didn't.

Tuning by measured before/after, not vibes.
