Based on a review of the code artifact against the specified contract, the implementation **does not fully satisfy the contract**. 

Here is the breakdown of findings:

---

### 1. Data Exposure Violation (Contract Clauses 1 & 3)
* **Contract Requirement:** The endpoint must only return `{ id, number, amount_cents, status, due_date, customer_name }`. It explicitly prohibits returning `customer_id` (or any other unspecified fields).
* **Artifact Code:**
  ```sql
  SELECT i.id,
         i.number,
         i.amount_cents,
         i.status,
         i.due_date,
         i.customer_id,   -- Selected here
         c.name AS customer_name
  ```
  The handler then returns the raw SQL result directly: `return res.json(invoice);`.
* **Issue:** `customer_id` is retrieved from the database and included in the JSON payload returned to the client.

---

### 2. Potential 500 Error on Edge-Case IDs (Contract Clause 4)
* **Contract Requirement:** Malformed IDs must never produce a `500` response.
* **Artifact Code:**
  ```js
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id <= 0) {
    return res.status(400).json({ error: 'Invalid invoice id' });
  }
  ```
* **Issue:** While non-numeric values and negative numbers return a `400`, JavaScript's `Number.isInteger()` accepts safe integers up to `9,007,199,254,740,991` (`Number.MAX_SAFE_INTEGER`). 
  * If the database `invoices.id` column uses a standard 32-bit signed integer (max value `2,147,483,647`), passing a value like `3000000000` passes validation but causes the database driver to throw an "integer out of range" error.
  * The error is caught by the `catch` block, returning a `500 Internal Server Error`.

---

### Compliant Behaviors
* **Organization Isolation & 404 Behavior (Clause 2):** The `WHERE` clause enforces both `i.id = $1` and `i.org_id = $2`. Invoices belonging to other organizations return `null` from `db.oneOrNone()` and consistently yield a `404` status, matching the behavior for non-existent IDs.

---

### Suggested Fixes

1. **Remove `i.customer_id`** from the SQL `SELECT` list.
2. **Cap integer bounds** in the validation logic to match the underlying database column type (e.g., `id > 2147483647`).
