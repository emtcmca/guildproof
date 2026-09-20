# Review: /v1/orders surface (pre-partner-publish)

Do not publish this as-is. Two of the five items can lose money or data on an ordinary network timeout, and the auth scheme puts credentials in log files you do not control.

## Contract as I read it

| Route | Inputs | Output | Side effects |
|---|---|---|---|
| `POST /v1/orders` | order body (fields unspecified) | `200` on success; `200` + `{"error":"..."}` on validation failure | creates an order |
| `PATCH /v1/orders/{id}` | full order object | unspecified | **replaces** the order record |
| `GET /v1/orders?page=N` | `page` (integer, unbounded) | 50 orders, newest first | none |
| `POST /v1/orders/{id}/refund` | none stated | unspecified | issues a refund; **repeatable, cumulative** |
| Auth (all routes) | `?key=<api key>` | — | — |

Assumed, because it was not given: no `Idempotency-Key` handling, no `ETag`/`If-Match`, no rate limiting, no tenant scoping on `{id}`, error body is the literal shape shown (`error` string, no code, no field path). No status codes other than `200` were named, so I assume none are specified. No currency/amount representation, no timestamps, no `status` field semantics given.

---

## Findings, worst first

### ❌ CRITICAL — `POST /{id}/refund` is not idempotent, and refunds are money
**What's wrong:** "Calling it twice refunds twice" is the whole bug. There is no idempotency key, no refund-state check, and no refundable-balance ceiling.

**Why it bites:** A partner's HTTP client times out at 30s while your processor call succeeds at 31s. The client retries — every sane client retries a timeout — and you refund twice. This is not a hypothetical edge: retry-on-timeout is default behavior in most HTTP libraries and every queue worker. It fires hardest during the exact incidents where you are least able to notice, and you find out from chargeback reconciliation days later. A hostile partner needs no exploit at all, just a `for` loop.

**The fix:** three layers, all of them.
1. Require `Idempotency-Key` on the request. Store `(key, endpoint, request_hash)` with a **unique DB constraint** — not an application-level "check then insert", which races. Replay the stored response on a repeat key; return `409` if the same key arrives with a different body.
2. Enforce the invariant independently: `sum(refunds) <= order.captured_amount`, checked inside the same transaction as the refund insert, with the row locked (`SELECT ... FOR UPDATE`) or a DB `CHECK`/trigger. Idempotency keys protect against duplicate *requests*; this protects against duplicate refunds arriving via any other path (support tool, backfill script, second partner integration).
3. Make the refund a state transition, not a verb: a refund is only legal from `captured`/`partially_refunded`. Return `409` with the current state otherwise.

Also add an explicit `amount` (and `currency`) to the request body now. If you ship full-refund-only and add partial refunds later, the "omitted amount means full" default becomes a breaking ambiguity you cannot fix without a new version.

### ❌ CRITICAL — API key in the query string
**What's wrong:** `?key=` puts a long-lived credential in the URL.

**Why it bites:** URLs are the single most-copied, most-logged string in a stack. That key lands in your access logs, the load balancer's logs, the CDN's logs, the partner's logs, APM/error-reporting payloads (Sentry captures request URLs by default), browser history and the `Referer` header if anything is ever fetched from a page, proxy caches, and every Slack message and support ticket where someone pastes a failing request. TLS does not help — the leak is at the endpoints, in plaintext, in systems with much broader read access than your database. You will find out when a partner grants log access to a vendor.

**The fix:** `Authorization: Bearer <key>` (or `X-API-Key`), header only. Reject `?key=` outright rather than accepting both — a "deprecated but still works" path means it never stops being used. Alongside that, before partners touch it: per-key scopes (a read-only reporting key must not be able to refund), key rotation with an overlap window so rotation is not an outage, hashed-at-rest storage, `created_at`/`last_used_at` per key so a partner can detect a stale leak, and per-key rate limits. Right now one string grants full read plus unbounded refunds, forever, with no revocation story stated.

### ❌ HIGH — `200 OK` with an error body
**What's wrong:** Validation failure returns `200`.

**Why it bites:** You have made the status code lie, so every layer that reads status codes — the partner's `response.raise_for_status()`, generated SDKs, retry middleware, API gateways, your own dashboards and alerting, load-balancer health metrics — records a failure as a success. Partners will ship code that treats `200` as "order created", because that is what `200` means. Your error rate graph will read 0% during an outage. Worse, an error that returns `200` is not retried by machinery that *should* retry it, and is retried by machinery that shouldn't.

