Based on a review of the code against the provided contract, the implementation **does not fully satisfy the contract**. 

Here is the breakdown of findings and required adjustments:

---

### Findings

#### 1. Contract Violation: Data Leakage (`customer_id` is returned)
* **Contract Requirement:** 
  * Response must strictly match `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }`.
  * "Nothing else about the invoice or the customer leaves the server (no ..., customer_id)."
* **Artifact Code:** 
  The SQL query selects `i.customer_id`:
  ```sql
  SELECT i.id,
         i.number,
         i.amount_cents,
         i.status,
         i.due_date,
         i.customer_id, -- <--- Leak
         c.name AS customer_name
  ```
  Since `res.json(invoice)` directly returns the query result, `customer_id` is included in the JSON payload sent to the client.

#### 2. Potential Contract Violation: 500 Error on Extremely Large Integer IDs
* **Contract Requirement:** "Malformed ids never produce a 500."
* **Artifact Code:** 
  `Number("999999999999999999999999999999")` will pass `Number.isInteger(id)`, but querying PostgreSQL with an integer exceeding 64-bit limits (or standard 32-bit `INTEGER` limits) will cause the database driver to throw an integer overflow error. This error gets caught by the `try...catch` block, which returns a `500 Internal Server Error`.

---

### Verification Summary

| Contract Requirement | Status | Note |
| :--- | :--- | :--- |
| Returns invoice belonging to caller's org | **PASS** | Filtered by `i.org_id = req.user.org_id`. |
| Cross-org or non-existent returns 404 | **PASS** | Returns uniform 404 via `oneOrNone` logic. |
| Strict DTO field subset (No `customer_id`) | **FAIL** | `customer_id` is included in SQL query and JSON response. |
| Malformed IDs never return 500 | **PARTIAL FAIL** | Handles non-numeric/string inputs with 400, but extreme numbers can trigger DB overflow resulting in 500. |

---

### Recommended Remediation

1. Remove `i.customer_id` from the SQL `SELECT` statement.
2. Add a safe upper bound check for `id` (e.g., `Number.MAX_SAFE_INTEGER` or standard PostgreSQL `INTEGER` max of `2147483647`).

```js
router.get('/api/invoices/:id', requireSession(), async (req, res) => {
  const id = Number(req.params.id);

  // Validate integer range to prevent DB overflow errors triggering 500
  if (!Number.isInteger(id) || id <= 0 || id > 2147483647) {
    return res.status(400).json({ error: 'Invalid invoice id' });
  }

  try {
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
