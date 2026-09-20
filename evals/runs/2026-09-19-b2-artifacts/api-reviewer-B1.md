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