**The fix:** `400` for malformed syntax, `422` for semantically invalid fields, `401`/`403` for auth, `404` for missing, `409` for state conflict, `429` for rate limit, `5xx` only for your own faults. Return `201 Created` with a `Location: /v1/orders/{id}` header on success. Make the error body machine-readable — a stable `code`, a human `message`, and a per-field list (`[{"field":"line_items[0].quantity","code":"must_be_positive"}]`). A bare `error` string forces partners to regex your prose, which then becomes a contract you can never reword.

While you are here: `POST /v1/orders` has the same idempotency problem as refund, one severity lower because a duplicate order is recoverable and a duplicate refund is not. Same `Idempotency-Key` mechanism.

### ❌ HIGH — no visible authorization; `{id}` is an IDOR until proven otherwise
**What's wrong:** Nothing in the contract scopes an order to the caller. `PATCH /v1/orders/{id}` and `POST /v1/orders/{id}/refund` take a bare id.

**Why it bites:** Authenticating the key is not authorizing the record. If the handler loads by primary key alone, partner A refunds partner B's order by incrementing a number — and refund is the worst possible verb to leave unscoped, because it moves money and is trivially enumerable if ids are sequential. `GET /v1/orders` looks list-scoped by implication, but the write paths are the exposure.

**The fix:** every lookup filters on the owner in the query, not after it: `WHERE id = ? AND account_id = ?`. Never load-then-compare, which fails open the day someone forgets the compare. Return `404`, not `403`, for another tenant's order — `403` confirms the id exists and hands over an enumeration oracle. Use non-sequential external ids (UUID or prefixed random) so a leaked id in a log reveals nothing about volume or neighbors. Add an authorization test per route per role; this is the class of bug that reappears every time someone adds an endpoint.

### ❌ HIGH — `PATCH` that replaces the whole object destroys data two different ways
**What's wrong:** It is labeled `PATCH` but has `PUT` semantics, with no concurrency control and no field allowlist.

**Why it bites:** Three distinct failures stacked on one route.
1. **Semantic mismatch.** `PATCH` means partial. A partner sends `{"shipping_address": {...}}` — the reasonable reading of the verb — and you null every other field. That is silent data loss with a `200`.
2. **Field-blindness.** Full replacement means any client on an older schema wipes fields it has never heard of. Add a field next quarter and every partner that has not redeployed starts erasing it on every update.
3. **Lost updates.** Two concurrent updates: both read, both write, last writer wins and the first change vanishes with no error. Guaranteed the moment a partner runs more than one worker.

Plus mass assignment: if the accepted body is "the full order object," can a caller write `status`, `total`, `paid_at`, `account_id`? Setting `status: "paid"` or rewriting `total` from the client side is a direct financial exploit, and `account_id` is a tenant escape.

**The fix:** Pick one and document it. Either real `PATCH` (JSON Merge Patch, RFC 7396, where explicit `null` deletes and absent means untouched) or a genuine `PUT` that requires the full representation and rejects a partial body outright. Add optimistic concurrency: return an `ETag`, require `If-Match`, `412` on mismatch — or a `version` integer with a compare-and-set update. Then a strict server-side allowlist of mutable fields; everything server-controlled (`id`, `account_id`, `total`, `status`, `created_at`, payment state) is rejected with `422` rather than ignored, so partners learn at integration time instead of discovering it worked once. Order status should move through dedicated transition endpoints, not through generic field writes.

### ⚠️ MEDIUM — offset pagination over a newest-first list skips and duplicates rows
**What's wrong:** `?page=N` with `ORDER BY created_at DESC` on a table that is actively receiving inserts.

**Why it bites:** The dataset shifts under the reader. Three orders arrive while a partner walks pages 1→2, and three rows that were on page 1's boundary slide onto page 2 — read twice — while others are never seen at all. A partner doing nightly full syncs will silently miss orders, and will blame you with logs that look clean on your side. If `created_at` is not unique and is the only sort key, the ordering is not even stable between identical queries.

**The fix:** Cursor (keyset) pagination: sort on a total order, `(created_at, id)`, and return an opaque `next_cursor` the client passes back. Query becomes `WHERE (created_at, id) < (?, ?) LIMIT ?` — stable under concurrent inserts and index-friendly at any depth, unlike `OFFSET 500000`, which makes the database count and discard every skipped row. Return `{"data": [...], "next_cursor": "..."}` from day one; a bare top-level array leaves you no place to add pagination metadata without a breaking change.

### ⚠️ MEDIUM — no filtering, no incremental sync, and page size is not the client's to choose
**What's wrong:** The only parameter is `page`. 50 is hardcoded. There is no `status`, no date range, no `updated_since`.

