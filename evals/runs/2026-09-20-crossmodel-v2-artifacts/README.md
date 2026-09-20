# Cross-model verifier run, V-2 (subtle leak) — RAW CELLS, NOT YET JUDGED

**Status: incomplete. These 28 cells are generated and integrity-checked. No judge has
scored them, so no number in this folder is a result yet.**

Input: `../../benchmarks/fixtures/v2-invoice-subtle.md` — a well-built invoice handler that
leaks `customer_id`, which its contract explicitly forbids. Sent verbatim to both arms.

Arm A is the bare model. Arm B gets `agents/verifier.md` as its system prompt. k=2.

## Models, all pinned

| Target | Model id | Transport |
|---|---|---|
| claude-haiku | `claude-haiku-4-5-20251001` | `claude -p` |
| claude-sonnet | `claude-sonnet-5` | `claude -p` |
| claude-opus | `claude-opus-5` | `claude -p` |
| gpt-5 | `gpt-5.6-luna` | `codex exec -m` |
| gpt-6 | `gpt-6-astra` | `codex exec -m` |
| gemini-flash | `gemini-3.8-flash` | Gemini REST |
| gemini-pro | `gemini-3.1-pro-preview` | Gemini REST |

No aliases and no CLI defaults. An alias resolves to whatever the vendor currently points
at, which silently changes what a published number was measured on.

## Isolation

Each arm runs in a fresh OS process with no channel to the authoring conversation. Verified
by asking each transport what context it could see:

- `claude -p` — "No prior conversation history, this is the first user message."
- `codex exec` — "no"
- Gemini REST — "The only context I was given is this single prompt."

This replaced an earlier in-harness approach; see `quarantine/WHY-QUARANTINED.md`.

## One integrity note that survives into the cells

`claude -p` executes this machine's SessionStart hooks, and one injected a "this directory
has no saved memory yet" prompt into two Claude cells. It is identical across arms so it
cannot bias the comparison, and it is stripped before any judge sees the text. It is left in
the raw cells rather than edited out, because the raw cell should be what the model actually
returned.

## What is known without a judge

All 28 cells identified the `customer_id` leak, in both arms, on every model. Detection is
not what separates the arms on this input.

## Pending

Two Sonnet judges per target, blinded. Sonnet is the judge on measured grounds: against a
two-Opus consensus over 69 cells it scored kappa 0.68, where Haiku scored 0.51 with a bias
that flipped direction depending on the specialist.
