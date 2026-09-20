---
id: "28"
route: sharpen
command: /guildproof:sharpen
expected-lenses: [security-reviewer, ux-designer]
tests: prohibitions / negative-space coverage — the PROHIBITIONS block must be task-specific and distinct from OUT OF SCOPE
---

## Input

```
/guildproof:sharpen add a "remember me" checkbox to the login form
```

## Must

- Emit a **PROHIBITIONS** block, filled, distinct from OUT OF SCOPE.
- PROHIBITIONS names *actions the agent must not take*, tied to this task's blast radius —
  e.g. must not change the existing auth/session mechanism, must not alter token lifetime for
  non-remembered sessions, must not weaken logout, must not touch the password-reset flow.
- OUT OF SCOPE names *work not being done* (e.g. SSO, device management), not actions.
- Session/cookie security surfaces as a requirement or guardrail (persistent auth is the whole
  feature), and the stack stays flagged rather than assumed.

## Must not

- Collapse PROHIBITIONS into OUT OF SCOPE, or emit only one of the two.
- Fill PROHIBITIONS with generic boilerplate untied to the task ("don't write bad code,"
  "don't do anything harmful") — the block degrading into a checkbox is the regression this
  case exists to catch.
- Invent the auth library, session store, or token TTL.
