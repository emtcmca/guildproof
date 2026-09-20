## Structural invariants (SHARPEN)

**1. All 9 blocks present and filled: ❌**
Only four of nine blocks appear: GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA and OUT OF SCOPE. ROLE, OBJECTIVE, CONTEXT, REQUIREMENTS and OUTPUT FORMAT are missing entirely. The output starts at "GUARDRAILS:", so it is a fragment and not a sharpened prompt.

**2. PROHIBITIONS and OUT OF SCOPE distinct, not boilerplate: ❌**
- The rubric names generic PROHIBITIONS untied to the task as a structural ❌, and that is what this is.
- Quotes: "Do not write insecure code." / "Do not introduce bugs." / "Do not do anything harmful or unethical." / "Do not ignore best practices."
- None of these mentions login, sessions, cookies, tokens or persistence. Any task at all could carry the same list.
- OUT OF SCOPE reads "Anything not related to this task." That names no deferred work, so it degrades into a checkbox.

**3. No unfilled `<...>` placeholders: ✅**
No angle-bracket placeholders remain. This is vacuous, because the missing blocks were dropped rather than filled.

**4. One copy-pasteable block, with assumptions, push-back and open questions after it: ❌**
There is no ROLE-to-OUT-OF-SCOPE prompt block and nothing follows. There are no assumptions, no push-back section and no open questions.

**5. Each assumption has an explicit "Override with:": ❌**
No assumptions are stated, and "remember me" has real gaps to assume over: session length, cookie versus token, and the auth stack. The Override contract cannot be met when nothing is stated.

## Quality dimensions (SHARPEN)

**Push-back is real: ❌**
There is none. Nothing raises the weaknesses in the request, such as how long "remember" lasts, what state the checkbox should default to, or the security implications of a persistent credential.

**Named concreteness: ❌**
- "The checkbox works and users stay logged in." names no duration, no storage mechanism and no observable test.
- "Follow existing code conventions" and "Write clean, maintainable code" are the vague adjectives the rubric wants named explicitly.

**Faithfulness (hard gate): ✅**
- Nothing is invented, and no endpoints or stack details are asserted.
- This passes only because the output says almost nothing. It is not evidence of careful assumption-handling.

**Lens fit: ❌**
A persistent-login feature is an auth and security topic, so a security lens should have been picked. There is no REQUIREMENTS block, so no checklist appears. Nothing covers httpOnly or Secure cookies, token rotation, expiry, server-side revocation, or logout behavior. "Do not write insecure code" gestures at the topic with no substance.

**Would steer: ❌**
A competent agent given this could not tell what "stay logged in" means, for how long, or how to implement it. There is no role, objective, context or output format. The prohibitions add no constraint beyond what any agent already assumes.

## Verdict rule

There are multiple ❌ marks, including on the structural hard gates (9 blocks present, PROHIBITIONS distinct from OUT OF SCOPE). One ✅ (faithfulness) and one vacuous ✅ (no placeholders) do not offset them. Any ❌ means FAIL.

VERDICT: FAIL