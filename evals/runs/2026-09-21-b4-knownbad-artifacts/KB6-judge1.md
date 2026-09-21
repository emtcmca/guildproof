**Route: sharpen. Judge: independent, given only the input, output and rubric.**

## Structural invariants

**1. All 9 blocks present and filled: ❌**
Only 4 of the 9 blocks appear: GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA and OUT OF SCOPE. ROLE, OBJECTIVE, CONTEXT, REQUIREMENTS and OUTPUT FORMAT are absent. The output opens directly with `GUARDRAILS:`. The blocks that do appear are barely filled. `SUCCESS CRITERIA: The checkbox works and users stay logged in.` is a single vague sentence.

**2. PROHIBITIONS and OUT OF SCOPE distinct, not boilerplate: ❌**
The two blocks are technically separate, but PROHIBITIONS is exactly the generic boilerplate the rubric names as a structural fail:
- "Do not write insecure code."
- "Do not introduce bugs."
- "Do not do anything harmful or unethical."
- "Do not ignore best practices."

None of these is tied to the task. A task-specific prohibition would be "must not store the password or a raw credential in a cookie/localStorage" or "must not change the existing session-expiry behavior when the box is unchecked." OUT OF SCOPE is `Anything not related to this task.`, which is also empty. It names no work that is being deferred this pass, such as "password reset" or "SSO login".

**3. No unfilled `<...>` template slots: ✅**
No angle-bracket slots remain in what was returned. This is a low bar here, because most of the template is missing entirely.

**4. One copy-pasteable block, with assumptions, push-back and open questions after it: ❌**
There is no fenced prompt block. There are no assumptions, no push-back section and no open questions after it.

**5. Each assumption has "Override with:": ❌**
There are no assumptions, so there is nothing that carries an override line. The route's required section is missing.

## Quality dimensions

**Push-back is real: ❌**
The output raises no weakness in the request. It never questions what "remember me" should mean here: persistent session cookie or long-lived refresh token, duration, or behavior on shared devices. Nothing in it reacts to the request at all.

**Named concreteness: ❌**
The output is all vague adjectives and no named specifics: "Follow existing code conventions", "Write clean, maintainable code", "The checkbox works and users stay logged in". It names no stack, duration, cookie attributes, label text or default state.

**Faithfulness (hard gate): ✅**
The output invents no domain facts. It also fails to flag any gap, such as `[stack?]` or `[session mechanism?]`, which `SKILL.md:106` requires for missing facts. The absence of invention comes from the absence of content. It is not the refuses-to-guess behavior working.

**Lens fit: ❌**
No lens checklist appears anywhere. A login and session feature should have pulled in a security lens, covering cookie flags, token expiry and revocation, and CSRF. `Do not write insecure code.` is the only trace of one, and it is a slogan.

**Would steer: ❌**
A competent agent given this text would learn nothing about what to build. It gets no role, no objective, no context and no requirements. It gets no stack and no persistence mechanism. The one statement about behavior is "users stay logged in", which is ambiguous. The output does not steer the task.

## Verdict rule

There are multiple ❌ marks, on structural invariants and on quality dimensions. The rubric says any ❌ makes the case FAIL.

VERDICT: FAIL