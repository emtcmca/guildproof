=== OUTPUT W ===

# Review: dashboard share links

Verdict: **not ready to merge as-is.** The core design is sound (opaque 128-bit token, separate table, ownership check on create, soft revoke), and nothing here is catastrophically broken. But there are four things I would block on, because three of them are the kind of defect that looks fine in testing and only shows up in production, and one of them is a false confirmation that will make Eric (or a user) believe a link is dead when it is still live.

Grouped by whether it blocks.

---

## Blocking

### 1. Revoke returns `{success: true}` when it revoked nothing

```javascript
await db.none(
  `UPDATE dashboard_shares SET is_active = FALSE
   WHERE token = $1 AND dashboard_id = $2
   AND dashboard_id IN (SELECT id FROM dashboards WHERE owner_id = $3)`,
  [token, id, user.id]
);
res.json({ success: true });
```

`db.none` asserts that no rows were *returned*. An `UPDATE` without `RETURNING` never returns rows, so this resolves successfully whether it flipped one row or zero. Every one of these paths reports success and changes nothing:

- wrong `:id` in the URL for that token (easy to hit: the token is the thing people copy, the dashboard id is the thing they guess)
- token already deleted, or never existed
- the caller does not own the dashboard
- a typo'd or truncated token pasted from an email

The security consequence is not privilege escalation, it is worse in practice: **the user is told the link is revoked, stops worrying about it, and the link still works.** Somebody pastes a share URL into the wrong Slack channel, hits revoke, gets a green check, and the dashboard stays public forever.

This is exactly the failure shape in the global rule about a tool's own success message not being evidence. Assert the postcondition:

```javascript
const result = await db.result(
  `UPDATE dashboard_shares SET is_active = FALSE, revoked_at = NOW(), revoked_by = $3
   WHERE token = $1 AND is_active = TRUE
   AND dashboard_id IN (SELECT id FROM dashboards WHERE owner_id = $3)`,
  [token, user.id]
);

if (result.rowCount === 0) {
  return res.status(404).json({ error: 'Share link not found' });
}
res.json({ success: true, revoked: result.rowCount });
```

Two other changes folded in there deliberately:

- **Drop `dashboard_id = $2` from the WHERE clause.** The token is globally unique, so the dashboard id in the path adds no security and only creates a way for a correct token to fail to revoke. Keep `:id` in the route for RESTful shape if you want, but do not let it gate the write. (If you keep it, you have to return 404 on mismatch rather than success, which is the same fix.)
- **Add `is_active = TRUE`** so `rowCount === 0` distinguishes "nothing matched" from "already revoked". If you would rather revoke be idempotent, drop that clause and check existence separately. Either is defensible; silently succeeding on both is not.

### 2. `BASE_URL` falls back to localhost instead of failing

```javascript
share_url: `${process.env.BASE_URL || 'http://localhost:3000'}/share/${token}`
```

If `BASE_URL` is missing or misspelled in the deploy environment, this does not error. It mints a real, live, permanent token in the database and hands the user a URL pointing at their own machine. The share is genuinely created and genuinely public; the only broken part is the link the user was given, so they retry, and now there are five live tokens for a dashboard nobody successfully shared.

Fail at boot, not per request:

```javascript
const BASE_URL = process.env.BASE_URL;
if (!BASE_URL) throw new Error('BASE_URL is required');
```

Keep the localhost default behind an explicit `NODE_ENV !== 'production'` check if local dev convenience matters. A dev-convenience default that silently applies in production is the whole problem.

### 3. Raw database errors are returned to the client

```javascript
res.status(500).json({ error: err.message });
```

Present in both the create and the revoke handler. `err.message` from pg-promise carries table names, column names, constraint names, and sometimes fragments of the failing SQL with parameter values interpolated into the text. That is free reconnaissance, and on the create endpoint it is reachable by any authenticated user.

Log server-side, return a generic body:

```javascript
} catch (err) {
  req.log.error({ err, dashboardId: id, userId: user.id }, 'share create failed');
  res.status(500).json({ error: 'Internal error' });
}
```

### 4. The public endpoint serves `d.config` unredacted, and there is no story for the data behind it

```javascript
`SELECT d.id, d.title, d.config, d.owner_id, u.name as owner_name ...`
```

`config` is whatever a dashboard's config blob happens to contain, returned verbatim to an unauthenticated caller. Dashboard configs typically hold datasource identifiers, raw query text or filter predicates, column and table names, internal hostnames, embed URLs, and sometimes API keys or connection strings that got stored there by an earlier feature. None of that is visible in this diff, which is the point: **the endpoint's exposure surface is defined by a column this code does not control**, and it will grow every time someone adds a field to config.

Two things needed before merge:

- **Serialize the public view through an explicit allowlist**, not `config` wholesale. A `toPublicConfig(config)` that names the fields a viewer needs (layout, chart types, titles, axis labels) and drops everything else. Then adding a secret to config later is safe by default instead of a silent leak.
- **Answer the question this diff does not: where does the viewer's actual chart data come from?** If the front end calls an authenticated data endpoint, the share page is broken for real anonymous viewers and you have not tested it. If it calls a data endpoint that trusts the share token, that endpoint is the real security boundary and it is not in this review. Either way, a share token must only be able to fetch the exact queries that dashboard defines, executed with the owner's privileges and nothing wider. That is the classic confused-deputy hole in every share-link feature, and it lives in the code that is not here.

