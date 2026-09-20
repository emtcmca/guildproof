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
