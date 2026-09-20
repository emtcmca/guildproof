=== OUTPUT W ===

### Verdict
**NOT VERIFIED** | **BLOCKING: yes**

---

### Independence
**INDEPENDENT** — The artifact arrived finished in the prompt; it was not authored or revised in this conversation.

---

### Observable evidence
- **Leak of forbidden field `customer_id` (observable):** The SQL query explicitly selects `i.customer_id` on line 17, and line 32 returns `invoice` directly via `res.json(invoice)`. The response contains `{ id, number, amount_cents, status, due_date, customer_id, customer_name }`.
- **Org isolation (observable):** Parameterized query uses `$2` bound to `req.user.org_id` against `i.org_id` and checks `c.org_id = i.org_id`.
- **Missing/cross-org behavior (observable):** If no matching row is returned by `db.oneOrNone`, line 28 returns 404 unconditionally.
- **Malformed ID handling (observable):** Non-integer or non-positive strings fail `!Number.isInteger(id) || id <= 0` and return 400 before DB execution.

---

### Assessment
The artifact fails a strict negative requirement and its explicit DTO shape by over-fetching and directly serializing the database record to JSON without projection or stripping.

---

### Defects

❌ **HIGH — Forbidden field `customer_id` leaked in response**
- *Contract breach:* The contract explicitly mandates the response shape `{ id, number, amount_cents, status, due_date, customer_name }` and forbids `customer_id` ("Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id)").
- *Demonstration:*
  Line 17 selects `i.customer_id`:
  ```sql
  SELECT i.id,
         i.number,
         i.amount_cents,
         i.status,
         i.due_date,
         i.customer_id,
         c.name AS customer_name
  ```
  Line 32 sends the row object directly:
  ```js
  return res.json(invoice);
  ```
  The caller receives `customer_id` in the JSON payload.

---

### Claimed vs. actual

| Property / Claim | Claimed | Actual |
| :--- | :--- | :--- |
| **Response DTO shape** | `{ id, number, amount_cents, status, due_date, customer_name }` | `{ id, number, amount_cents, status, due_date, customer_id, customer_name }` |
| **Field exclusion** | `customer_id` never leaves server | `customer_id` is queried and emitted |
| **Org isolation / 404 behavior** | 404 on missing or foreign org | Matches claim |
| **Malformed ID guard** | 400 returned, never 500 | Matches claim |

---

### Confirm-these
*(None — the contract breach is fully demonstrable from the provided source code).*

---

### How each clean axis was checked
- **Org scoping:** Line 24 binds `req.user.org_id` to `$2` in `WHERE i.id = $1 AND i.org_id = $2`.
- **404 parity for non-existent vs foreign org:** Line 28 checks `!invoice` and returns 404 with identical payloads in both cases.
- **Malformed ID input validation:** Lines 5–8 parse and validate `req.params.id` with `Number.isInteger` and `<= 0`, returning 400 prior to SQL execution.


=== OUTPUT X ===

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


=== OUTPUT Y ===

### Verdict
**NOT VERIFIED** — **BLOCKING: yes**

### Independence
**INDEPENDENT** — The artifact and contract arrived finished in the prompt; no prior drafting or refinement occurred in this session.

---

### Observable evidence
- **Data leakage / contract breach:** Line 17 explicitly queries `i.customer_id`, and `res.json(invoice)` on Line 31 transmits the raw query row without filtering or DTO mapping.
- **Contract violation:** The contract specifies that `InvoiceDTO` is `{ id, number, amount_cents, status, due_date, customer_name }` and explicitly mandates: *"Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id)."*

---

### Assessment
- The leak is deterministic: every successful request (`200 OK`) leaks `customer_id` into the response body.
- The parameter validation (`Number.isInteger(id) && id > 0`) and tenant isolation (`WHERE i.id = $1 AND i.org_id = $2`) successfully prevent SQL injection, cross-org data leaks, and unhandled 500 errors on non-numeric IDs.

---

### Defects
1. ❌ **HIGH — Leak of forbidden field `customer_id` / DTO schema violation**
   - *Breach:* The contract explicitly forbids returning `customer_id`, and defines the DTO without it. The artifact includes `i.customer_id` in the SQL `SELECT` statement (line 17) and serializes the raw result directly via `res.json(invoice)` (line 31).
   - *Demonstration:* Request `GET /api/invoices/123` with valid auth. Response payload is `{"id":123,"number":"INV-01","amount_cents":5000,"status":"paid","due_date":"2025-01-01","customer_id":456,"customer_name":"Acme Corp"}`.
2. ⚠️ **LOW — Inner JOIN hides invoices with deleted/missing customer records**
   - *Breach:* Using an `INNER JOIN customers c` means if an invoice has a null `customer_id` or an orphaned customer reference, the query returns null and responds with a `404 Not Found` rather than retrieving the invoice. (Assessment: minor depending on DB foreign key constraints).

---

### Claimed vs. actual
- **Claimed:** Returns `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }` with no `customer_id`.
- **Actual:** Returns `{ id, number, amount_cents, status, due_date, customer_id, customer_name }`.

---

### Confirm-these
- *None.* All axes relevant to the contract were directly verifiable from the provided source code.

---

### How each clean axis was checked
- ✅ **IDOR / Multi-tenancy isolation:** Line 23 enforces `AND i.org_id = $2` with parameterized `$2 = req.user.org_id`; cross-tenant lookups evaluate to null.
- ✅ **Uniform 404 behavior:** Line 27 (`if (!invoice)`) returns identical 404 responses whether an invoice does not exist or belongs to another tenant.
- ✅ **Malformed ID handling:** Lines 5–8 check `!Number.isInteger(id) || id <= 0` and return HTTP 400, preventing non-integer input from reaching the database driver or triggering a 500.
- ✅ **Other forbidden fields protected:** Line 11–18 selects specific columns and omits `email`, `tax_id`, `payment_token`, `portal_password_hash`, and `org_id`.


=== OUTPUT Z ===

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

