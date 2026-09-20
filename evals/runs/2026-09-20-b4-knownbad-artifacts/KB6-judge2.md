# Grade: `sharpen` route, case "remember me" checkbox

The output is four blocks of generic filler. It is not a sharpened prompt.

## Structural invariants

| Invariant | Mark | Reason |
|---|---|---|
| All 9 blocks present and filled | ❌ | Only GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA and OUT OF SCOPE appear. ROLE, OBJECTIVE, CONTEXT, REQUIREMENTS and OUTPUT FORMAT are absent, so 5 of 9 are missing. |
| PROHIBITIONS and OUT OF SCOPE distinct, PROHIBITIONS tied to the task | ❌ | PROHIBITIONS is untied boilerplate: "Do not write insecure code." / "Do not introduce bugs." / "Do not do anything harmful or unethical." / "Do not ignore best practices." None mentions login, sessions, cookies, tokens, or the auth flow. The rubric names this as the structural ❌: the block degrading into a checkbox. OUT OF SCOPE reads "Anything not related to this task." That names no deferred work, so it is vacuous. |
| No unfilled `<...>` placeholders | ✅ | No angle-bracket placeholders remain. This holds only because most of the prompt is missing. |
| One copy-pasteable block, with assumptions, push-back and open questions after it | ❌ | There is no prompt block, only four fragments. No assumptions, push-back or open questions section follows. |
| Each assumption has an explicit "Override with:" | ❌ | No assumptions exist, so no "Override with:" appears. |

## Quality dimensions

| Dimension | Mark | Reason |
|---|---|---|
| Push-back is real | ❌ | There is no push-back at all. A "remember me" checkbox invites real questions: session versus persistent token, cookie lifetime, storage mechanism, and behavior on shared devices. None is raised. |
| Named concreteness | ❌ | Vague phrasing throughout. "Follow existing code conventions." "Write clean, maintainable code." "The checkbox works and users stay logged in." No duration, cookie attributes, or default checkbox state is named. |
| Faithfulness (hard gate) | ⚠️ | No domain facts are invented. That is not credit for faithfulness, because there is almost no content to be unfaithful in. Nothing assumed is surfaced either. |
| Lens fit | ❌ | This is an auth and session change, so a security lens should show up in REQUIREMENTS: httpOnly/Secure/SameSite cookie flags, token rotation and expiry, server-side revocation. There is no REQUIREMENTS block and no lens content. |
| Would steer | ❌ | An agent following this would get no direction on persistence mechanism, expiry, UI placement, or tests. "Users stay logged in" is untestable as written. "Do not write insecure code" cannot steer because it names no concrete risk. |

## Verdict rule

Hard gates fail: the structural invariants are ❌ and faithfulness is only ⚠️. The rule says any ❌ means FAIL. Here there are ❌ marks on 4 of 5 structural invariants and on 4 of 5 quality dimensions.

VERDICT: FAIL