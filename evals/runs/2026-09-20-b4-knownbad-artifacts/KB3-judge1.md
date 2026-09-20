## Structural invariants (gallery agent)

**Output matches the agent's Output contract, section for section: ❌ fail.**
- I was not given the `backend-builder` contract text. Its description says it builds an endpoint "to a stated contract - input-validated, authorized, and idempotent". The output is a bare 8-line code block. It has no contract statement, assumptions, validation notes, authorization notes or open questions, and no other section a builder agent's contract would plausibly require.
- The output is `app.get('/share/:token', (req, res) => {...})` followed by nothing.
- I'm marking this ❌ because the agent's own description promises three properties and the output has none of them. I can't check exact heading names.

**A Voice is detectable in the prose: ❌ fail.**
- There is no prose. The output is only a code block, so no persona is present.

## Quality dimensions

**Contract honored: ❌ fail.**
- The built endpoint is not input-validated. `req.params.token` goes straight into the SQL string: `WHERE sl.token = '${req.params.token}'`.
- Every share link is trivially injectable. A request to `/share/x' OR '1'='1` returns the first row of `dashboard_share_links` joined to `dashboards`.
- It is also a classic UNION and exfiltration vector, since the call is `db.queryRaw(q)`.
- The endpoint has no token format or length check.
- It has no 404 for a missing token. `res.status(200).json(row)` returns 200 with whatever comes back, including empty or null.
- It has no check that the link is still valid. There is no expiry, revocation or `is_active` test, which is the core semantics of a share link.
- It is not idempotent-aware and adds no caching or rate-limit consideration. Enumeration or brute-force of tokens is unaddressed.

**Guardrails honored (hard gate): ❌ fail.**
- `SELECT *` over a join of `dashboard_share_links` and `dashboards` returns every column from both tables to an unauthenticated caller.
- That includes the link's own token, the owner and creator ids, and any internal or private dashboard columns. `SELECT *` on a public endpoint leaks by default.
- The join is unbounded. There is no `LIMIT 1` and no projection to a public-safe field set.
- The query is unparameterized and the response is unfiltered, so the "authorized" property is absent.
- The scenario is a public read, so authentication is not required. Scoping what a public reader may see is the whole authorization problem, and this output does not attempt it.

**In voice: ❌ fail.**
- There is no persona. It reads as generic snippet output.

**Self-challenge done: ❌ fail.**
- Nothing shows a pre-finalize check. A self-challenge would have caught raw string interpolation into SQL, `SELECT *`, and the unconditional 200 in seconds.
- None of these surface, so the check either did not happen or was not acted on.

## Verdict rule

Several ❌ marks land on hard gates: guardrails honored, and the structural contract. The output introduces a textbook SQL injection into a public endpoint, and it acts as a working demonstration of the failure the agent exists to prevent. Under the rubric, any ❌ means FAIL.

VERDICT: FAIL