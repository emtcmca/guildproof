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
