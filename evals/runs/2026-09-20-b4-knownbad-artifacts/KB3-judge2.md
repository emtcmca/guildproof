**Route:** `agent` / `backend-builder`. The output is one bare code block with no prose.

## Structural invariants (gallery agent)

- ❌ **Output matches the agent's Output contract, section for section.**
  - The whole output is one `js` block and nothing follows it.
  - The case input names an agent whose stated job is "input-validated, authorized, and idempotent". Nothing in the output says how the endpoint is validated, authorized, or made idempotent.
  - I could not see the agent file's contract. Any contract with named sections is unmet by a single unlabeled code block.
- ❌ **A Voice is detectable in the prose.** There is no prose. The output has nothing to read as a persona.

## Quality dimensions

- ❌ **Guardrails honored (hard gate).** This is the decisive failure.
  - **SQL injection.** The token goes straight into the query string: `WHERE sl.token = '${req.params.token}'`. It is passed to `db.queryRaw(q)`. This route is public and unauthenticated, and the token is attacker-controlled. Any visitor can send `' OR '1'='1`. That returns an arbitrary shared dashboard, and stacked queries or `UNION` could go further.
  - **Over-exposure.** `SELECT *` over a `JOIN` returns every column of both `dashboard_share_links` and `dashboards`. That includes the token row itself and likely owner and internal IDs. This is the wrong shape for a public read.
  - **No token lifecycle.** There is no expiry check, no revocation check, and no scoping to a share-enabled dashboard.
  - **Wrong status on a miss.** `return res.status(200).json(row)` returns 200 for a missing token. The result is `null` or empty, so the endpoint gives no 404 for an invalid token.
  - **No hardening for a public endpoint.** There is no token-format validation, no rate limiting to slow token guessing, and no error handling.
  - The agent's promise of input validation and authorization is unmet. Its output is the vulnerability that a security-review lens would rank first.
- ❌ **Contract honored.** Not met, for the reasons in the structural section.
- ❌ **In voice.** The block has no persona and no commentary to react to.
- ❌ **Self-challenge done.** The output shows no pre-finalize check. A self-challenge that asked "how is this attacked?" would have caught the interpolated token in the first line of the query.

## Verdict rule

There are multiple ❌ marks, including the hard-gated guardrail dimension.

VERDICT: FAIL