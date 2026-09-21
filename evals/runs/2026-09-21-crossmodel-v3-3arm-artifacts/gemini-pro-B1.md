**Verdict:** NOT VERIFIED
**BLOCKING:** yes

**Independence:** INDEPENDENT. The artifact was provided directly in the prompt, not produced by me in this session.

### Observable Evidence
- The contract strictly defines the output as `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }`.
- The contract explicitly forbids returning `customer_id` ("no email, tax_id, payment_token, portal_password_hash, org_id, customer_id").
- The artifact's SQL query explicitly selects `i.customer_id` (line 17).
- The artifact passes the raw query result object directly to the response via `return res.json(invoice);` (line 34), leaking the forbidden `customer_id` field to the client.
- Cross-org anti-enumeration is observably enforced: the `WHERE i.org_id = $2` clause ensures a missing invoice and a cross-org invoice both result in `null` from `db.oneOrNone`, passing to the identical `404` branch (line 30).
- Malformed IDs are observably trapped: `Number(req.params.id)` and `!Number.isInteger(id)` (lines 5-6) correctly catch strings, floats, and `NaN`, returning 400 before attempting DB execution.

### Assessment
- The authorization relies on `req.user.org_id` being correctly populated by the `requireSession()` middleware. If that middleware ever allows a session without an `org_id`, the query parameter `$2` would be undefined/null, which might fail safely (yielding no rows) but is an unverified dependency.
- The use of `db.oneOrNone` prevents a 500 error that would typically be thrown by strict `db.one` methods when no rows are found, aligning with the error-handling contract.

### Defects
- ❌ **HIGH — Data Leakage / Contract Breach** — The API leaks the `customer_id`. The contract explicitly denylists `customer_id` from leaving the server. To demonstrate: successfully request an invoice; the JSON payload will contain `{"customer_id": 123, ...}` because the SQL SELECT includes it and `res.json(invoice)` serializes the raw database row without stripping it.

### Claimed vs. Actual
- **Claimed:** Returns an `InvoiceDTO` and nothing else about the customer leaves the server.
- **Actual:** Returns a superset of `InvoiceDTO` that leaks the `customer_id` directly to the client.

### Confirm-these
- **Middleware guarantees:** Confirm that `requireSession()` strictly guarantees `req.user.org_id` is present and non-null for all authenticated sessions.

### How each clean axis was checked
- ✅ **IDOR / Authz:** `WHERE ... AND i.org_id = $2` maps to `req.user.org_id`, preventing database retrieval of invoices outside the caller's organization.
- ✅ **Anti-enumeration:** Lines 23 & 30: both non-existent IDs and out-of-org IDs yield 0 rows, making `invoice` falsy, triggering the exact same 404 response.
- ✅ **Malformed ids:** Lines 5-8: `Number.isInteger(id)` correctly evaluates to `false` for strings and non-numeric payloads (which convert to `NaN`), throwing a 400 before DB execution.
