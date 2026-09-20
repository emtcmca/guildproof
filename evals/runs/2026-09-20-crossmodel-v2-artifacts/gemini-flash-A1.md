The artifact **violates the contract** in the following ways:

### 1. Data Leak: `customer_id` is returned to the client (Major Violation)
* **Contract requirement:** 
  > *InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }.*  
  > *Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, **customer_id**).*
* **Artifact implementation:**
  ```sql
  SELECT i.id,
         i.number,
         i.amount_cents,
         i.status,
         i.due_date,
         i.customer_id,           -- <--- customer_id is selected
         c.name AS customer_name
  ```
  `res.json(invoice)` directly serializes the query output, exposing `customer_id` in violation of the contract.

---

### 2. Potential 500 on large integer IDs (Edge Case Violation)
* **Contract requirement:** 
  > *Malformed ids never produce a 500.*
* **Artifact implementation:**
  While non-integer or non-positive values are caught (`!Number.isInteger(id) || id <= 0`), integers exceeding the database column's integer limits (e.g., values $> 2^{31} - 1$ for standard 4-byte Postgres `INTEGER` or values exceeding `BIGINT`) will cause the database driver to throw an "integer out of range" error, triggering the `catch` block and returning HTTP **500**.

---

### Recommended Fix
1. Remove `i.customer_id` from the `SELECT` list.
2. Ensure the ID does not exceed the maximum integer size supported by your database schema before querying (e.g., `id > 2147483647`).
