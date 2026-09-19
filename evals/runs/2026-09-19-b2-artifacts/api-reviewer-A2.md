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
