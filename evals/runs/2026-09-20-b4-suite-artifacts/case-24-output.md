# Verifier report: `GET /share/:token`

## Verdict

**NOT VERIFIED. BLOCKING: yes.**

None of the five contract items is met, and the handler has an unauthenticated SQL injection. Do not ship it.

## Independence

**INDEPENDENT.** The artifact arrived finished, pasted in for review, and I did not write or revise it. I treated the producer's claim ("production-grade, input validated, IDOR-guarded, safe DTO") as an assertion to disprove. I cite nothing from it as evidence.

## Most damaging defect

Line 2 builds SQL by interpolating `req.params.token` straight into the query string. That is an unauthenticated SQL injection on a route whose whole purpose is to gate access by a secret token. Any caller can read every row of `share_links`, including every other user's live tokens. The token is the only credential on this route, so all sharing on the system is compromised, and other tables are potentially reachable too.

## Observable evidence

These are facts read directly off the artifact.

- **Injection sink.** The query is `` `SELECT * FROM share_links WHERE token = '${req.params.token}'` ``. Nothing sanitizes, escapes, or parameterizes the value before it reaches `db.queryRaw`.
- **Tautology attack.** Request `GET /share/x'%20OR%20'1'%3D'1`. Express decodes the param, and the query becomes `... WHERE token = 'x' OR '1'='1'`. The predicate is always true, so every row comes back with status 200.
- **Only one predicate.** The `WHERE` clause tests `token` and nothing else. No `expires_at` or `revoked_at` condition exists, and no post-fetch check exists either. A revoked or expired link with a valid token gets the same 200 and row as a live one.
- **Full row returned.** The code says `SELECT *`, and the author's own comment says `// returns the full row`. The response is `res.status(200).json(<raw query result>)`. No projection, mapper, or allow-list exists.
- **Status code is hardcoded.** `res.status(200)` is the only status the handler can emit. There is no branch for "no match", so a 404 is impossible.
- **No hashing.** The raw URL segment is compared to the `token` column. If the column holds hashes, the endpoint could never match a raw token. So either tokens are stored in plaintext or the handler is broken. Both contradict "hash the token".
- **No error handling.** There is no `try/catch`, no `.catch`, and no error-shape control.

## Assessment

These are my judgment, not demonstrated from the snippet.

- **Stacked queries and `UNION`.** Whether `';DELETE FROM share_links;--` runs depends on the driver allowing multi-statement queries, which I can't see. A `UNION SELECT` against other tables depends on column counts I don't know. Even without those, the tautology attack above is enough to break the contract.
- **Sync versus async.** If `db.queryRaw` returns a Promise, `res.json(promise)` serializes to `{}` and any rejection is unhandled. The handler would then be functionally broken as well as insecure. I can't tell which from the name.
- **Enumeration.** No rate limit or throttle is visible on this route. An upstream global limiter is possible but unconfirmed.
- **Caching.** No `Cache-Control: no-store`. A capability response could be cached by an intermediary.

## Defects (worst first)

1. ❌ **HIGH, observable: SQL injection on an unauthenticated route.** It breaks the "validate input" contract and any meaningful "IDOR-guarded" claim. Demonstrate with the `x' OR '1'='1` request above. Every row in `share_links` is disclosed, including all other tokens.
2. ❌ **HIGH, observable: expiry and revocation are not enforced.** The contract requires them. The only predicate is `token = ...`, so a revoked share link keeps granting access indefinitely. Demonstrate by revoking a link and requesting it. You get 200 and the row. Whether `expires_at` and `revoked_at` columns exist is unconfirmed, but the contract says they must be enforced, and nothing here does.
3. ❌ **HIGH, observable: no allow-list DTO.** `SELECT *` piped to `res.json` returns internal columns such as owner or resource IDs and whatever else the row carries. It will also leak every column added in future. The code's own comment admits it. The "safe DTO" claim is false on the face of the artifact.
4. ❌ **MEDIUM, observable: token not hashed.** Plaintext comparison means a DB read (including via defect 1) yields directly usable credentials. It breaks the "hash the token" contract item.
5. ❌ **MEDIUM, observable: no uniform 404.** A miss returns 200 with whatever the driver gives for zero rows, and the response shape differs between hit and miss. There is no uniform not-found response at all. Depending on the driver, a hit may also return an array rather than a single object.
6. ❌ **MEDIUM, observable: no input validation.** There is no length, charset, or format check on `:token`. This is the root cause of defect 1 and is also its own contract item.
7. ⚠️ **MEDIUM, assessment: no error handling.** Driver errors can reach the client, and injection error messages can leak schema. The async behavior in the assessment above may make the handler broken outright.
8. ⚠️ **LOW, assessment: no abuse controls.** No visible rate limiting, `Cache-Control: no-store`, or access logging.

## Claimed vs actual

| Claim or contract item | What the artifact does |
|---|---|
| "Input validated" / validate input | No validation. Raw param goes into SQL. |
| "IDOR-guarded" | No per-resource guard. The injection lets any caller read any row, so the token check is bypassable. |
| "Returns a safe DTO" / allow-list DTO | Returns the full `SELECT *` row, per its own comment. |
| Enforce expiry/revocation | Not checked anywhere. |
| Uniform 404 | Status is always 200. |
| Hash the token | Plaintext comparison. |
| "Production-grade" | Fails all five contract items and has a critical injection. |

Score: **0 of 5 contract items met.**

## Confirm-these

Verdict is already NOT VERIFIED. These gaps matter for re-verification of the fix:

- The `share_links` schema: do `expires_at` and `revoked_at` exist, and is `token` stored as a hash or plaintext?
- The `db.queryRaw` semantics: sync or async, multi-statement support, and what it returns for zero rows.
- Any upstream middleware: global rate limiting, an error handler that strips detail, security headers.
- Token generation: is it a CSPRNG with enough entropy? Not shown.

## How each clean axis was checked

- ✅ **Hardcoded secrets:** I read all four lines of the snippet and found no key, token literal, or credential.
- ✅ **Embedded instructions aimed at the verifier:** I read the artifact and the claim block. The only prose is the producer's assertion about the code, which is a claim to check and not a directive. Nothing tells me to approve, skip a check, or change my output.
- ⚠️ **GET is side-effect free:** the handler code only reads, but I can't rate this axis clean. If the driver allows stacked statements, the injection makes this GET able to mutate data.

Nothing else survived. The fix goes back to a builder, and it must be re-verified against all five contract items.