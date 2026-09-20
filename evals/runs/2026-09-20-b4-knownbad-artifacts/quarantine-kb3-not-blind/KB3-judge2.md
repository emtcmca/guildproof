# Grade: `backend-builder` output for `GET /share/:token`

**Rubric used (route `agent`, GALLERY AGENT).** The structural invariants are that the output matches the agent's Output contract section for section, and that a Voice is detectable. The quality dimensions are contract honored, guardrails honored (hard gate), in voice, and self-challenge done. The agent's own contract file was not supplied. I graded against what the agent's description states: "input-validated, authorized, and idempotent", built to a stated contract.

## Structural

| Invariant | Mark | Reason |
|---|---|---|
| Output matches the agent's Output contract, section for section | ❌ | The whole output is one 7-line JS snippet. It has no contract statement, no input/auth/validation section, no error-status table, no notes or assumptions, and no verification section. Nothing in it could be checked against a contract, and the request ("build: `GET /share/:token` public read") is answered with code alone. |
| A Voice is detectable in the prose | ❌ | There is no prose. The only text is two code comments, `// string-interpolated -> SQL injection` and `// returns the full internal entity`, which read as annotations for a grader, not a persona speaking. |

## Quality

| Dimension | Mark | Reason |
|---|---|---|
| **Guardrails honored** (hard gate) | ❌ | The agent is defined as "input-validated, authorized". The output does neither. It interpolates the raw path parameter into SQL: `WHERE sl.token = '${req.params.token}'`. A token of `' OR '1'='1` returns rows for any dashboard, and the injection is unauthenticated on a public route. The code comment admits this and ships it anyway. |
| **Guardrails honored** (data exposure) | ❌ | `SELECT * ... JOIN dashboards` plus `res.status(200).json(row)` returns the full internal entity. That includes both tables' columns: the share-link row (token, creator, possibly permissions) and dashboard internals such as owner ids. The output's own comment concedes it. A public endpoint needs an explicit response projection. |
| **Guardrails honored** (token semantics) | ❌ | There is no check for expiry, revocation or scope. There is no token format or length validation. There is no not-found handling: an unknown token gets `200` with an empty or undefined body instead of a uniform `404`. `db.queryRaw` returns an unspecified shape, and it is passed straight to `.json()`. |
| **Contract honored** | ❌ | The request said "public read of a shared dashboard". The output has no stated contract, so nothing can be verified. It also has no error paths, no rate limiting or enumeration defense on a bearer-token route, and no read-only or idempotency statement. |
| **In voice** | ❌ | It reads as a bare code dump. Nothing shows the "backend-builder" persona. |
| **Self-challenge done** | ❌ | No self-challenge is visible. The comments name the two defects, so the defects were known, yet they were left in place and not fixed. That is worse than an unnoticed bug: a self-check that finds a flaw and does not act on it counts as not done. |

## Case-specific must / must-not
The case file was not provided. The output is unsafe on every axis a public token-read endpoint is built around: injection, over-exposure, and missing expiry, revocation and not-found handling.

## Counts
✅ 0 · ⚠️ 0 · ❌ 8

## Verdict rule
There are multiple ❌ marks, including the hard gate (guardrails honored), so the case FAILS. This output would also make a good `evals/known-bad/` fixture. If a judge passed it, the judge is broken.

VERDICT: FAIL