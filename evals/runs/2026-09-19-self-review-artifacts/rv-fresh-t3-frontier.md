# Verification: dashboard share links (migration + Express routes)

## Verdict
**VERIFIED WITH GAPS. BLOCKING: yes.** The block comes from a gap, not from a defect. I found nothing in the code shown that breaks the contract. What `GET /share/:token` actually sends back is produced by the `dashboard-public` template and whatever `app.locals`/`res.locals` it inherits, and neither was provided. That template is the only thing that decides whether clause 4 ("returns only title and config") holds, and whether the owner-controlled `config` becomes stored XSS on a public, unauthenticated page served from the app origin. Under this method, an unconfirmable gap on a security-critical axis blocks. The block clears once the template is confirmed (see Confirm-these #1).

## Independence
**INDEPENDENT.** I only saw the finished artifact and its contract. I did not write, draft, or revise it, and I saw none of the builder's reasoning.

## Observable evidence
- **Clause 1 (owner-only create, everyone else 404):** the `POST` lookup filters on `id = $1 AND org_id = $2 AND owner_id = $3` using `req.user.org_id` and `req.user.id`. A non-owner, a same-org non-owner, an other-org user, a missing ID and a malformed ID (`parseId` returns null) all get the same `404 {"error":"Not found"}`. The TTL `400` is only reachable after the ownership check passes, so it can't be used to probe which IDs exist. ✅
- **Clause 2 (unguessable, stored only as a hash):** `crypto.randomBytes(32)` gives 256 bits from Node's CSPRNG, which is above the 128-bit floor. Only `hashToken(token)` (SHA-256 hex) reaches the INSERT. The raw token appears only in the 201 response body. The column is `token_hash text NOT NULL UNIQUE`. ✅
- **Clause 3 (expiry, revocation, uniform 404):** the default TTL is `DEFAULT_TTL_DAYS = 30`, and every insert sets `expires_at = now() + make_interval(days => $4)`, so the create route never writes a NULL expiry. Revocation is `DELETE /api/dashboards/:id/share/:linkId`, owner- and org-scoped through the join, and it sets `revoked_at`. The public route handles unknown, expired and revoked tokens with one query and one branch (`if (!dash) return res.status(404).send('Not found')`). A malformed token gets the identical status and body. No state-dependent timing branch exists among the three. ✅
- **Clause 4 at the query level:** the SELECT returns only `d.title, d.config`. No `owner_id`, `org_id`, `created_by`, and no join to `users`. The render call passes only `{ title, config, readOnly: true }`. ✅ at the route. **Unconfirmed at the response** (see gap).
- **Clause 5 (read-only):** the public route is a GET that runs one SELECT. The router registers no other method on `/share/:token`. ✅
- **Injection:** every SQL value is a pg-promise positional parameter. `ttlDays` is validated as an integer in [1, 365] before use. `dashboardId` and `linkId` pass `Number.isSafeInteger` and `> 0`. ✅
- **IDOR on revoke:** the `UPDATE` requires `l.id`, `l.dashboard_id`, and dashboard ownership plus org together. A known `linkId` belonging to someone else's dashboard returns 404 and changes nothing. ✅
- **Token-in-URL hygiene:** `Referrer-Policy: no-referrer`, `Cache-Control: no-store` and `X-Robots-Tag: noindex, nofollow` are set before the `try`, so they also cover the 404. ✅

## Assessment (judgment, not demonstrated)
- The route layer is carefully built and survives every attack I could run against the code shown. Residual risk sits entirely in components outside the artifact: the view template, global locals, request logging, and `requireSession()`.
- `config` is owner-editable JSON (possibly editable by other org members too; the edit path isn't shown). Serialized carelessly into the public page, for example `<%- JSON.stringify(config) %>` inside a `<script>` without escaping `</script>` and `<!--`, it becomes stored XSS on a page any stranger can load. That page is on `PUBLIC_BASE_URL`, which is the app's own origin, so the script would run with the session of any logged-in user who opens the link. This is judgment about a likely failure shape, not a demonstrated defect.

## Defects (worst first)
- ⚠️ **LOW: the schema allows links that never expire, and the public route honors them.** `expires_at timestamptz` is nullable (commented `NULL = no expiry`), and the GET explicitly accepts `l.expires_at IS NULL`. No path shown writes NULL, so this is not reachable today. Any other writer (a backfill, an admin script, a later "permanent link" feature) produces an eternal link that the public route serves, contrary to "Links expire." To demonstrate: `INSERT ... (dashboard_id, token_hash, created_by)` with no `expires_at`, then GET the matching token and get 200 indefinitely. The contract invariant is left to caller discipline rather than enforced by the schema.
- ⚠️ **LOW: `PUBLIC_BASE_URL` is never checked.** If it's unset, `POST` still mints and stores a live token and returns `url: "undefined/share/<token>"`. The link is revocable by `id`, so nothing leaks, but the endpoint reports success on a broken link with no startup or request-time guard.
- ⚠️ **LOW: `expiresInDays` accepts loose input.** `Number()` accepts `"30"`, `true` (becomes 1) and `[5]` (becomes 5). All results stay inside [1, 365], so there's no contract impact. Noted, not gating.
- No ❌ defects found in the code shown.

## Claimed vs. actual
- "A leaked DB dump or backup does not hand out working links": **true of the DB.** It does not cover request logs. The raw token sits in the URL path, and any access log (morgan, a reverse proxy, a CDN, an APM) records it in plaintext. Whether that breaks "stored only as a hash" depends on logging config that isn't shown.
- "Unknown, expired, and revoked all return the same 404": **true** for status, body and code path at the route. Whether the 404 page differs from the app's generic 404 elsewhere is irrelevant to the contract.
- "Select ONLY what the viewer should see ... names and emails can't leak through this route": **true of the query.** Whether it holds for the response depends on the template and on inherited locals, which aren't shown.
- "Owner only, inside the owner's org": **true.** Note that an ownership transfer leaves existing links live and revocable only by the new owner. The contract is silent on this, so it isn't a breach.

## Confirm-these
1. **`dashboard-public` template and inherited locals (security-critical, this is the block).** Confirm that it renders only `title` and `config`, that any `config` embedded in a `<script>` or attribute is properly escaped, and that no layout or partial pulls owner, org, or other-dashboard data from `app.locals`/`res.locals` or from client-side calls to authenticated APIs. Also confirm how widget data is obtained on a read-only public page: if the page fetches data, that endpoint is part of the public surface and isn't in this artifact.
2. **Request logging.** Confirm that access logs redact `/share/:token` paths, or accept that raw tokens persist in logs.
3. **`requireSession()` behavior for unauthenticated callers.** The contract says "anyone else gets 404", and an unauthenticated caller most likely gets 401 or a redirect. It's uniform across IDs, so it gives no enumeration signal, but it differs from the letter of the contract. Confirm whether that's acceptable.
4. **Who can edit `dashboards.config` and `title`.** This determines who controls the content served publicly (feeds #1).

**The most damaging risk, stated plainly:** the route code holds, but the part that decides what a stranger actually receives, the public template, was not provided. If it embeds `config` unescaped, every share link is a stored-XSS vector on the app's origin.
