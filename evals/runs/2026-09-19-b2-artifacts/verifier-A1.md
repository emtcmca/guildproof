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
