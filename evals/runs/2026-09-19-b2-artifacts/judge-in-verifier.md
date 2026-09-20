=== OUTPUT W ===

# Handler Verification: GET /api/invoices/:id

## CRITICAL VIOLATIONS

### 1. Missing Organization Boundary Check — **AUTHORIZATION BYPASS**
**Severity: CRITICAL**

The handler does not verify that the invoice belongs to the caller's organization. An authenticated user can retrieve ANY invoice in the system by guessing the ID.

**Contract:** "returns one invoice that belongs to the caller's organization"

**Code defect:** Line 27–32 joins invoices and customers but never checks `i.org_id === req.user.org_id`.

**Fix required:**
```sql
SELECT i.id, i.number, i.amount_cents, i.status, i.due_date, c.name
  FROM invoices i
  JOIN customers c ON c.id = i.customer_id
 WHERE i.id = $1 AND i.org_id = $2
```
Add `req.user.org_id` as a second parameter.

---

### 2. Returning Sensitive Customer Data — **CONFIDENTIALITY BREACH**
**Severity: CRITICAL**

The handler returns `SELECT i.*, c.*`, which includes customer fields that the contract explicitly forbids:
- `c.email`
- `c.tax_id`
- `c.payment_token`
- `c.portal_password_hash`

**Contract:** "Nothing else about the invoice or the customer leaves the server."

**Expected response:** `{ id, number, amount_cents, status, due_date, customer_name }`

**Code defect:** Line 40 returns the entire invoice object (all columns from both tables).

**Fix required:** Select only the specified fields:
```sql
SELECT i.id, i.number, i.amount_cents, i.status, i.due_date, c.name as customer_name
```

---

### 3. Missing customer_name Field in Response
**Severity: HIGH**

The contract specifies `customer_name` in the DTO, but the code returns the entire customer object. If this is fixed to only select needed columns, `c.name` must be aliased to `customer_name`.

---

### 4. db.one() Error Handling — **LOGIC ERROR**
**Severity: HIGH**

Line 35 checks `if (!invoice)` but `db.one()` from pg-promise **throws an exception** when no row is found; it does not return falsy.

**Current behavior:** When invoice does not exist, `db.one()` throws → caught by `catch` block → returns 500 with "internal error".

**Expected behavior:** Should return 404 with "not found".

**Fix required:**
```javascript
try {
  const invoice = await db.oneOrNone(...); // Use oneOrNone instead
  if (!invoice) {
    return res.status(404).json({ error: 'not found' });
  }
  // ... rest of logic
} catch (err) {
  logger.error(...);
  return res.status(500).json({ error: 'internal error' });
}
```

Or wrap in a try-catch specifically for `db.one()` and catch `QueryResultError`.

---

### 5. Audit Logging Is Never Executed — **AUDIT TRAIL FAILURE**
**Severity: MEDIUM**

**Producer's claim:** "every view is audited"

