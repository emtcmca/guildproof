# Review: dashboard share links (Express + pg-promise)

**Verdict:** VERIFIED WITH GAPS. **BLOCKING: yes.**
Reading the code, I found nothing that breaks any of the five contract clauses. Two checks I couldn't make bear directly on clauses 2 and 4, and both are security-critical, so this should not merge until they're confirmed.

**Independence:** NOT INDEPENDENT. I wrote this code earlier in the same conversation, so I share its blind spots, and this result counts for less than an independent check would. For an independent check, paste the code and the contract into a fresh conversation.

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
