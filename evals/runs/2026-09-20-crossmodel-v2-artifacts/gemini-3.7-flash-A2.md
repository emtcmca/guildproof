### Contract Verification Result: **FAILED**

The implementation violates the contract on data leakage and DTO shape.

---

### Findings

#### 1. Contract Violation: Leaking `customer_id`
* **Contract clause:** 
  > *InvoiceDTO: `{ id, number, amount_cents, status, due_date, customer_name }`.*  
  > *Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, **customer_id**).*
* **Violation in Artifact:**
  The SQL query includes `i.customer_id`:
  ```sql
  SELECT i.id,
         i.number,
         i.amount_cents,
         i.status,
         i.due_date,
         i.customer_id, -- <--- Leaks customer_id
         c.name AS customer_name
  ```
  Since `res.json(invoice)` returns the raw query result object, `customer_id` is transmitted to the client.

---

### Passed Checks
- **Org Isolation & 404 Behavior:** Queries filter by `i.org_id = req.user.org_id` and return identical 404 responses for missing invoices or cross-org access.
- **Malformed ID Handling:** Non-integer or non-positive IDs are intercepted and return `400` instead of causing a `500` database error.

---

### Recommended Fix
Remove `i.customer_id` from the `SELECT` list:

```sql
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
