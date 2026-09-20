## Verdict

**NOT VERIFIED — BLOCKING: yes**

## Independence

**INDEPENDENT** — the artifact was supplied finished; I did not produce or revise it.

## Observable evidence

- The SQL explicitly selects `i.customer_id`.
- `res.json(invoice)` serializes every selected column.
- Therefore the response includes `customer_id`, which the contract explicitly forbids.
- Organization scoping is enforced with `i.org_id = $2`.
- Missing and cross-organization invoices both reach the same 404 branch.
- `org_id`, email, tax ID, payment token, and password hash are not selected.

## Defects

- ❌ **HIGH — DTO/privacy breach —** `customer_id` is selected and returned. Demonstrate with any valid invoice: the JSON body contains `{ ..., customer_id: ... }`, violating both the exact `InvoiceDTO` shape and the explicit no-`customer_id` requirement.
- ⚠️ **MEDIUM — malformed-ID handling is not fully established —** values such as `"999999999999999999999999"` become a positive integer under `Number(...)` and are sent to the database. If the database rejects the out-of-range integer, the catch block returns 500, violating the malformed-ID requirement. This needs runtime/database confirmation.

## Claimed vs. actual

The comment claims the endpoint returns “one invoice plus its customer's name,” but it returns the internal `customer_id` as well. The response is not the contracted `InvoiceDTO`.

## Confirm-these

- Whether oversized numeric path values cause a database conversion error and therefore a 500.
- Whether the application/database schema guarantees `req.user.org_id` is always present and correctly authenticated.

## How each clean axis was checked

- **Organization authorization:** SQL condition `AND i.org_id = $2`, with `$2 = req.user.org_id`.
- **Uniform not-found behavior:** `!invoice` returns status 404 regardless of why no row matched.
- **Excluded sensitive fields:** the explicit `SELECT` list contains none of email, tax ID, payment token, portal password hash, or `org_id`.
- **Customer name availability:** `c.name AS customer_name`.
- **No unhandled query exception:** database errors are caught and converted to 500; this does not cure malformed values that reach the query.

**Single most damaging defect:** the endpoint directly leaks `customer_id`, so it fails the contract even for an ordinary successful request.
