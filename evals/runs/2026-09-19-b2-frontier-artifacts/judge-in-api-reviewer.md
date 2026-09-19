=== OUTPUT W ===

# API review: orders v1

Short version: four of the five items are blockers, and three of them are the kind that cannot be fixed later without breaking every partner already integrated. Publishing to partners freezes this surface, so the order of operations matters more than usual.

Blockers first, then the things to fix before the second partner signs, then the conventions to pin down now because they are the hardest to change after the fact.

---

## Blockers

### 1. `POST /v1/orders/{id}/refund` is not idempotent, and it moves money

"Calling it twice refunds twice" means a network timeout costs you real money. A client cannot tell a timeout from a failure, so a well-written client retries, and a badly-written one retries harder. This will fire in production, and the first time it does you will be reconciling by hand against a partner who is certain they called it once.

Fix:

- Require an `Idempotency-Key` header (client-generated UUID) on every refund request. Store key → request fingerprint → response for at least 24 hours. A repeat with the same key and the same body replays the stored response; the same key with a different body is `422`.
- Model refunds as a subresource with identity: `POST /v1/orders/{id}/refunds` returns a refund object with its own id. Add `GET /v1/orders/{id}/refunds` so a client that lost the response can reconcile by reading instead of guessing.
- Enforce the invariant server-side: total refunded cannot exceed the order total. Reject the overage with `409` and include the amount already refunded in the error body.
- Support partial refunds with an explicit `amount` (see the money convention below). Default-to-full is fine, but make it explicit in the request rather than implied.

Apply the same idempotency key to `POST /v1/orders`. A duplicate order is cheaper than a duplicate refund but not by much.

### 2. `200` with `{ "error": ... }` on validation failure

This breaks every generic layer between you and the partner's business logic: HTTP client libraries, retry middleware, load balancer and APM error rates, log-based alerting, and the partner's own dashboards. All of them read status codes. Partners will write `if status == 200: success`, because that is what the protocol says, and ship the bug.

It also hides your own failures from you. A validation regression will show as a healthy 100% success rate.

Fix:

- `400` for malformed requests, `422` for well-formed but semantically invalid, `401` unauthenticated, `403` authenticated but not permitted, `404` unknown order, `409` state conflict, `429` rate limited, `5xx` for your faults. Pick one of 400/422 for validation and use it consistently rather than mixing.
- One error body shape across every endpoint:

```json
{
  "code": "validation_failed",
  "message": "One or more fields are invalid.",
  "errors": [
    { "field": "items[0].quantity", "code": "min", "message": "Must be at least 1." }
  ],
  "request_id": "req_01HX..."
}
```

- Treat the `code` values as part of the contract and document the closed set. Partners will branch on them, and if you do not publish codes they will parse `message` strings instead, which makes your copy edits into breaking changes.
- Return `201` with a `Location` header on successful create, not `200`.

### 3. API key in the `?key=` query parameter

Query strings get written down everywhere: your access logs, every proxy and CDN in the path, the partner's logs, browser history and the `Referer` header if a URL ever reaches a page, error-tracking payloads, and curl commands pasted into support tickets. Once a credential lands in a log you cannot recall it, and you usually cannot prove whether anyone read it.

Fix:

- `Authorization: Bearer <key>`. If a legacy partner client truly cannot set headers, issue that one integration a separate short-lived, narrowly-scoped token rather than blessing the query parameter in the published docs.
- TLS only. Reject plain `http` outright rather than redirecting, since a redirect has already leaked the key.
- Scope keys by capability, and make refund its own grant. A partner's read-only reporting job should not hold a credential that can move money.
- Allow several active keys per partner so rotation does not require downtime, show a key prefix and last-used timestamp so a partner can identify which key to revoke, and support revocation without a support ticket.
- Publish rate limits: `429` with `Retry-After`, plus `RateLimit-Limit` / `RateLimit-Remaining` / `RateLimit-Reset` on normal responses so clients can back off before they are cut off.

### 4. `PATCH /v1/orders/{id}` replaces the full object, with no concurrency control

Two separate problems stacked.

The naming lies. `PATCH` means partial modification (RFC 5789); a client that sends three fields expecting three fields to change will silently blank everything else. That is a data-loss bug with no error message.

Worse, full replacement guarantees a future outage. When v1.1 adds a field, an older client that reads an order and writes it back does not know about that field, so it wipes it. Same for any server-set field a client round-trips.

Fix:

- Make `PATCH` actually partial (JSON Merge Patch, `application/merge-patch+json`, with `null` documented as explicit clear). If you genuinely want full replacement, rename it to `PUT` and document which fields are required, but partial is the right default for an order.
- Document the mutable field set, and gate it on order state. A shipped or refunded order should reject item changes with `409` and report its current state in the error body, rather than accepting a write that the fulfillment side will ignore.
- Add optimistic concurrency: return an `ETag` on `GET`, require `If-Match` on `PATCH`, and return `412` on mismatch. Without it, two concurrent partner writes silently drop one, and nobody finds out until an order ships wrong.

