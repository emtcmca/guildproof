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
