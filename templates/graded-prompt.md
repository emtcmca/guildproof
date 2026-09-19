# Graded Prompt — output skeleton

> The engine fills this in for the **GRADE** route. Lead with the verdict — the user asked
> for a measurement, so the measurement comes first, not a preamble.

---

## Verdict

**<PASS | WEAK | FAIL>** — <n> ✅ · <n> ⚠️ · <n> ❌ across coverage + quality.
<One line: the single thing most responsible for that verdict.>

<If a hard gate failed, say so here in its own line: **Hard gate failed: Grounded** — and name
what the prompt asserts that cannot be verified.>

## Rubric used

<Name it. If the user supplied `--rubric`, say "supplied by you". If it's the default, say so
and list the dimensions, so the user can reject the rubric before trusting the scores.>

## Coverage — the nine concerns

| Concern | | Evidence |
|---|---|---|
| Role | ✅ | "<quote from the prompt>" |
| Objective | ⚠️ | <what's partial> |
| Context | ❌ | <what's missing that the agent cannot infer> |
| Requirements | | |
| Guardrails | | |
| Prohibitions | | |
| Success criteria | | |
| Output format | | |
| Out of scope | | |

<Coverage is scored on whether the concern is *resolved*, not whether the prompt uses these
headings. A concern marked `n/a` carries a reason.>

## Quality

- **Unambiguous** ✅/⚠️/❌ — <reason, quoting the line reacted to>
- **Testable** — <reason>
- **Bounded** — <reason>
- **Grounded** *(hard gate)* — <reason>
- **Would steer** — <reason>

## Top fixes

1. **<the change>** — lifts *<dimension>*. <Why this one first.>
2. **<the change>** — lifts *<dimension>*.
3. **<the change>** — lifts *<dimension>*.

**Skip:** <the nits deliberately not worth fixing, so the list stays honest about leverage.>

## Next

- `/guildproof:sharpen <the same request>` — rebuild it with the gaps filled.
- `/guildproof:lens <revised> --grade --against <original>` — confirm the revision actually scored
  better and regressed nothing.

---

## Comparison mode (`--against`) — replaces Coverage + Quality above

## Verdict

**<A | B> is stronger** — <one line on why>.

| Dimension | A | B | Δ |
|---|---|---|---|
| Role | ✅ | ✅ | — |
| Objective | ⚠️ | ✅ | **improved** |
| Bounded | ✅ | ⚠️ | **regressed** |

**Regressions:** <list every dimension that got worse, even if B wins overall. This is the
reason to measure at all, and it is exactly what a one-shot rewrite hides.>

**Attribution:** <If the two versions differ in more than one respect, say so — the ranking
holds, but the improvement cannot be credited to a single change.>
