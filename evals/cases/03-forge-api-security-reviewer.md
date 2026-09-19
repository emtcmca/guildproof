---
id: "03"
route: forge
command: /guildproof:forge-agent
expected-lenses: [api-design, security-reviewer, skeptic]
tests: forge durability, gallery seeding, voice + self-challenge + output contract
---

## Input

```
/guildproof:forge-agent an agent that reviews backend endpoints for security holes
```

## Must

- **Seed from the gallery**: `api-reviewer` / `security-review` are close matches — adapt one
  rather than building cold, and it should be evident (structure, lenses).
- Produce a durable system prompt: persona + Voice line, Objective, Operating principles,
  Inputs, Method (with a real self-challenge step), Constraints/guardrails, Output contract,
  When-unsure.
- Bake the api-design + security lenses in as standing behavior, not a one-time pass.

## Must not

- Be task-specific to one endpoint; it must generalize to every future review.
- Omit the Voice line or the self-challenge step.
