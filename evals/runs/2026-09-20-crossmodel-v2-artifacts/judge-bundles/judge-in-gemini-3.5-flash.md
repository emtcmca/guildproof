=== OUTPUT W ===

### Verdict
**NOT VERIFIED** — **BLOCKING: YES**  
The artifact fails its contract on two separate fronts: it leaks restricted information (`customer_id`) to the API caller, and it allows large integer inputs to bypass validation and trigger a `500 Internal Server Error` from the database.

### Independence
**INDEPENDENT** — The artifact and contract were provided externally; I had no role in drafting, authoring, or revising either.

---

### Observable evidence
1. **Data Leakage (`customer_id`):** 
   - Line 17 of the artifact explicitly queries `i.customer_id` from the database.
   - Line 31 directly returns the raw query result to the client via `res.json(invoice)`.
   - The contract explicitly states: *"Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id)."*

2. **Database Integer Overflow (Produces `500` status):**
   - Line 7 validates the ID parameter using `Number.isInteger(id)`. 
   - A value such as `2147483648` (exceeding standard PostgreSQL 32-bit signed integer limits) returns `true` for `Number.isInteger()`, passing the guard.
   - When executed by the database driver, the database throws a numeric out-of-range error (`22003`), triggering the `catch (err)` block on Line 33.
   - Line 35 responds with a `500 Internal Server Error` instead of a validation error or standard `404` status, violating the contract: *"Malformed ids never produce a 500."*

---

### Assessment
- It is highly probable that the database uses a standard 32-bit signed `INTEGER` for the primary key `id`. If so, any valid JS integer larger than `2147483647` and smaller than `Number.MAX_SAFE_INTEGER` will reliably trigger the DB-level range error and subsequent `500` response. 
- Even if the DB column type is a 64-bit `BIGINT`, a value exceeding standard limits or any JS integer value that loses precision (e.g., `99999999999999999999`) will trigger parser or binding errors inside the database driver before reaching PostgreSQL, generating a `500` response.

---

### Defects

#### ❌ HIGH — Direct Information Leakage of restricted attribute (`customer_id`)
- **Contract Breach:** The contract explicitly bans the transmission of `customer_id` outside of the server.
- **Demonstration:**
  An HTTP request is made to `GET /api/invoices/123`. The server queries the database, binds `customer_id` to the returned object, and responds with:
  ```json
  {
    "id": 123,
    "number": "INV-1001",
    "amount_cents": 5000,
    "status": "PAID",
    "due_date": "2023-12-31",
    "customer_id": 456,          // <--- LEAKED RESTRICTED FIELD
    "customer_name": "ACME Corp"
  }
  ```

#### ⚠️ MEDIUM — Database Error Leaking as a `500` status on out-of-range IDs
- **Contract Breach:** *"Malformed ids never produce a 500."*
- **Demonstration:**
  Make a request to `GET /api/invoices/2147483648`.
  - `Number.isInteger(2147483648)` evaluates to `true`.
  - The database query executes with `$1 = 2147483648`.
  - PostgreSQL throws `error: integer out of range`.
  - The exception is caught by the query try-catch block and logs an error, returning `500 Internal Server Error` to the user.

---

### Claimed vs. actual

| Feature / Behavior | Claimed by Contract | Actual Artifact Behavior |
| :--- | :--- | :--- |
| **Response Fields** | `{ id, number, amount_cents, status, due_date, customer_name }` | Also includes **`customer_id`** in the response. |
| **Exclusion of `customer_id`** | Strictly hidden from client. | Exposed directly. |
| **Out-of-range IDs** | Must not cause a `500` error. | Causes a `500 Internal Server Error` via database overflow exceptions. |

---

### Confirm-these
*Verify these assumptions in your deployment environment:*
1. **DB Column Types:** Confirm whether `invoices.id` is defined as a standard 32-bit `INTEGER` or a 64-bit `BIGINT`. If standard, the validation ceiling must be clamped to `2147483647` to avoid the database exception.
2. **Session Context:** Confirm that `requireSession()` ensures that `req.user` and `req.user.org_id` are always populated; otherwise, accessing `req.user.org_id` will throw a `TypeError` and crash the execution path into a `500` response.

