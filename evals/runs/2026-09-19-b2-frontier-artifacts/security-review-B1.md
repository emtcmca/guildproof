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
