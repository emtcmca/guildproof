```
ROLE: Senior full-stack engineer with an application-security and accessibility eye. You are making a small, contained change to an authentication surface, so you treat it as a security change first and a UI change second.

OBJECTIVE: Add a "Remember me" checkbox to the existing login form. When checked, the user stays signed in across browser restarts for a fixed maximum period. When unchecked, login behaves exactly as it does today.

CONTEXT:
- Stack: [stack? framework, language, auth library or provider]. Do not assume one. Read the repo first.
- Before editing anything, find and report in 10 lines or fewer: (1) the login form component, (2) where and how the session is created (cookie session, JWT, provider-managed, other), (3) where session lifetime is currently set, (4) whether sessions can be revoked server-side (logout, password change).
- If session lifetime is controlled by an auth provider's or library's own config option, use that mechanism rather than hand-rolling a second one.

REQUIREMENTS:
Behavior
- The checkbox is unchecked by default. Its state is sent with the login request as a boolean.
- Checked: the session persists across browser restarts for at most [30 days, confirm]. Unchecked: current behavior, unchanged.
- The server decides the lifetime. The client flag is a request only. Parse it strictly (true only for boolean true or the exact string your framework's form encoding produces for a checked box). Missing, malformed, or unexpected values mean false.
- For a remembered session, set persistence (Max-Age/Expires or the library equivalent) only in that case. Keep every existing cookie attribute (HttpOnly, Secure, SameSite, path, domain) as it is today.
- Logout and password change must end a remembered session, using whatever revocation mechanism already exists. If sessions are stateless with no revocation path, STOP and report that instead of lengthening their lifetime.
- On a failed login, keep the checkbox state. Never repopulate the password.

Interface (a UI pass must include accessibility)
- Use a native checkbox input with a real associated label, and reuse the form's existing components and styles.
- Label text: "Remember me". Helper text, tied to the input with aria-describedby: "Stay signed in on this device. Don't use on a shared computer."
- Place it between the password field and the submit button. Tab order is email, password, checkbox, then the rest of the form in its existing order. Enter still submits from any field.
- Keyboard: Tab focuses it, Space toggles it, and the focus indicator is visible.
- Contrast: label and helper text at least 4.5:1, checkbox border and focus ring at least 3:1. Checked state must not rely on color alone.
- The click and touch target includes the label and is at least about 44px tall. Layout holds at narrow mobile widths.
- Cover the disabled state while the form is submitting and the state after a failed login.

GUARDRAILS (from red-team pass):
- A "remember me" flag that only changes something client-side is decoration. Prove the difference in the server's response (the session cookie's persistence), not in the UI.
- A long-lived session is a long-lived credential. Never put a session token or credential in localStorage, sessionStorage, or any script-readable place.
- Existing session fixation and rotation behavior on login must be identical for both checkbox states.
- If the app has sensitive actions (change email or password, billing, delete account) that currently rely on a fresh login, they must not silently become reachable through a 30-day session. Check whether a re-auth step exists and report what you find. Do not build one.
- If the app has privileged roles (admin, staff), report whether they should be excluded. Do not decide that unilaterally.

PROHIBITIONS (must NOT do):
- Don't invent identifiers, cookie names, config keys, endpoints, or file paths. Use what the repo actually contains, and flag anything you cannot find.
- Don't touch: password hashing or validation, MFA, OAuth/SSO flows, CSRF handling, rate limiting or lockout, password reset, or public API contracts, beyond the one added boolean on the login request.
- Don't add a database column or migration without stopping to ask first. If persistence needs one, describe why and wait.
- Don't add dependencies.
- Don't refactor, rename, or restyle anything outside the login form and the session-lifetime code path.
- Don't store or log the credentials, the session token, or the checkbox value alongside personal data.

SUCCESS CRITERIA:
- Login with the box unchecked: response session cookie has no persistent expiry (or the provider's non-remembered equivalent), same as before the change.
- Login with the box checked: the session cookie is persistent, and its expiry is at most [30 days] out.
- Requests sending "false", "0", "", an array, or omitting the field are all treated as unchecked. Each has a test.
- After logout, and after a password change, a previously remembered session no longer authenticates. Each has a test, or a written statement of why it cannot be tested.
- Keyboard-only walkthrough (Tab, Space, Enter) completes a login. Contrast and focus checks pass.
- The existing login tests pass unchanged, and `tsc --noEmit` / the project's type-check and lint pass. If the project is not TypeScript, run its equivalent.

OUTPUT FORMAT: First the 10-line findings report described under CONTEXT, then the implementation. Finish with: files changed (paths), one line per test added and what it proves, how to verify by hand (numbered steps a beginner could follow, with what a successful result looks like), and a list of anything you could not verify, marked UNVERIFIED.

OUT OF SCOPE: Prefilling the username or email; "trust this device" or skipping MFA; social login; a "sign out of all devices" or active-sessions page; redesigning the login form; changing how long non-remembered sessions last.
```

## Assumptions I made
- I assumed "remember me" means a persistent login (a longer-lived session), not prefilling the username. Override with: "it means username prefill only," and the whole security half of the prompt drops out.
- I assumed the checkbox is unchecked by default. Override with: "default checked."
- I assumed a 30-day maximum for remembered sessions. It's a policy number, so it is bracketed in the prompt. Override with: "use N days."
- I assumed the label "Remember me" plus one line of helper text warning against shared computers. Override with: "no helper text" or different wording.
- I assumed the box sits between the password field and the submit button.
- I assumed unchecked behavior must stay exactly as it is today, so I put nothing in scope for changing the current session length.
- I assumed a schema change is not pre-approved, so the prompt makes the agent stop and ask.

## Push-back worth hearing
- **This is a credential-lifetime decision with a checkbox on top.** The UI is about ten percent of the work. The rest is whether your sessions can be revoked and what a 30-day session can reach. If sessions are stateless tokens with no server-side revocation, a stolen remembered session survives a password change. Fix that first, or accept it knowingly.
- **Your auth library or provider may already do this.** Many expose session duration as one setting. If yours does, the right change is a config value plus the checkbox. Hand-rolled cookie logic would create a second session mechanism to maintain. The prompt tells the agent to look before building.

## Open questions (answer these, or run with `--deep`)
1. What is the stack and auth mechanism (framework, session cookies vs JWT vs a provider like Auth0 or Supabase)? This most changes what the agent builds, and I left it as `[stack?]` rather than guess.
2. Does the app have privileged roles or sensitive actions (billing, account deletion, admin) that should be excluded from long sessions, or should require re-entering the password?
3. Is 30 days right for your users, or is there a compliance or client requirement on session length?

Run `/guildproof:sharpen add a "remember me" checkbox to the login form --deep` for a one-question-at-a-time interview that resolves these before the prompt is finalized.