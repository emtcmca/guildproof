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
