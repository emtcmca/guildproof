## 1. Structural invariants (SHARPEN)

- ✅ **All 9 blocks present and filled.** ROLE, OBJECTIVE, CONTEXT, REQUIREMENTS, GUARDRAILS (labeled "from red-team pass"), PROHIBITIONS, SUCCESS CRITERIA, OUTPUT FORMAT and OUT OF SCOPE all appear with real content.
- ✅ **PROHIBITIONS and OUT OF SCOPE are distinct and tied to the task.**
  - PROHIBITIONS holds actions: "Don't add a database column or migration without stopping to ask first" and "Don't touch: password hashing or validation, MFA, OAuth/SSO flows, CSRF handling…".
  - OUT OF SCOPE holds work not being done: "Prefilling the username or email; 'trust this device'…; a 'sign out of all devices' or active-sessions page".
  - There is minor conceptual overlap on MFA and SSO, but the two blocks are not collapsed and the PROHIBITIONS are not boilerplate.
- ✅ **No unfilled `<...>` template slots.** `[stack? framework, language, auth library or provider]` and `[30 days, confirm]` are square-bracket gap flags, which the rubric scores as correct behavior.
- ✅ **One copy-pasteable block, with assumptions, push-back and open questions after it.**
- ❌ **Each assumption has an explicit "Override with:".** Four of the seven assumptions have one, and three do not:
  - "I assumed the box sits between the password field and the submit button." has no override.
  - "I assumed unchecked behavior must stay exactly as it is today, so I put nothing in scope for changing the current session length." has no override.
  - "I assumed a schema change is not pre-approved, so the prompt makes the agent stop and ask." has no override.

This is a hard-gate structural failure. The invariant says "each," and 3 of 7 miss it.

## 2. Quality dimensions

- ✅ **Push-back is real.** "This is a credential-lifetime decision with a checkbox on top… a stolen remembered session survives a password change." and "Your auth library or provider may already do this." are genuine weaknesses in the request, not flattery.
- ✅ **Named concreteness.**
  - Label text is exact: "Remember me".
  - Helper text is exact: "Stay signed in on this device. Don't use on a shared computer."
  - Contrast ratios are stated: 4.5:1 and 3:1.
  - Target size is stated: about 44px.
- ⚠️ **Faithfulness (hard gate).**
  - The stack, the 30-day TTL and the auth mechanism are all bracketed or hedged ("Do not assume one").
  - The prompt does assume a domain fact, though: "Tab order is email, password, checkbox". The form may use a username, and nothing in the request says it is an email field.
  - It also leans on a cookie-session framing ("the session cookie's persistence"), hedged only by "or the provider's non-remembered equivalent".
  - No ❌ here, since none of this is a fabricated identifier, library or TTL, but it is not a clean ✅.
- ✅ **Lens fit.** The security and accessibility lenses are auto-picked and show up in REQUIREMENTS and GUARDRAILS: session fixation, no token in localStorage, aria-describedby, keyboard behavior.
- ⚠️ **Would steer.** A competent agent would do the right thing, and the STOP conditions are good ("If sessions are stateless with no revocation path, STOP"). The prompt is very heavy for a "small, contained change", though. A findings report followed by an implementation, with many conditional branches, risks over-scoping the agent. That is a real but non-fatal concern.

## 3. This case's must list

- ✅ PROHIBITIONS block is emitted, filled, and distinct from OUT OF SCOPE.
- ✅ PROHIBITIONS is tied to the blast radius: auth and MFA/CSRF/reset/hashing surfaces, no migration, no new dependencies, no refactor outside the login path. Not changing lifetime for non-remembered sessions is covered by "Unchecked: current behavior, unchanged" in REQUIREMENTS. Logout is covered in REQUIREMENTS.
- ✅ OUT OF SCOPE names work not being done (username prefill, trust-this-device, SSO, active-sessions page).
- ✅ Session and cookie security appears as a requirement and guardrail ("A long-lived session is a long-lived credential. Never put a session token… in localStorage"). The stack stays flagged as `[stack?]`.

## 4. This case's must-not list

- ✅ PROHIBITIONS is not collapsed into OUT OF SCOPE, and both are emitted.
- ✅ PROHIBITIONS is not generic boilerplate.
- ✅ No auth library, session store or TTL is invented. The 30 days is bracketed with "confirm".

## Verdict

The output is strong on every case-specific criterion and would probably score WEAK or PASS on quality alone. It still fails a hard structural invariant, because three of seven assumptions carry no "Override with:". Under the rubric's rule, any ❌ on a structural invariant fails the case.

VERDICT: FAIL