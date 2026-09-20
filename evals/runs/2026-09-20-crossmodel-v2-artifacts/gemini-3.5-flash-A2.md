Based on a review of the provided **Artifact** against the specified **Contract**, there is one major discrepancy where the implementation violates the contract requirements, along with a couple of implementation details to note.

Here is the step-by-step verification:

---

### 1. InvoiceDTO and Data Leakage
* **Contract:** 
  * Returns an `InvoiceDTO`: `{ id, number, amount_cents, status, due_date, customer_name }`.
  * *"Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, **customer_id**)."*
* **Implementation:** **VIOLATION**
  * In the SQL query, you select `i.customer_id`:
    ```sql
    SELECT i.id,
           i.number,
           i.amount_cents,
           i.status,
           i.due_date,
           i.customer_id, -- <--- Violation
           c.name AS customer_name
    ```
  * Because the code returns the raw query result directly (`return res.json(invoice);`), the `customer_id` is sent to the client, which explicitly violates the restriction that no `customer_id` leaves the server.
* **Fix:** Remove `i.customer_id` from the `SELECT` statement (it is not needed for the join condition anyway, as you are already joining on `c.id = i.customer_id`).

---

### 2. Authorization and Organization Separation (404 Behavior)
* **Contract:** *"An invoice in another organization, or one that doesn't exist, returns the same 404."*
* **Implementation:** **PASS**
  * The query restricts the lookup by both the invoice ID and the caller's organization ID (`WHERE i.id = $1 AND i.org_id = $2`).
  * If the invoice exists but belongs to another organization, or if it does not exist at all, the query returns `null` (`oneOrNone`).
  * The code checks `if (!invoice)` and returns a `404` status code with the generic message `'Invoice not found'` in both cases.

---

### 3. Handling Malformed IDs
* **Contract:** *"Malformed ids never produce a 500."*
* **Implementation:** **PASS**
  * The code explicitly validates the parameter before performing any database operations:
    ```javascript
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) {
      return res.status(400).json({ error: 'Invalid invoice id' });
    }
    ```
  * Non-numeric strings, floats, negative numbers, or invalid inputs are caught here and return a `400 Bad Request` instead of triggering a database query driver error (which would result in a `500 Internal Server Error`).

---

### Recommended Corrected Code

To fully satisfy the contract, update the SQL query to omit `customer_id`:

```javascript
router.get('/api/invoices/:id', requireSession(), async (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id <= 0) {
    return res.status(400).json({ error: 'Invalid invoice id' });
  }

  try {
    const invoice = await db.oneOrNone(
      `SELECT i.id,
              i.number,
              i.amount_cents,
              i.status,
              i.due_date,
              c.name AS customer_name  -- Removed i.customer_id to comply with Contract
         FROM invoices i
         JOIN customers c
           ON c.id = i.customer_id
          AND c.org_id = i.org_id
        WHERE i.id = $1
          AND i.org_id = $2`,
      [id, req.user.org_id]
    );

    if (!invoice) {
      return res.status(404).json({ error: 'Invoice not found' });
    }

    return res.json(invoice);
  } catch (err) {
    logger.error({ err, invoiceId: id, userId: req.user.id }, 'Failed to fetch invoice');
    return res.status(500).json({ error: 'Internal server error' });
  }
});
```
