**Verdict**: NOT VERIFIED
**BLOCKING**: yes

**Independence**: INDEPENDENT — The artifact was provided in the prompt; I did not produce or revise it.

**Observable evidence**:
- The artifact passes the database row directly to the client via `res.json(invoice)`.
- The database query explicitly selects `i.customer_id`.
- Consequently, `customer_id` is exposed in the JSON response payload.
- The artifact avoids 500 errors on malformed IDs by casting to a Number and returning a 400 Bad Request before database execution.
- Cross-tenant IDOR is prevented at the database level by enforcing `i.org_id = $2` (`req.user.org_id`).
- Unauthorized/missing IDs are structurally forced to return the identical 404 response.

**Assessment**:
- I judge that the underlying database driver (`db.oneOrNone`) correctly handles parameterized queries (`$1`, `$2`), preventing SQL injection.

**Defects**:
- ❌ **HIGH — Contract Breach / Data Leak —** The endpoint leaks `customer_id` to the caller. The contract explicitly forbids `customer_id` from leaving the server, but the SQL query selects it (`i.customer_id`), and `res.json(invoice)` dumps the entire database row back to the client without mapping it to the agreed `InvoiceDTO`.

**Claimed vs. actual**:
- **Claimed**: Returns `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }`. Nothing else leaves the server.
- **Actual**: Returns `{ id, number, amount_cents, status, due_date, customer_id, customer_name }`, violating the explicit negative constraint on `customer_id`.

**Confirm-these**:
- The `requireSession()` middleware reliably populates `req.user.org_id` on every request. If it fails to do so (e.g., leaving it `undefined`), the query may execute with a null/undefined parameter, potentially altering the authorization boundary or throwing a 500 depending on the DB driver's strictness.

**How each clean axis was checked**:
- ✅ **IDOR / Cross-Org Access**: Traced `req.user.org_id` to `$2` in the parameterized query, strictly filtered by `AND i.org_id = $2`.
- ✅ **Probe prevention (Same 404)**: Traced missing IDs and cross-org IDs. Both cause `db.oneOrNone` to return a falsy value, which drops into `if (!invoice)` and returns the exact same `res.status(404).json({ error: 'Invoice not found' })`.
- ✅ **Malformed IDs do not 500**: Traced `req.params.id`. "xyz" parses to `NaN`, which fails `Number.isInteger(NaN)`. This halts execution and returns a safe 400 error before ever reaching the database layer.
- ✅ **SQL Injection**: Traced the ID through strict integer validation and into `$1` of a parameterized query method. Untrusted input is structurally separated from the query string.
