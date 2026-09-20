## Verdict

**FAIL**: 0 ✅ · 6 ⚠️ · 8 ❌ across coverage and quality.
The prompt tells the agent to guess when it doesn't know, which contradicts its own "accurately" and "don't make mistakes."

**Hard gate failed: Grounded.** "If you don't know something, use your best guess" instructs the agent to state unverifiable answers to customers. Nothing says to flag a guess as uncertain or hand off to a human. The prompt also supplies no product, policy, or knowledge source, so the agent will be guessing on most company-specific questions.

## Rubric used

The default rubric, not one you supplied. It has two parts:
- **Coverage:** the nine concerns of Role, Objective, Context, Requirements, Guardrails, Prohibitions, Success criteria, Output format, and Out of scope.
- **Quality:** Unambiguous, Testable, Bounded, Grounded (hard gate), and Would steer.

Coverage is scored on whether a concern is resolved, not on whether the prompt uses any particular headings. I defaulted to ⚠️ when uncertain, so ✅ has to be earned. This is a single-prompt grade, so no `--against` comparison was run.

## Coverage: the nine concerns

| Concern | | Evidence |
|---|---|---|
| Role | ⚠️ | "a helpful assistant for our support team": generic. It doesn't say whether the agent talks to customers or assists support staff. |
| Objective | ⚠️ | "Answer customer questions accurately and professionally": this names an activity, not a finished outcome. It doesn't say whether "done" means resolved, escalated, or ticket-ready. |
| Context | ❌ | Nothing supplied: no company, product, policies, knowledge source, or escalation path. All of it is something the agent can't infer. |
| Requirements | ⚠️ | "accurately and professionally", "concise but thorough": stated, but the adjectives are unmeasurable and the last two pull against each other. |
| Guardrails | ❌ | Nothing on what to be careful with: billing, refunds, account access, personal data, angry customers. The one uncertainty instruction points the wrong way. |
| Prohibitions | ❌ | No action is forbidden. "don't make mistakes" is a wish, not a prohibited action. |
| Success criteria | ❌ | None stated. |
| Output format | ⚠️ | "Be concise but thorough" covers length only. There's no shape, channel, structure, or handoff format. |
| Out of scope | ❌ | Nothing excluded, so the agent is implicitly licensed to answer anything a customer asks. |

## Quality

- **Unambiguous** ⚠️: "concise but thorough" lets two competent readers write a 2-line and a 10-line reply. "for our support team" leaves the audience unclear.
- **Testable** ❌: "professionally" and "don't make mistakes" can't be checked. There's no checkable pass condition anywhere in the prompt.
- **Bounded** ❌: the only limit is "don't make mistakes." Nothing says what not to do, which is where a support agent fails most: promising refunds, quoting policy, or confirming account details.
- **Grounded** *(hard gate)* ❌: "use your best guess" directs the agent to assert unverified answers. This directly contradicts "accurately" and "don't make mistakes," and there's no rule for choosing between them.
- **Would steer** ⚠️: it would probably produce polite, generic support tone. On the company-specific questions that are most of the job, it depends on knowledge the prompt never provides.

## Top fixes

1. **Replace "use your best guess" with a hard rule on uncertainty.** For example: answer only from the supplied sources; if the answer isn't there, say so plainly and hand off to a human with a summary; never guess on policy, pricing, refunds, dates, or account status. This lifts *Grounded* (the gate) and *Bounded*. It comes first because it is the only ❌ that turns a mediocre prompt into an unsafe one.
2. **Supply the context and say who the reader is.** Add the company and product, whether replies go to customers or to staff, the knowledge source or policy text, and the escalation route. Use bracketed placeholders (`[refund policy]`, `[escalation contact]`), not invented details. This lifts *Context*, *Role*, and *Would steer*. Fix 1 only works once this exists. Otherwise every answer becomes "I don't know."
3. **Swap the adjectives for checkable rules.** Add a short prohibitions list: no promising credits or timelines not in policy, no legal or medical claims, no asking for passwords or full card numbers. Define done as "answered from a cited source, or escalated with a summary." This lifts *Testable*, *Bounded*, *Prohibitions*, and *Success criteria*.

**Skip:** rewording the "helpful assistant" opener, and settling "concise but thorough" now. Once the output format is defined, the length question mostly resolves itself.

## Next

- `/guildproof:sharpen` with the same request rebuilds it with the gaps filled and the assumptions listed.
- `/guildproof:lens <revised prompt> --grade --against <original>` confirms the revision scored better and regressed nothing.