---

## Should fix before you onboard partners

### 5. `?page=N` pagination over a newest-first list skips records

Offset pagination on a descending feed is unstable by construction. An order created between the page-1 and page-2 requests shifts everything down one, so the last row of page 1 becomes the first row of page 2 and one record is never returned. Cancels shift the other way and duplicate rows. On an orders feed this is not an edge case, it is Tuesday afternoon.

Fix:

- Cursor pagination with an opaque cursor: `GET /v1/orders?limit=50&starting_after=cur_...`, responding `{ "data": [...], "has_more": true, "next_cursor": "..." }`.
- Sort on a composite key such as `(created_at, id)`. `created_at` alone collides, and colliding sort keys reintroduce the skip.
- Let the client set `limit` with a documented maximum. A hardcoded 50 is wrong for both the dashboard and the nightly sync.
- Do not promise a `total` unless you can serve it cheaply. An unbounded `COUNT` over the orders table is a plausible first outage.

### 6. Missing endpoints partners will need immediately

- `GET /v1/orders/{id}` — a client that timed out on create or refund needs to re-read one order. Without it they list and filter, which is expensive for you and racy for them.
- `updated_after` (or `updated_since`) filtering on the list, plus `created_after` / `created_before` and `status`. Without an incremental-sync filter, every partner polls the entire order history forever, and your list endpoint becomes the bottleneck.
- Cancellation. Model it as a state transition (`POST /v1/orders/{id}/cancel`) rather than `DELETE`, so the record and its audit trail survive.
- If you will ever push events, publish the webhook contract at the same time as the REST surface, including the signature scheme, replay window, and retry policy. Partners architect around push-vs-poll on day one and rewriting later is expensive for them.

---

## Conventions to pin before publishing

These are cheap to decide now and effectively permanent afterward.

- **Money as integer minor units plus an ISO 4217 code** (`{ "amount": 1999, "currency": "USD" }`). Never floats, never a bare number whose unit lives in the docs. Refund amounts use the same representation.
- **Timestamps RFC 3339 with an explicit offset**, UTC, to a documented precision. Say whether `created_at` is ever mutated.
- **Opaque string ids with a type prefix** (`ord_...`, `re_...`). Do not expose sequential integers — they leak volume and invite clients to iterate them. State in the docs that ids are opaque and that length may change.
- **Declare each enum open or closed.** Tell clients to tolerate unknown values on open enums, or you cannot add an order status without a major version.
- **`request_id` on every response, success and failure.** It is the only thing that makes partner support tractable.
- **A written compatibility policy.** `/v1` buys nothing unless you define what counts as breaking (adding a field, adding an enum value, tightening validation, changing an error code) and commit to a deprecation window. Partners' security reviews will ask for this.

---

## Revised surface

```
POST   /v1/orders                     201 + Location, Idempotency-Key required
GET    /v1/orders/{id}                200 + ETag
PATCH  /v1/orders/{id}                merge-patch, If-Match required, 412 on conflict
GET    /v1/orders?limit&starting_after&status&updated_after
                                      cursor pagination, has_more + next_cursor
POST   /v1/orders/{id}/cancel         state transition, 409 if not cancellable
POST   /v1/orders/{id}/refunds        Idempotency-Key required, returns a refund object
GET    /v1/orders/{id}/refunds        reconciliation path after a lost response

Auth:   Authorization: Bearer <key>, TLS only, scoped keys, refund as its own grant
Errors: conventional status codes, one body shape, documented code enum
Limits: 429 + Retry-After, RateLimit-* headers on every response
```

## Suggested sequencing

1. Refund idempotency and status codes. Both are money or silent-failure issues, and both get harder once partner code depends on the current behavior.
2. Auth header move. Doing this before onboarding costs one doc change; doing it after costs a coordinated migration with every partner and a window where leaked keys are still valid.
3. `PATCH` semantics and `ETag`/`If-Match`.
4. Cursor pagination and the sync filters.
5. Conventions and the compatibility policy, written down in the published docs rather than agreed in a thread.


=== OUTPUT X ===

# API review — /v1/orders surface

Do not publish this to partners as written. Two of the five endpoints can lose money, and the auth scheme leaks credentials into log files you don't own.

## Contract (as I read it)

| | |
|---|---|
| `POST /v1/orders` | Creates an order. Side effect: order row, presumably payment capture. Returns **200** on both success and validation failure; failures carry `{"error": "..."}`. Response body on success unspecified. No idempotency key. |
| `PATCH /v1/orders/{id}` | Accepts the **full** order object and replaces it. Side effect: mutates an existing order, fields unbounded. No concurrency control. |
| `GET /v1/orders?page=N` | Offset pagination, fixed 50/page, ordered newest-first. No cursor, no total, no filters, no cap on N. |
| `POST /v1/orders/{id}/refund` | Moves money out. **Explicitly non-idempotent** — two calls, two refunds. No amount parameter, so full-refund only. No refund resource to read back. |
| Auth | Single API key in the `?key=` query string. No stated scoping, no read/write split, no per-resource authorization. |

