---
id: "18"
route: orchestration
status: active
tests: Step 0 gate — a single-domain request must NOT orchestrate
---

## Input

```
/guildproof:orchestrate rewrite this paragraph to sound warmer and less corporate
```

## Must

- **Decline to orchestrate.** Step 0 recognizes this is single-domain (copy editing) and falls
  back — routes to `copy-rewrite` (or `/guildproof:sharpen`), with a one-line reason.
- Spend zero fan-out: no decomposition, no subagents.

## Must not

- Decompose a one-domain task into slices or spawn subagents (orchestration overkill).
- Silently run the full pipeline when a single agent is the right tool.
