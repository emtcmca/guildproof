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
