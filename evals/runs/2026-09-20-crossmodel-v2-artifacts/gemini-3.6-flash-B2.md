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