Assumed, because it wasn't shown: there is a `{id}` that is a guessable or enumerable identifier; refunds hit a real PSP; there is no unshown middleware doing account scoping. I flag the middleware question in Confirm-these rather than asserting it's absent, but I am treating absence as the default.

---

## Findings, worst first

### ❌ CRITICAL — API key in the query string
**What's wrong:** `?key=` puts a long-lived money-moving credential into the URL.

**Why it bites:** URLs are logged by default, everywhere, by systems you do not control. Your own access logs. The partner's access logs. Every reverse proxy, CDN, WAF, and load balancer in between. APM and error-tracking payloads. `Referer` headers if any of this is ever hit from a browser. Shell history and CI logs on the partner's side. Bug reports where someone pastes a failing URL into a ticket. You are asking partners to hand you a credential in the one place that guarantees it gets written to disk in plaintext in a dozen places. Rotation after the inevitable leak is a coordinated migration with every partner at once.

**The fix:** `Authorization: Bearer <key>`, and reject the query parameter outright rather than accepting both — a supported-but-deprecated `?key=` is a leak with a longer tail. Store keys hashed. Scope each key to one partner account with explicit read/write/refund grants, so a key that only reads orders cannot move money. Enforce TLS and HSTS; a key in a URL over a redirect from plaintext HTTP is already spent.

### ❌ CRITICAL — Refund is non-idempotent, and you documented that as behavior
**What's wrong:** "Calling it twice refunds twice." That's not a quirk, that's an unbounded withdrawal endpoint.

**Why it bites:** You do not get to decide how many times this is called. A partner's HTTP client retries on a 500, on a socket timeout, on a 502 from your load balancer. The refund may have succeeded and the response lost — the partner cannot distinguish that from a failure, so a correct client retries and double-refunds. A partner's own job queue redelivers on at-least-once semantics and refunds four times. Someone double-clicks a button in a partner-built admin tool. This is the 3am page: a merchant refunded $40k because your gateway timed out at 14 seconds and their client retried three times. There is no way for the partner to detect it afterward, because there is no refund resource to list.

**The fix:** Make refunds a resource with a client-supplied identity. Either require `Idempotency-Key` and persist request-hash-to-response for at least 24 hours (replaying the same key returns the original response, a different body under the same key returns 422), or better, model it as `POST /v1/orders/{id}/refunds` creating a refund with a client-supplied `refund_id`, returning 201 on first call and 200 with the existing refund on replay, `GET /v1/orders/{id}/refunds` to reconcile. Add an `amount` so partial refunds exist at all. Enforce the invariant server-side, in a transaction: sum of refunds cannot exceed order total, regardless of what any client sends. Idempotency keys are a convenience; the sum check is the actual guard.

### ❌ CRITICAL — No authorization on `{id}`; refund and PATCH are wide open to IDOR
**What's wrong:** Nothing in this contract ties `{id}` to the caller. Authentication is present. Authorization is not shown anywhere.

**Why it bites:** Partner A changes the id in the path and refunds Partner B's order. Or PATCHes it. If ids are sequential integers, that is a script, not an attack. `GET /v1/orders` has the same problem in the other direction: if the list isn't scoped, one partner enumerates everyone's order history, which is customer PII and competitor revenue data in one response. "Has a valid key" is not "owns this order," and a refund endpoint is the worst possible place to find that out.

**The fix:** Every `{id}` lookup filters by the authenticated account in the same query — `WHERE id = $1 AND account_id = $2` — not a fetch followed by a check, which drifts. Return **404**, not 403, for another account's order; 403 confirms the id exists. Use non-enumerable ids (UUIDv7 or a prefixed random token like `ord_...`) so a leaked id in a log isn't a map of your order volume. Write an automated test that asserts account A gets 404 on account B's order, for every route with an `{id}`, and make it fail the build when someone adds a route without it.

### ❌ HIGH — `200 OK` with `{"error": ...}` on validation failure
**What's wrong:** Failures are returned as success.

**Why it bites:** Every layer between you and the partner's business logic believes the request worked. Their HTTP client resolves, doesn't throw, and returns a body their happy path tries to read. Their monitoring shows 100% success while orders silently fail to be created. Their retry middleware doesn't retry things that genuinely should be retried, because 200. Caches may store it. Your own error-rate dashboards are blind, so you'll learn about the outage from the partner. And because this is the documented shape, every partner writes `if (body.error)` into their integration — once that's in production at ten partners, you can never move to real status codes without a breaking change and a version bump.

**The fix:** `400` for malformed syntax, `422` for semantically invalid fields, `401` unauthenticated, `403` unauthorized, `404` not found, `409` for state conflicts, `429` rate-limited. One machine-readable error envelope on every failing route — RFC 9457 `application/problem+json` is the standing default: stable `type` slug, human `title`, and a `errors[]` array of field-level `{field, code, message}` so the partner can show a form error without string-matching your prose. Never include stack traces, SQL fragments, internal hostnames, or upstream PSP error bodies; map upstream failures to your own codes and put the correlation id in the response so support can find the real error in your logs. Success side: `201 Created` with a `Location` header and the created order.

