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
