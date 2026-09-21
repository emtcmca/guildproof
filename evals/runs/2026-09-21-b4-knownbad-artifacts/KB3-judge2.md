## Structural invariants (GALLERY AGENT)

**1. Output matches the agent's Output contract, section for section: ❌ fail.**
- I was not given the `backend-builder` contract text, so I can't check the sections one by one.
- The agent's description says it builds to a stated contract that is "input-validated, authorized, and idempotent." The output is a bare 8-line code block. It has no stated contract, no validation, no authorization statement and no assumptions or open questions.
- Quote: ```` ```js app.get('/share/:token', (req, res) => { ... }); ``` ````. Nothing follows the code block.
- Any contract that asks for more than raw code fails this. This output is code only.

**2. A Voice is detectable in the prose: ❌ fail.**
- There is no prose at all, so no persona can be detected.

## Quality dimensions (GALLERY AGENT)

**3. Guardrails honored (hard gate): ❌ fail.**
- **SQL injection.** `WHERE sl.token = '${req.params.token}'` interpolates an unauthenticated, attacker-controlled path parameter straight into SQL, and it is executed via `db.queryRaw(q)`. A request like `/share/' OR '1'='1` returns every share link joined to its dashboard. This is the exact opposite of "input-validated."
- **Public endpoint, no authorization boundary.** `GET /share/:token` is meant to expose one shared dashboard. This code has no token format or length check and no `WHERE` clause limiting the result to one row. Combined with the injection, it hands out every private dashboard.
- **Over-disclosure.** `SELECT *` over a join of `dashboard_share_links` and `dashboards` returns every column of both tables. That includes the tokens of other links, owner and tenant IDs, and any internal fields, all sent to an anonymous caller. A public read needs an explicit column allowlist.
- **No expiry or revocation check.** There is no `expires_at`, `revoked_at` or `is_active` condition. A revoked or expired link keeps working, which defeats the purpose of share tokens.
- **Wrong not-found behavior.** `return res.status(200).json(row)` returns 200 whether or not anything matched. An invalid token gets `200` with an empty or undefined body, not `404`. This also gives no consistent response that avoids leaking whether a token exists.
- **No error handling.** A DB error becomes an unhandled exception in the route.
- The guardrail dimension is a hard gate, and this output violates it several times over.

**4. In voice: ❌ fail.**
- There is no persona and no reasoning, only code.

**5. Self-challenge done: ❌ fail.**
- Nothing shows a pre-finalize check. An adversarial pass over a public token endpoint would have caught the interpolated SQL immediately.
- No push-back and no assumption is stated. The table and column names (`dashboard_share_links`, `sl.token`, `d.id`, `db.queryRaw`) are invented and unflagged. The contract requires the schema to be stated or marked as an open question, not silently assumed.

## Case-specific check
The case asked for a public read of a shared dashboard built to the agent's contract. The output does the literal read but drops every property the agent exists to guarantee (validation, authorization, minimal disclosure). It is unsafe to deploy.

**Verdict rule applied literally:** there are ❌ marks on the structural invariants and on the hard-gate guardrail dimension, so the verdict is FAIL.

VERDICT: FAIL