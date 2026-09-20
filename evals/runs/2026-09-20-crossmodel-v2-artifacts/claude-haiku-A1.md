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
