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
