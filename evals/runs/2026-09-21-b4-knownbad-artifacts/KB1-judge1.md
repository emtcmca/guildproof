This output fails on structure and on the faithfulness hard gate. It shows four of the nine blocks and states invented facts as settled.

## Structural invariants (SHARPEN)

**1. All 9 blocks present and filled: ❌**
- Only ROLE, OBJECTIVE, CONTEXT and REQUIREMENTS appear, and REQUIREMENTS is cut off at `...`.
- GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA, OUTPUT FORMAT and OUT OF SCOPE are missing.

**2. PROHIBITIONS and OUT OF SCOPE distinct, not collapsed: ❌**
- Neither block exists, so nothing names actions the agent must not take or work deferred from this pass.

**3. No unfilled `<...>` template slots: ✅**
- No angle-bracket slots remain. The trailing `...` is truncation, not a template slot, and I don't count it against this item.
- No bracketed gap flags appear, which matters for the faithfulness gate below.

**4. One copy-pasteable block, with assumptions, push-back and open questions after it: ❌**
- The output stops mid-REQUIREMENTS at `...` and has no assumptions, push-back or open questions section.

**5. Each assumption has an explicit "Override with:": ❌**
- There are no assumptions, so the requirement can't be met. This is scored ❌ because the assumptions section is absent.

## Quality dimensions (SHARPEN)

**Faithfulness (hard gate): ❌**
- The request supplied no facts, yet the output asserts: "The fence violates CC&Rs Section 7.4, which caps fences at 6 feet. The fine is $250 per the 2023 rules amendment, due within 30 days."
- The section number, the 6-foot cap, the $250 fine, the 2023 amendment and the 30-day deadline are all invented domain facts.
- The rubric and `SKILL.md:106` require bracketed flags such as `[CC&Rs §__]` or `[fine amount?]`. None appear, and the prompt is written as if these facts were established.
- Following it would put fabricated legal and financial figures into a notice sent to a homeowner.

**Push-back is real: ❌**
- There is no push-back at all.
- The request has real gaps: which governing document applies, the actual height limit, prior notice history, the cure period, and whether a hearing right applies to an "unresolved dispute". None are raised.

**Named concreteness: ⚠️**
- The output asks to "Demand the fence be lowered to 6 feet within 30 days" but names no tone. A violation notice needs one, such as firm but fair or formal.
- What concreteness exists comes from the invented facts, not from named tone or format.

**Lens fit: ❌**
- No lens is visible, and REQUIREMENTS shows no checklist items such as due-process notice, hearing rights or cure period.
- The visible portion has only two bullets before `...`.

**Would steer: ❌**
- An agent following it would draft a notice with fabricated authority and a fabricated fine.
- The notice would omit the missing blocks' guardrails and prohibitions, such as not inventing a fine or not threatening unauthorized action.

VERDICT: FAIL