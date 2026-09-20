=== OUTPUT W ===

### Verdict
**NOT VERIFIED** | **BLOCKING: yes**

### Independence
**INDEPENDENT** — The artifact and contract arrived finished in the prompt; no prior drafting or collaboration in this conversation.

---

### Observable evidence
- **Leak of `customer_id`:** Line 17 selects `i.customer_id`, and line 33 directly returns `res.json(invoice)`. The response object contains `{ customer_id: ... }`, which directly breaches the negative contract clause explicitly forbidding `customer_id`.
- **Potential 500 on large integer input:** `Number("1e30")` passes `Number.isInteger(id) && id > 0` (evaluating to `true`). When passed to PostgreSQL for an integer column (`i.id = $1`), the driver/database throws an integer/numeric range overflow, which drops into `catch (err)` and returns `500 Internal server error`.

---

### Assessment
- The data leak is a direct contract failure caused by selecting a join key into the projection and returning the raw database row instead of mapping to the specified `InvoiceDTO`.
- The integer overflow on `req.params.id` represents improper input sanitization for SQL integer types; numeric strings larger than `Number.MAX_SAFE_INTEGER` or 32-bit/64-bit integer limits bypass the pre-DB check and cause an unhandled 500.

---

### Defects

#### ❌ HIGH — Prohibited field `customer_id` returned in response payload
- **Breach:** Contract states: *InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }* and explicitly mandates: *“Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id).”*
- **Demonstration:**
  - Query at line 17 explicitly selects `i.customer_id`.
  - Line 33 returns `res.json(invoice)`.
  - Response body:
    ```json
    {
      "id": 101,
      "number": "INV-2024-001",
      "amount_cents": 5000,
      "status": "paid",
      "due_date": "2024-12-01",
      "customer_id": 42,
      "customer_name": "Acme Corp"
    }
    ```
  - `customer_id` is present in the payload.

#### ⚠️ MEDIUM — Large numeric ID causes 500 Internal Server Error
- **Breach:** Contract states: *“Malformed ids never produce a 500.”*
- **Demonstration:**
  - Request: `GET /api/invoices/999999999999999999999999999999`
  - `Number("999999999999999999999999999999")` yields `1e+30`.
  - `Number.isInteger(1e+30)` evaluates to `true`, and `1e+30 > 0` evaluates to `true`.
  - The parameter is forwarded to Postgres: `WHERE i.id = $1`.
  - PostgreSQL raises error `22003: integer out of range`.
  - The catch block executes: `res.status(500).json({ error: 'Internal server error' })`.

---

### Claimed vs. actual

| Claimed Contract | Actual Behavior |
| :--- | :--- |
| Returns `InvoiceDTO` with only `{ id, number, amount_cents, status, due_date, customer_name }` | Returns row containing `customer_id` alongside the DTO fields. |
| No `customer_id` leaves server | `customer_id` is queried and serialized in JSON response. |
| Malformed IDs never return 500 | Out-of-range integer values pass validation and trigger a 500 DB error. |
| Invoices in another org return 404 | **Matches:** `AND i.org_id = $2` with `oneOrNone` returns `null` $\to$ 404. |

---

### Confirm-these
1. **`req.user.org_id` stability:** Assumed `requireSession()` guarantees `req.user` and `req.user.org_id` exist and are well-typed. If `org_id` can be undefined/null, the query fails or exhibits unexpected behavior.
2. **Database column types:** Assumed `i.id` is standard integer or bigint in PostgreSQL.

---

### How each clean axis was checked
- **Org Isolation & Anti-probing 404s:** Line 24 enforces `AND i.org_id = $2` parameterized with `req.user.org_id`. Line 28 checks `if (!invoice)` (null return from `oneOrNone`) and returns status `404`, masking whether an ID exists in another org.
- **SQL Injection Prevention:** Lines 10–25 use parameterized positional placeholders (`$1`, `$2`) passed via array `[id, req.user.org_id]`.
- **String/Negative ID Rejection:** Lines 5–8 execute `const id = Number(req.params.id); if (!Number.isInteger(id) || id <= 0)` and return HTTP 400 for non-numeric strings, negative numbers, floats, and zero.


=== OUTPUT X ===

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


=== OUTPUT Y ===

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


=== OUTPUT Z ===

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

