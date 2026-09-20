=== OUTPUT W ===

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


=== OUTPUT X ===

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


=== OUTPUT Y ===

### Verdict
**NOT VERIFIED** | **BLOCKING: yes**

### Independence
**INDEPENDENT** — Artifact was provided as a complete input; verifier did not draft, modify, or consult on its implementation.

---

### Observable evidence
- **Data Leak / Schema Violation (Line 12 & Line 27):**
  - Line 12 explicitly includes `i.customer_id` in the SQL query projection:
    ```sql
    i.customer_id,
    ```
  - Line 27 outputs the raw DB result object directly:
    ```js
    return res.json(invoice);
    ```
  - **Contract Breach:** The contract explicitly dictates the allowed `InvoiceDTO` fields (`{ id, number, amount_cents, status, due_date, customer_name }`) and explicitly mandates:
    > *"Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, **customer_id**)."*
  - Exposing `customer_id` in the JSON output directly violates both the DTO shape and the security/data boundary clause.

---

### Assessment
- **Numeric Overflow Risk (Lines 5–7, 28–31):**
  - `Number.isInteger(1e25)` evaluates to `true` in JavaScript. Passing an integer string that exceeds PostgreSQL's column limits (e.g., `req.params.id = "99999999999999999999"`) bypasses the `Number.isInteger` check and triggers a database parameter overflow exception.
  - This exception hits the `catch` block on line 28, causing the endpoint to return a `500 Internal Server Error`, violating the requirement: *"Malformed ids never produce a 500."*

---

### Defects
1. **HIGH** — **`customer_id` leaked in response payload (Breach of Contract Rule #2 & DTO Specification)**
   - *Demonstration:* Issue `GET /api/invoices/1` with valid credentials. The returned JSON object contains `"customer_id": <int>`, which is explicitly forbidden from leaving the server.

---

### Claimed vs. Actual

| Aspect | Claimed / Contract Requirement | Actual Implementation |
| :--- | :--- | :--- |
| **Response Schema** | `InvoiceDTO`: `{ id, number, amount_cents, status, due_date, customer_name }` | Includes `customer_id` in the response payload. |
| **Data Containment** | `customer_id` must NOT leave the server | `i.customer_id` is selected from DB and serialized directly into HTTP response. |
| **404 Behavior** | Non-existent or cross-org invoices return 404 | **Satisfied** for standard valid integer IDs (`i.org_id = $2` returning null -> 404). |

---

### Confirm-these
- Database driver behavior when `req.params.id` is a valid JavaScript integer exceeding the target database column type range (e.g., values exceeding standard 32-bit `INTEGER` or 64-bit `BIGINT` limits). If the driver/database throws a query execution error instead of handling parameter coercion, it triggers the catch block and returns a 500.

---

### How each clean axis was checked
- **404 isolation across org boundaries:** Checked lines 19–20 (`AND i.org_id = $2`) and lines 23–25 (`if (!invoice) return res.status(404)`). Cross-org invoices produce identical 404 responses to non-existent invoices.
- **Non-integer / negative ID rejection:** Checked lines 5–8 (`!Number.isInteger(id) || id <= 0` returns 400), ensuring standard invalid strings (`"abc"`, `"-5"`, `"1.5"`) fail fast with a 400 before querying the database.


=== OUTPUT Z ===

**Verdict:** NOT VERIFIED  
**BLOCKING:** yes  
**Independence:** INDEPENDENT — The artifact arrived finished in the prompt.

---

### Observable evidence
- **Data leak (`customer_id` in response payload):** Line 17 explicitly selects `i.customer_id` in SQL (`SELECT i.id, i.number, i.amount_cents, i.status, i.due_date, i.customer_id, c.name AS customer_name`). Line 31 returns `res.json(invoice)` directly. The HTTP response body contains `"customer_id"`, explicitly violating contract bullet #3 ("no ... customer_id").
- **Malformed ID causes HTTP 500:** Requesting `/api/invoices/99999999999999999999999` evaluates `Number("99999999999999999999999")` to `1e+23`. `Number.isInteger(1e+23)` evaluates to `true`, bypassing line 7 validation. The query parameter `$1` passed to Postgres causes a database driver integer bounds exception, falling into the `catch` block (line 32) and returning HTTP 500 (line 34).

---

### Assessment
- The tenant isolation logic correctly prevents cross-organization access by scoping the query to `req.user.org_id` and returning a uniform HTTP 404 for missing or unauthorized IDs.
- Non-numeric or negative ID strings (`"abc"`, `"-1"`, `"1.5"`) are rejected cleanly with HTTP 400 before reaching the database.

---

### Defects

1. **HIGH — Contract Breach / Data Leak (`customer_id` exposed)**  
   *Contract breach:* Contract specifies returning `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }` and prohibits `customer_id` from leaving the server.  
   *Demonstration:* Execute `GET /api/invoices/<valid_id>` with valid session. Observe response JSON payload:
   ```json
   {
     "id": 123,
     "number": "INV-001",
     "amount_cents": 1000,
     "status": "PAID",
     "due_date": "2026-01-01",
     "customer_id": 456,
     "customer_name": "Acme Corp"
   }
   ```
   The field `"customer_id"` is present in the payload.

2. **MEDIUM — Contract Breach / HTTP 500 on Malformed ID**  
   *Contract breach:* Contract specifies "Malformed ids never produce a 500."  
   *Demonstration:* Execute `GET /api/invoices/99999999999999999999999`. Line 6 converts this to `1e+23`, which passes `Number.isInteger()` on line 7. The parameter `$1` fails DB type conversion or bounds check in `db.oneOrNone`, throwing an error caught at line 33 and yielding HTTP 500.

---

### Claimed vs. actual
- **Claimed:** Returns `InvoiceDTO` `{ id, number, amount_cents, status, due_date, customer_name }`; no `customer_id` leaves server; malformed IDs never produce 500.
- **Actual:** Includes `customer_id` in response JSON; returns HTTP 500 when presented with numeric string inputs exceeding integer boundary range.

---

### Confirm-these
- Verification that `requireSession()` guarantees `req.user` and `req.user.org_id` are defined prior to entering the handler execution path (otherwise line 22 will throw `TypeError` and trigger HTTP 500).

---

### How each clean axis was checked
- **Tenant Isolation & 404 Parity:** `WHERE i.id = $1 AND i.org_id = $2` with `[id, req.user.org_id]` (lines 20–22) forces non-existent or foreign-org invoices to yield `null`, triggering line 27 HTTP 404 response.
- **Basic Non-numeric ID Validation:** `!Number.isInteger(id) || id <= 0` (line 7) evaluates `NaN`, non-integers, and negative numbers to `true`, returning HTTP 400 on line 8.

