Based on a comparison of the **Contract** requirements and the provided **Artifact** implementation, there are a few discrepancies—one of which is a direct security/privacy violation of the contract.

Here is the step-by-step verification:

---

### 1. Data Exposure / DTO Compliance
* **Contract Requirement:** 
  > *"Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id)."*
* **Artifact Implementation:** 
  The SQL query selects `i.customer_id`:
  ```sql
  SELECT i.id, ..., i.customer_id, c.name AS customer_name ...
  ```
  And the route handler directly serializes the database result to the client:
  ```js
  return res.json(invoice);
  ```
* **Result:** **FAIL**. The `customer_id` is included in the payload sent to the client, violating the contract.

---

### 2. Error Handling for Malformed IDs (400 vs. 404)
* **Contract Requirement:** 
  > *"An invoice in another organization, or one that doesn't exist, returns the same 404."*
  > *"Malformed ids never produce a 500."*
* **Artifact Implementation:** 
  ```js
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id <= 0) {
    return res.status(400).json({ error: 'Invalid invoice id' });
  }
  ```
* **Result:** **PARTIAL COMPLIANCE / POTENTIAL MISMATCH**. 
  * It successfully avoids a `500` error (satisfying the second clause).
  * However, by returning a `400 Bad Request` instead of a `404 Not Found` for malformed IDs (e.g., `/api/invoices/abc` or `/api/invoices/-5`), it behaves differently than for a non-existent but well-formed ID (which returns `404`). If the goal of returning the "same 404" is to completely prevent client-side probing or resource enumeration signatures, malformed IDs should also return a `404`.

---

### 3. Authentication & Scope Isolation
* **Contract Requirement:** 
  > *"returns one invoice that belongs to the caller's organization"*
  > *"An invoice in another organization, or one that doesn't exist, returns the same 404."*
* **Artifact Implementation:** 
  The query restricts the search using:
  ```sql
  WHERE i.id = $1 AND i.org_id = $2
  ```
  If the invoice belongs to another organization, the query returns no rows, and the code triggers the `404` block:
  ```js
  if (!invoice) {
    return res.status(404).json({ error: 'Invoice not found' });
  }
  ```
* **Result:** **PASS**. This correctly enforces organizational isolation and handles authorization failures identically to missing resources.

---

### Recommended Remediation

To fully satisfy the contract, you should:
1. Remove `customer_id` from the SQL projection.
2. Change the malformed ID validation response from `400` to `404` to ensure complete uniformity for any invalid or missing resource request.

Here is the corrected code:

```js
// GET /api/invoices/:id
// Returns one invoice plus its customer's name. Only invoices in the caller's org are visible.
router.get('/api/invoices/:id', requireSession(), async (req, res) => {
  const id = Number(req.params.id);
  
  // Malformed IDs return 404 to match non-existent resources and avoid 500s
  if (!Number.isInteger(id) || id <= 0) {
    return res.status(404).json({ error: 'Invoice not found' });
  }

  try {
    const invoice = await db.oneOrNone(
      `SELECT i.id,
              i.number,
              i.amount_cents,
              i.status,
              i.due_date,
              c.name AS customer_name  -- customer_id removed to prevent data leakage
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
