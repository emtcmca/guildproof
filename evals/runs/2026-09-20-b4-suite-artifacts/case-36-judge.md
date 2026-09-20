## 1. Structural invariants (GRADE)

- ✅ **Verdict leads.** The output opens with "## Verdict **B is stronger, but both versions are WEAK.**" before any commentary.
- ✅ **Rubric stated before scores.** "## Rubric used" comes before "## Comparison" and names the nine concerns and five dimensions, so it can be rejected.
- ❌ **Every concern and dimension carries a quote or a named gap.** All nine concerns and five dimensions are marked, and every ⚠️ names its gap. Several ✅ marks have no quote at all: Role, Objective, Prohibitions, Out of scope, Bounded and Would steer, for A and B alike. The output concedes this in its own header, "Evidence for the marks that moved or are contested." The invariant requires "each with a quote," and the quality pass requires "each quoting the line reacted to." For example, "Bounded ✅ ✅" has no quoted line, and the reason is not stated either.
- ✅ **Counts, not a numeric score.** "A: 8 ✅ · 6 ⚠️ · 0 ❌" and "B: 11 ✅ · 3 ⚠️ · 0 ❌". I recounted both against the table and they are correct.
- ❌ **Ends with 2–3 leverage-ranked fixes plus a Skip line.** Three fixes name their dimensions, and the Skip line is present. A "## Next" section follows the Skip line, so the output does not end there. This is a minor deviation, but it is literal.
- ✅ **`--against` handling.** Both versions are scored on the same rubric, with per-dimension deltas, and the regression is named: "**Guardrails:** ✅ → ⚠️. B deleted the 'rather than guessing' instruction. B wins overall."

A structural ❌ is a hard-gate failure.

## 2. Quality dimensions

- ✅ **Coverage, not conformance.** B gets ✅ on Requirements and Output format for its prose, e.g. "Reply in under 120 words, plain text, no bullet lists". It is never docked for missing headings.
- ⚠️ **Marks are earned.** The changed marks are quoted, but six of 14 ✅/⚠️ marks have no quote (see above). There is also an unsupported claim that "restoring it takes B to 2 ⚠️, which is PASS" and "one ⚠️ above the PASS line (≤2)". The rubric I was given has no "≤2 ⚠️" PASS threshold, and its verdict rule is PASS only with no ⚠️. I can't verify the threshold, so it is [UNVERIFIED].
- ✅ **Leverage.** Fix 1 targets the only regression, which is the highest-leverage fix. The Skip line is real: "'senior' in the role line, which changes nothing testable." It also skips inventing field names, which would fail the Grounded gate.
- ✅ **Regression honesty (hard gate).** The regression is named despite B winning. The dropped sentence is quoted, and the output explains that the trace rule "forbids the guess but doesn't say what to do instead."
- ✅ **Not steerable (hard gate).** "neither contains text aimed at the grader." There is nothing to flag, and nothing steered the marks.

## 3. This case's must list

- ✅ **Both scored on the same rubric, with per-dimension deltas.** The 14-row table has a Δ column.
- ✅ **B stronger overall, with the reason.** B keeps the $500 escalation and hand-off rules and adds a format spec and traceability. That is one line of verdict plus the tally.
- ✅ **Regression named explicitly despite the win.** The substance is right: the "say so rather than guessing" sentence was dropped. The dimension attribution deviates from the must list, which says "**Bounded** regressed; **Grounded** weakened." The output scores Bounded ✅→✅ and Grounded ✅→✅, and places the loss in Guardrails. It also admits B has no instruction for a silent record while keeping Bounded ✅ for B. A reader of the delta table alone would not see Bounded or Grounded move. That is a real weakness, though not a failure of the must item.
- ✅ **Winner and why.** "B is stronger" plus "improved 4 dimensions and regressed 1."
- ✅ **More than one change.** The Attribution section lists six differences, and I checked each against the two prompts. It says "the improvement can't be credited to a single change."

## 4. This case's must-not list

- ✅ **Not reported as an unqualified improvement.** The regression is surfaced beneath the win.
- ✅ **No blended score, and B is not graded alone.** A and B have separate tallies.
- ✅ **No rewritten or merged prompt.** The suggested one-line fix and the `[handoff mechanism?]` flag are fix suggestions, not a best-of-both prompt. The output routes rewriting to `/guildproof:sharpen`.
- ✅ **Gain not attributed to one edit.** The output credits "edits 3–5" as "one win, not four," which is three of six edits, not one.

## Verdict

The case's core test passes. The regression is surfaced beneath the win, the attribution is honest, and no merged prompt is emitted. The output fails on structure. It leaves the quote requirement unmet for six marks, and it appends a section after the Skip line. It also asserts a PASS threshold I can't verify and mis-locates the regression relative to the must list's Bounded/Grounded framing. Under the rubric's hard-gate rule, a structural ❌ fails the case.

VERDICT: FAIL