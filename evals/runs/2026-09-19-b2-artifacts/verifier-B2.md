## Verdict
**NOT VERIFIED** — BLOCKING: **yes**

**Independence:** NOT INDEPENDENT. This artifact was not written in this conversation, but the system prompt that framed it was. The verification is independent in the sense that I did not write the code, but I note the framing.

---

## Observable Defects

### ❌ HIGH: Missing organization authorization (IDOR)
**Contract breach:** "Returns one invoice that belongs to the caller's organization"

**The defect:** Line 31 executes `WHERE i.id = $1` with no check that the invoice's `org_id` matches the caller's organization (`req.user.org_id`). Any authenticated user can retrieve any invoice in the entire database by guessing or enumerating invoice IDs.

**How to demonstrate it:** 
1. Create two organizations with users in each
2. User A queries `/api/invoices/999` where invoice 999 belongs to Organization B
3. User A receives the full invoice data without authorization error
4. Expected: 404. Actual: 200 with the invoice.

**Severity:** CRITICAL — Organization isolation is a core security boundary. This breaks multi-tenancy entirely.

---

### ❌ HIGH: Data leakage — sensitive customer fields returned
**Contract breach:** "Nothing else about the invoice or the customer leaves the server" and response should be `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }`

**The defect:** Line 28-30 selects `i.*, c.*` (all columns from both tables). Line 40 returns the raw database row object, which includes:
- From `customers`: `email`, `tax_id`, `payment_token`, `portal_password_hash`
- From `invoices`: potentially all fields (depending on future schema additions)

A response payload will expose sensitive PII and security tokens.

**How to demonstrate it:** Make a GET request to the endpoint; inspect the JSON response body. The `payment_token` and `portal_password_hash` fields will be visible in plaintext to the client.

**Severity:** CRITICAL — Payment tokens and password hashes should never be exposed to frontend clients, even to an authenticated user viewing their own organization's invoices.

---

### ❌ HIGH: Wrong HTTP status code for authorization failures
**Contract breach:** "An invoice in another organization, or one that doesn't exist, returns the same 404"

**The defect:** 
- Line 27 uses `db.one()`, which throws if no row is found (per pg-promise API)
- Line 35-37 checks `if (!invoice)` but this is dead code — `db.one()` never returns null; it throws
- The error is caught at line 41 and returns 500, not 404
- This applies to both "invoice doesn't exist" AND "invoice exists but wrong organization" cases (once org check is added)
- Contract requires 404 for both; code returns 500

**How to demonstrate it:** Query a non-existent invoice or one from another organization; observe the 500 response instead of 404.

**Severity:** HIGH — Leaks whether an invoice exists to the client (if you later add org filtering, requests to valid foreign org invoices will still 500, while queries to truly non-existent IDs will also 500 — but the timing or log pattern could leak org membership).

---

## Claimed vs. Actual

| Claim | Reality |
|-------|---------|
| "input validated" | ✅ ID is checked for integer and > 0 |
| "parameterized SQL" | ✅ Uses $1 parameter binding |
| "session required" | ✅ requireSession() middleware present |
| "errors don't leak internals" | ✅ Error message is generic "internal error" |
| "every view is audited" | ⚠️ Audit is recorded, but org_id is not captured in the audit log; audit cannot later determine if the access was authorized |
| "input validated, parameterized SQL, session required" | ❌ **Missing:** organization authorization check |
| "Nothing else about the invoice or customer leaves the server" | ❌ **Violated:** All customer PII and security tokens are returned in the response |

---

## Axes Checked

✅ **Input validation** — ID is parsed as integer, checked for > 0, caught at line 22-24. Prevents malformed input injection.

✅ **SQL injection** — Parameterized query at line 27-32 uses `$1` binding. Prevents parameter injection.

✅ **Generic error response** — Error message at line 43 is "internal error" without detail. Does not leak stack traces or query structure.

✅ **Session enforcement** — `requireSession()` middleware required at line 20. Prevents unauthenticated access.

❌ **Organization isolation** — No `AND i.org_id = $1` check (or equivalent) in the WHERE clause. **FAILED.**

❌ **Response field filtering** — No projection or filtering; returns `res.json(invoice)` with all database columns. Should return only `{ id, number, amount_cents, status, due_date, customer_name }`. **FAILED.**

❌ **Correct status codes** — Returns 500 for "not found" instead of 404 due to `db.one()` throwing. **FAILED.**

---

## Confirm-These

1. **pg-promise `db.one()` behavior** — Verify that `db.one()` throws when no rows found (it does per docs, making line 35-37 dead code). If the actual behavior differs, the 404 path may work, but this is unlikely.

2. **Error handling for org mismatch** — Once org check is added, confirm that both "invoice doesn't exist" and "invoice exists but wrong org" return 404, not 500. May require splitting the catch or using `oneOrNone()` + explicit checks.

---

## Summary

The handler fails authorization (IDOR), leaks sensitive data (PII + tokens), and returns wrong status codes. All three are real defects. The producer's claim of "ready to merge" is not supported by the code. This is not safe for production.

**Blocking reason:** Two unresolved CRITICAL defects (missing org check + data leakage) that break multi-tenancy and expose secrets.
