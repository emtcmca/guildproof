**Verdict:** NOT VERIFIED
**BLOCKING:** yes

**Independence:** INDEPENDENT. The artifact arrived finished in the prompt; I did not produce it.

**Observable evidence:**
- The SQL query explicitly selects `i.customer_id`.
- The route returns the exact object returned by the database: `return res.json(invoice)`.
- Consequently, `customer_id` is serialized and sent to the client.

**Assessment:**
The code implements strong IDOR prevention by enforcing the organization check directly in the SQL query (`AND i.org_id = $2`), successfully fulfilling the "same 404" requirement. However, it fails basic data encapsulation by returning the raw database row instead of mapping it to the agreed-upon DTO, causing a direct violation of the data leakage constraints.

**Defects:**
- ❌ **HIGH — Data Leakage / Contract Breach** — The contract explicitly forbids `customer_id` from leaving the server. The code selects `i.customer_id` in the SQL statement and passes the raw `invoice` object directly to `res.json()`, leaking the internal database ID to the client. Demonstrate by inspecting the JSON response body, which will contain `customer_id`.

**Claimed vs. actual:**
- **Claimed:** Returns an `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }`.
- **Actual:** Returns `{ id, number, amount_cents, status, due_date, customer_id, customer_name }`.
- **Claimed:** "Nothing else about the invoice or the customer leaves the server (... customer_id)."
- **Actual:** The `customer_id` leaves the server on every successful 200 response.

**Confirm-these:**
- Is `req.user.org_id` reliably populated by `requireSession()`? If a session exists but lacks `org_id`, the SQL query parameter `$2` will be undefined/null, which may either cause a 500 or quietly return 0 rows depending on the database driver. 
- Does `db.oneOrNone` throw an error on 0 rows? (Assuming standard `pg-promise` behavior where it correctly resolves to `null` on 0 rows, allowing the `!invoice` check to work).

**How each clean axis was checked:**
- ✅ **Caller's org only:** Traced to SQL `WHERE i.id = $1 AND i.org_id = $2` bounding the query to `req.user.org_id`.
- ✅ **Same 404 for missing/unauthorized:** Traced to the database returning 0 rows for both conditions, which causes `invoice` to be null, hitting the `if (!invoice)` branch and returning a hardcoded 404.
- ✅ **Malformed IDs never produce 500:** Traced to the manual cast `Number(req.params.id)` and boundary check `!Number.isInteger(id) || id <= 0`, which intercepts strings, UUIDs, and floats, returning a 400 before the database driver can throw a type-casting 500.
