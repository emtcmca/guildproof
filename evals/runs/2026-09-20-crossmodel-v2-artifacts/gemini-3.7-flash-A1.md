### Contract Verification Result: **FAIL**

The implementation violates the contract regarding the response data shape and prohibited fields.

---

### Detailed Findings

1. **Information Leakage (`customer_id` is exposed)**
   - **Contract requirement:** 
     > Returns as an `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }`.  
     > *Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id).*
   - **Violation:**  
     The SQL query explicitly selects `i.customer_id`:
     ```sql
     SELECT i.id,
            i.number,
            i.amount_cents,
            i.status,
            i.due_date,
            i.customer_id, -- <--- Included in SELECT
            c.name AS customer_name
     ```
     Because `res.json(invoice)` sends the raw query result directly to the client, `customer_id` is included in the HTTP response.

---

### Other Requirements (Passed)

- **Multi-tenant scoping & 404 handling:** ✅ Scoped by `i.org_id = $2` (`req.user.org_id`), returning `404` for both non-existent invoices and invoices in other organizations.
- **Malformed ID handling:** ✅ Non-integer or non-positive values are caught before querying the database and return `400` rather than triggering a `500` database syntax/casting error.

---

### Recommended Fix

Remove `i.customer_id` from the SQL `SELECT` list:

```diff
     const invoice = await db.oneOrNone(
       `SELECT i.id,
               i.number,
               i.amount_cents,
               i.status,
               i.due_date,
-              i.customer_id,
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