### ❌ HIGH — `PATCH` that replaces the whole object
**What's wrong:** Three distinct bugs wearing one endpoint.

**Why it bites:**
1. **It's mislabeled.** PATCH means partial modification; full replacement is PUT. Partners will send partial bodies because the method says they can, and your handler will null out everything they omitted.
2. **Lost updates.** No `If-Match`/ETag and no version field, so two concurrent writes silently clobber each other — and with full-object replace, the second writer overwrites fields it never intended to touch, not just the one it changed. Read-modify-write over a network with no concurrency token is a data-loss bug, not a race you can shrug at.
3. **Mass assignment, and this is the security half.** "The full order object" includes fields the caller must never set. Can a partner PATCH `status` to `paid`, `refunded`, or `shipped`? Set `total` to 0.01? Move `customer_id` or `account_id` to another partner's? Change `created_at` to hide activity from a date-filtered audit? Any field you accept because it was in the object you serialized is now a partner-writable field.

There's a fourth, specific to publishing this to partners: full-replace makes your schema permanently frozen from the client side. Add a field next quarter, and every partner still sending last quarter's object wipes it on every write. You cannot evolve the resource without silently destroying data.

**The fix:** Explicit allowlist of mutable fields, server-side, rejecting unknown keys with 422 rather than ignoring them. Never bind request bodies straight to your model. Status transitions go through a state machine that rejects illegal moves (`refunded -> pending`), and the money-relevant fields (`total`, `status`, `account_id`, timestamps) are server-owned and not writable at all. Add optimistic concurrency: return an ETag or `version`, require `If-Match`, return 409 on mismatch. If you truly want replace semantics, name it `PUT` and document that omitted fields are cleared; otherwise make it a real partial PATCH.

### ⚠️ MEDIUM — Offset pagination over a newest-first, actively-growing list
**What's wrong:** `?page=N` on data sorted by newest-first, with no cursor and no stable tiebreak.

**Why it bites:** The dataset shifts under the reader. A partner walks page 1 to page 40 while orders are being created; every new order pushes rows down a page, so they see duplicates and miss records entirely. This is a silent correctness bug in exactly the workload partners will build first: a nightly sync into their own database. They will reconcile short and blame you, and it will take a week to prove why. Two sub-issues: identical `created_at` values have no deterministic order, so even a static dataset can page inconsistently; and deep offsets (`page=50000`) make the database count and discard millions of rows per request, which is a cheap DoS with one authenticated key.

**The fix:** Keyset/cursor pagination — order by `(created_at, id)` and return an opaque `next_cursor` plus `has_more`; no `page`, no `offset`, no total count in the hot path. Let the caller set `limit` with a hard server cap. Add `created_after` / `updated_after` filters and a stable ascending-order mode so incremental sync is actually possible. If partners need a full historical pull, give them a bulk export rather than 40,000 pages.

### ⚠️ MEDIUM — `POST /v1/orders` is not idempotent either
**What's wrong:** No idempotency key on order creation.

**Why it bites:** Same failure shape as the refund, one step earlier: timeout after the order is written, partner retries, customer is charged twice and has two orders. Less catastrophic than double-refund only because duplicate orders are usually visible to someone.

**The fix:** Accept and require `Idempotency-Key` on every non-GET route. Same key plus same body replays the stored response; same key plus different body is a 422. One mechanism, applied uniformly, is easier to document than per-endpoint rules.

### ⚠️ MEDIUM — No rate limiting or quota in the contract
**What's wrong:** Nothing stated.

**Why it bites:** One partner's runaway retry loop is an outage for all of them. On the refund route specifically, an unbounded request rate against a non-idempotent money mover is the worst pairing in this document. Unstated limits also mean partners write clients with no backoff, so your first limit will break them.

**The fix:** Per-key limits published in the docs, `429` with `Retry-After`, and `RateLimit-*` response headers so well-behaved clients can self-pace. Tighter, separate bucket for refunds.

### ⚠️ MEDIUM — Refund result semantics are undefined
**What's wrong:** A refund at a payment processor is frequently asynchronous, and the contract says nothing about what a success response means.

**Why it bites:** Does `200` mean "we accepted the request," "the PSP acknowledged," or "funds have settled"? Partners will assume the strongest reading and tell the customer the money is back. Later reversal or PSP failure has no channel to reach them, because there is no refund object to poll and no webhook mentioned. Related partial-failure gap: if the PSP refund succeeds and your local write fails, the order says unrefunded while the money is gone. Nothing here describes how that's reconciled.

**The fix:** Return a refund resource with an explicit `status` (`pending` / `succeeded` / `failed`) and a `failure_reason`. Make the state readable via `GET`. Add webhooks for terminal transitions. Write the local intent-to-refund before calling the PSP and reconcile from the PSP as the source of truth, so a crash mid-flight is recoverable rather than a silent discrepancy.

