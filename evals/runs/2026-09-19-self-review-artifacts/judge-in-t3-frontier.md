=== REVIEW A ===
# Verification: dashboard share links (migration + Express routes)

## Verdict
**VERIFIED WITH GAPS. BLOCKING: yes.** The block comes from a gap, not from a defect. I found nothing in the code shown that breaks the contract. What `GET /share/:token` actually sends back is produced by the `dashboard-public` template and whatever `app.locals`/`res.locals` it inherits, and neither was provided. That template is the only thing that decides whether clause 4 ("returns only title and config") holds, and whether the owner-controlled `config` becomes stored XSS on a public, unauthenticated page served from the app origin. Under this method, an unconfirmable gap on a security-critical axis blocks. The block clears once the template is confirmed (see Confirm-these #1).


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

=== REVIEW B ===
# Review: dashboard share links (Express + pg-promise)

**Verdict:** VERIFIED WITH GAPS. **BLOCKING: yes.**
Reading the code, I found nothing that breaks any of the five contract clauses. Two checks I couldn't make bear directly on clauses 2 and 4, and both are security-critical, so this should not merge until they're confirmed.


Nothing was run: no tests, no build, no database. Everything below comes from reading the code.

## Observable evidence (read from the code)

- **Clause 1: owner-only creation, 404 for anyone else.** [CLEAN] The POST route queries `WHERE id = $1 AND org_id = $2 AND owner_id = $3`, using `req.user.org_id` and `req.user.id`. No matching row returns 404. A non-numeric, zero or negative `:id` returns 404 through `parseId`. The body check (the 400) runs only after the owner check passes, so a non-owner can't get a 400 where a 404 is required. DELETE puts the same owner and org condition in its `UPDATE ... FROM dashboards` join and returns 404 when `rowCount` is 0.
- **Clause 2: tokens are unguessable and stored hashed.** [CLEAN in the database] `crypto.randomBytes(32)` gives 256 bits from a CSPRNG. The INSERT writes only `hashToken(token)` (sha256). The raw token appears only in the 201 response body.
- **Clause 3: expiry, revocation, one 404.** [CLEAN in the route code] Every INSERT sets `expires_at = now() + make_interval(days => ttlDays)`: 30 days by default, 365 at most. DELETE sets `revoked_at`. GET runs one query that filters on `revoked_at IS NULL` and on expiry, so unknown, expired and revoked tokens all reach the same `res.status(404).send('Not found')`. The response headers are set before that branch, so they match too. A malformed token gets the same 404 without a query, and it only tells an attacker the format is wrong, which they already know.
- **Clause 4: GET returns only title and config.** [CLEAN in the query] The SELECT reads only `d.title, d.config`. It doesn't join `users` and doesn't read `owner_id` or `org_id`. The render call passes only `title`, `config` and `readOnly`.
- **Clause 5: the public route is read-only.** [CLEAN] The GET handler runs one SELECT. There's no INSERT, UPDATE or DELETE, and no view counter. Express also answers HEAD on this route, which is read-only as well.
- **SQL injection.** [CLEAN] Every value goes through pg-promise `$n` formatting. No SQL is built by joining strings.

## Defects (worst first)

1. [WEAK] MEDIUM: **Expiry is enforced by the route, not by the schema.** `expires_at` is nullable, the schema comment reads "NULL = no expiry", and the GET query treats NULL as never expiring. Any other writer (an admin script, a future route, manual SQL) can create a permanent link, and the public route will serve it. The note shipped with the code told the reader how to do exactly that ("drop the `make_interval` and insert `NULL`"). To show it: insert a row with `expires_at = NULL` and GET serves it forever. Clause 3 holds only for this route.
2. [WEAK] MEDIUM: **Revoking needs a link id that only the POST response ever returns.** There's no route that lists a dashboard's links. An owner who didn't save the `id` has no supported way to revoke a leaked link, short of trying serial ids one by one. "Can be revoked" holds only while the owner still has the id.
3. [WEAK] LOW: **The owner check and the INSERT aren't in a transaction.** If ownership changes between the two statements, the former owner still gets a link. The window is tiny. This is judgment, not something I demonstrated.
4. [WEAK] LOW: **`created_by REFERENCES users(id)` has no ON DELETE rule.** Deleting any user who ever created a link fails with a foreign-key error. This is outside the contract, but it will break account deletion.
5. [WEAK] LOW: **Nothing checks `PUBLIC_BASE_URL` at startup.** If it isn't set, POST returns `undefined/share/<token>` with a 201, and the link can't be used, with no error to say so.

## Assessment (judgment, not demonstrated)

- **Tokens in logs.** The raw token is in the URL path, so any request logger (morgan, a reverse proxy, a load balancer, an APM agent) writes it to its logs in plain text. The code doesn't redact it. If that happens, clause 2 ("stored only as a hash") fails outside the database.
- **Unauthenticated requests.** A POST or DELETE with no session gets whatever `requireSession()` returns, probably 401 rather than 404. That reveals nothing about which dashboards exist, but it doesn't match "anyone else gets 404" word for word.
- **CSRF.** If sessions ride on cookies with no CSRF protection, a form on another site can make a logged-in owner create a link. The attacker can't read the response, so the impact is low.
- **Rate limiting.** `/share/*` has none. Guessing a 256-bit token isn't possible, so the risk is load, not brute force.

## Claimed vs. actual

- **Claim:** only title and config go out. True of the query. Whether that meets clause 4 depends on what `config` holds, and the code never looks inside it.
- **Claim:** links expire after 30 days by default. True for this route, not enforced for the table (defect 1).
- **Claim:** the DELETE route turns a link off. True only if you still have the link id (defect 2).
- **The note's advice on never-expiring links contradicts clause 3.**

## Confirm-these (why this is WITH GAPS, and why it blocks)

1. **What `config` contains.** Blocking, clause 4. If it holds org ids, other dashboard ids, data-source credentials or anything about the owner, the public route sends them unchanged.
2. **Request logging.** Blocking, clause 2. Find out whether any logger or proxy records `/share/<token>` URLs.
3. **The `dashboard-public` template and its layout.** Check that the template escapes `config` if it puts it inside a script tag, and that the layout doesn't render anything about the org from `app.locals` or `res.locals`.
4. **What `requireSession()` returns when there's no session.** This affects the wording of clause 1.
5. **Node version.** `Buffer.toString('base64url')` needs Node 14.18+ or 15.7+.
6. **CSRF protection** on the session-authenticated routes.

**Most damaging issue:** no line of this code breaks the contract. It's safe only if `config` holds nothing about the owner, the org or other dashboards, and nothing writes share URLs to logs. This code can't show either one, which is why the review blocks.