---

### How each clean axis was checked
- **Organization Boundary Enforcement:** Checked lines 23-24 (`AND i.org_id = $2`) and matching line 25 parameter binding `req.user.org_id`. This correctly restricts results only to the caller's organization.
- **Uniform 404 Response:** Checked lines 28-30. If no record is found (whether due to nonexistence or organization mismatch), the returned query response is falsy and yields a `404 Not Found` payload.
- **Join Consistency:** Checked lines 19-22. It ensures customers are locked down to the same organization as the invoice during the join, preventing cross-tenant leakage of customer names.


=== OUTPUT X ===

### Verdict
**NOT VERIFIED**
**BLOCKING: Yes** — A high-severity data leakage defect exists where an forbidden database identifier is exposed to the client, directly violating the contract constraints.

---

### Independence
**INDEPENDENT** — The artifact was provided complete, and this review was performed independently without participating in its generation or modification.

---

### Observable evidence

#### ❌ Real Defect: Leakage of `customer_id` (HIGH Severity)
* **Contract Breach:** The contract explicitly states: *"Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, **customer_id**)."*
* **Demonstration:**
  The SQL query selects `i.customer_id`:
  ```sql
  SELECT i.id,
         ...
         i.customer_id,
         c.name AS customer_name
  ```
  The router then serializes this query output directly to the HTTP response body:
  ```js
  return res.json(invoice);
  ```
  As a result, the returned JSON payload includes the forbidden `"customer_id"` property (e.g., `{"id":123,"number":"INV-01","customer_id":456,"customer_name":"Acme Corp"}`), violating the data exclusion requirement.

---

### Assessment

#### ⚠️ Potential Defect: Large Out-of-Bounds Integers leading to DB Error / 500 (LOW Severity)
* **Contract Breach:** The contract states: *"Malformed ids never produce a 500."*
* **Demonstration:**
  The router attempts to validate the ID with `Number.isInteger(id)`. In JavaScript, very large numbers represented in scientific notation (e.g., `1e21`) return `true` for `Number.isInteger(1e21)`.
  If a client passes an extremely large integer, it will pass the validation check, reach the database driver (`pg` / `pg-promise`), and likely trigger an `"integer out of range"` database driver exception. This exception is caught in the `catch` block and returns a `500 Internal Server Error`, potentially violating the "never produce a 500" rule for edge-case numeric payloads. Utilizing `Number.isSafeInteger(id)` would prevent this.

---

### Claimed vs. Actual

| Contract Requirement | Actual Behavior | Status |
| :--- | :--- | :--- |
| Returns invoice belonging to caller's org as `InvoiceDTO` | Returns correct fields but appends forbidden fields | ❌ **FAIL** |
| Missing or cross-org invoices return the same 404 | Both scenarios result in `!invoice` and return 404 | ✅ **PASS** |
| No forbidden properties leave the server | Directly leaks `customer_id` via serialization | ❌ **FAIL** |
| Malformed IDs never produce a 500 | Handled correctly via validation, except for extreme integer overflows | ⚠️ **PARTIAL** |

---

### Confirm-these
* **`requireSession()` Guard Contract:** Verify that the `requireSession()` middleware guarantees that `req.user` is defined and contains populated, valid `id` and `org_id` properties. If `req.user` is undefined, accessing `req.user.org_id` will raise a unhandled `TypeError` inside the route handler.

---

### How each clean axis was checked
* **404 path (missing or unauthorized invoice):** Traced to lines 27–30 where `!invoice` (which is the result of a non-matching ID or non-matching `org_id` in SQL) explicitly triggers `res.status(404).json(...)`.
* **SQL Injection Prevention:** Traced to parameterized input mapping on line 24 (`[id, req.user.org_id]`), ensuring the dynamic ID parameter is sanitized at the database driver level.
* **Non-integer ID validation:** Traced to lines 5–8 where string-based IDs (like `"/api/invoices/abc"`) or fractional IDs yield `NaN` or non-integers, triggering an early exit with status `400`.


=== OUTPUT Y ===

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


=== OUTPUT Z ===

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

