**VERDICT:** **NOT VERIFIED**  
**BLOCKING:** Yes  
**INDEPENDENCE:** INDEPENDENT (Artifact was provided directly in the prompt; I did not produce it.)

### Observable Evidence
- The contract strictly defines the `InvoiceDTO` and explicitly forbids `customer_id` from leaving the server.
- The SQL query explicitly selects `i.customer_id` alongside the allowed fields.
- The handler returns the raw database row to the client via `res.json(invoice)` without mapping or stripping the output, exposing the forbidden field.
- The authorization constraint is structurally present: the query demands `i.org_id = req.user.org_id`.
- Parameterized queries are used (`$1`, `$2`), preventing basic SQL injection.
- ID validation explicitly rejects non-integers and numbers `<= 0` before touching the database.

### Assessment
- The reliance on `res.json(invoice)` to serialize a raw database row directly couples the database schema/query to the API response. This is fundamentally fragile and the direct cause of the data leak.
- The existence of `req.user.org_id` is assumed to be guaranteed by the `requireSession()` middleware.

### Defects
- ❌ **HIGH — Contract Breach / Data Leakage —** The endpoint leaks `customer_id` to the client. The contract explicitly forbids `customer_id` from leaving the server, yet the query selects `i.customer_id` and the handler passes the entire unmapped row directly into `res.json(invoice)`.

### Claimed vs. Actual
- **Claimed:** Returns an `InvoiceDTO` strictly limited to `{ id, number, amount_cents, status, due_date, customer_name }` with no `customer_id`.
- **Actual:** Returns `{ id, number, amount_cents, status, due_date, customer_id, customer_name }`.

### Confirm-These
*(No unconfirmable gaps on the core contract; the defect is directly observable in the code.)*

### How Each Clean Axis Was Checked
- ✅ **Caller's org enforcement:** The SQL query requires `i.org_id = $2`, passing `req.user.org_id` as the parameter, restricting access to invoices within the caller's organization.
- ✅ **Uniform 404 for missing/unauthorized:** An invoice in another org fails the `i.org_id = $2` constraint. Both missing and cross-org invoices cause `db.oneOrNone` to return `null`, which the code maps to a generic `404` (line 30), preventing ID enumeration.
- ✅ **Malformed IDs never 500:** Express route matching populates `req.params.id`. It is immediately coerced to a `Number`. Non-numeric strings become `NaN`, bypassing `Number.isInteger()`, and are safely rejected with a `400 Bad Request` on line 7 before any database execution.
- ✅ **SQL Injection:** Inputs are bound to parameters (`$1`, `$2`) rather than interpolated into the SQL string.
