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
- Produce the cleaned rewrite, then run the **second pass** and report it.

## Must not

- Introduce new tells in the rewrite (the second pass exists to catch exactly that).
- Flag every Tier 3 word on a single appearance — Tier 3 is a density signal.
- Leave the placeholders unflagged, or fill them with invented values.
