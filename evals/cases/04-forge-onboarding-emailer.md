---
id: "04"
route: forge
command: /guildproof:forge-agent
expected-lenses: [editorial, skeptic]
tests: forge in a writing domain, voice specificity, faithfulness guardrail
---

## Input

```
/guildproof:forge-agent an assistant that writes customer onboarding emails in our brand voice
```

## Must

- Auto-pick the editorial lens and bake it into operating principles.
- Voice line is specific (a named editorial tone), and the body reads in that voice.
- Include a guardrail that the agent must not invent product facts, promises, or details not
  supplied — it writes to a brief, it doesn't make up the product.
- Define an output contract (e.g. subject + body + the facts it assumed/needs).

## Must not

- Hard-code one company's brand voice as if known; "brand voice" is an input to receive.
- Produce a one-off email instead of a reusable assistant.
