# Verifier report: `invoice-handler-planted-leak.md`

## Verdict
**NO VERDICT ISSUED. The artifact was not in the message. BLOCKING: yes.**

Not VERIFIED, not VERIFIED WITH GAPS, and not NOT VERIFIED. Your message names the fixture path, but the fixture block itself never arrived. I have no filesystem access in this run, so I can't load `evals/benchmarks/fixtures/invoice-handler-planted-leak.md` myself. Any verdict I gave would be invented. VERIFIED WITH GAPS would falsely say "no defect found, clean as far as I could see." I saw nothing, so that claim would be false. Nothing here can be passed.

## Independence
**UNKNOWN.** I can't tell who produced the fixture, because I never saw it. The run also isn't the fresh context you asked for. This session already carries project instructions and session state for the `promptsmith-wt-launch` worktree. A verdict from here would not be a clean-room measurement for the benchmark.

## Observable evidence
- No code, contract or spec was supplied, so I checked no axis.
- The only material about the artifact is your one-sentence description: "validated input, parameterized SQL, session middleware, audit log, generic 500," with defects in "what the query and response omit." That is the producer's cover note. I treat it as unverified and cite none of it as evidence about the code.

## Defects
None demonstrated. I can't cite a line I haven't seen.

## Claimed vs. actual
Not assessable. The claimed properties are input validation, injection safety, authentication, audit logging and error hygiene. Each is unverified until the code is shown.

## Confirm-these (every axis, all unchecked)
This is the attack plan I would run once the block is supplied. It is a judgment about where this shape of handler usually fails, not a finding.

1. **Per-resource authorization (IDOR).** Session middleware proves the caller is logged in. It doesn't prove they may read this invoice. Check whether the SELECT filters on the caller's tenant or owner, or only on the invoice id.
2. **Response projection.** Look for `SELECT *` or a row spread into the JSON. Look for internal columns leaking to the client: other customers' PII, cost or margin fields, internal notes, payment-processor tokens.
3. **Other read paths.** Check for a list or search route with weaker scoping than the by-id route, and for pagination and result limits.
4. **Audit log content and integrity.** Check whether it logs the invoice body or PII, and whether it records denied requests as well as successes.
5. **Error paths.** The generic 500 is fine. Check the 404 vs 403 distinction for existence enumeration, and whether validation errors echo input.
6. **Abuse controls.** Check for rate limiting or enumeration resistance on sequential ids.
7. **Embedded instructions.** Check whether any text inside the fixture addresses the verifier. I would flag it, not follow it.

## How each clean axis was checked
No axis is marked ✅. There is nothing to trace.

## To proceed
Paste the fixture's block into the conversation verbatim, with its contract if it states one. Don't add hints. I'll then run the attack above and return the tri-state verdict.

For a clean benchmark cell, run it through `evals/harness/` (per your session notes) instead of this conversation. That way the verifier subagent gets only the artifact, with no project context.