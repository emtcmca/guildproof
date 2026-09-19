=== OUTPUT W ===

## Contract
- **POST /v1/orders** — creates an order; returns 200 with `{ "error": "..." }` in body on validation failure
- **PATCH /v1/orders/{id}** — full replace of order object at given ID
- **GET /v1/orders?page=N** — list orders, 50 per page, newest first
- **POST /v1/orders/{id}/refund** — refunds the order; calling twice refunds twice
- **Auth** — API key passed as `?key=` query parameter

---

## Findings (severity-first)

❌ **CRITICAL — HTTP 200 on validation failure breaks client contracts**
- POST /v1/orders returns 200 with error in body, not 4xx. Clients check status codes to know whether a request succeeded. Returning 200 tells every HTTP client "success" while the body says "failed," splitting the truth. Proxies, caches, and retry logic will treat it as success.
- **Fix:** Return 400 (bad request) or 422 (unprocessable entity) with error body on validation failure.

❌ **CRITICAL — Refund endpoint is non-idempotent; retries cause double-charges**
- POST /v1/orders/{id}/refund spec says "calling it twice refunds twice." Networks duplicate requests routinely on timeouts. A client retry after a network stall will refund the order twice. Crediting the customer twice is a data-loss and revenue issue.
- **Fix:** Make refund idempotent using an idempotency key (client supplies a UUID; server returns same result on repeat keys within a window). Or: implement atomic state machine where refund can only move from "pending" → "refunded," never fire twice.

❌ **CRITICAL — Query-parameter API key is logged and exposed**
- Auth: ?key= in URL gets logged by every proxy, load balancer, CDN, browser history, referrer headers, and server access logs. A single leaked access log exposes all API keys.
- **Fix:** Use Authorization header with Bearer token. Always enforce HTTPS.

❌ **CRITICAL — No authorization checks mentioned; probable IDOR**
- PATCH /v1/orders/{id} — can caller A modify caller B's order by changing the id? No mention of user ownership checks.
- POST /v1/orders/{id}/refund — can caller A refund caller B's order?
- GET /v1/orders?page=N — returns 50 orders per page. Does it return *all* orders in the system, or only the authenticated user's? If all orders, this is a data leak.
- **Fix:** Every endpoint must verify the authenticated user owns the resource before granting access. Add user_id to order table; filter GET to `WHERE user_id = authenticated_user_id`; validate ownership on PATCH and refund.

❌ **HIGH — Unbounded pagination enables expensive queries**
- GET /v1/orders?page=9999999 will scan or fetch 50 orders from a huge offset, or if offset-based, cause full-table scans on the database.
- **Fix:** Paginate using cursor (primary key) not offset. Set a max page size (e.g., page 10000 max) and reject requests beyond it.

❌ **HIGH — No rate limiting; endpoint is DoS-able**
- Nothing prevents a single client from hammering POST /v1/orders or GET /v1/orders?page=1000 continuously.
- **Fix:** Add per-API-key rate limits (e.g., 100 requests/minute). Implement request signing or nonce to prevent replay.

⚠️ **MEDIUM — PATCH full-replace semantics risks concurrent-update bugs**
- PATCH /v1/orders/{id} takes the full order object and replaces it. If two clients fetch the same order, both modify it, and both patch, the second write wins and the first client's changes are lost (lost update problem).
- **Fix:** Use PATCH semantics that merge (partial update), or add a version/ETag field so the second PATCH rejects with 409 Conflict if the object changed since fetch.

⚠️ **MEDIUM — Error messages in 200 response leak structure**
- Returning `{ "error": "..." }` in a 200 status code means error messages are visible and logged. If the message says "Credit card number must be valid," attackers learn the data model. Secrets or stack traces in error messages expose internals.
- **Fix:** Return 4xx with generic error message to clients; log detailed error server-side for debugging.

⚠️ **WEAK — No mention of HTTPS enforcement**
- Query parameter auth over HTTP is plaintext credential transmission.
- **Fix:** Document that all calls must use HTTPS and reject (or log) any HTTP request.

---