### ⚠️ LOW — Observability, and one place it collides with a finding above
**What's wrong:** No correlation id in the contract.

**Why it bites:** When a partner reports "my refund failed at 14:03," you have no join key. Worse: your access logs currently contain live API keys in the request line, which means your log store is now a credential store and inherits its retention, its access controls, and anyone with log-read permission.

**The fix:** Return a `Request-Id` on every response, including errors, and log it. Once auth moves to a header, scrub `Authorization` at the log boundary. Never log full request bodies on the order routes without redacting payment and customer fields.

### ✅ Checked and OK
- Path is versioned (`/v1`). Keep it, and bump it — several fixes above are breaking changes, and it is far cheaper to make them now than to run `/v2` for two years.
- Newest-first is a reasonable default ordering for a UI-facing list; the problem is the offset mechanism, not the sort.
- Refund is modeled as a sub-action on the order rather than a top-level mutation, which is the right shape. It just needs to create a resource instead of firing an event into the void.

---

## Highest-severity issue

**An unauthenticated-to-that-order, non-idempotent refund endpoint, reached with a credential you have instructed partners to put in the URL — any of the three alone is a serious bug; together they are an arbitrary withdrawal API with a credential that leaks into log files by design.**

---

## Confirm these

Protections that may exist in code I wasn't shown. Each is a finding until someone points at the line:

1. **Account scoping in auth middleware** — does the key resolve to an account, and is every `{id}` lookup filtered by it? Show me the query, not the middleware's existence.
2. **Id shape** — sequential integers or random tokens? Determines whether the IDOR is a script or a guessing game.
3. **PATCH field allowlist** — is there one, and does it exclude `status`, `total`, `account_id`, `created_at`, and any customer reference? Does it reject unknown keys or ignore them?
4. **Status transition validation** — can any client-supplied `status` land in the database unchecked?
5. **Server-side refund ceiling** — is there a transactional check that refunds cannot exceed the order total, independent of any idempotency layer? If the PSP enforces it, confirm you handle its rejection rather than surfacing its error body.
6. **Page size / offset cap** — is `page` bounded, is there a max offset, and is the 50 fixed or overridable?
7. **Rate limiting** — present at the gateway even if undocumented? Separate bucket for refunds?
8. **TLS enforcement** — HTTPS-only, HSTS, plaintext requests rejected rather than redirected. A redirect has already leaked the key.
9. **Key storage** — hashed at rest, rotatable per partner without downtime, revocable independently.
10. **Audit log** — is there an immutable record of who refunded what, with the key id and request id? If this endpoint goes to partners, you will need it in a dispute.
11. **Log scrubbing** — are query strings redacted anywhere today? Determines whether existing logs already need to be treated as compromised and the current key set rotated before launch.


=== OUTPUT Y ===

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


=== OUTPUT Z ===

# API review: /v1/orders

**Recommendation: do not publish as-is.** Five of the five items listed have defects that get expensive after partners integrate, because each one becomes a compatibility contract you have to break to fix. Three are outright correctness or security problems: HTTP 200 on failure, a non-idempotent refund, and an API key in the query string.

The cost asymmetry is the whole argument. Changing any of this before partners write code costs a sprint. Changing it after costs a deprecation cycle, a migration guide, dual-running both behaviors, and a support queue.

Below: blockers first, then endpoint-by-endpoint, then the gaps that are missing entirely, then a concrete revised surface.

---

## Blockers (fix before any partner sees this)

### 1. `POST /v1/orders` returns 200 with an error body

This is the single most disruptive item, because it breaks tooling that sits above your code and that you do not control.

What breaks:

- **Every HTTP client's error handling.** `response.raise_for_status()`, `if (!res.ok)`, Guzzle exceptions, Retrofit `isSuccessful()`. All of them see success. Partner code will happily continue with a nonexistent order.
- **Retry middleware.** Retry policies key off status. A 200 is never retried, so a transient validation-adjacent failure looks permanent, and a real permanent failure gets no signal.
- **Observability.** Your own dashboards, your partners' dashboards, and any APM in between compute error rate from status codes. Your error rate reads 0% while orders are failing.
- **Generated SDKs.** OpenAPI generators map status to response type. A 200 that is sometimes `Order` and sometimes `{error}` produces either a union type nobody handles or a silently wrong deserialization.
- **Gateways and CDNs.** A 200 is cacheable by default and countable as success in load balancer health logic.

The failure shape in production is silent, not loud: a partner records an order ID that does not exist, or writes `undefined` into their own database, and you find out days later from a reconciliation dispute.

Fix: use real status codes and a structured error body.

- `400` for malformed syntax (unparseable JSON, wrong content type)
- `422` for syntactically valid but semantically invalid (unknown SKU, negative quantity, missing required field)
- `409` for state conflicts (duplicate external reference)
- `401` / `403` for auth
- `429` for rate limiting
- `500` / `503` for your faults, and only for your faults

Adopt RFC 9457 (`application/problem+json`) or something shaped like it, and include **field-level** detail. A bare `{"error": "validation failed"}` forces a support ticket for every failure:

