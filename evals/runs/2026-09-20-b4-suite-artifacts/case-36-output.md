## Verdict

**B is stronger, but both versions are WEAK.**

- **A:** 8 ✅ · 6 ⚠️ · 0 ❌ → WEAK
- **B:** 11 ✅ · 3 ⚠️ · 0 ❌ → WEAK, one ⚠️ above the PASS line (≤2)

B improved 4 dimensions and regressed 1. It dropped A's "say so rather than guessing" instruction. Restoring it takes B to 2 ⚠️, which is PASS.

No hard gate failed on either version. Neither prompt asserts anything the agent can't verify, and neither contains text aimed at the grader.

## Rubric used

The default rubric, since you didn't pass `--rubric`. It has two parts, both applied to A and B:

- **Coverage:** nine concerns: Role, Objective, Context, Requirements, Guardrails, Prohibitions, Success criteria, Output format, Out of scope.
- **Quality:** five dimensions: Unambiguous, Testable, Bounded, Grounded (hard gate), Would steer.

Coverage is scored on whether a concern is resolved, not on headings. Ambiguous cases default to ⚠️.

## Comparison

| Dimension | A | B | Δ |
|---|---|---|---|
| Role | ✅ | ✅ | — |
| Objective | ✅ | ✅ | — |
| Context | ⚠️ | ⚠️ | — |
| Requirements | ⚠️ | ✅ | **improved** |
| Guardrails | ✅ | ⚠️ | **regressed** |
| Prohibitions | ✅ | ✅ | — |
| Success criteria | ⚠️ | ✅ | **improved** |
| Output format | ⚠️ | ✅ | **improved** |
| Out of scope | ✅ | ✅ | — |
| Unambiguous | ⚠️ | ⚠️ | — |
| Testable | ⚠️ | ✅ | **improved** |
| Bounded | ✅ | ✅ | — |
| Grounded *(gate)* | ✅ | ✅ | — |
| Would steer | ✅ | ✅ | — |

## Evidence for the marks that moved or are contested

- **Requirements, Output format, Testable (A ⚠️):** A says "Keep replies short." Two competent readers would write 30 words or 200. B replaces it with "Reply in under 120 words, plain text, no bullet lists," which can be checked mechanically.
- **Success criteria (B ✅):** B gives four checks a grader can run:
  - word count;
  - format;
  - "Every claim must trace to a field in the order record";
  - "name anything you escalated."
- **Guardrails (A ✅, B ⚠️):** A says "If the order record doesn't cover what the customer asked, say so rather than guessing." B has no equivalent. The nearest line is the trace rule, which forbids the guess but doesn't say what to do instead. A competent agent will probably say the record doesn't show it, but that is inference, not instruction. I scored the loss once, here. I did not also dock Would steer for the same deletion.
- **Context (both ⚠️):** Three things are missing from both:
  - "the order record supplied in the conversation" names no fields;
  - "a human" has no mechanism;
  - neither says whether the agent may act on refunds of $500 or less.
- **Unambiguous (both ⚠️):** "Escalate any refund over $500" and "hand those to a human" use two different verbs. B's "name anything you escalated" then leaves open whether a handed-off billing dispute counts. Neither says whether "over $500" means the requested refund or the order total. B narrowed the ambiguity from A but didn't clear it, so the mark holds.
- **Grounded (both ✅):** The $500 threshold is a policy you set. It is an instruction, not a factual claim the agent has to assert.

## Regressions

- **Guardrails:** ✅ → ⚠️. B deleted the "rather than guessing" instruction. B wins overall, and this is the only thing it lost.

## Attribution

The two versions differ in more than one respect:

1. "senior" added to the role;
2. the coverage-gap sentence deleted;
3. "Keep replies short" replaced by the word, format, and bullet spec;
4. the trace rule added;
5. the escalation-naming rule added;
6. the hand-off clause moved.

The ranking holds, but the improvement can't be credited to a single change.

The four "improved" marks (Requirements, Success criteria, Output format, Testable) mostly come from edits 3–5. Read them as one win, not four. The one regression traces to edit 2. Edits 1 and 6 look neutral.

## Top fixes

1. **Restore the coverage-gap instruction in B.** Lifts *Guardrails*. It is the only regression, and it brings B to 2 ⚠️, which is PASS. Suggested line:
   ```
   If the order record doesn't cover what the customer asked, say so and name what's missing rather than guessing.
   ```
2. **Pick one verb for "escalate" and "hand to a human," define what it does, and state whether "name anything you escalated" includes hand-offs.** Lifts *Unambiguous* and *Context*. The hand-off mechanism (a queue, a tag, a handoff message) is a fact only you can supply, so I've left it out rather than invent one. Add `[handoff mechanism?]` to the prompt until you fill it in.
3. **Say whether "over $500" means the refund requested or the order total, and whether the agent may act on refunds of $500 or less.** Lifts *Unambiguous* and *Context*. Today the prompt says only what happens above the line, not below it.

**Skip:**

- "senior" in the role line, which changes nothing testable.
- Naming order-record fields, unless you have the real schema. Guessing field names would fail the Grounded gate.
- A separate "success criteria" paragraph. The checks in B already cover it.

## Next

- `/guildproof:sharpen` on B with fixes 1–3 applied, to rebuild it with the gaps filled.
- `/guildproof:lens <revised B> --grade --against <this B>` to confirm the revision reaches PASS and regresses nothing.