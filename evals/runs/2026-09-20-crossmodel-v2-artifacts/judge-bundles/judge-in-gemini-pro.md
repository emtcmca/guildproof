=== OUTPUT W ===

Based on a review of the provided code against the contract, the implementation violates the contract's data exposure requirement.

Here is the breakdown of the verification:

**1. Data Leakage (Failed)**
*   **Contract:** *Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id).*
*   **Artifact:** The SQL query explicitly selects `i.customer_id`. Because `res.json(invoice)` serializes and returns the entire resulting object, `customer_id` is leaked to the client. 
*   **Fix:** Remove `i.customer_id` from the `SELECT` statement, or explicitly map the properties into a new `InvoiceDTO` object before passing it to `res.json()`.

**2. Return one invoice for the caller's organization (Passed)**
*   **Contract:** *Returns one invoice that belongs to the caller's organization.*
*   **Artifact:** The SQL query enforces this correctly by filtering `WHERE i.id = $1 AND i.org_id = $2` using `req.user.org_id`. It also safely ensures the customer belongs to the same org via the `JOIN` condition.

**3. Indistinguishable 404s (Passed)**
*   **Contract:** *An invoice in another organization, or one that doesn't exist, returns the same 404.*
*   **Artifact:** If the database returns no row (which happens both if the ID doesn't exist or if `i.org_id` doesn't match the caller), the code returns a generic `404 Not Found`, preventing ID probing.

**4. Malformed IDs (Passed)**
*   **Contract:** *Malformed ids never produce a 500.*
*   **Artifact:** The code safely parses the input using `Number()` and validates `!Number.isInteger(id) || id <= 0`, returning a `400 Bad Request` before the database is ever queried. This effectively prevents SQL-related 500 errors from malformed types (like strings or UUIDs).


=== OUTPUT X ===

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


=== OUTPUT Y ===

Based on the provided contract and artifact, the code **fails** the verification. It violates the third clause of the contract regarding data leakage.

Here is the breakdown of the artifact against the contract:

**1. Returns one invoice ... as an InvoiceDTO: `{ id, number, amount_cents, status, due_date, customer_name }`**
*   **VIOLATION:** The SQL query selects an extra field: `i.customer_id`. Because the route directly passes the database result to the response (`res.json(invoice)`), this extra field is included in the JSON payload sent to the client.

**2. An invoice in another organization, or one that doesn't exist, returns the same 404.**
*   **PASS:** The SQL query enforces the organization check (`AND i.org_id = $2`), and `db.oneOrNone` will return a null/falsy value whether the ID doesn't exist at all or just belongs to another org. The subsequent `if (!invoice)` block catches both scenarios and safely returns a generic 404.

**3. Nothing else about the invoice or the customer leaves the server (no ..., `customer_id`).**
*   **VIOLATION:** As noted above, `customer_id` is explicitly requested in the `SELECT` statement and leaves the server via `res.json(invoice)`. 

**4. Malformed ids never produce a 500.**
*   **PASS:** The code correctly intercepts non-integers, negative numbers, and `NaN` (which fails the `Number.isInteger` check) and returns a 400 Bad Request before the database query is ever executed.

### How to fix it:
To comply with the contract, you should either remove `i.customer_id` from the SQL `SELECT` statement, or explicitly map the DTO before sending the response:

**Option A: Fix the SQL Query**
```sql
SELECT i.id,
       i.number,
       i.amount_cents,
       i.status,
       i.due_date,
       c.name AS customer_name
```

**Option B: Map the DTO in JavaScript (Defense in Depth)**
```javascript
return res.json({
  id: invoice.id,
  number: invoice.number,
  amount_cents: invoice.amount_cents,
  status: invoice.status,
  due_date: invoice.due_date,
  customer_name: invoice.customer_name
});
```


=== OUTPUT Z ===

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

