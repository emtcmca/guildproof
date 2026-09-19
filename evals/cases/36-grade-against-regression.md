---
id: "36"
route: grade
command: /guildproof:lens --grade
tests: --against comparison — per-dimension deltas, and naming a regression even when the revision wins overall
---

## Input

```
/guildproof:lens --grade --against
```

**Version B (the revision, under grade):**

```
You are a senior support engineer for Northwind Tools, a warehouse inventory SaaS.

Answer questions about orders, returns, and shipping using only the order record supplied in
the conversation. Escalate any refund over $500 to a human. Don't handle billing disputes,
account access, or legal matters — hand those to a human.

Reply in under 120 words, plain text, no bullet lists. Every claim must trace to a field in
the order record; name anything you escalated.
```

**Version A (the original, `--against`):**

```
You are a support engineer for Northwind Tools, a warehouse inventory SaaS.

Answer questions about orders, returns, and shipping using only the order record supplied in
the conversation. Escalate any refund over $500 to a human. If the order record doesn't cover
what the customer asked, say so rather than guessing.

Keep replies short. Don't handle billing disputes, account access, or legal matters — hand
those to a human.
```

## Must

- Score **both** on the same rubric and report per-dimension deltas.
- Judge B stronger **overall** — B keeps both of A's safety rules ($500 escalation, the
  out-of-scope handoff) *and* adds a concrete output format and a traceability requirement,
  where A had only "keep replies short."
- **Name the regression explicitly, despite B winning.** B replaced A's *"If the order record
  doesn't cover what the customer asked, say so rather than guessing"* with *"Every claim must
  trace to a field in the order record"* — which says where claims come from but no longer says
  **what to do when the record is silent**, the exact case where a support agent invents a
  delivery date. **Bounded** regressed; **Grounded** weakened.
- State the winner and why in one line.
- Note that the two versions differ in more than one respect, so the improvement cannot be
  attributed to a single change.

## Must not

- **Report B as an unqualified improvement.** Surfacing a regression *underneath an overall win*
  is the entire purpose of this route — a version that wins on the scoreboard while quietly
  giving something back is what eyeballing a rewrite misses.
- Merge the two into a single blended score, or grade only B.
- Rewrite either version, or emit a merged "best of both" prompt — that's `/sharpen`.
- Attribute the overall gain to one specific edit when several changed at once.

## Calibration note (2026-07-21)

The first version of this fixture had B drop *both* of A's behavioral guardrails — the $500
escalation rule and the never-state-unverifiable-details prohibition — while gaining only format
and a success line. A producer run correctly judged **A** stronger ("B is now bounded on
typography and unbounded on money"), which is the right call on those inputs and means the
fixture never exercised what it was written to test: a regression hiding *beneath* a win.

Rebalanced so B genuinely wins — it now retains both safety rules — while carrying one real,
narrower regression. **The fixture was wrong, not the implementation.**
