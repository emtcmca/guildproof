## VERDICT: NOT VERIFIED — BLOCKING: yes

**Independence:** NOT INDEPENDENT — I wrote the artifact earlier in this conversation and read my own reasoning, so I inherited its blind spots.

---

## Observable Evidence

### ✅ Authorization / IDOR — axis clean
- WHERE clause enforces `i.org_id = $2`, binding to the caller's org_id from req.user
- oneOrNone() returns null for both "invoice missing" and "wrong org" cases
- Same 404 response for both, per contract ✅

### ❌ CRITICAL: PII and internal fields leaked in response
The query selects:
```
i.id, i.org_id, i.customer_id, i.number, i.amount_cents, i.status, i.due_date,
c.name as customer_name, c.email as customer_email, c.tax_id
```

The endpoint does `res.json(invoice)`, returning the entire object.

**Contract requires:** `{ id, number, amount_cents, status, due_date, customer_name }`

**What actually leaves the server:**
- `org_id` — internal implementation detail ❌
- `customer_id` — internal implementation detail ❌
- `customer_email` — customer PII ❌
- `tax_id` — customer PII ❌

The contract explicitly states: "Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id)."

This is a direct contract violation. Severity: **HIGH** — active PII leak.

### ✅ Malformed ids do not produce 500
- Parameter id from req.params.id is passed as $1 to parameterized query
- pg-promise escapes and validates; string "abc" compared to integer column returns 0 rows, not an error
- Returns 404, not 500 ✅

### ⚠️ Assessment: org_id from middleware not validated
- org_id comes from req.user, set by requireSession() middleware
- Code assumes middleware guarantees org_id is a valid integer
- If middleware is broken or missing validation, malformed org_id could reach the query
- Verdict depends on middleware implementation (not shown)
- **If middleware is correct:** non-issue. **If not:** could bypass the org check or produce 500.

---

## Defects

❌ **HIGH — PII and internal fields leaked in response**
- **Contract breach:** Response includes org_id, customer_id, customer_email, tax_id; contract forbids all four
- **How to demonstrate:** Call the endpoint, observe the response body includes fields not in the contract DTO
- **Impact:** Leaks customer tax_id (PII) and email (PII); exposes internal IDs that could enable other attacks
- **Fix required:** SELECT only the fields in the contract; filter the response object before res.json(), or use a database view/stored procedure that returns only the contract fields

---

## Claimed vs. Actual

**Producer claim:** "Ship it" (production-ready)

**Reality:** Returns 5 fields not in the contract, including customer PII (email, tax_id) and internal implementation details (org_id, customer_id).

---

## Confirm-these

1. **requireSession() middleware behavior** — Does it validate org_id as an integer? If org_id is not validated, malformed org_id could reach the query. Verdict assumes middleware is correct.

---

## Summary

The authorization and 404 handling are correct. Malformed input handling is safe. However, the endpoint violates its contract by leaking customer PII (email, tax_id) and internal implementation details (org_id, customer_id) in every response. This is a blocking defect that must be fixed before merge.

**Single most damaging defect:** res.json(invoice) returns the entire database row instead of filtering to the contract shape, leaking PII and breaking the contract.