Also note `owner_id` is selected but never used, and `u.name` (the owner's real name) is disclosed to anyone holding the link. The name disclosure is probably intended for a "shared by" byline, but make it a decision rather than a side effect of `SELECT`, and drop `owner_id` from the query.

---

## Should fix before this ships, not necessarily before merge

### 5. Nothing expires, and the error message claims things do

`res.status(404).json({ error: 'Share link not found or expired' })` is the only place expiry is mentioned. The table has no `expires_at`. Every token is permanent until manually revoked. That is a defensible product choice, but the message is a lie and the schema is the wrong shape to change later without a migration under load.

Add the column now even if the default is null (never expires):

```sql
expires_at TIMESTAMPTZ
```

```sql
WHERE ds.token = $1 AND ds.is_active = TRUE
  AND (ds.expires_at IS NULL OR ds.expires_at > NOW())
```

A 30 or 90 day default with an explicit "never" option is the right posture for links that get pasted into email threads and forwarded.

### 6. Unbounded token minting, so revocation is incomplete

Every `POST` creates another token. Click Share four times, get four live tokens; the UI shows the newest, the user revokes that one, three stay live. Nothing in the schema or the handler prevents this.

Pick one:

- reuse the existing active token for `(dashboard_id, created_by)` if one exists (partial unique index on `is_active`), or
- cap active shares per dashboard and return 409 past the cap, or
- keep multi-token but give the UI a list view and a "revoke all" that reports its `rowCount`

Whichever you pick, the API needs a way to enumerate a dashboard's active shares. Right now the owner cannot answer "how many live links exist for this?" and neither can Eric.

### 7. `err.received === 0` as the 404 signal is fragile

```javascript
if (err.received === 0) {
  return res.status(404).json({ error: 'Dashboard not found or access denied' });
}
```

`received` is a pg-promise `QueryResultError` property, so this works today. But there are two `db.one` calls in the try block, and the second is the `INSERT ... RETURNING`. If that insert ever returns zero rows, a failed *write* gets reported to the user as "Dashboard not found or access denied", which is a diagnosis that will cost somebody an hour.

Collapse the check and the write into one statement, which removes the ambiguity, removes the TOCTOU window between the ownership read and the insert, and makes 0 rows unambiguously mean "not yours":

```javascript
const share = await db.oneOrNone(
  `INSERT INTO dashboard_shares (dashboard_id, token, created_by)
   SELECT d.id, $2, $3
   FROM dashboards d
   WHERE d.id = $1 AND d.owner_id = $3
   RETURNING id, token`,
  [id, token, user.id]
);

if (!share) {
  return res.status(404).json({ error: 'Dashboard not found or access denied' });
}
```

If you keep the two-query version, match on `err.code === pgp.errors.queryResultErrorCode.noData` and scope it to the first query.

### 8. Headers the share route needs

The token is in the URL path, which means it leaks through channels the code cannot see:

- **`X-Robots-Tag: noindex, nofollow`** on the share response and the HTML page that wraps it. A share URL pasted into any indexed page puts a private dashboard into Google. This happens.
- **`Referrer-Policy: no-referrer`** on the share page, so the token is not sent to every third-party font, analytics script, or image host the page loads.
- **`Cache-Control: private, no-store`** so no CDN or intermediary holds private dashboard JSON.
- Make sure the access log for `/share/*` does not record the full path, or you have a permanent plaintext record of every live credential in your log store.

None of these are in the diff, and all four are standard for token-in-URL designs.

### 9. No view audit

There is no record that a share was ever viewed. After an incident the owner cannot answer "was this accessed, how often, from where, between when I shared it and when I revoked it." A minimal `share_views (share_id, viewed_at, ip_hash, user_agent)` insert on the public GET, or a `last_viewed_at` and `view_count` on the share row, changes an unanswerable question into an answerable one. Add `revoked_at` and `revoked_by` at the same time; `is_active` flipping with no trail is not an audit record.

---

## Smaller things

- **`idx_dashboard_shares_token` is a duplicate index.** `token VARCHAR(32) NOT NULL UNIQUE` already creates a unique btree index on that column. The explicit index adds write cost and storage for no read benefit. Drop it.
- **`VARCHAR(32)` is exactly the token length.** 16 bytes hex is 32 chars, so there is zero headroom. 128 bits of entropy is correct and I would not change it, but any future bump to 24 or 32 bytes needs a migration. `VARCHAR(64)` or plain `TEXT` costs nothing in Postgres and removes the tripwire.
- **`created_at TIMESTAMP`** should be `TIMESTAMPTZ`. Same for any expiry column. Timestamps without zone on share links that get compared against `NOW()` are a dependable source of off-by-hours bugs.
- **`is_active BOOLEAN DEFAULT TRUE` should be `NOT NULL`.** The current filter `is_active = TRUE` excludes NULL, so a NULL fails closed, which is the safe direction. Still worth making impossible.
- **`created_by INTEGER NOT NULL REFERENCES users(id)`** has no `ON DELETE` behavior, so deleting a user will fail on this constraint or silently depend on the default. Decide explicitly: `ON DELETE RESTRICT` (deleting a user requires cleaning up shares) or a nullable column with `ON DELETE SET NULL` (keep the share, lose the attribution). The `ON DELETE CASCADE` on `dashboard_id` is right.
- **`SELECT *` in the ownership check** pulls the whole dashboard row to check one boolean. Moot if you take the single-statement insert above.
- **The DELETE route puts the token in the authenticated user's request path**, which writes the secret into another set of logs. Prefer revoking by the share row's `id`, which the create response can return alongside the token.
- **Response field naming.** In the public handler, `share.id` is actually `d.id`, the dashboard's internal id, while the variable is named `share`. Confusing to read, and it hands the dashboard's internal id to an anonymous viewer for no stated reason. Either drop it or return an opaque identifier.
- **No rate limit on create.** Not a brute-force concern (a 128-bit token is not guessable and the lookup is indexed, so I would not worry about timing or enumeration on the public GET), but an authenticated user can create rows without limit. A per-user limit is cheap.

---

## Two design questions worth an answer before merge

**Ownership transfer.** The share is bound to `dashboard_id`, and the public query resolves the owner at read time through `d.owner_id`. If a dashboard is ever transferred to another user or team, every pre-existing share stays live and now exposes the new owner's dashboard under a token the new owner never created and cannot see. Decide whether transfer revokes shares. If dashboards cannot be transferred today, write that down somewhere, because this code assumes it.

**Only the owner can share.** `owner_id = $2` means collaborators, team members, and admins cannot create or revoke a share, including an admin cleaning up after a leak. If the app has any notion of shared or team-owned dashboards, this check is both too narrow (a legitimate editor cannot share) and the wrong boundary (an admin cannot revoke someone else's link during an incident). If dashboards are strictly single-owner today, fine, but the revoke path specifically should probably accept an admin override from day one.

---

## What is good, so it does not get changed by accident

- `crypto.randomBytes(16)` is the right generator and 128 bits is the right size. Not `Math.random`, not a sequential id, not a hash of the dashboard id.
- The token is opaque and carries no information about the dashboard, so the URL leaks nothing on its own.
- Parameterized queries throughout. No string interpolation into SQL anywhere in this diff.
- Soft revoke via `is_active` rather than `DELETE`, which preserves the row for audit. Keep that, and add the `revoked_at` and `revoked_by` columns to make it a real audit record.
- The create endpoint returns the same 404 for "does not exist" and "not yours", which avoids confirming the existence of other users' dashboards. Correct, and easy to lose in a later refactor.
- `ON DELETE CASCADE` from share to dashboard means deleting a dashboard cannot leave an orphaned live link.

---

## Minimum to merge

1. `rowCount` check on revoke, 404 when nothing was revoked, and drop `dashboard_id` from the revoke WHERE clause.
2. `BASE_URL` required at boot.
3. Generic 500 bodies, real errors to the log.
4. Allowlist the public `config` serialization, and confirm in writing where the viewer's chart data comes from and what the token can reach there.

Items 5 through 9 I would want in the same sprint, and 5 and 6 specifically before any external user touches this, since both are schema-shaped and get more expensive after there are live tokens in the table.


=== OUTPUT X ===

# Security review — dashboard share links

## Attack surface

Three routes and one table. What I can see:

- **`POST /api/dashboards/:id/share`** — session-authenticated. Untrusted input: `:id` (path), session cookie. Writes a row. Returns a bearer token.
- **`GET /share/:token`** — **unauthenticated, internet-facing**. Untrusted input: `:token` (path). This is the whole trust boundary. Possession of a 32-character string is the entire authorization model. Emits `dashboards.config`, `dashboards.title`, the internal dashboard `id`, and the owner's real name to anyone.
- **`DELETE /api/dashboards/:id/share/:token`** — session-authenticated. Untrusted input: `:id`, `:token`.

Sinks: parameterized SQL (all three), JSON responses, and an unshown renderer that consumes `title` and `config` to actually draw the shared dashboard.

Trust-boundary summary: the share token is a **permanent, non-expiring, non-enumerable bearer credential transported in a URL path**. Every finding below is downstream of that one design choice.

Context I do not have, and am not assuming into existence: the `config` schema, the renderer, the data-fetch path the share page uses, session/CSRF middleware, CORS policy, rate limiting, CDN config, and any org-level sharing policy. Per the rules I work under, I treat unseen controls as absent and list them as confirm-items rather than asserting they are missing.

---

## Findings

### ❌ CRITICAL — the full `config` blob is published to anonymous callers with no field allowlist

**Vector:** `GET /share/:token` selects `d.config` and returns it verbatim. Nothing filters, redacts, or allowlists fields. Whatever a dashboard config holds is now readable by anyone who obtains the URL, with no login, no logging, and no expiry.

**Impact:** depends entirely on what `config` holds, which is exactly why this is the finding to resolve first. In BI-shaped products a dashboard config routinely carries datasource identifiers, saved SQL or query DSL, filter values (which are often themselves sensitive — customer names, account ids, date ranges tied to a specific deal), webhook or API endpoints, and in bad cases embedded connection strings or API keys. If any of that is in there, "share a dashboard" silently means "publish our warehouse query and credentials to an unauthenticated URL." The owner's mental model is that they shared a picture. They shared the wiring.

**Severity reasoning:** likelihood of the endpoint being hit is 1.0 (it is the feature). Impact is unbounded until someone reads the config schema. I am not inflating this on speculation — I am ranking it first because it is the one finding whose blast radius cannot be bounded from the code shown, and it is cheap to check.

**Fix:** serialize through an explicit allowlist of the fields the renderer actually needs, built as a separate `toPublicConfig(config)` projection rather than a delete-list. Anything resembling a credential, connection string, raw query, or internal id gets resolved server-side and never crosses the boundary. Add a test that fails when a new config key appears in the public projection without being explicitly named.

---

### ❌ HIGH — share links never expire, cannot be listed, and can only be revoked with a token shown exactly once

**Vector:** three gaps compounding:

1. The schema has no `expires_at` and no code path sets one. The only state is `is_active`.
2. There is **no endpoint that lists a dashboard's share links.** No `GET /api/dashboards/:id/shares`.
3. `DELETE .../share/:token` requires the token. The token is returned only in the `POST` response body. Nothing else ever reveals it.

**Impact:** a token you did not write down is a link you can never revoke. An owner who creates a share, closes the tab, and later learns the Slack channel it was pasted into was exported to a departing contractor has **no mechanism to shut it off** — not through the API as written. They cannot even enumerate how many live links exist. Every `POST` mints a fresh token with no dedupe and no cap, so the set of valid credentials for a dashboard grows monotonically and is unknowable to its owner. Repeated clicking of a "Share" button in the UI produces N independently-valid permanent keys.

Note the error string on the public route: `'Share link not found or expired'`. Nothing expires. The message describes a control that does not exist, which is how operators come to believe stale links died on their own.

**Severity reasoning:** high rather than critical because the credential itself is strong (see the ✅ below) — this is not remotely brute-forceable. The severity comes from permanence plus invisibility. Leaked-link exposure in real incidents is measured in months precisely because nobody can find the links to kill.

**Fix:** add `expires_at TIMESTAMPTZ NOT NULL` with a default and a maximum, enforce it in the `WHERE` clause (`AND ds.expires_at > now()`), add a list endpoint returning id / created_at / expires_at / last_accessed_at but **not** the token, and key revocation on the share row's `id` rather than the secret. Consider a per-dashboard cap on active shares.

---

### ❌ HIGH — the token is in the URL path, so it leaks through channels nobody audits

**Vector:** `/share/<32 hex>` puts the secret in the request line. That path is written to server access logs, load-balancer and proxy logs, CDN logs, and APM traces. It lands in browser history and in the sync store of any signed-in browser profile. Link-preview bots in Slack, Teams, iMessage, and WhatsApp fetch it, so the credential is exercised by third-party infrastructure the moment it is pasted. If the rendered share page loads any third-party resource without a restrictive referrer policy, the full URL including the token travels in the `Referer` header to that third party.

Two consequences worth naming separately:

- **Search indexing.** An unauthenticated 200 with no `X-Robots-Tag: noindex` and no `robots.txt` exclusion, on a URL that gets pasted into public forums, ticket trackers, and status pages, gets crawled and indexed. This is not hypothetical; it is the standard failure mode for share-link features.
- **Log-based privilege escalation.** Anyone with log read access — support engineers, an ingestion vendor, an SIEM — holds every share credential ever issued. Log access is usually granted far more liberally than dashboard access.

**Impact:** anonymous read of the dashboard by any party that touched the URL, indefinitely (compounded by the previous finding).

**Fix:** you cannot fully remove a link-shaped secret from a link, so reduce what possession buys and how far it travels. Set `Referrer-Policy: no-referrer` and `X-Robots-Tag: noindex, nofollow` on the share response, scrub or hash the token in access logs, and pair the token with a short expiry. For anything above low sensitivity, the correct answer is to stop using a pure bearer link: require an email-verified recipient list or a second factor (passcode) alongside the token, so a leaked URL alone is insufficient.

---

### ❌ MEDIUM-HIGH — the shared-data path is unaccounted for, and the public response hands out the internal dashboard id

**Vector:** `GET /share/:token` returns `config` and `title` but no dashboard *data*. The rendered share page must get its numbers from somewhere. The response also returns `id: share.id`, which the `SELECT` aliases from `d.id` — the internal `SERIAL` primary key of the dashboard.

That leaves exactly two possibilities, and both are problems:

1. **There is an unshown public data endpoint.** It must be scoped by the *share token*, not by dashboard id, and it must re-check `is_active`. If it accepts a dashboard id (which this response just handed to the anonymous caller) it is an unauthenticated IDOR over every dashboard in the system, and sequential `SERIAL` ids make walking them trivial. This is the single worst outcome available in this change, which is why it is the confirm-item I would chase before merge.
2. **The data endpoint requires a session.** Then the feature is broken for its actual audience, and someone will "fix" it under deadline pressure — probably by loosening the data endpoint. The insecure version of this feature is the one that works, which is a bad gradient to ship on.

**Impact:** case 1 is unauthenticated mass data disclosure. Case 2 is a functional gap that converts into case 1 on the next commit.

**Fix:** define the data path in this change, not later. Issue the token as the sole credential for a read-only, token-scoped data route that re-validates `is_active` and expiry on every request. Stop returning the internal dashboard id; the share token is a perfectly good opaque handle for the client to use.

---

### ❌ MEDIUM — raw database error messages are returned to the client

**Vector:** `res.status(500).json({ error: err.message })` in both authenticated handlers. Concretely reachable: `POST /api/dashboards/abc/share` passes `'abc'` into `id = $1` against an integer column. Postgres raises an invalid-input-syntax error. That error has no `received` property, so the `err.received === 0` branch is skipped and the raw driver message is serialized to the caller.

**Impact:** information disclosure — column types, table names, constraint names, and depending on the driver's formatting, fragments of the query or bound values. It hands an attacker the schema reconnaissance they would otherwise have to guess at, and it is the standard opening move for building an injection or logic attack elsewhere in the app. A unique-violation on `token` would surface the same way.

**Fix:** log `err` server-side with a correlation id, return `{ error: 'Internal error', id: <correlation id> }`. Validate and coerce `:id` to an integer at the route boundary and reject non-numeric with a 400 before it reaches SQL.

---

### ⚠️ MEDIUM — revocation reports success unconditionally

**Vector:** the `DELETE` handler runs `db.none(...)` and then returns `{ success: true }` without inspecting how many rows were affected. `db.none` resolves happily when the `UPDATE` matches zero rows. So a request naming the wrong `:id` for the token, a token that was already revoked, a token that never existed, or a caller who does not own the dashboard all produce an identical `200 {"success": true}`.

**Impact:** the UI tells the owner the link is dead when it is still live. Given that revocation is the *only* mitigation available for a leaked link (no expiry), a revoke path that lies is a security control that silently fails closed for the attacker and open for the defender. The most likely real trigger is benign: a mismatched dashboard id in the client call, yielding a confident green checkmark over a still-serving URL.

Secondary: the ownership check means revocation is owner-only. If dashboard ownership ever transfers, the previous owner's links keep serving and neither party can revoke them without the token.

**Fix:** use a result-returning call, assert the affected row count, and return 404 when nothing matched. Key revocation on the share row id. Add a "revoke all shares for this dashboard" action, which is the operation an owner actually wants during an incident and which does not require knowing any token.

---

### ⚠️ MEDIUM — no CSRF defense visible on the state-changing routes

**Vector:** `requireSession()` implies ambient credentials. If the session is a cookie without `SameSite=Lax|Strict` and without a CSRF token, a page the victim visits can force `POST /api/dashboards/1/share`, minting a permanent public link on a dashboard the victim owns. The attacker cannot read the response cross-origin under default CORS, so this is link *creation* rather than direct token theft — but combined with the absence of a list endpoint, the owner has no way to discover the link was created. Forged `DELETE` calls let an attacker break sharing. If CORS anywhere in the app reflects `Origin` with `credentials: true`, the token becomes directly readable and this escalates to token theft.

**Fix:** confirm `SameSite` and CSRF middleware. Confirm the CORS policy does not reflect arbitrary origins with credentials. Sharing is sensitive enough to warrant a re-authentication or explicit confirmation step rather than a bare authenticated POST.

---

### ⚠️ MEDIUM — no abuse controls on either route

**Vector:** nothing rate-limits `POST /api/dashboards/:id/share` (unbounded row creation per dashboard, storage and index growth, and an unbounded credential set as noted above) or `GET /share/:token` (unbounded anonymous request volume against a joined three-table query on a public route).

Brute-forcing the token itself is **not** a credible path at 128 bits, and I am not going to dress it up as one. The real abuse shapes are resource exhaustion and using the public route as a free unauthenticated compute/query surface.

**Fix:** rate-limit both by session and by IP respectively, cap active shares per dashboard, and put the public route behind whatever caching or shielding the edge already offers — with the caching caveat below.

---

### ⚠️ MEDIUM — no access logging on the share row, so a leaked link's use is invisible

**Vector:** the table records creation and an active flag. It does not record `last_accessed_at`, an access count, or any per-request audit event.

**Impact:** an owner cannot tell whether a link has been used once by the intended recipient or ten thousand times by a scraper. During an incident there is no way to establish exposure. This is the difference between "we revoked it, and it was fetched 4 times, all from the recipient's ASN" and "we have no idea."

**Fix:** record `last_accessed_at` and a counter on the share row, and emit a structured audit event per public fetch. Surface both in the list endpoint. This is also what makes stale-link cleanup possible later.

---

### ⚠️ MEDIUM — revocation may not take effect if anything caches the public route

**Vector:** `GET /share/:token` returns a `200` with JSON and sets no `Cache-Control`. If a CDN or reverse proxy fronts the app, the response is cacheable under a default heuristic policy. The cache key includes the token, so this is not a cross-user mixing risk — the risk is that flipping `is_active` to `FALSE` does not stop the content from being served until the TTL expires.

**Impact:** revocation, already the only available mitigation, becomes eventually-consistent with an interval you do not control.

**Fix:** `Cache-Control: no-store, private` on the share response, and purge on revoke if an edge cache is in play.

---

### ⚠️ Unknown severity, plausibly HIGH — stored XSS through the renderer that draws the shared page

**Vector:** the renderer is not in this change, so I am flagging rather than asserting. But the shape is there: `title` and `config` are owner-controlled strings that reach a page served from your origin, and the public share page is the one page in the product that renders another user's content to a viewer who may themselves be logged in.

The attack is not an owner defacing their own page. It is: attacker creates a dashboard, plants script in `title` or in a config field the renderer interpolates, sends the share link to a victim who holds a live session on the same origin, and the script executes with the victim's cookies on your domain. Dashboard configs are exactly the kind of structure where a field ends up in an `innerHTML`, a chart label, a `dangerouslySetInnerHTML`, or a formatter that allows HTML.

**Fix:** confirm the renderer escapes every field by default. Serve the share page from a separate origin or a sandboxed context so that even a successful injection cannot reach same-origin session state, and add a CSP without `unsafe-inline`. If `config` supports any HTML, formula, or URL-valued field, that field needs a dedicated sanitizer and a scheme allowlist (block `javascript:` and `data:`).

---

### ⚠️ LOW-MEDIUM — one user's click publishes org data anonymously, with no policy control

**Vector:** the only gate on creating a public link is `owner_id = user.id`. There is no org-level sharing toggle, no admin approval, no per-datasource restriction, no notification to anyone, and no record an admin can review.

**Impact:** insider and accident path. Any user with a dashboard over sensitive data can make it world-readable in one request, permanently, without leaving a trace an administrator can find. Given no list endpoint exists, an org has no way to answer "what of ours is publicly reachable right now?"

**Fix:** an org-level policy flag gating public sharing, a per-dashboard or per-datasource restriction for anything classified, an audit event on creation, and an admin view of all active shares. At minimum, notify the owner by email on creation so an accidental or forged share is visible to a human.

---

### ⚠️ LOW — owner's real name is disclosed to unauthenticated callers

**Vector:** `u.name as owner_name` is returned to anyone with the link.

**Impact:** minor PII disclosure, plausibly intended ("shared by Jane Smith"). Worth a conscious decision rather than a side effect of the join. It provides an attacker with a verified employee name tied to a specific internal system, which is useful pretexting material for phishing the rest of the org.

**Fix:** decide deliberately. If attribution is needed, prefer a display name the user controls, or drop it.

---

### ⚠️ LOW — `BASE_URL` fallback to `localhost:3000`

**Vector:** `process.env.BASE_URL || 'http://localhost:3000'`. If the variable is unset in a production deploy, the API cheerfully returns unusable share URLs.

**Impact:** not a disclosure. It is a silent misconfiguration that fails at the user rather than at boot, and the surrounding failure mode (a user retrying "Share" several times) mints extra permanent tokens each attempt.

**Fix:** fail fast at startup on a missing required config value. Never default a public base URL, and never derive it from a request header.

---

### ⚠️ LOW — status code correctness is coupled to a driver-internal property

**Vector:** `err.received === 0` reaches into pg-promise's `QueryResultError` shape to distinguish "no such dashboard / not yours" from a genuine failure.

**Impact:** it works today. On a driver upgrade that renames or restructures that property, every not-found and not-authorized case silently becomes a `500` carrying `err.message` — converting a correct 404 into the information-disclosure finding above. A dependency bump, not a code change, flips the behavior.

**Fix:** use `db.oneOrNone` and branch on a null result. Let the error handler handle errors.

---

### ✅ Done right, worth keeping

- **All SQL is parameterized.** Every one of the four queries uses positional placeholders with a values array. No string interpolation anywhere near the SQL. No injection path here.
- **Token entropy is correct.** `crypto.randomBytes(16)` is a CSPRNG and 128 bits is not guessable. Hex-encoded to 32 characters, matching `VARCHAR(32)` exactly. No `Math.random`, no timestamp, no sequential id. The credential itself is sound; every problem above is about its lifecycle, not its strength.
- **No existence oracle on the create path.** `'Dashboard not found or access denied'` covers both cases with one message and one status, so an attacker cannot enumerate which dashboard ids exist by probing.
- **No existence oracle on the public path either.** A revoked token and a nonexistent token both return the same 404.
- **The `is_active = TRUE` predicate is fail-closed.** The column is nullable (`DEFAULT TRUE` with no `NOT NULL`), which is sloppy, but an explicit `NULL` would make a share unreadable rather than readable. Errs in the right direction.
- **The `token` index exists**, so lookup cost does not vary in a way that is observable across tokens.
- **`ON DELETE CASCADE` on `dashboard_id`** means deleting a dashboard cannot leave an orphaned share row still serving a join. Correct choice.
- **Revocation does check ownership** via the `dashboard_id IN (SELECT ... WHERE owner_id = $3)` subquery. The authz predicate is right; only the response handling around it is wrong.

---

## Highest-severity issue

The public route returns the entire `dashboards.config` blob to anonymous callers with no allowlist, behind a bearer token that never expires and, absent a list endpoint, frequently cannot be revoked at all — so whatever wiring lives in a dashboard config is published permanently by one click.

---

## Confirm-these

Controls or context that may exist in code I was not shown. I have defaulted to treating each as absent; none of these is a fact I am asserting.

1. **What does `dashboards.config` actually contain?** Read the schema and a production row. This single answer sets the severity of the top finding. Look specifically for datasource ids, raw queries, connection strings, API keys, webhook URLs, and filter values carrying customer or account identifiers.
2. **How does the rendered share page obtain dashboard data?** Find the endpoint. If one exists and is public, confirm it is scoped by share token and re-checks `is_active` — not by dashboard id. If it requires a session, the feature does not work for its audience, and that gap needs resolving before someone loosens the wrong thing.
3. **Does the renderer escape `title` and `config` fields?** Check for `innerHTML`, `dangerouslySetInnerHTML`, HTML-permitting formatters, and URL-valued config fields without a scheme allowlist.
4. **Is there CSRF protection and what is the cookie `SameSite` setting?** Check the session middleware.
5. **Does CORS anywhere reflect the request `Origin` with `credentials: true`?** If so, the CSRF finding escalates to token theft.
6. **Is there global rate-limiting middleware**, and does it cover the unauthenticated `/share/*` path as well as the API prefix?
7. **Is a CDN or reverse proxy in front of `/share/:token`**, and does it cache 200s without an explicit `Cache-Control`? If yes, confirm revocation purges the cache.
8. **Is `BASE_URL` set in every deployed environment**, and is there a startup check?
9. **Is there any admin surface listing active public shares org-wide?** If not, the org cannot currently answer what it is exposing.
10. **Do share rows survive dashboard ownership transfer**, and if ownership can change, who can revoke a link the previous owner created? The `DELETE` predicate suggests nobody can.
11. **Are access logs scrubbed of the `/share/:token` path**, and who has read access to those logs? Everyone on that list currently holds every share credential.


=== OUTPUT Y ===

# Security review: dashboard share links

Overall: the core primitive is sound. Tokens are 128 bits from a CSPRNG, every query is parameterized, ownership is checked before a link is minted, and the public read filters on `is_active`. The problems are not in the crypto. They are in revocation, in how much of the dashboard the public route hands out, and in the things the schema promises but does not have.

Five items below I would fix before merging. The rest can be follow-ups, but item 6 is the one that bites in production.

---

## Blocking

### 1. Revoke reports success without revoking anything

```js
await db.none(
  `UPDATE dashboard_shares SET is_active = FALSE
   WHERE token = $1 AND dashboard_id = $2
   AND dashboard_id IN (SELECT id FROM dashboards WHERE owner_id = $3)`,
  [token, id, user.id]
);
res.json({ success: true });
```

`db.none` resolves when the query returns no rows, which an `UPDATE` never does. It resolves identically whether one row changed or zero did. So `{ success: true }` is returned when:

- the token does not exist
- the token exists but belongs to a different dashboard than the `:id` in the path
- the caller is not the owner
- the link was already revoked

The authorization logic is correct. The reporting is not, and for a revocation endpoint that distinction is the whole feature. Concretely: the owner of a leaked link copies the token out of one email and the dashboard id out of another, gets them mismatched, sees a green confirmation, and closes the tab. The link is still live. Nothing anywhere records that the revoke did not happen.

Use the row count, and make the authorization part of the statement rather than a subquery so a mismatch cannot pass:

```js
const result = await db.result(
  `UPDATE dashboard_shares ds
      SET is_active = FALSE,
          revoked_at = NOW(),
          revoked_by = $2
     FROM dashboards d
    WHERE ds.dashboard_id = d.id
      AND ds.token = $1
      AND d.owner_id = $2
      AND ds.is_active = TRUE`,
  [token, user.id]
);

if (result.rowCount === 0) {
  return res.status(404).json({ error: 'Share link not found' });
}
res.json({ revoked: true });
```

Note this drops `:id` from the route. The token is globally unique, so the dashboard id in the path adds no security and creates exactly one new failure mode: the silent mismatch above. `DELETE /api/shares/:token` is both simpler and harder to get wrong.

Also worth writing a test that asserts a non-owner revoke attempt returns 404 **and** that the row is still `is_active = TRUE` afterward. A test that only asserts the status code would pass against the current buggy version too, since the current version returns 200 for everyone.

### 2. The public route hands out the entire dashboard config

```js
res.json({ id: share.id, title: share.title, config: share.config, ... });
```

`d.config` goes out verbatim to an unauthenticated caller. Whatever a dashboard config accumulates over the product's life ships with it. In practice these objects end up holding things like data-source identifiers, connection hints or internal hostnames, saved SQL or query fragments, filter values that are themselves sensitive (a customer name, an employee id), and sometimes a stray API key or embed token from a widget that was configured once and never revisited.

Today it may be clean. The exposure is that this line makes every future addition to `config` public by default, and nobody adding a field to a dashboard config will think about this endpoint.

Invert the default. Project explicitly, in one function, and have the public route call only that:

```js
function publicDashboardView(row) {
  return {
    title: row.title,
    owner: row.owner_name,
    widgets: row.config.widgets.map(w => ({
      type: w.type,
      title: w.title,
      layout: w.layout,
      data: w.data,          // resolved values only, not the query that produced them
    })),
  };
}
```

A unit test that feeds a config containing an unexpected key and asserts it does not appear in the output is what keeps this honest as the config schema grows.

Two smaller things in that same response. `id` is `d.id`, the internal dashboard id, which lets a link recipient name a resource in the authenticated API surface. Use the token as the client-side identifier and drop it. And `owner_name` is a real person's name on a public endpoint. That may well be intended, but it should be a deliberate product decision rather than a side effect of the join.

### 3. Database error messages are returned to clients

```js
res.status(500).json({ error: err.message });
```

Two places. Postgres and pg-promise errors carry column names, table names, constraint names, and sometimes a fragment of the statement. Log the error server side with a correlation id, return the id and nothing else:

```js
const ref = crypto.randomUUID();
logger.error({ ref, err }, 'share link failure');
res.status(500).json({ error: 'Internal error', ref });
```

### 4. There is no expiration, and the code says there is

The public handler's failure message is `'Share link not found or expired'`. Nothing in the schema or the code can expire a link. Every token is permanent until somebody remembers to revoke it, and item 1 means their attempt to do so may not have worked.

Either add the column and enforce it, or stop claiming it in the error text. I would add it:

```sql
ALTER TABLE dashboard_shares ADD COLUMN expires_at TIMESTAMPTZ;
```

```sql
WHERE ds.token = $1
  AND ds.is_active = TRUE
  AND (ds.expires_at IS NULL OR ds.expires_at > NOW())
```

A default on creation (30 or 90 days, with an explicit opt-out for links that genuinely need to be permanent) converts the failure mode from "leaked forever" to "leaked until it lapses." That default matters more than the mechanism, because the mechanism only helps links whose creators chose to use it.

### 5. Missing response headers on the public route

Two headers, both cheap, both closing real leaks:

```js
res.set('Cache-Control', 'no-store');
res.set('X-Robots-Tag', 'noindex, nofollow');
res.set('Referrer-Policy', 'no-referrer');
```

`no-store` keeps intermediate proxies and CDNs from holding dashboard content. `noindex` matters because share URLs escape into places crawlers reach, and public-link indexing is how this class of feature has leaked at several products before this one. `no-referrer` covers item 6.

---

## Should fix

### 6. The token is a bearer credential living in a URL path

Anything with the link has full read access, and the token sits in the path, which means it lands in web server access logs, reverse proxy and load balancer logs, browser history, any client-side analytics that reports `location.pathname`, and the `Referer` header of every outbound link a viewer clicks from the shared page.

Nothing here is free to fix, but three things help:

- `Referrer-Policy: no-referrer` on the share response (item 5).
- Scrub the path for `/share/:token` in the access log formatter, or move the token to a query parameter that your logging already redacts. Whichever you pick, verify it against an actual log line rather than assuming.
- Refuse to serve share links over plaintext. Related, the `process.env.BASE_URL || 'http://localhost:3000'` fallback is a footgun: a deploy that forgets `BASE_URL` will happily mint `http://localhost:3000/share/...` URLs and email them to people. Fail fast at boot instead, and require an `https://` origin outside development.

### 7. No record of access, and no record of revocation

For a credential that anyone can hold, access logging is the only thing that makes a leak detectable. Right now a link that leaked six months ago and has been polled daily since looks exactly like a link nobody opened.

```sql
ALTER TABLE dashboard_shares
  ADD COLUMN last_accessed_at TIMESTAMPTZ,
  ADD COLUMN access_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN revoked_at TIMESTAMPTZ,
  ADD COLUMN revoked_by INTEGER REFERENCES users(id);
```

Counter updates on a read path need care so they do not serialize traffic to a popular link, so make the increment fire and forget rather than blocking the response. Even a coarse "last seen" and a total is enough to answer "has this been used, and by roughly how many people" during an incident.

### 8. Unbounded link creation, and no dedupe

`POST /api/dashboards/:id/share` mints a new permanent credential on every call with no cap and no reuse of an existing active link. Click a Share button five times and there are five live tokens. A UI that shows the most recently created one leaves four invisible and unrevocable through the interface.

Either return the existing active link when one exists, or cap the count per dashboard and list them all in the UI. Returning the existing one is usually what users expect.

### 9. Offboarding does not revoke

`created_by` references `users(id)` with no cascade or trigger. When someone leaves, the links they created keep working. Whatever your deactivation path is, it should revoke that user's active share links, and that should be a test rather than a runbook step.

Separately, `ON DELETE CASCADE` on `dashboard_id` is the right call and is worth keeping.

### 10. Schema details

```sql
is_active BOOLEAN DEFAULT TRUE      -- add NOT NULL
created_at TIMESTAMP DEFAULT ...    -- prefer TIMESTAMPTZ
```

Without `NOT NULL`, a NULL `is_active` is representable, and `is_active = TRUE` evaluates to NULL rather than FALSE for such a row. That happens to fail closed here, which is lucky rather than designed. Add the constraint.

`TIMESTAMP` without time zone will cause an off-by-hours bug the first time you compute an expiry or render a "created 3 days ago" across a DST boundary. Use `TIMESTAMPTZ` now while the table is empty.

`idx_dashboard_shares_token` is redundant. The `UNIQUE` constraint on `token` already creates an index that serves the lookup in the public route. Drop the explicit one.

`VARCHAR(32)` is exactly sized for 16 bytes of hex, which is correct today but means any future change to token length fails at insert time. `TEXT` with a `CHECK (length(token) >= 32)` expresses the actual intent, which is a floor rather than a ceiling.

### 11. The `err.received === 0` check is fragile, and the 404 catch-all is too broad

In the POST handler, `err.received === 0` reaches into pg-promise internals to detect "no rows." Prefer the documented code:

```js
if (err.code === pgp.errors.queryResultErrorCode.noData) { ... }
```

Cleaner still, use `db.oneOrNone` and branch on a null result, which removes the need to classify an exception at all.

In the GET handler the problem is the opposite. Every error becomes a 404, so a connection pool exhaustion, a timeout, or a bad migration all present to the user as "link not found" and to your monitoring as nothing at all. During an outage you will get support tickets saying links are broken with no error rate to correlate against. Distinguish "no row" from "everything else," 404 the first, 500 and alert on the second.

### 12. CSRF, if sessions are cookie based

`requireSession()` is not shown. If it authenticates from a cookie, both state-changing routes are CSRF-reachable. A forced create is an attacker-triggered exposure (they cannot read the cross-origin response, but the token now exists and may surface elsewhere), and a forced revoke is a nuisance denial of service. `SameSite=Lax` on the session cookie plus a token on these two routes covers it. If `requireSession()` reads a bearer header, this does not apply.

### 13. No org-level sharing policy

There is no check that public sharing is permitted for this dashboard, this workspace, or this account tier. The moment one customer asks to turn public links off, this becomes a schema change plus an audit of every call site. A single `canShare(user, dashboard)` guard at the top of the POST handler is much cheaper to add now than to retrofit.

---

## Deliberately not flagging

So these do not get re-litigated in the next review:

- **Token entropy.** `crypto.randomBytes(16)` is 128 bits from a CSPRNG. Correct source, correct size.
- **Brute force on `/share/:token`.** Guessing a 128-bit token is not a threat model, so the absence of rate limiting on that route is not a security gap. Rate limiting for cost and availability reasons is still reasonable, just not urgent.
- **Timing attacks on token comparison.** SQL `=` against an indexed random 128-bit value is not practically exploitable. Not worth constant-time machinery.
- **SQL injection.** Every query is parameterized, including the dynamic-looking ones. Clean throughout.
- **Ownership check on create.** `owner_id = $2` in the same statement that fetches the dashboard is the right shape, and it fails closed.

One nit outside the security scope: `SELECT *` on line 26 pulls the whole dashboard row only to discard it. `SELECT 1` is enough for an existence-and-ownership check.

---

## Suggested order

Items 1 through 5 before merge. Item 1 first, because a revocation path that lies is worse than one that does not exist, and it is a ten-line change with a clear test. Item 6 and item 7 in the same follow-up, since both are about what happens after a link escapes, which is the scenario this whole feature needs an answer for.


=== OUTPUT Z ===

# Security review — dashboard share links

## Attack surface

Three endpoints, two trust zones.

**Zone 1 — authenticated (`requireSession()`):**
- `POST /api/dashboards/:id/share` — untrusted input: `:id` (path), session cookie/header.
- `DELETE /api/dashboards/:id/share/:token` — untrusted input: `:id`, `:token`, session.

**Zone 2 — fully anonymous:**
- `GET /share/:token` — untrusted input: `:token`. No session, no origin check, no rate limit. The token is the *entire* access control decision for this route.

**Data flow:** attacker-controlled path params → parameterized SQL (pg-promise `$1`) → row → JSON response. The sink of real interest is `d.config`, which is returned verbatim to an anonymous caller.

**Boundary the diff does not show:** `GET /share/:token` returns a dashboard's *config* but no dashboard *data*. Whatever endpoint the share page calls to populate charts is not in this change, and it has to accept an anonymous caller somehow. That unshown path is where the blast radius actually lives.

---

## Findings

### ❌ HIGH — revocation reports success without verifying that anything was revoked

**Vector:** `db.none(...)` returns successfully when the `UPDATE` matches **zero rows**, and the handler unconditionally responds `{ success: true }`. Wrong token, wrong `:id`, already-revoked row, or a dashboard the caller does not own — every one of those returns HTTP 200 `success: true`.

**Impact:** This is the security control for a leaked bearer credential, and it cannot fail loudly. An owner who learns a link leaked, clicks Revoke, and sees a green confirmation has no way to distinguish "killed" from "did nothing." A UI passing a stale or URL-encoded token, or the dashboard id of a *copy* of the dashboard, silently leaves the link live and publicly serving data. The authorization in the `WHERE` clause is correct, so this is not unauthorized revocation — it is the worse failure mode where the user is told the link is dead while it is still serving.

**Fix:** Use a result-returning call and assert the postcondition. `UPDATE ... RETURNING id`, then 404 when nothing came back:

```
const rows = await db.any(`UPDATE dashboard_shares SET is_active = FALSE
  WHERE token = $1 AND dashboard_id = $2
  AND dashboard_id IN (SELECT id FROM dashboards WHERE owner_id = $3)
  RETURNING id`, [token, id, user.id]);
if (rows.length === 0) return res.status(404).json({ error: 'Share link not found' });
```

Note the 404 is ambiguous on purpose — do not distinguish "not yours" from "does not exist."

---

### ❌ HIGH — the token is a permanent, unlimited, unaudited bearer credential

**Vector:** Three gaps compound:

1. **No expiry.** The schema has no `expires_at` and no query checks one — yet `GET /share/:token` returns the string `'Share link not found or expired'`. The code advertises a control that does not exist. Anyone who ever sees the URL has access forever.
2. **No cap on concurrent tokens.** Nothing is unique per `dashboard_id`, so a dashboard can carry N active tokens. An owner who revokes "the share link" has revoked *one row*; the others keep serving. Combined with the finding above, an owner can revoke every link they know about, get `success: true` each time, and still be public.
3. **No access log.** Nothing records a view. There is no way to answer "was this link used after it leaked, and by whom," which is the first question asked in an incident.

**Impact:** A URL pasted into a Slack channel, a ticket, a forwarded email, or a screenshot is a permanent unauthenticated read of that dashboard, and the owner has no signal that it happened and no reliable way to stop it.

**Fix:** Add `expires_at TIMESTAMPTZ NOT NULL` with a bounded default (7 or 30 days) and include `AND ds.expires_at > NOW()` in the view query — then the error string becomes true. Add a `revoked_at`/`revoked_by` column rather than a bare boolean so revocation is attributable. Log each view (share id, timestamp, coarse IP/UA) and expose active links per dashboard in the UI so "revoke" can mean "revoke all." Cap active tokens per dashboard.

---

### ❌ HIGH (confirm) — `d.config` is shipped whole to an anonymous caller with no field filtering

**Vector:** `GET /share/:token` selects `d.config` and returns it unmodified. Dashboard config blobs in this class of product routinely carry datasource identifiers, connection strings or datasource ids, raw SQL, saved filter values, internal hostnames, and occasionally embedded credentials or API keys for third-party chart sources. None of that is stripped, redacted, or allowlisted here, and the caller is unauthenticated by design.

I cannot see the shape of `config` in this diff, so I am flagging the sink, not asserting a leaked secret. But the code makes no attempt to distinguish "the parts of config a public viewer needs to render" from "everything the editor stored." Treat that as absent until the filtering is shown.

**Impact:** If config carries any datasource or credential material, the share link escalates from "read one dashboard" to "read the connection details behind it," which is a far larger blast radius than the feature intends.

**Fix:** Build an explicit public projection — a serializer that names the fields a viewer needs (layout, chart types, titles, axis config) and drops everything else by default. Deny-by-default on new config keys, so a future field cannot leak by being added.

---

### ❌ HIGH (confirm) — the data-fetch path for shared dashboards is not in this change

**Vector:** The share view returns config but no rows. To render, the page must call a data endpoint. Two possibilities, both bad if unaddressed:

- That endpoint takes a **dashboard id** and accepts anonymous requests → straight IDOR: an attacker with one valid share token discovers the pattern and reads *every* dashboard's data by incrementing the id, no token needed. Note that `GET /share/:token` helpfully returns `id: share.id` (the internal, sequential `dashboards.id`), handing the attacker the exact parameter and confirming ids are enumerable integers.
- That endpoint requires a session → the share page is broken for the anonymous recipients it exists to serve, and someone will "fix" it by loosening auth.

**Impact:** Case one is the highest-impact outcome available in this feature: full cross-tenant data read.

**Fix:** The token must be the credential for the data path too. Scope data requests by token, resolve `dashboard_id` server-side from the token row, and never accept a client-supplied dashboard id on any anonymous route. Also stop returning the internal `d.id` in the public response — return the token or a per-share opaque id.

---

### ⚠️ MEDIUM — raw database error text returned to the client

**Vector:** Both authenticated handlers end in `res.status(500).json({ error: err.message })`. pg-promise error messages carry query fragments, table and column names, constraint names, and type-coercion detail. Reaching this path is trivial: `POST /api/dashboards/abc/share` makes Postgres reject `'abc'` as an integer, `err.received` is undefined, and the handler hands the caller the database's own complaint.

**Impact:** Schema and query disclosure, which shortens the reconnaissance phase for everything else. Not exploitable alone; a reliable accelerator.

**Fix:** Log `err` server-side with a correlation id; return a fixed `{ error: 'Internal error', request_id }`. No `err.message` on any response.

---

### ⚠️ MEDIUM — the token travels in the URL path, so it leaks through channels you do not control

**Vector:** `GET /share/:token` puts the credential in the request line. That lands in web server and proxy access logs, CDN logs, browser history, and bookmark sync. If the rendered share page loads any third-party resource (fonts, chart CDN, map tiles, images referenced from `config`), the full URL goes out in the `Referer` header to that third party by default.

**Impact:** Silent credential disclosure to log aggregators and to any external origin the page touches — with no expiry (see above) to limit the window.

**Fix:** Send `Referrer-Policy: no-referrer` on the share route, and set `Cache-Control: private, no-store` so shared content is not held by intermediaries. Scrub the path from access logs for `/share/*`. Stronger: make `/share/:token` a thin HTML shell that immediately exchanges the token for a short-lived, `HttpOnly`-cookie-scoped view session, so the long-lived token stops appearing in subsequent requests.

---

### ⚠️ MEDIUM (confirm) — no CSRF defense visible on the state-changing routes

**Vector:** If `requireSession()` is cookie-based, both `POST .../share` and `DELETE .../share/:token` are cross-site forgeable. The `DELETE` is the more interesting one: an attacker who knows or has seen a token can force the victim's browser to revoke it (denial of access), and forged `POST`s create share rows the victim never authorized. An attacker cannot read the `POST` response cross-origin, so they do not directly obtain the new token — but any "list my share links" surface, or a notification email containing the URL, closes that gap.

I cannot see whether `requireSession()` enforces a CSRF token or `SameSite` cookies; treating the control as absent.

**Fix:** Confirm `SameSite=Lax` or `Strict` on the session cookie plus an origin check or CSRF token on both mutating routes. If auth is a bearer header rather than a cookie, this finding drops away.

---

### ⚠️ LOW — no rate limiting or quota on share creation

**Vector:** `POST /api/dashboards/:id/share` is unbounded per user and per dashboard. A session can mint unlimited rows.

**Impact:** Table and index growth, and an audit surface no owner can meaningfully review. Not a data breach. Brute-forcing `GET /share/:token` is *not* a concern here — 128 bits of entropy makes guessing infeasible — so rate limiting on the read path is defense in depth, not a gap.

**Fix:** Per-user rate limit on creation, plus a cap on active tokens per dashboard (which the cap in the expiry finding already covers).

---

### ⚠️ LOW — `:id` is never validated, and `BASE_URL` fails open to localhost

**Vector:** `:id` reaches SQL as an untyped string. Parameterization means this is not injection, but it produces the 500-with-DB-text path above and defers a type error to the database.

Separately, `process.env.BASE_URL || 'http://localhost:3000'` means a missing production env var silently emits `http://localhost:3000/share/<token>` share URLs — a broken feature that looks like it worked, and a valid token handed out attached to a useless host.

**Fix:** Validate `:id` as a positive integer at the route boundary and 400 on failure. Read `BASE_URL` at startup and fail to boot if it is unset outside development, rather than defaulting.

---

### ⚠️ LOW — data-integrity nits in the schema

- `token VARCHAR(32)` is exactly the width of `randomBytes(16).toString('hex')`. Zero headroom: raising token length later turns every insert into a 500. Use `TEXT`, or `VARCHAR(64)` with a `CHECK (char_length(token) >= 32)`.
- `is_active BOOLEAN DEFAULT TRUE` has no `NOT NULL`, so an explicit `NULL` is storable. `is_active = TRUE` evaluates false against NULL, so this fails *closed* — correct direction, but make it explicit: `NOT NULL DEFAULT TRUE`.
- `created_at TIMESTAMP` is timezone-naive. Use `TIMESTAMPTZ`, especially since expiry logic will read it.
- `created_by REFERENCES users(id)` has no `ON DELETE` behavior, so deleting a user errors on this constraint. Decide explicitly (`ON DELETE SET NULL` with a nullable column, or restrict deliberately).

---

### ✅ What is actually right

- **No SQL injection.** Every query uses pg-promise numbered parameters. `:id` and `:token` never reach string concatenation. Verified across all three handlers.
- **Token entropy is correct.** `crypto.randomBytes(16)` is a CSPRNG at 128 bits. Not guessable, not enumerable, no `Math.random` anywhere.
- **Ownership check on create is correct.** `WHERE id = $1 AND owner_id = $2` is a per-resource authorization check, not a session check — a user cannot mint a share link for someone else's dashboard.
- **No id-enumeration oracle on create.** A nonexistent dashboard and an existing-but-not-owned dashboard both return zero rows and the same 404 with the same message. That is the right behavior and it was easy to get wrong.
- **Revoke authorization is sound** (the `WHERE` clause enforces ownership twice over). Its defect is the silent no-op, not a missing check.
- **`owner_id` is selected but not returned** on the public route. The owner's *display name* is returned, which is a deliberate product decision worth confirming with whoever owns the privacy story, but the internal user id does not leak.

---

## Highest-severity issue

Revocation cannot fail visibly: `db.none` plus an unconditional `{ success: true }` means an owner can revoke a leaked share link, see a success response, and still be serving that dashboard publicly forever — because nothing expires and nothing is logged.

---

## Confirm these

1. **What is inside `config`?** Specifically: any datasource id, connection string, raw SQL, credential, or internal hostname. This decides whether the config finding is HIGH or informational.
2. **What endpoint does the share page call for chart data, and what authenticates it?** If it accepts a dashboard id from an anonymous caller, that is a cross-tenant IDOR and outranks everything above.
3. **Is `requireSession()` cookie-based, and does it carry CSRF protection / `SameSite`?** Determines whether the CSRF finding stands.
4. **Is there upstream middleware doing rate limiting, `Referrer-Policy`, or error sanitization?** I see none in this change and am treating all three as absent.
5. **Is there a "list share links for this dashboard" surface?** Without one, the unlimited-tokens problem is invisible to owners, and it also changes the CSRF impact.
6. **Does making a dashboard private, transferring its ownership, or moving it between teams touch `dashboard_shares`?** Nothing in this change re-evaluates a share against current dashboard state at view time, so an ownership or visibility change likely leaves old links serving.
7. **Are `/share/*` request paths scrubbed from access-log retention?** If logs ship to a third-party aggregator, the tokens are in there today.

