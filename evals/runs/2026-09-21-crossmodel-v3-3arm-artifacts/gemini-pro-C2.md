**Verdict** — NOT VERIFIED, and **BLOCKING: yes**

**Independence** — INDEPENDENT, as all logic for the endpoint, query, and response are contained in the provided snippet.

**Observable evidence**
- The SQL query explicitly includes `i.customer_id` in its `SELECT` clause.
- The route returns the raw database object using `res.json(invoice)`.
- Malformed IDs are intercepted and return 400 Bad Request before database execution.
- Missing invoices and unauthorized invoices both return null from `db.oneOrNone` because of the `AND i.org_id = $2` clause, yielding the same 404 response.

**Assessment**
- The database schema and `db.oneOrNone` behavior are assumed standard based on common SQL/Node.js library conventions (e.g., pg-promise), meaning `res.json(invoice)` serializes everything in the select list.

**Defects**
- ❌ HIGH — Data Leakage — The contract explicitly forbids returning `customer_id`, but the query selects `i.customer_id` and the endpoint returns it verbatim via `res.json(invoice)`. Demonstrate by calling the endpoint with a valid ID and observing `"customer_id"` in the JSON response.

**Claimed vs. actual**
- *Claimed:* Returns exactly the InvoiceDTO and nothing else leaves the server (specifically forbidding `customer_id`).
- *Actual:* Includes the `customer_id` in the API response.

**Confirm-these**
- None (independent artifact evaluated).

**How each clean axis was checked**
- ✅ Endpoint path and method checked: `router.get('/api/invoices/:id' ...)` matches `GET /api/invoices/:id`.
- ✅ Only caller's org visible checked: `WHERE i.id = $1 AND i.org_id = $2` binds `$2` to `req.user.org_id`.
- ✅ Same 404 for missing/other org checked: Unowned/non-existent IDs fail the `WHERE` clause, `db.oneOrNone` returns a falsy value, triggering `if (!invoice) { return res.status(404)... }`.
- ✅ Malformed IDs never produce 500 checked: `id <= 0` or non-integers are caught by `!Number.isInteger(id) || id <= 0` and return 400 before DB execution; actual errors caught by `catch (err)` return 500 but are insulated from bad input data types.