## Highest-severity issue
**Non-idempotent refund endpoint will cause double-refunds on network retries; query-parameter auth leaks credentials to logs and browser history; IDOR on all endpoints (no authorization checks); HTTP 200 on validation failure breaks HTTP semantics.**

---

## Confirm these
1. **Is there per-user ownership filtering on GET /v1/orders?** Confirm the query returns only authenticated user's orders, not all orders in the system.
2. **Is there authorization middleware enforcing user ownership on PATCH and refund?** Confirm the code validates `order.user_id == authenticated_user_id` before allowing modification.
3. **Is HTTPS enforced?** Confirm the API rejects or logs HTTP requests and documents HTTPS-only.
4. **Are there input validation and size limits?** What fields are required? What's the max order object size? Unbounded inputs can exhaust memory.
5. **Is there rate limiting or request signing?** Confirm the API is protected against spam and replay attacks.


=== OUTPUT X ===

# API Review — Pre-Partner Release

## Critical Issues

### 1. Validation Errors Return HTTP 200 (Wrong Status Code)
**POST /v1/orders** returns 200 with `{ "error": "..." }` on validation failure. This violates HTTP semantics and breaks client-side error handling.

**Fix:** Return 400 (Bad Request) or 422 (Unprocessable Entity) with the error body. HTTP 200 means success; errors need appropriate 4xx codes.

---

### 2. Refund Endpoint Allows Duplicate Refunds (Financial Integrity Risk)
**POST /v1/orders/{id}/refund** can be called twice, causing duplicate refunds. This is a critical bug.

**Fix:** Make refund idempotent — return 200 if already refunded, or reject with 409 (Conflict) / 400 (Bad Request) on the second attempt. Store refund state on the order and check it before processing.

---

### 3. API Key in Query Parameter (Security Vulnerability)
**Auth: `?key=` query parameter** exposes credentials in logs, browser history, and referrer headers.

**Fix:** Move to `Authorization: Bearer <key>` header instead. Query parameters are not private; headers are stripped from logs by standard HTTP tooling.

---

## Moderate Issues

### 4. PATCH Endpoint Semantics Unclear
**PATCH /v1/orders/{id}** "takes the full order object and replaces it" — this is actually PUT semantics (full replacement), not PATCH (partial update). Callers won't know which fields are required, what happens to fields they omit, or if the response body returns the updated order.

**Fix:** Clarify the contract — if full replacement, use PUT instead. If partial update, document which fields can be modified and what happens to omitted fields (preserved or deleted?). Document the response format.

---

### 5. Pagination Incomplete
**GET /v1/orders?page=N** lacks:
- Whether `page` is 1-indexed or 0-indexed
- What happens if N is out of range (return empty? 404?)
- Total count of orders or page count (for client UI pagination)
- Whether it's stable (cursor-based pagination is safer for fast-changing data)

**Fix:** Document the indexing scheme, add `total` and `page_count` to the response metadata, or switch to cursor-based pagination.

---

### 6. Page Size Not Configurable
**Hardcoded 50 orders per page** may not suit all use cases (mobile clients want fewer, bulk operations want more).

**Fix:** Accept optional `limit` or `per_page` query parameter with a documented max (e.g., 100).

---

## Recommendations Before Publishing

1. **Add response format documentation** — what fields are in the order object? What are their types?
2. **Define error response schema** — how are non-validation errors returned (500s, etc.)?
3. **Add HTTP status code table** — document all possible responses per endpoint (200, 201, 400, 404, 409, 500, etc.).
4. **Add rate limiting info** — how many requests per minute are allowed?
5. **Version the API** — `/v1/` is good; stick with it and document deprecation policy.

---

## Go/No-Go Recommendation

**NO-GO for partner release.** Issues #1, #2, and #3 are blockers. Fix those three, then circle back on #4–#6.


=== OUTPUT Y ===

# API Review Findings

## Critical Issues (Block Publication)

### 1. POST /v1/orders returns 200 on validation failure
**Status:** 200 with `{ "error": "..." }` is not HTTP-compliant. Validation failures must return 4xx (400 Bad Request).