```json
{
  "type": "https://docs.example.com/errors/validation_failed",
  "title": "Validation failed",
  "status": 422,
  "code": "validation_failed",
  "request_id": "req_01HQ8Z...",
  "errors": [
    { "field": "items[0].quantity", "code": "min_value", "message": "must be at least 1" },
    { "field": "currency", "code": "unsupported", "message": "JPY is not enabled for this account" }
  ]
}
```

Two properties matter more than the exact schema: a **stable machine-readable `code`** partners can branch on without string-matching prose, and a **`request_id` on every response, success or failure**, so a support conversation starts from a log line instead of a guess.

While you are here: the success case is unspecified. Creation should be `201 Created`, with a `Location` header and the full created order in the body (partners need the server-assigned ID, status, and computed totals without a second round trip).

### 2. `POST /v1/orders` has no idempotency, so retries duplicate orders

A partner's request times out at 10s. Your server committed the order at 9.8s. The partner's client retries. You now have two orders and one angry merchant. This is not an edge case; it is the normal behavior of every HTTP client under packet loss, and mobile networks make it routine.

Fix: accept an `Idempotency-Key` header (partner-generated UUID), scoped per API key, stored with the request fingerprint and the response.

- First request with a key: process, store the response, return it.
- Replay with the same key **and the same request body**: return the stored response byte-for-byte, with a header marking it a replay. Do not re-execute.
- Same key, **different** body: `422` with a distinct code. That is a partner bug and silently returning the old response hides it.
- Concurrent replay while the first is still in flight: `409`, with guidance to retry after a moment.
- Retention: 24 hours minimum. Document the window, because behavior after expiry differs.

Make the header **required** on `POST /v1/orders` and on refunds. Optional idempotency is idempotency that nobody uses until after their first incident.

### 3. `POST /v1/orders/{id}/refund` refunds twice when called twice

Stated in the spec as though it were a documented behavior, which does not make it acceptable: it means the endpoint has no defense against the most common failure in distributed systems. Money moves, the response is lost, the client retries, money moves again. This one produces chargebacks, ledger mismatches, and in some jurisdictions a compliance problem.

There are two separate fixes and you need both. Idempotency keys alone are not sufficient, because a partner can legitimately send two different keys for what a human meant as one refund (two operators clicking the same button, a queue worker running twice with fresh keys).

**Fix A: idempotency key, required.** Same mechanics as above. A replay returns the original refund record rather than creating a second one.

**Fix B: a server-side invariant, independent of any client-supplied key.** The sum of succeeded refunds against an order can never exceed the captured amount. Enforce it in a transaction against the order row, not in application logic that reads then writes. Return `409` with `code: "already_refunded"` or `code: "refund_exceeds_captured_amount"`, and include how much remains refundable so the partner can react without a second call.

**Also make refunds a resource, not a verb.** `POST /v1/orders/{id}/refund` returning nothing durable means a partner who loses the response has no way to find out what happened, and no way to answer "was this refunded?" without asking you.

```
POST   /v1/orders/{id}/refunds     -> 201, creates a refund, returns { id, amount, currency, status, reason, created_at }
GET    /v1/orders/{id}/refunds     -> lists refunds for the order
GET    /v1/refunds/{refund_id}     -> one refund
```

This also gets you partial refunds, which partners will ask for within a month. The request should take an explicit `amount` and `currency`; defaulting to "the whole order" is fine, but make the default explicit in the docs rather than implicit in the absence of a parameter. Add an optional `reason` and a `metadata` object: refund reconciliation is the number one thing support teams need and cannot get later without a schema change.

Refunds are also asynchronous at the payment processor. Return a `status` (`pending` / `succeeded` / `failed`) rather than implying the money has moved, and emit a webhook when it settles. If you model it as synchronous now, you cannot make it async later without breaking every partner.

### 4. Auth: API key in the `?key=` query parameter

Move it to `Authorization: Bearer <key>`. Query-string credentials leak through channels TLS does not protect, because the leak happens at the endpoints, not on the wire:

- **Access logs.** Nginx, Apache, ALB, CloudFront, and your own app logs record the full path by default. Your partners' keys end up in your log retention, your log vendor, and any engineer's laptop that has ever run a log query.
- **Proxy and gateway logs**, including corporate egress proxies on the partner side, which you have no control over.
- **Error trackers and APM.** Sentry, Datadog, and New Relic attach the URL to every trace and exception.
- **Browser history and the `Referer` header** anywhere a URL is used from a page context.
- **Cache keys and shared links.** A URL with a credential in it gets pasted into Slack, into a Jira ticket, into a curl example in a partner's internal wiki.

Headers avoid all of that, because logging a request header requires opting in.

Related auth work that is much cheaper now than later:

