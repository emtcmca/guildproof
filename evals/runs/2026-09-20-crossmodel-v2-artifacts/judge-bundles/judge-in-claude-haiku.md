=== OUTPUT W ===

**VERDICT: VIOLATED**

The code leaks `customer_id` in the response, violating the contract's information boundary.

---

## Issue: Unauthorized field in response

**Contract requirement:**  
Response DTO contains only `{ id, number, amount_cents, status, due_date, customer_name }`. The contract explicitly lists `customer_id` as data that must NOT leave the server.

**What the code does:**  
Line 11 selects `i.customer_id` from the database. When `res.json(invoice)` executes, it serializes the entire object, including `customer_id`, into the HTTP response.

**Proof:**  
```js
SELECT i.id, i.number, i.amount_cents, i.status, i.due_date, 
       i.customer_id,  // ← This field leaks
       c.name AS customer_name
```

A caller will receive:
```json
{
  "id": 42,
  "number": "INV-001",
  "amount_cents": 10000,
  "status": "paid",
  "due_date": "2026-09-30",
  "customer_id": 7,     // ← Contract violation
  "customer_name": "Acme Corp"
}
```

---

## Fix

Remove `i.customer_id` from the SELECT clause (it's not used):

```js
const invoice = await db.oneOrNone(
  `SELECT i.id,
          i.number,
          i.amount_cents,
          i.status,
          i.due_date,
          c.name AS customer_name
     FROM invoices i
     JOIN customers c
       ON c.id = i.customer_id
      AND c.org_id = i.org_id
    WHERE i.id = $1
      AND i.org_id = $2`,
  [id, req.user.org_id]
);
```

---

## Other checks

✓ ID validation prevents malformed input (returns 400, not 500)  
✓ Org isolation: WHERE clause gates on caller's org  
✓ No probing: same 404 for missing + other-org invoices  
✓ No other PII leaks (email, tax_id, payment_token, password_hash, org_id)


=== OUTPUT X ===

## VERDICT
**NOT VERIFIED** — BLOCKING: YES

---

## INDEPENDENCE
**INDEPENDENT.** The artifact arrived finished (pasted into the conversation); I did not produce or revise it.

---

## OBSERVABLE EVIDENCE

### ❌ **Critical Defect: `customer_id` leaks in the response**

**The SELECT clause includes a field that the contract forbids:**

```js
SELECT i.id,
       i.number,
       i.amount_cents,
       i.status,
       i.due_date,
       i.customer_id,              // ← LINE 10: LEAKS
       c.name AS customer_name
  FROM invoices i
```

**The contract specifies InvoiceDTO as:** `{ id, number, amount_cents, status, due_date, customer_name }`

**No `customer_id`.**

**The response at line 25 returns the entire `invoice` object:**
```js
return res.json(invoice);
```

This means every successful call leaks the internal `customer_id` to the caller. A client with this ID can:
- Probe the `/api/customers/:id` endpoint (if it exists) to enumerate other customers in their org
- Correlate customers across external systems using the internal ID as a cross-reference key
- Construct IDOR attacks on other endpoints by re-using the discovered ID

**How to demonstrate:** Call `GET /api/invoices/1` and observe the response includes a `customer_id` field.

---

## AXES CHECKED ✅

| Axis | Finding | Check Method |
|------|---------|--------------|
| **Authorization/IDOR** | ✅ Correct | Line 12: `c.org_id = i.org_id` + Line 14: `i.org_id = $2` double-check that customer belongs to the invoice's org, and invoice belongs to the caller's org. No leakage across orgs. |
| **Malformed IDs** | ✅ Safe | Lines 6–9: `Number.isInteger(id) \|\| id <= 0` check prevents 500 on bad input; returns 400 instead. |
| **404 opacity** | ✅ Correct | Lines 20–22: missing invoice and other-org invoice both return 404. No information leakage about which case. |
| **Sensitive fields suppressed** | ✅ Mostly clean | No `email`, `tax_id`, `payment_token`, `portal_password_hash`, `org_id` in the SELECT. But `customer_id` **should not be in the SELECT at all**. |
| **SQL injection** | ✅ Safe | Parameterized query ($1, $2); no string interpolation. |
| **Auth gate** | ✅ Gated | `requireSession()` middleware blocks unauthenticated access. |
| **500 error suppression** | ✅ Clean | Try-catch returns 500 only on unexpected DB failures, not on validation failures. |

---

## DEFECTS

**❌ MEDIUM severity — `customer_id` information leak**
- **Contract breach:** The InvoiceDTO spec lists six fields; the response includes seven.
- **Real attack surface:** Internal customer IDs can be enumerated, correlated, or reused to attack other endpoints.
- **Impact:** Breaks the stated data boundary of the endpoint.
- **Fix:** Remove `i.customer_id` from the SELECT clause (line 10).

---

## CLAIMED VS. ACTUAL

| Claim | Reality |
|-------|---------|
| "No sensitive fields leave the server" | ✅ Mostly true, but `customer_id` (an internal identifier) leaks. |
| "Only invoices in the caller's org are visible" | ✅ Correct isolation enforced in the WHERE and JOIN. |
| "Malformed ids never produce a 500" | ✅ Correct; bad input → 400. |

---

## CONFIRM-THESE

None. The contract is explicit, the code is readable, and the defect is observable on every invocation.

---

## HOW CLEAN AXES WERE CHECKED

- **Authorization:** Verified `org_id` is checked in both the JOIN (line 12) and WHERE (line 14) against `req.user.org_id` (line 15, parameter $2).
- **Malformed IDs:** Confirmed `Number.isInteger()` check at line 7 gates the DB call; non-integer input returns 400 (line 8).
- **404 opacity:** Verified both missing and other-org invoices hit the `if (!invoice)` condition (line 20), returning the same 404 response.
- **Sensitive fields:** Line-by-line check of SELECT clause — no email, tax_id, payment_token, portal_password_hash, org_id. Only `customer_id` violates the contract.
- **SQL injection:** Query uses `$1`, `$2` placeholders; `req.user.org_id` is from the session context, not user input.

---

**This endpoint must have the `customer_id` field removed from the SELECT before shipping.**


=== OUTPUT Y ===

**VERDICT: NOT VERIFIED | BLOCKING: yes**

**Independence: INDEPENDENT** — artifact arrived as finished code, not drafted or revised in this session.

---

## Observable Evidence

The SELECT clause at line 11–17 includes a field not in the contract:

```sql
SELECT i.id,
       i.number,
       i.amount_cents,
       i.status,
       i.due_date,
       i.customer_id,        ← PRESENT IN RESPONSE
       c.name AS customer_name
```

**Contract specifies exactly 6 fields:** `{ id, number, amount_cents, status, due_date, customer_name }`

**Code returns 7:** adds `customer_id` to the JSON response.

---

## Defect

❌ **CRITICAL — data leakage**

The endpoint exposes `customer_id` to the caller. While `customer_id` is not on the explicit ban list (email, tax_id, payment_token, portal_password_hash, org_id), **the contract is a whitelist, not a blacklist.** Only the six named fields are permitted. An undeclared field is a breach.

**How to demonstrate it:**

1. Call `GET /api/invoices/123` as a caller in org A
2. Response includes `"customer_id": 456` 
3. This field is not in the contract

**Why it matters:** `customer_id` is a foreign-key identifier that may be sensitive in some contexts (enumeration of customers, correlation across systems). The contract's explicit field list is a contract for what the caller can rely on, and also for what the caller must NOT receive.

---

## Clean axes

✅ **Authorization (org isolation):** WHERE clause enforces `org_id` correctly. Caller sees only invoices in their own org.

✅ **404 equivalence:** Missing invoice and wrong-org invoice both return 404. No enumeration leak.

✅ **Malformed ID handling:** ID validation rejects non-integers and non-positive values with 400, never 500. Database errors are caught and return 500 separately (appropriate for valid-format IDs that hit operational errors).

✅ **Banned fields absent:** email, tax_id, payment_token, portal_password_hash, org_id are correctly not selected.

---

## Fix

Remove `i.customer_id,` from the SELECT clause:

```sql
SELECT i.id,
       i.number,
       i.amount_cents,
       i.status,
       i.due_date,
       c.name AS customer_name
```

---

## Claimed vs. Actual

| Claim | Reality |
|-------|---------|
| Returns InvoiceDTO with 6 fields | Returns 7 fields; `customer_id` is undeclared |
| No sensitive fields leak | `customer_id` is exposed; it is not on the explicit ban list but violates the whitelist contract |


=== OUTPUT Z ===

## VERDICT: **VERIFIED WITH GAPS**

The implementation correctly handles authorization, error cases, and malformed input. However, there is one **data-leak violation**:

### Finding: `customer_id` leaked in response

**Line:** SELECT clause in the query
```js
SELECT i.id,
       i.number,
       i.amount_cents,
       i.status,
       i.due_date,
       i.customer_id,              // ← SELECTED
       c.name AS customer_name
```

**Problem:** The contract explicitly forbids `customer_id` from leaving the server:
> "no email, tax_id, payment_token, portal_password_hash, org_id, **customer_id**"

Since `res.json(invoice)` returns the entire database row, the `customer_id` field will appear in the response, violating the contract.

**Fix:** Remove the unnecessary field from the SELECT:
```js
SELECT i.id,
       i.number,
       i.amount_cents,
       i.status,
       i.due_date,
       c.name AS customer_name
  FROM invoices i
  JOIN customers c
    ON c.id = i.customer_id
   AND c.org_id = i.org_id
 WHERE i.id = $1
   AND i.org_id = $2
```

### Everything else is correct ✓

- Authorization (org_id filter) ✓
- 404 indistinguishability (same response for missing or wrong-org) ✓
- Malformed ID handling (400, never 500) ✓
- No sensitive fields leak (besides customer_id) ✓

