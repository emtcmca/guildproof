**VERDICT:** NOT VERIFIED
**BLOCKING:** yes, due to an unresolved HIGH defect (contract violation/data leakage).
**INDEPENDENCE:** INDEPENDENT — Artifact was provided in the prompt and not authored by me.

### Observable Evidence
- **Data Leakage:** The `SELECT` statement explicitly retrieves `i.customer_id` (line 14).
- **Direct Serialization:** The payload returned to the client is the raw database row (`return res.json(invoice);` on line 33), bypassing any DTO mapping.
- **Contract Explicitly Refuted:** The contract explicitly dictates `no customer_id` leaves the server. The response will contain `{"id": ..., "number": ..., "amount_cents": ..., "status": ..., "due_date": ..., "customer_id": ..., "customer_name": ...}`.

### Assessment
- The producer likely included `i.customer_id` in the `SELECT` statement out of habit or confusion with the `JOIN` clause, failing to recognize that returning raw database rows directly into `res.json()` breaks the strict API boundary and leaks internal identifiers. 

### Defects
- ❌ **HIGH — Contract Violation / Data Leakage —** The API leaks `customer_id` in the response payload. Demonstrate by executing the query and inspecting the JSON output; `res.json(invoice)` serializes the entire database row returned by `db.oneOrNone`, which includes `i.customer_id` retrieved in the `SELECT` list.

### Claimed vs. Actual
- **Claimed:** Returns an `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }` with explicitly *no* `customer_id`.
- **Actual:** Returns a database row containing `{ id, number, amount_cents, status, due_date, customer_id, customer_name }`.

### Confirm-these
- None. The context provided is sufficient to fully refute the artifact against its contract.

### How each clean axis was checked
- ✅ **IDOR / Cross-Org Access:** Line 24 enforces `AND i.org_id = $2` with parameter `$2` firmly mapped to `req.user.org_id` (line 25).
- ✅ **Indistinguishable 404s:** Line 30 checks `if (!invoice)` and returns a generic 404, satisfying the requirement that non-existent and wrong-org invoices are indistinguishable.
- ✅ **Malformed IDs produce 400, not 500:** Lines 6-7 parse route parameter strictly using `Number()` and `Number.isInteger()`, immediately returning 400 for anything like `"abc"` (`NaN`) or floats before execution reaches the database. 
- ✅ **SQL Injection prevention:** The query uses parameterized queries (`$1, $2`) correctly (line 25), mitigating string concatenation vulnerabilities.
