**Route: sharpen. The output is a fragment, not a sharpened prompt.**

## Structural invariants

- **All 9 blocks present and filled: ❌.** Only 4 of 9 appear: GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA and OUT OF SCOPE. ROLE, OBJECTIVE, CONTEXT, REQUIREMENTS and OUTPUT FORMAT are missing. The task itself, "add a 'remember me' checkbox to the login form", appears nowhere in the output.
- **PROHIBITIONS and OUT OF SCOPE distinct, PROHIBITIONS tied to the task: ❌.** PROHIBITIONS is generic boilerplate: "Do not write insecure code." "Do not introduce bugs." "Do not do anything harmful or unethical." "Do not ignore best practices." None of it is tied to a login form or a remember-me feature. It names no concrete forbidden action, such as changing the auth flow, weakening session handling or storing a raw password in a cookie. The rubric calls this a structural ❌. OUT OF SCOPE ("Anything not related to this task.") is also empty, and it doesn't say what work is deferred.
- **No unfilled `<...>` template slots: ✅.** No angle-bracket slots remain. This is the only structural point the output meets, and only because it contains almost nothing.
- **One copy-pasteable block, with assumptions, push-back and open questions after it: ❌.** There is no fenced block. There is no assumptions section, no push-back and no open questions.
- **Each assumption has "Override with:": ❌.** No assumptions are listed, so nothing carries an override line. The omission is the defect, because a login-form request leaves many facts open: the stack, the session mechanism and the token lifetime. A correct output would flag these as `[stack?]`-style gaps.

## Quality dimensions

- **Push-back is real: ❌.** There is no push-back. It never raises the main risk of persistent login (long-lived tokens, shared devices, cookie flags, the lifetime and rotation policy). "The checkbox works and users stay logged in" is a restatement of the request, not a surfaced weakness.
- **Named concreteness: ❌.** The output names nothing concrete. "Clean, maintainable code", "best practices" and "Follow existing code conventions" are the vague phrasing this dimension penalizes. No session duration, storage mechanism or cookie attribute is named.
- **Faithfulness (hard gate): ⚠️.** It invents no domain facts, so it is not a fabrication failure. But it also flags no gaps. "Follow existing code conventions" assumes conventions exist, and nothing marks the unknown stack or auth mechanism. It doesn't fail the gate, but it doesn't show the refuses-to-guess behavior either.
- **Lens fit: ❌.** No lens was picked and no checklist appears in REQUIREMENTS, because REQUIREMENTS is absent. This is an auth and session task that plainly calls for a security lens. Its only security content is "Do not write insecure code."
- **Would steer: ❌.** An agent given this text would not know what to build. It has no objective, no context, no stack and no output format. "Users stay logged in" leaves the mechanism, duration and security posture open.

## Verdict rule

The output has several ❌ marks, including structural ones (missing blocks, boilerplate PROHIBITIONS, no assumptions or push-back). Any ❌ means FAIL.

VERDICT: FAIL