**VERDICT:** NOT VERIFIED  
**BLOCKING:** yes  

**INDEPENDENCE:** INDEPENDENT — The artifact was provided in the prompt and not produced by me.

**OBSERVABLE EVIDENCE:**
- The SQL query explicitly selects `i.customer_id` on line 14 (`SELECT i.id, i.number, i.amount_cents, i.status, i.due_date, i.customer_id, c.name AS customer_name`).
- The endpoint blindly passes the raw database result to the client via `res.json(invoice)` on line 33.
- The contract strictly forbids `customer_id` from leaving the server.

**ASSESSMENT:**
- The input validation `Number.isInteger(id)` fails to account for numbers that are integers in JavaScript but out of bounds for PostgreSQL (e.g., passing `1e30` or `999999999999999999`). Such values will bypass the 400 check, trigger a database-level `out of range` exception, fall into the `catch` block, and return a 500, violating the "Malformed ids never produce a 500" constraint.

**DEFECTS:**
- ❌ **HIGH** — Data leakage / DTO violation — `customer_id` is exposed to the client. Demonstrate by calling the endpoint with a valid ID; the response payload will include `"customer_id": <id>`, explicitly violating the negative constraint in the contract.
- ❌ **MEDIUM** — Unhandled malformed ID / 500 error — Out-of-bounds numeric strings (e.g. `"999999999999999999999999"`) parse as valid JS integers but cause DB query exceptions. Demonstrate by passing a massive integer; observe a 500 response instead of the contracted 400.
- ✅ **Clean** — Authorization / Tenant isolation.
- ✅ **Clean** — Indistinguishable 404s.
- ✅ **Clean** — SQL Injection sinks.

**CLAIMED VS. ACTUAL:**
- **Claimed:** "Returns one invoice plus its customer's name... Nothing else about the invoice or the customer leaves the server."
- **Actual:** Returns the invoice, the customer's name, *and* the `customer_id`.
- **Claimed:** "Malformed ids never produce a 500."
- **Actual:** Malformed integer IDs that exceed DB bounds produce a 500.

**CONFIRM-THESE:**
- None. The contract breaches are observable from the provided code.

**HOW EACH CLEAN AXIS WAS CHECKED:**
- ✅ **Authorization**: Line 24 `AND i.org_id = $2` with parameter `req.user.org_id` ensures the database strictly limits matches to the caller's tenant.
- ✅ **Indistinguishable 404s**: Line 29 `if (!invoice)` checks the single result. Because the `WHERE` clause filters out both non-existent IDs and IDs belonging to other orgs, the exact same `404` response (Line 30) is returned for both scenarios, preventing probing.
- ✅ **SQL Injection**: Line 25 uses an array of parameterized inputs (`[id, req.user.org_id]`) corresponding to `$1` and `$2`, neutralizing injection.
