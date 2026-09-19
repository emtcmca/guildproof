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
