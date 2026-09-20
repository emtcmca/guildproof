**Verdict**: NOT VERIFIED
**BLOCKING**: yes

**Independence**: INDEPENDENT — Artifact arrived finished in the prompt; verifier had no role in drafting it.

---

### Observable evidence
- **Leak of forbidden field `customer_id`**: The SQL query explicitly queries `i.customer_id` (line 16), and the handler directly returns the raw row object to the client (`return res.json(invoice);` on line 33). The contract explicitly specifies: `"Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id)."`

---

### Assessment
- **Potential 500 on large numeric input**: `Number.isInteger(id)` passes JavaScript safe integers and values up to standard IEEE-754 precision (e.g., `1e25` is an integer in JS). If the underlying PostgreSQL column is a standard 32-bit `integer` (max `2,147,483,647`) or 64-bit `bigint` (max `9,223,372,036,854,775,807`), sending `/api/invoices/99999999999999999999` causes Postgres to throw `integer out of range`. This lands in `catch (err)` and responds with HTTP 500, violating `"Malformed ids never produce a 500"`.
- **Session precondition**: The route assumes `requireSession()` populates `req.user.org_id` and `req.user.id`. If `req.user` is unpopulated or lacks `org_id`, the database query or logger will throw an unhandled TypeError, yielding a 500.

---

### Defects

❌ **HIGH — Leak of forbidden field `customer_id` in response payload**
- *Contract breach*: Contract specifies return type `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }` and explicitly forbids `customer_id` from leaving the server.
- *Demonstration*: Look at lines 10–23:
  ```js
  SELECT i.id,
         i.number,
         i.amount_cents,
         i.status,
         i.due_date,
         i.customer_id,   // <-- selected here
         c.name AS customer_name
  ```
  Line 33 executes `res.json(invoice)`, transmitting `customer_id` directly in the response JSON.

⚠️ **MEDIUM — Large integer values in `:id` can trigger HTTP 500**
- *Contract breach*: `"Malformed ids never produce a 500."`
- *Demonstration*: Request `GET /api/invoices/99999999999999999999`. `Number(req.params.id)` evaluates to `1e20`, which satisfies `Number.isInteger(id) && id > 0`. The database driver executes `$1 = 1e20`. If `invoices.id` is typed as standard integer or bigint, the database rejects the query with an out-of-range error, jumping to `catch` and returning `500 Internal server error`.

---

### Claimed vs. actual
- **Claimed**: Returns only `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }` with no `customer_id`.
  **Actual**: Returns `customer_id` as part of the JSON response.
- **Claimed**: Malformed IDs never produce a 500.
  **Actual**: Out-of-range integer representations pass JS validation and trigger database errors caught by the 500 handler.

---

### Confirm-these
- **Column data type of `invoices.id`**: Confirm whether `invoices.id` is bounded to standard 32-bit `INT` or 64-bit `BIGINT` in the schema to determine the exact boundary where input produces an unhandled SQL exception and a 500 response.
- **`requireSession()` middleware guarantees**: Confirm that `requireSession()` guarantees `req.user` and `req.user.org_id` exist before passing execution to the handler.

---

### How each clean axis was checked
- **Org tenant isolation & IDOR prevention (✅)**: Line 22 checks `AND i.org_id = $2` with parameter `req.user.org_id`. Cross-tenant invoices evaluate to null.
- **Nonexistent vs. other-tenant 404 equivalence (✅)**: Lines 27–29 check `if (!invoice) return res.status(404).json({ error: 'Invoice not found' });`, treating cross-tenant and non-existent rows identically with no status or timing disparity in response construction.
- **Non-numeric ID handling (✅)**: Lines 5–7 check `if (!Number.isInteger(id) || id <= 0)` and reject strings, floats, and negative numbers with HTTP 400 before DB dispatch.
