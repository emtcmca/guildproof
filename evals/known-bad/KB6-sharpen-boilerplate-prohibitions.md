---
id: KB6
route: sharpen
expect: FAIL (PROHIBITIONS present but generic — the block degraded into a checkbox)
plants: a sharpen output whose PROHIBITIONS block is boilerplate disconnected from the task
---

## Input

```
/guildproof:sharpen add a "remember me" checkbox to the login form
```

## Bad output (must FAIL — excerpt)

```
GUARDRAILS:
- Follow existing code conventions.
- Write clean, maintainable code.

PROHIBITIONS (must NOT do — negative space):
- Do not write insecure code.
- Do not introduce bugs.
- Do not do anything harmful or unethical.
- Do not ignore best practices.

SUCCESS CRITERIA: The checkbox works and users stay logged in.

OUT OF SCOPE: Anything not related to this task.
```

## Why it must FAIL

The block is **present and structurally valid**, which is exactly what makes this fixture
necessary — a structural pass counting nine blocks scores this ✅. It fails on substance.

1. **The prohibitions are not task-specific.** "Don't write insecure code" applies to every
   prompt ever written. The point of negative space is to name *this* task's blast radius: must
   not change the existing session/token mechanism, must not extend token lifetime for
   non-remembered sessions, must not weaken logout, must not touch password reset. None appear —
   and a persistent-auth feature is precisely where an unstated boundary causes damage.
2. **It reads as a safety disclaimer, not a scope boundary.** "Nothing harmful or unethical" is
   the intent gate's job, not the prohibitions block's.
3. **OUT OF SCOPE is equally empty.** "Anything not related to this task" is a tautology; it
   names no feature (SSO, device management, session listing) actually being deferred.
4. **Success criteria are unmeasurable** — "the checkbox works" is not checkable.

A judge that returns PASS here has confirmed the structural check alone can be satisfied by
boilerplate, which is how a real feature decays into a template slot that is always filled and
never useful.
