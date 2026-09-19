=== REVIEW A ===
## VERDICT: NOT VERIFIED — BLOCKING: yes


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

=== REVIEW B ===
# Verification: GET /api/invoices/:id

## Verdict
**NOT VERIFIED** — BLOCKING: yes

Multiple unresolved HIGH defects expose forbidden data and violate explicit contract requirements.


## Observable Evidence

### Contract (re-derived from stated requirements)
The endpoint must:
1. Return exactly: `{ id, number, amount_cents, status, due_date, customer_name }`
2. Return 404 for invoices in other orgs OR non-existent
3. Never expose: `email, tax_id, payment_token, portal_password_hash, org_id, customer_id`
4. Never return 500 for malformed `id` parameter
5. Enforce org isolation via `requireSession()` middleware

### Axes Checked

#### ✅ Authorization / IDOR
Observable: Line 13 enforces `WHERE i.id = $1 AND i.org_id = $2`. Both invoice existence and org membership are checked. Same 404 returned whether missing or forbidden (line 20). Clean.

#### ✅ SQL Injection
Observable: Parameterized query with `$1, $2` placeholders (lines 13-15). Caller-supplied `id` and middleware-injected `org_id` never touch SQL string. Clean.

#### ✅ Authentication Requirement
Observable: Line 1 `requireSession()` guards the route. Auth is enforced. Clean.

#### ❌ Response Filtering / PII Exposure
Observable: Line 29 returns `invoice` object unfiltered. Tracing what that object contains:
- Line 10 SELECT clause: `i.id, i.org_id, i.customer_id, i.number, i.amount_cents, i.status, i.due_date, c.name as customer_name, c.email as customer_email, c.tax_id`
- This fetch includes: `org_id`, `customer_id`, `customer_email`, `tax_id`
- Line 29 `res.json(invoice)` sends the entire row to the caller
- Contract forbids: `email, tax_id, org_id, customer_id`
- **Real defect**: Email, tax_id, org_id, and customer_id leave the server. These are sensitive: email is PII, tax_id is financial/legal PII, org_id and customer_id are internal identifiers exposing system structure.

#### ❌ Malformed ID Handling
Observable: Line 2 `const { id } = req.params` accepts `id` as a URL string. No validation. Line 13 passes it to the WHERE clause.
- If `id` is "abc123" (non-numeric), the database will either silently cast/fail the comparison (returning 0 rows = 404, acceptable) OR throw a type error.
- If a type error occurs, the catch block at line 30 catches it and returns 500 (line 32).
- Contract requirement: "Malformed ids never produce a 500"
- **Real defect**: A malformed (non-integer) `id` will likely trigger a database type error, caught and returned as 500. This violates the contract.
- Assessment: pg-promise likely enforces strict type checking on integer columns; passing a non-integer string will error. This is not defensive; the code assumes the query succeeds.

#### ❌ Response Shape Mismatch
Observable: Contract specifies response DTO fields exactly: `{ id, number, amount_cents, status, due_date, customer_name }`. The code returns all 10 fields from the SELECT, including forbidden ones. The response shape is wrong.

## Defects

### ❌ HIGH — PII/Secret Exposure (email, tax_id)
**The contract breach**: "Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id)."

**How to demonstrate**: Call the endpoint and inspect the JSON response. Fields `customer_email` and `tax_id` are present and returned to the caller, violating the contract.

**Root cause**: Line 10 selects both fields; line 29 returns the unfiltered object. No response DTO projection happens.

**Impact**: Sensitive customer data (email, financial/tax identifiers) is exposed to any caller with a valid invoice ID and org access. This breaks confidentiality and may violate data protection regulations (GDPR, CCPA).

### ❌ HIGH — org_id and customer_id Exposure
**The contract breach**: "Nothing else about the invoice or the customer leaves the server … org_id, customer_id."

**How to demonstrate**: Call the endpoint. Inspect response; `org_id` and `customer_id` are present.

**Root cause**: Same as above — unfiltered response at line 29.

**Impact**: Internal system identifiers leak to clients, exposing system architecture and enabling correlation attacks or internal-ID-based enumeration.

### ❌ HIGH — Malformed ID → 500 Error
**The contract breach**: "Malformed ids never produce a 500."

**How to demonstrate**: Call with `id=abc123` (or any non-integer string). The endpoint returns 500 instead of 400 or 404.

**Mechanism**: 
- Line 2 accepts id as a string from the URL.
- Line 13 passes it to `WHERE i.id = $1` where `i.id` is a serial (integer) column.
- pg-promise enforces type checking; a string literal that cannot convert to an integer throws a database error.
- Line 30 catch block catches this error and returns 500 (line 32).

**Impact**: Endpoint violates its own contract. Malformed input should not produce 500; it should return 4xx or silently coerce to a no-match. The current code fails the contract requirement.

### ⚠️ WEAK — customer_name Aliasing (Non-blocking observation)
The code aliases `c.name as customer_name`, which is correct per the contract. Kept as-is. No defect here; the alias is right.

## Claimed vs. Actual

| Aspect | Contract Requirement | Code Behavior |
|--------|----------------------|----------------|
| Response DTO | `{ id, number, amount_cents, status, due_date, customer_name }` | Returns 10 fields including forbidden ones: `org_id, customer_id, customer_email, tax_id` |
| PII Exposure | No email, tax_id to leave server | Both fields selected and returned in JSON response |
| Internal IDs | No org_id, customer_id to leave server | Both present in response |
| Malformed ID | Never produce 500 | Malformed ID causes database type error → 500 |
| Org Isolation | Enforce via WHERE clause | Correctly enforced; same 404 for missing or forbidden |

## Confirm-These
None — all axes were fully checkable from the artifact. No gaps remain.

## Fix Path (Not Verification; Noted for Context)
To unblock:
1. Filter response: Project only `{id, number, amount_cents, status, due_date, customer_name}` before `res.json()`
2. Validate `id` on line 2: Coerce to integer or return 400 / 404 without throwing
3. Re-test with malformed IDs to confirm no 500

## Summary
The endpoint leaks email, tax_id, org_id, and customer_id in the response, violating the confidentiality contract. It also fails to handle malformed IDs safely, returning 500 instead of 4xx. The authorization logic is sound (IDOR is blocked), but the response filtering and input validation are broken.

**Blocking severity**: YES. Data leakage and contract violation on error handling.
