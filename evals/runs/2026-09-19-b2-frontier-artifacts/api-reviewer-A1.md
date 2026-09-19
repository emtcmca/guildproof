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
