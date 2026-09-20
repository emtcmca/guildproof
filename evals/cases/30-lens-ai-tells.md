---
id: "30"
route: lens
command: /guildproof:lens
expected-lenses: [ai-tells]
tests: ai-tells tiering, priority ordering, and the two-pass discipline
---

## Input

```
/guildproof:lens --lens ai-tells
```

Artifact under review (marketing copy):

```
In today's rapidly evolving landscape, [Company] is proud to unveil a game-changing platform
that empowers teams to seamlessly leverage cutting-edge AI. Our robust, comprehensive solution
delves into the intricate tapestry of your workflow, fostering a holistic approach that
underscores what truly matters. It's not just a tool — it's a testament to what's possible.

Whether you're a startup navigating the realm of scale, or an enterprise seeking to elevate
operational efficiency, our platform unlocks meaningful, impactful outcomes. Let's dive in and
embark on this journey together!

Ready to transform your workflow? [Insert CTA here]
```

## Must

- Report findings **worst-first by priority**: P0 the unfilled `[Company]` / `[Insert CTA here]`
  placeholders, then P1 tiered vocabulary, then P2 rhythm/structure.
- Tier the vocabulary correctly — Tier 1 always-flag (`leverage`, `delve`, `robust`, `seamless`,
  `cutting-edge`, `game-changing`, `foster`, `underscore`, `realm`, `tapestry`, `testament`,
  `landscape`, `navigate`, `elevate`, `unlock`, `embark`) vs Tier 2 clustered (`comprehensive`,
  `holistic`, `intricate`) vs Tier 3 density (`meaningful`, `impactful`).
- Catch the template phrases: "In today's rapidly evolving landscape," "It's not just X — it's
  Y," "Let's dive in," "Ready to transform…?"
- Quote each offending span rather than only naming the category.
- Give each finding its **proposed replacement**, inline. This case runs WITHOUT `--fix`, and
  `lenses/ai-tells.md:53-55` is explicit that the no-fix path is findings only: "**Do not emit a
  rewritten artifact** - the command's default contract is critique, not rewrite, and a lens may
  not override it." So a cleaned rewrite here is a CONTRACT VIOLATION, not a requirement.
  The rewrite-plus-second-pass expectation belongs to a `--fix` case; case 31 is that case.

## Must not

- **Emit a rewritten artifact.** No `--fix` was passed, so a rewrite breaks the lens's own rule
  (`lenses/ai-tells.md:55`). Proposed replacements per finding are correct; an assembled
  rewrite is not.
- Flag every Tier 3 word on a single appearance — Tier 3 is a density signal.
- Leave the placeholders unflagged, or fill them with invented values.

## Note on this case, 2026-09-20

The Must list used to require "Produce the cleaned rewrite" while the Input passes no `--fix`.
That contradicted `lenses/ai-tells.md:53-55`, and the 2026-09-20 B4 suite run failed this case
for obeying the lens rather than the case. The producer was right and the case was wrong. This
is the fifth instance in that run of the measuring instrument disagreeing with the shipped
contract, and the only one that lived in a case file rather than in `evals/rubric.md`.
