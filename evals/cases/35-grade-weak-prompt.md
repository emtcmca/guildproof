---
id: "35"
route: grade
command: /guildproof:lens --grade
tests: the GRADE route — scored verdict, coverage over the nine concerns, leverage-ranked fixes
---

## Input

```
/guildproof:lens --grade
```

Prompt under grade:

```
You are a helpful assistant for our support team. Answer customer questions accurately and
professionally. Be concise but thorough. Use good judgment and don't make mistakes. If you
don't know something, use your best guess.
```

## Must

- Lead with the **verdict** (FAIL — "use your best guess" instructs unverifiable assertion,
  tripping the **Grounded** hard gate) before any commentary.
- **State the rubric before the scores.**
- Mark all nine coverage concerns. At minimum: Role ⚠️ (generic "helpful assistant", no domain),
  Context ❌ (no product, no policy, no escalation path), Success criteria ❌ ("accurately",
  "professionally", "good judgment" are unmeasurable), Output format ❌, Prohibitions ❌,
  Out of scope ❌.
- Score all five quality dimensions with a quote each — including **Testable** ❌ and the
  "concise but thorough" contradiction under **Unambiguous**.
- End with 2–3 leverage-ranked fixes, each naming the dimension it lifts, plus a **Skip** line.
- Offer `/guildproof:sharpen` as the next step.

## Must not

- Emit a numeric score ("62/100") — the rubric is host-judged and doesn't support it. Report
  ✅/⚠️/❌ counts.
- Return lens-style findings instead of a scored verdict — that's `/lens`, a different route.
- Rewrite the prompt (grading is not fixing).
- Dock the prompt for not using guildproof's block headings — coverage, not conformance.