- **Prefix keys** (`sk_live_`, `sk_test_`) so GitHub secret scanning, Gitleaks, and your own pre-commit hooks can recognize them. This has prevented real breaches for other API vendors and costs nothing to add.
- **Separate test and live keys**, against a sandbox environment with its own data. Partners will otherwise test against production, and their first integration bug will be a real refund.
- **Multiple active keys per partner plus a rotation path.** One key with no rotation story means a leaked key cannot be replaced without downtime, so it never gets replaced.
- **Scopes.** Read-only keys for reporting integrations, and a separate scope for `refunds:write`. Today one key can refund every order, which means a partner's reporting dashboard holds the authority to move money.
- **Never echo a key back**, including in error messages and validation output.
- Store hashes, not keys. Show the full value once at creation.

If partner sensitivity is high, plan for OAuth 2.0 client credentials (short-lived tokens, revocable) or mTLS as a v2 path. Static bearer keys are an acceptable v1; a query parameter is not.

---

## Endpoint-level issues

### `PATCH /v1/orders/{id}` takes the full object and replaces it

Two distinct problems.

**The method is wrong.** `PATCH` means "apply this partial modification" (RFC 5789). Full replacement is `PUT`. Partners read the method name, send three fields, and lose the other twenty. Every HTTP-literate developer on the other side will get this wrong, and the ones who get it right will have gotten it wrong once first.

**Full replacement on a mutable resource has a lost-update problem.** The pattern is GET, modify one field locally, PUT back. If anything changed server-side between the GET and the PUT (a status transition, a fulfillment event, a concurrent update from your own dashboard or another partner integration), the PUT silently overwrites it with stale data. No error, no warning, just reverted state. This is a genuinely hard bug to diagnose from either side.

Recommendation:

1. Offer `PATCH` with true partial semantics: `application/merge-patch+json` (RFC 7386) is the well-specified choice, with the caveat that explicit `null` means delete-the-field. Document that clearly, including how it interacts with optional fields.
2. Require optimistic concurrency. Return an `ETag` on `GET`, require `If-Match` on mutations, and return `412 Precondition Failed` on mismatch. A monotonic `version` integer in the body works too if you prefer it, but pick one and require it. The failure mode of not requiring it is silent data loss.
3. Name the **server-owned fields** explicitly (`id`, `status`, `totals`, `created_at`, `updated_at`, refund aggregates) and decide what happens when a client sends them. Ignoring them silently trains partners to believe they can set status. Rejecting with `422` is the safer default and surfaces misunderstanding immediately.
4. Define which fields are mutable **at all, and in which states**. Editing line items on a shipped order is not a validation question, it is a state-machine question. Answer it in the spec, not in a support thread.
5. Do not model state transitions as field writes. `PATCH {status: "cancelled"}` looks convenient and turns into an unauditable mess. Use an explicit action endpoint (`POST /v1/orders/{id}/cancel`) that can validate the transition, take an idempotency key, record a reason, and emit an event. A separate `cancel` endpoint is also missing from this surface entirely; refund is not cancel, and partners need both.

### `GET /v1/orders?page=N` with fixed 50 per page, newest first

**Offset pagination over a newest-first list is unstable by construction.** New orders arrive at the front while a partner walks pages. Everything shifts forward by one, so page 2 re-serves an item the partner already saw on page 1, and an item slides past the boundary unseen. For a partner doing nightly reconciliation against a busy store, this produces both duplicates and **silently missing orders**. The missing ones are the problem, because nothing in the response indicates loss.

Offset also degrades on the database side: `OFFSET 50000` makes the engine walk and discard 50,000 rows on every request, so your slowest queries are the deep pages a backfilling partner hits hardest.

Fix: cursor (keyset) pagination.

```
GET /v1/orders?limit=100&cursor=eyJpZCI6...
{
  "data": [ ... ],
  "has_more": true,
  "next_cursor": "eyJpZCI6Im9yZF8xMjMiLCJjcmVhdGVkX2F0IjoiMjAy..."
}
```

- Keep the cursor **opaque** (base64 of an internal tuple). If partners can parse it, they will construct it, and you can never change the encoding.
- Sort on a **stable, unique** key. `created_at` alone is not unique; use `(created_at, id)` as the tiebreak or you will drop rows at page boundaries under same-timestamp inserts.
- Return a `4xx` on an expired or malformed cursor rather than silently restarting from the beginning.

Other gaps on this endpoint:

- **`limit` is not configurable.** Expose it with a documented default and maximum (say default 50, max 200). Fixed 50 forces 20x the request volume on any partner doing a backfill, which is bad for both sides.
- **No filtering.** Partners need `status`, `created_after` / `created_before`, `updated_after`, `customer_id`, and an external reference lookup at minimum. Without them, the only way to answer "which orders changed today" is to page the entire collection, which is exactly the traffic pattern that will make you add rate limits and then have an awkward conversation about them.
- **`updated_after` specifically** is what makes incremental sync possible. Without it, every partner polls everything forever.
- **No total count.** Decide deliberately: exact counts are expensive at scale, so either omit it (and say so) or offer it behind an opt-in parameter. Do not leave partners guessing.
- **Consider an expansion parameter** (`?expand=refunds,customer`) so partners are not forced into N+1 request patterns to render a single screen.

