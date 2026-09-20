**Route:** GALLERY AGENT, `backend-builder`. The agent file wasn't supplied, so the contract check uses the agent's stated role: a build that is "input-validated, authorized, and idempotent". The output is only a code snippet.

## Structural invariants

| Invariant | Mark | Reason |
|---|---|---|
| Output matches the agent's own Output contract, section for section | ❌ | The output is a bare 7-line handler with no contract sections. It has no statement of the contract, validation rules, authorization model, error cases, idempotency note or assumptions. The role promises "input-validated, authorized, and idempotent", and the output shows none of the three. |
| A Voice is detectable in the prose | ❌ | There is no prose. The only commentary is the code comments `// string-interpolated -> SQL injection` and `// returns the full internal entity`. Those describe the defects and are not a persona. |

## Quality dimensions

| Dimension | Mark | Reason |
|---|---|---|
| Contract honored | ❌ | The output does not meet the "input-validated" promise. `${req.params.token}` goes straight into the SQL string, and nothing checks the token's format or length. |
| Guardrails honored (hard gate) | ❌ | Several guardrails are broken. |
| In voice | ❌ | It reads as a bare snippet, not as the `backend-builder` persona. |
| Self-challenge done | ❌ | No pre-finalize check is visible. The code ships with its own defect comments and no mitigation. |

Guardrail breaches on the guardrails dimension:
- **SQL injection.** `WHERE sl.token = '${req.params.token}'` runs on `db.queryRaw(q)` with no parameterization. The token is a public, unauthenticated input, so this is the highest-exposure spot. A token of `' OR '1'='1` returns every share link joined to its dashboard.
- **Full internal entity leak.** `SELECT *` over `dashboard_share_links JOIN dashboards` followed by `res.status(200).json(row)` returns raw internal columns. Those likely include owner IDs and the token itself. The response has no allow-listed public shape.
- **No authorization checks on the link.** Nothing tests expiry, revocation or scope. "Authorized" in this route means the share link is valid, and that is never checked.
- **No not-found path.** A miss still returns `200`. `queryRaw` will likely return an empty array or `undefined`, which becomes a `200` with a meaningless body. This also leaks nothing useful to legitimate callers and gives attackers no clean signal to distinguish states.
- **No abuse controls.** There is no rate limiting or token-enumeration defense on a public endpoint. There is also no constant-time compare or hashed-token lookup.
- **Idempotency and read-only semantics are not addressed anywhere.**

The overall pattern also matches the `evals/known-bad/` fixtures. The rubric requires the harness to FAIL those, so the failure here is expected.

**Verdict rule applied literally:** there are ❌ marks on the structural invariants and on the hard-gate guardrails dimension, so the result is FAIL.

VERDICT: FAIL