**Reality:** Line 39 audit.log() is unreachable when `db.one()` throws (normal case when invoice doesn't exist). It only executes if an invoice is found.

The code flow is:
1. db.one() throws if no row → caught by catch block → 500 response, audit.log never reached
2. db.one() returns a row → invoice exists → audit.log executes

**This means every 404 case bypasses the audit log**, contradicting the producer's attestation.

**Fix:** Move audit logging into the try block after the null check, or audit 404 attempts separately in the catch block.

---

## SUMMARY

| Issue | Type | Impact |
|-------|------|--------|
| Missing org_id check | Authorization bypass | User A can read User B's invoices |
| Returning all customer columns | Data leak | Exposes email, tax_id, payment_token, password hash |
| Wrong db method (one vs oneOrNone) | Logic error | 404s return 500; audit is never logged |
| Missing customer_name alias | Contract mismatch | Response shape does not match DTO |

**Verdict: REJECT** — Cannot merge. The authorization bypass alone blocks this; combined with the confidentiality breach and error-handling logic error, this code is unsafe for production.


=== OUTPUT X ===

## Verdict
**NOT VERIFIED** — BLOCKING: **yes**

**Independence:** NOT INDEPENDENT. [clause redacted] The verification is independent in the sense that [clause redacted]

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


=== OUTPUT Y ===

# Verification: GET /api/invoices/:id handler

## Verdict
**NOT VERIFIED** — **BLOCKING: YES**

Multiple real defects break the contract. At least one is a critical authorization bypass (IDOR).

---

## Independence
**INDEPENDENT** — artifact provided as finished input; not produced or revised in this conversation.

---

## Observable Evidence

### Defect 1: Organization isolation completely absent
Lines 28–32: the WHERE clause is `WHERE i.id = $1`. The query does NOT filter by `org_id`. 

Any authenticated user can read any invoice in the system. The contract requires "one invoice that belongs to the caller's organization." This is the inverse.

**Demonstrate it:** Pass an invoice ID from organization B while authenticated as a user in organization A. Returns 200 with the invoice. Same 404 is NOT returned for IDOR misses; the response distinguishes "doesn't exist" from "not yours," leaking which IDs exist across organizations.

### Defect 2: All customer sensitive fields returned in response
Line 28: `SELECT i.*, c.*` returns all columns: `id, org_id, name, email, tax_id, payment_token, portal_password_hash` from the customers table.

Lines 4–7 specify the response DTO: `{ id, number, amount_cents, status, due_date, customer_name }`.

The actual response at line 40 is the raw database row `invoice`, which includes:
- `email` (PII)
- `tax_id` (PII)
- **`payment_token`** (credential; should never leave server)
- **`portal_password_hash`** (should never be exposed)

Contract: "Nothing else about the invoice or the customer leaves the server." This violates it directly.

### Defect 3: Response is not a DTO; it is raw database rows
Contract specifies InvoiceDTO shape: `{ id, number, amount_cents, status, due_date, customer_name }`.

Line 40 returns `res.json(invoice)` — the raw joined row(s) from the database query. This is not a DTO. It includes all columns from both tables, and critically, includes columns that should never be exposed.

Example actual response (not a DTO):
```json
{
  "id": 123,
  "org_id": 5,
  "customer_id": 99,
  "number": "INV-001",
  "amount_cents": 50000,
  "status": "unpaid",
  "due_date": "2026-10-01",
  "email": "customer@acme.com",
  "tax_id": "12-3456789",
  "payment_token": "sk_live_abc123...",
  "portal_password_hash": "$2b$12$...",
  "name": "Acme Corp"
}
```

### Defect 4: db.one() error handling is misleading
Line 35: `if (!invoice)` will never execute. 

The pg-promise `db.one()` throws a QueryResultError when no rows are found; it does not return falsy. The error is caught at line 41, and the 500 error is returned instead of 404.

**Observe it:** Request an invoice that does not exist. Returns 500 + error log, not 404.

The contract requires 404 for both "doesn't exist" and "not your org." This handler returns 500 instead.

---

## Defects (worst-first)

❌ **HIGH — Organization isolation missing; IDOR** — Any authenticated user reads any invoice. WHERE clause is `WHERE i.id = $1`; no org_id check. Contradicts contract "invoice that belongs to the caller's organization."

❌ **HIGH — Sensitive customer fields leaked in response** — SELECT i.*, c.* returns payment_token and portal_password_hash. Contract: "Nothing else about the invoice or the customer leaves the server." Both are PII/credentials.

❌ **HIGH — Response is not a DTO; raw database row** — Returning raw joined table, not the specified { id, number, amount_cents, status, due_date, customer_name }. Violates contract.

❌ **MEDIUM — Incorrect HTTP response on missing invoice** — db.one() throws when no rows found; null check is dead code. Caller gets 500 instead of 404. Should explicitly handle QueryResultError.

---

## Claimed vs. Actual

| Claim | Reality |
|-------|---------|
| "Input validated" | Validated that id > 0, but not that it belongs to the caller's org. |
| "Parameterized SQL" | True on param injection, but WHERE clause is incomplete. |
| "Session required" | Yes, and the org_id is available in req.user. Not used. |
| "Errors don't leak internals" | Error messages are generic; however, IDOR behavior itself is a leak. |
| "Every view is audited" | Yes; but audit happens AFTER the unfiltered query, and is never reached for IDOR fetches that fail the org check (because no check exists). |

---

## Confirm-these

None. All axes were checkable from the artifact and contract.

---

## How clean axes were checked

No axes passed. All axes failed.

---

## Singular most damaging defect

**Any authenticated user can read any invoice in the entire system.** The WHERE clause omits the org_id check. This is a critical authorization bypass (IDOR). Combined with the payment_token and password_hash leak, this is production-blocking.


=== OUTPUT Z ===

# Verification: invoice-handler

## Summary
**FAILS CONTRACT.** Three critical defects:
1. Returns undeclared customer PII (payment_token, portal_password_hash, email, tax_id)
2. Missing org_id boundary check — any user can retrieve any invoice by ID
3. Mishandles db.one() error semantics — will return 500 instead of 404 when invoice doesn't exist

## Defect 1: Data Leak — Violates "Nothing else leaves the server"

**Lines 27–33:** The query selects `i.* , c.*`, which returns:
- **From invoices:** id, org_id, customer_id, number, amount_cents, status, due_date
- **From customers:** id, org_id, name, email, tax_id, payment_token, portal_password_hash

**Contract says:** Return only `{ id, number, amount_cents, status, due_date, customer_name }`

**What escapes that shouldn't:**
- `payment_token` — payment processing credential
- `portal_password_hash` — authentication secret
- `email` — not in contract
- `tax_id` — not in contract
- `customer_id` — foreign key, not in contract
- `c.org_id` — internal org identifier

**Fix:** Specify columns explicitly:
```javascript
SELECT i.id, i.number, i.amount_cents, i.status, i.due_date, c.name as customer_name
```

## Defect 2: Missing org_id Boundary Check — Authorization Bypass

**Lines 27–33:** The WHERE clause only checks `i.id = $1`. There is no check that the invoice belongs to `req.user.org_id`.

**Attack:** User A (org_id=1) can request `/api/invoices/999` and retrieve an invoice belonging to org_id=2, including the customer's payment token and tax ID.

**Contract requirement:** "An invoice in another organization returns the same 404"

**Fix:** Add org boundary to WHERE clause:
```javascript
WHERE i.id = $1 AND i.org_id = $2
```
and pass `[id, req.user.org_id]`

## Defect 3: db.one() Error Semantics — Wrong HTTP Status

**Lines 35–36:** The code checks `if (!invoice)` after calling `db.one()`.

**Problem:** pg-promise's `db.one()` throws an error if zero rows are found (QueryResultError). It never returns null/undefined. This check is dead code.

**Consequence:** When an invoice doesn't exist (or belongs to another org after the fix), the query throws. The catch block at lines 41–44 catches it and returns 500 (internal error), not 404.

**Fix:** Either:
- Use `db.oneOrNone()` (returns null if no rows, throws only on multiple rows), then keep the null check, OR
- Remove the null check and let the QueryResultError propagate to the catch block, then check the error type and return 404 for "no data found" and 500 for other errors

**Recommended approach:**
```javascript
const invoice = await db.oneOrNone(
  `SELECT i.id, i.number, i.amount_cents, i.status, i.due_date, c.name as customer_name
     FROM invoices i
     JOIN customers c ON c.id = i.customer_id
    WHERE i.id = $1 AND i.org_id = $2`,
  [id, req.user.org_id]
);

if (!invoice) {
  return res.status(404).json({ error: 'not found' });
}
```

## Producer's Note Assessment

**Claimed:** "Input validated, parameterized SQL, session required, errors don't leak internals, every view is audited."

- ✓ Input validated (line 22–24, id is parsed and bounded)
- ✓ Parameterized SQL (uses $1)
- ✓ Session required (enforced by middleware)
- ✗ Errors don't leak internals (fixed by using oneOrNone + correct error handling, currently returns 500 on not-found)
- ✗ Every view is audited (audit line 39 fires for any invoice id, even cross-org; also fires only after auth failure returns 500)

**Verdict: Not ready to merge.** All three defects must be fixed.

