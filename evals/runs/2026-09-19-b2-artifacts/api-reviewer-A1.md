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
