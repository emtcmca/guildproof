# Does a verifier need a fresh conversation? (2026-09-19)

**Question.** `agents/verifier.md` now says to run it in a fresh conversation, never the one that
built the artifact. Is that true, or is it a rule that sounds right?

**Short answer: half true.** On a frontier model, with the verifier prompt loaded, reviewing in the
builder's own conversation was as accurate as a fresh review in all three tasks. On a small model,
the fresh review was more accurate in two of three. In both of those, the same-conversation review
certified a real contract breach as clean. In the third, the fresh review did that instead.

Every raw input and output is in [`2026-09-19-self-review-artifacts/`](2026-09-19-self-review-artifacts/).

## Setup

- **Three build tasks**, each asked the way a user would, loosely and in a hurry:
  - T1: an org-scoped invoice endpoint
  - T2: a retry wrapper for payment calls
  - T3: public dashboard share links
- **Two model tiers:** the session's frontier model and Haiku. Exact model ids weren't recorded by
  the harness.
- **Build.** Each builder wrote code with no contract. The code is in `sr-*.md`.
- **Same-conversation review (self).** The builder, still in its own conversation, was given
  `verifier.md` and the contract and asked to verify what it wrote. Output is in `rv-self-*.md`.
- **Fresh review.** A new agent got the identical `verifier.md`, contract and code, and nothing
  else. Output is in `rv-fresh-*.md`.
- **Contracts** were written before any build output was seen (`selfreview-contracts.md`).
- **Blind judge.**
  - One frontier judge per task. Each wrote its own list of real defects from the code and contract
    *before* reading the reviews, then scored reviews A and B.
  - Lines that reveal which arm wrote a review (the Independence line, "I wrote this") were
    removed first by `blind-pairs.py`. The A/B assignment is in that script and was never shown to
    a judge.
  - Judgments are in `judge-out-*.md`.
- k=1 everywhere. Six pairs is a small sample.

## Results

| Task | Tier | More accurate (unblinded) | What decided it |
|---|---|---|---|
| T1 | frontier | tie | Both found all three real defects. |
| T1 | small | **fresh** | Self-review called the HIGH defect clean: "Malformed ids do not produce 500 ✅" (they do). |
| T2 | frontier | tie | Both found all five. |
| T2 | small | **fresh** | Self-review called 408 retries and Retry-After handling clean. Both were defects. |
| T3 | frontier | fresh, slightly | Self-review found two more LOW issues, but quoted its own build note as evidence. The note isn't in the artifact. |
| T3 | small | **self** | Fresh review marked "expired tokens return 404" clean. Expired links return 200. |

**Verdicts: 12 of 12 correct.** Every review returned NOT VERIFIED on code with a contract breach,
and VERIFIED WITH GAPS on the one artifact with none (frontier T3). Every review blocked.

**Independence line: 11 of 12 correct.**
- All six same-conversation reviews said NOT INDEPENDENT.
- Five of six fresh reviews said INDEPENDENT.
- The small-model fresh review of T2 said NOT INDEPENDENT ("code read in same session"). It
  misread "I read the code in this session" as "I wrote it."

## What this supports, and what it doesn't

**Supported:**
- **A self-review can certify its own bug as clean.** It happened on the small model in T1 and T2.
  The worst case was a HIGH contract breach marked ✅ with a confident, wrong explanation.
- **The frontier self-reviews leaned on the builder's own cover note.** Three of three quoted
  claims from their build message as if they were evidence, and a blind judge flagged each one as
  "not in the artifact." That's the contamination the independence rule is about, visible even when
  it didn't cost accuracy.
- **The verifier's output contract held in every run:** tri-state verdict, blocking, severity, and
  no rewrite.

**Not supported:**
- **"A fresh reviewer catches more."** Not on a frontier model in this sample. On the small model it
  won two of three, and one fresh review made the same mistake it is supposed to prevent.
- **Any rate or percentage.** Six pairs at k=1 is an anecdote with a method, not a measurement.

## Changes this points to

1. **Independence wording.** "Read in this session" is not "wrote in this session." The rule should
   key on who produced the artifact, not on when it was read.
2. **"Confirm-these: None" needs a receipt.** A verifier that lists no gaps should list the axes it
   actually checked. Two small-model reviews declared an axis clean with a false mechanism, which a
   forced "how I checked it" line might have caught.
3. **Recommended use:** say "run it fresh, especially on smaller models," not "a fresh verifier
   finds what yours misses."