**Impact:** Clients checking only status codes will treat failures as success. This breaks error handling.

**Fix:** Return 400 with error body. Example: `POST /v1/orders returns 400 { "error": "Invalid field: email", "field": "email" }`

---

### 2. POST /v1/orders/{id}/refund is not idempotent
**Status:** Calling twice refunds twice. This is a severe bug.

**Impact:** Network retry, browser back-button, or user double-click causes unintended duplicate refunds. Partners will lose money or gain customer complaints.

**Fix:** Refund operations must be idempotent. Calling the same endpoint with the same request twice should produce the same result (idempotent key pattern, or refund state tracking). Example: `POST /v1/orders/{id}/refund with an idempotency_key header or body field`.

---

### 3. API key in query parameter (?key=)
**Status:** Query parameters are logged in access logs, browser history, and forwarding proxies.

**Impact:** API keys will be exposed in logs and caches. Partners' credentials become vulnerable.

**Fix:** Move to HTTP Authorization header: `Authorization: Bearer <api_key>` or `Authorization: ApiKey <api_key>`.

---

## Major Issues (Fix Before Publishing)

### 4. PATCH semantics incorrect
**Status:** PATCH should update fields, not replace the entire object. Full replacement is PUT.

**Impact:** Clients following REST conventions will be confused or use the wrong method.

**Fix:** 
- Use `PUT /v1/orders/{id}` for full replacement (requires all fields).
- Use `PATCH /v1/orders/{id}` for partial updates (only changed fields sent).

---

### 5. Insufficient error documentation
**Status:** No error codes, error types, or list of possible error messages.

**Impact:** Partners cannot implement proper error handling or display meaningful messages to users.

**Fix:** Document error scenarios. Example:
```
POST /v1/orders can return:
- 400: validation_error (invalid field, missing required field)
- 400: insufficient_funds (account balance too low)
- 409: order_duplicate (order already exists for this reference)
- 500: internal_error (transient, retry after 5 seconds)
```

---

### 6. Pagination response structure undefined
**Status:** GET /v1/orders?page=N returns 50 items per page, but no metadata about total, has_more, or current_page.

**Impact:** Partners cannot build correct pagination UI or know when to stop fetching.

**Fix:** Document response structure. Example:
```json
{
  "data": [ { order }, ... ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 1240,
    "has_more": true
  }
}
```

---

## Minor Issues (Should Fix)

### 7. No rate limiting documented
**Status:** No mention of rate limits, quotas, or throttling.

**Impact:** Partners don't know how much they can call the API; may trigger rate limits unexpectedly.

**Fix:** Document rate limits: "100 requests per minute per API key; returns 429 when exceeded."

---

### 8. No field validation rules for PATCH
**Status:** "Takes the full order object" is vague. What fields are required? Can all fields be updated?

**Impact:** Partners won't know which fields are mutable or what constraints exist.

**Fix:** Document mutable fields and constraints. Example: `PATCH /v1/orders/{id}: can update customer_email, shipping_address, items; cannot update order_total or status.`

---

### 9. No ordering clarity for GET
**Status:** "Newest first" — but newest by what? Created date? Updated date?

**Impact:** Partners may get inconsistent results if the server's "newest" definition changes.

**Fix:** Clarify: "Ordered by created_at DESC (newest creation date first)."

---

### 10. No versioning deprecation strategy
**Status:** v1 exists, but no plan for v2 or how breaking changes are handled.

**Impact:** When you need to change the API, partners won't know what to expect.

**Fix:** Publish versioning policy: "Major version bumps for breaking changes (e.g., v2). v1 will be sunset on [DATE] with 12 months notice."

---

## Summary

**Do not publish this API yet.** Issues #1, #2, #3, and #4 are breaking problems. Fix these first, then address #5 and #6. The minor issues are polish but should be resolved before partners begin integration.


=== OUTPUT Z ===

# API Review: Orders Service

## Contract

