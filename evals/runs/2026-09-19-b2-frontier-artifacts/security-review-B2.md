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
