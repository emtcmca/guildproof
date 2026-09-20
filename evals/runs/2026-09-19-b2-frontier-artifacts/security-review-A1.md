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