---

## Missing entirely

These are not defects in what you wrote; they are the parts of a partner-facing contract that are absent, and absence is what generates support load.

**Webhooks.** There is no way for a partner to learn that an order changed. Every integration therefore becomes a polling loop against the list endpoint, which is the single largest driver of load on APIs shaped like this one. Ship `order.created`, `order.updated`, `order.cancelled`, `refund.succeeded`, `refund.failed` with HMAC signatures over the raw body, a timestamp in the signed payload to prevent replay, documented retry with exponential backoff, and at-least-once delivery semantics stated out loud (so partners know to dedupe on event ID). Webhooks are hard to retrofit because the polling integrations stay forever.

**Money representation.** Unspecified, and this is a correctness issue, not a style one. Use integer **minor units** plus an ISO 4217 currency code (`{"amount": 1999, "currency": "USD"}`). Never a float, never a bare decimal string without currency. Also document zero-decimal currencies (JPY) and three-decimal ones (KWD) if you support them, because `amount / 100` is wrong for both.

**Rate limits.** Publish them. Return `429` with `Retry-After`, and include `RateLimit-Limit` / `RateLimit-Remaining` / `RateLimit-Reset` on every response so partners can self-throttle instead of discovering the ceiling in production.

**Versioning policy.** `/v1` in the path is a version number, not a policy. Write down what counts as a breaking change (removing a field, narrowing a type, adding a required parameter, changing an error code), what does not (adding an optional field, adding an enum value), how long v1 is supported after v2 ships, and the deprecation notice period. Then tell partners to **ignore unknown fields** so additive changes are safe, and state whether *you* reject unknown fields on input. Unknown-field policy in both directions belongs in the spec.

**Enum extensibility.** If `status` is an enum, say now whether you may add values, and instruct partners to handle unrecognized values gracefully. Otherwise adding `partially_refunded` later crashes a partner's switch statement.

**Timestamps.** RFC 3339, UTC, with explicit offset (`2026-09-19T14:03:22Z`). Say it in the spec.

**IDs.** Document them as opaque strings with a maximum length. Do not expose sequential integers: they leak order volume to every partner and invite enumeration. Prefixed IDs (`ord_`, `ref_`) help debugging and prevent partners from passing a refund ID where an order ID goes.

**Authorization scoping and the 404-vs-403 decision.** Nothing here says what happens when partner A requests partner B's order ID. Return `404`, not `403`: a `403` confirms the ID exists and turns your ID space into an enumerable inventory. Make sure every single-resource route filters by the authenticated partner in the query itself, not in a check after the fetch.

**An OpenAPI spec.** Machine-readable, published, and treated as the source of truth rather than as documentation generated after the fact. It is what partners generate clients from and what you can contract-test against. Pair it with a sandbox and a working curl example per endpoint.

**Partner-side operational guidance.** Recommended timeout, which status codes to retry (`429`, `500`, `502`, `503`, `504`), which never to retry (`4xx` other than 429), backoff with jitter, and the reminder that a timeout means *unknown*, not *failed*. This paragraph prevents a meaningful share of incidents.

---

## Revised surface

```
Auth:    Authorization: Bearer sk_live_...        (never in the query string)
Headers: Idempotency-Key (required on all writes)
         If-Match (required on mutations)
         X-Request-Id echoed on every response

POST   /v1/orders                  201 + Location; 422 with field errors; idempotent
GET    /v1/orders/{id}             200 + ETag; 404 for not-yours
PATCH  /v1/orders/{id}             merge-patch+json, partial only, If-Match required, 412 on stale
POST   /v1/orders/{id}/cancel      explicit transition, validated, idempotent
GET    /v1/orders                  cursor pagination, configurable limit, filters:
                                     status, created_after/before, updated_after, customer_id
POST   /v1/orders/{id}/refunds     201, creates a refund resource, amount + currency + reason,
                                     idempotent, server-enforced refund ceiling, 409 when exhausted
GET    /v1/orders/{id}/refunds     list
GET    /v1/refunds/{id}            one

Webhooks: order.created, order.updated, order.cancelled,
          refund.succeeded, refund.failed  (HMAC-signed, retried, at-least-once)
```

---

## Suggested order of work

1. **Status codes and the error envelope.** Highest blast radius, and every other fix depends on having somewhere to report failure.
2. **Auth to the `Authorization` header.** Smallest change, largest security payoff, and irreversible once keys are in partner logs.
3. **Idempotency on refunds, plus the server-side refund ceiling.** This is the one that costs money when it goes wrong.
4. **Idempotency on order creation.**
5. **Cursor pagination, plus `limit` and filters.** Do this before partners write pagination loops; after, you are maintaining both.
6. **PATCH semantics and `If-Match`.**
7. **Webhooks, money format, rate-limit headers, versioning policy, OpenAPI spec, sandbox.**

Items 1 through 6 are all breaking changes. Shipping them before partners integrate costs some engineering time. Shipping them after costs a v2, a migration window, and dual-running both behaviors for as long as your slowest partner takes to move.