**Why it bites:** A partner who needs "orders changed since my last run" has exactly one option: walk every page, every time. That is your load, driven by their loop, and it scales with your total order count rather than with their change volume. It also pushes partners toward polling page 1 every few seconds, which is the traffic pattern that takes the endpoint down.

**The fix:** `limit` with a documented default (50) and a hard ceiling (say 200) — enforced server-side, clamped rather than erroring. Add `status`, `created_after`/`created_before`, and an `updated_since` cursor over `(updated_at, id)` for incremental sync. Reject unknown query parameters loudly instead of ignoring them; a partner's typo'd filter that silently returns everything is a data-exposure bug wearing a `200`.

### ⚠️ MEDIUM — no rate limiting stated on a surface that includes refunds
**What's wrong:** No limits, no `429`, no `Retry-After`.

**Why it bites:** A single partner's retry storm is an outage for all of them, and with refund non-idempotent, an unthrottled loop is a financial incident rather than a capacity one. Rate limiting is also the only backstop you have between "a key leaked" and "the damage is bounded."

**The fix:** Per-key limits, tighter on writes than reads and tightest on refund. Return `429` with `Retry-After` and `RateLimit-*` headers so clients back off instead of hammering. Document the numbers before partners build against the absence of them.

### ⚠️ LOW — undocumented surface details that become breaking changes later
Each of these is cheap now and expensive after partners integrate:
- **Money representation.** State it explicitly: minor units as integers (`"amount": 1050`) plus an ISO-4217 `currency`. If any amount is currently a float, fix it before publishing — binary floats cannot represent `0.10`, and rounding drift in refund math is a reconciliation nightmare.
- **Timestamps.** RFC 3339, UTC, with offset. Not epoch seconds, not local time, not a bare date.
- **Status codes and error codes** as a documented enumerated list, not discovered by partners in production.
- **Request IDs.** Return one on every response, including errors, and log it. Without this, "order 1234 failed yesterday" is unsupportable.
- **Versioning and deprecation policy.** `/v1` implies a `/v2`. Say now what counts as a breaking change, what notice partners get, and how long old versions live. Adding a field should be explicitly non-breaking, and clients should be told to ignore unknown fields.
- **Webhooks / events.** Absent an event stream, polling is the only integration pattern available, which is the root cause of the sync and load problems above.
- **Observability without PII.** Log request id, key id, route, status, latency. Never the key itself, never full card or address payloads. Given the key currently rides in the URL, your access logs are already a credential store — that stops being true only after the header fix lands.

### ✅ Checked and OK
- `newest first` is a sane default ordering for this resource.
- 50 is a reasonable default page size.
- Path shapes are conventional and readable: collection, item, action-as-subresource. `POST /{id}/refund` is the right shape for a non-CRUD state transition — the problem is its semantics, not its URL.
- Versioned path prefix exists.

---

## Highest-severity issue

`POST /v1/orders/{id}/refund` double-refunds on an ordinary retry, and nothing in the contract stops it — require an `Idempotency-Key` with a unique DB constraint **and** enforce `sum(refunds) <= captured_amount` in the transaction, before any partner sees this.

---

## Confirm these (may exist in code I was not shown)

1. **Tenant scoping on `{id}`.** Is the query `WHERE id = ? AND account_id = ?`, or a bare primary-key load? If the ownership check happens after loading, it fails open on the next new endpoint.
2. **Auth middleware coverage.** Is the key verified on *every* route including `/refund`, and is it constant-time compared against a hash, not looked up as plaintext?
3. **Does `?key=` get scrubbed** from access logs, APM, and error reporting today? If so, the leak is narrower than I assessed — but the fix is still the header, because you do not control the partner's logs.
4. **Validation.** Is there a schema on the `POST` and `PATCH` bodies, and does it reject unknown fields, or coerce and pass them through?
5. **Mutable-field allowlist on `PATCH`.** Can a caller currently write `status`, `total`, `paid_at`, or `account_id`? Test this directly — do not read the code and assume.
6. **Refund atomicity.** Is the processor call and the local refund record written in one transaction with a compensating path? If the processor succeeds and your insert fails, your ledger is wrong and your idempotency record never got written.
7. **`created_at` uniqueness / index.** Is there an index supporting `(created_at, id)`, and is deep pagination currently doing a large `OFFSET` scan?
8. **TLS enforcement.** Is plain HTTP redirected or refused? A redirect still transmits the key in cleartext once — refuse it.
9. **Rate limiting at the gateway.** If the LB or gateway already limits, what are the numbers, and are they per-key or per-IP? Per-IP is close to useless for server-to-server partners behind NAT.