- **POST /v1/orders** — Creates an order. Input: order object (undefined schema). Output: 200 with `{ "error": "..." }` on validation failure, or (implied) order object on success. Side effect: creates order record.
- **PATCH /v1/orders/{id}** — Replaces order. Input: full order object. Output: (not specified). Side effect: overwrites the resource.
- **GET /v1/orders?page=N** — Lists orders, 50 per page, newest first. Pagination: query-based. Output: (not specified).
- **POST /v1/orders/{id}/refund** — Refunds order. Input: (not specified). Output: (not specified). Side effect: applies refund; non-idempotent.
- **Auth:** API key in `?key=` query parameter.

---

## Findings

❌ **CRITICAL — POST returns 200 on validation failure.** Clients must parse response body to know success from failure. Should return 400 Bad Request. Status codes are the contract; hiding failure in the body breaks every standard HTTP client and monitoring tool.

❌ **CRITICAL — API key in query parameter.** Keys are logged in server logs, proxy logs, browser history, and referrer headers. Move to `Authorization: Bearer <key>` or `X-API-Key` header. This is a credential leak on every request.

❌ **CRITICAL — Refund is non-idempotent.** Calling `POST /v1/orders/{id}/refund` twice refunds twice. Networks duplicate packets; clients retry on timeout. This is data loss / financial impact. **Fix:** make it idempotent — check if already refunded before applying a second one, or use an idempotency-key header to deduplicate requests.

❌ **HIGH — No authorization check visible on PATCH.** What stops caller A from patching caller B's order? Full-object replacement means overwriting any field (amount, status, owner). **Confirm:** Is there per-record authorization middleware? If not, add a check: `if order.user_id != caller.user_id return 403`.

❌ **HIGH — No authorization check visible on GET.** What stops one caller from listing all orders? Pagination doesn't filter by ownership. **Confirm:** Does auth middleware filter results? If not, add `WHERE user_id = ?` to the list query.

❌ **HIGH — No authorization check visible on POST /refund.** Can any authenticated caller refund any order? No mention of order ownership check. **Confirm:** authorization exists. If not, add ownership check before applying refund.

⚠️ **MEDIUM — GET pagination unbounded.** No limit on `page=N`. Caller can request `page=999999` and force a table scan. Add `MAX_PAGE=1000` or use cursor-based pagination. Also undocumented: does the sort order change between requests if new orders arrive? (TOCTOU race).

⚠️ **MEDIUM — PATCH field validation undefined.** Does order require certain fields (e.g., amount)? What happens if a required field is missing? Can you patch immutable fields like `created_at` or `id`? No schema, no validation rules. **Fix:** document required fields, mark immutable fields, return 400 if required fields are missing.

⚠️ **MEDIUM — POST validation rules not specified.** What makes an order "valid"? Empty order? Negative amount? Missing customer? No validation contract. **Fix:** document all validation rules in one place.

⚠️ **MEDIUM — Refund response codes undefined.** What if order doesn't exist? Returns 404? What if already refunded and you're calling it a second time? Returns 200 again (because it succeeds twice)? Undocumented. **Fix:** document all response codes and the error shape for each.

⚠️ **MEDIUM — No rate limiting mentioned.** API key is the only auth. No mention of per-key rate limits. Can be abused. **Fix:** add rate limiting by key, document limits.

✅ **Input validation — assume validated upstream or missing.** The message says nothing about input sanitization. Flag as confirm-item.

---

## Highest-Severity Issue

**Non-idempotent refund combined with no authorization check and status-code hiding on create: you can refund any order twice by accident and never know it failed because POST lies about success.** Fix the refund idempotency, move auth to the API boundary (not middleware assumptions), and use correct HTTP status codes.

---

## Confirm These

1. Is per-record authorization enforced in unshown middleware for PATCH, GET, and `/refund`? (Assume no; if yes, state it explicitly.)
2. Is input validation (required fields, type checking, ranges) enforced in unshown middleware for POST? (Assume no; if yes, document the contract.)
3. Does GET filter results to the caller's own orders, or do all authenticated callers see all orders?
4. What error shape is returned on non-2xx status codes? (e.g., `{ "error": "...", "code": "..." }` or something else?)
5. Are idempotency keys supported anywhere in the contract? (Not mentioned for refund.)

