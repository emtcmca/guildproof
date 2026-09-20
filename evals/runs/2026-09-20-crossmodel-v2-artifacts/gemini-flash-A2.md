The artifact **fails** verification against the contract.

---

### Violations

#### 1. Leaking `customer_id` (Violates Clauses 1 & 3)
* **Contract:** 
  * Response must be an `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }`.
  * *"Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id)."*
* **Artifact:**
  ```sql
  SELECT i.id,
         i.number,
         i.amount_cents,
         i.status,
         i.due_date,
         i.customer_id,           -- <--- Included in query
         c.name AS customer_name
  ```
  The handler executes `return res.json(invoice);` directly on the database row, which exposes `customer_id` in the API response.

---

### Potential Edge Case / Risk

* **Database Integer Overflow (Clause 4: *"Malformed ids never produce a 500"*):**
  The check `Number.isInteger(id) && id > 0` allows integers up to `Number.MAX_SAFE_INTEGER` (`9,007,199,254,740,991`). If the database column `i.id` is a standard 32-bit signed integer (`INT4`, max `2,147,483,647`), queries with values exceeding this range will cause PostgreSQL to throw an `"integer out of range"` error. That error is caught by the `catch` block and returned as a `500 Internal server error`.

---

### Recommended Fix

1. Remove `i.customer_id` from the SQL query (or map to an explicit DTO object before returning).
2. (Optional but recommended) Ensure the ID does not exceed the database column bounds before querying.

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
