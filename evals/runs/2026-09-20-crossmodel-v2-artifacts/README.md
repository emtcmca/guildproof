# Cross-model verifier run, V-2 (subtle leak) — artifacts

**Status: complete and judged.** 48 cells, 12 targets, k=2, scored by two blinded
`claude-sonnet-5` judges per target. Write-up:
[`../2026-09-20-crossmodel-verifier.md`](../2026-09-20-crossmodel-verifier.md). Published
numbers: [`../../../docs/FINDINGS.md`](../../../docs/FINDINGS.md) section 2.

*This file previously read "RAW CELLS, NOT YET JUDGED — these 28 cells", listing 7 targets and
2 OpenAI models. That was accurate mid-run on 2026-09-20 and went stale as the run grew to 12
targets and was judged. Rewritten 2026-09-20; the substance below is preserved from it.*

To re-derive the whole table from what is here, with **no model call and no cost**:

```bash
python evals/harness/judge-crossmodel.py --tabulate --cells evals/runs/2026-09-20-crossmodel-v2-artifacts
```

Input: [`../../benchmarks/fixtures/v2-invoice-subtle.md`](../../benchmarks/fixtures/v2-invoice-subtle.md)
— a well-built invoice handler that leaks `customer_id`, which its contract explicitly forbids.
Sent verbatim to both arms. Arm A is the bare model. Arm B gets `agents/verifier.md` as its
system prompt.

## What each file is

| File | What it is |
|---|---|
| `run.json` | **The run's definition** — input, specialist prompt, roster, reps, judge, checklist, blinding. Both harness halves read it, so neither can disagree about what this run was. It is also the model table: read it rather than a prose list like the one that went stale here. |
| `<target>-{A,B}{1,2}.md` | One cell. `A` bare, `B` with the specialist prompt. 12 targets x 2 arms x k=2 = 48. |
| `judge-bundles/judge-in-<target>.md` | The four cells of one target, blinded to W/X/Y/Z and stripped of self-description. Exactly what a judge received. |
| `label-key.csv` | Which label was which arm. **Never sent to a judge.** Reproducible from `run.json`. |
| `scorecards/score-<target>-<n>.json` | One judge's scores for one target. |
| `cells.json` | The per-cell log: which cells exist, their size, target and arm. |
| `manifest.json` | **Superseded by `cells.json`.** Kept as-is; see below. |
| `quarantine/`, `quarantine-*/` | Cells excluded from the result, each with a `WHY-QUARANTINED.md`. Kept so the defects stay reproducible instead of disappearing. |

## Pinned models, no aliases

Every model id is exact, in `run.json`. No aliases and no CLI defaults: an alias resolves to
whatever the vendor currently points at, which silently changes what a published number was
measured on.

## Isolation

Each arm ran in a fresh OS process with no channel to the authoring conversation. Verified by
asking each transport what context it could see:

- `claude -p` — "No prior conversation history, this is the first user message."
- `codex exec` — "no"
- Gemini REST — "The only context I was given is this single prompt."

So blinding is a property of the transport, not a rule a harness was asked to respect. This
replaced an earlier in-harness approach; see `quarantine/WHY-QUARANTINED.md`.

## One integrity note that survives into the cells

`claude -p` executes this machine's SessionStart hooks, and one injected a "this directory has no
saved memory yet" prompt into two Claude cells. It is stripped before any judge sees the text, and
left in the raw cells rather than edited out, because a raw cell should be what the model actually
returned.

It is identical across arms. **It does not follow from that that it cannot bias the comparison**,
and an earlier version of this note claimed it could not. Identical background text can interact
differently with a bare prompt than with a specialist one, and the raw cells show different
reactions to it. The contamination is disclosed; the stronger claim is withdrawn.

## Why Sonnet judged, and the one caveat on that reason

Two blinded `claude-sonnet-5` judges per target. The choice was made on measured grounds rather
than by preference: against a two-Opus consensus over 69 cells of the earlier small-tier run,
Sonnet scored Cohen's κ 0.68 with a 3-point present-rate gap, while Haiku scored κ 0.51 with a
bias that flipped direction by specialist — too generous on `debugger` and `api-reviewer`, too
harsh on `security-review`. A judge whose error direction depends on the thing being judged would
corrupt exactly the per-target comparison this run reports.

**That κ comparison has no committed scorecards.** The calibration was run and its numbers were
written down in prose, but the per-cell scores behind them were never committed anywhere in this
repo, so a reader cannot check them. It is stated here because it is the actual reason for the
decision, and flagged because an uncheckable number is not evidence. Either those scorecards get
committed or the figure stops being quoted.

## What is true without reference to any judge

Every cell identified the `customer_id` leak, in both arms, on every model. **Detection is not
what separates the arms on this input** — what the model does with a defect is. One defect type,
one artifact.

## Two honesty notes about this directory

**The 48 cells and 24 scorecards carry no fingerprints, and every command that reuses them says
so.** Fingerprint sidecars were added 2026-09-20, after this run. A sidecar records which input
bytes, which specialist-prompt bytes, which model id and which transport produced a file. Nobody
recorded those here at the time, so they are reported UNFINGERPRINTED rather than back-filled:
writing one now would assert exactly the thing that cannot be checked.

**`manifest.json` describes 16 of the 48 cells, and that is the original file, not a loss.** The
runner used to overwrite its per-cell log on every invocation, and this run was taken in batches
by transport, so the committed log ended up describing only the last batch. The runner now merges.
`cells.json` covers all 48, reconstructed from what is readable on disk — target, arm, rep, size,
non-empty — and marked `"reconstructed": true`. What was never written down, such as whether a
given cell was fresh or reused, is absent rather than guessed.
