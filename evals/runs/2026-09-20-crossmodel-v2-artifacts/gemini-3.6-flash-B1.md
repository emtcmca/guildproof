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
