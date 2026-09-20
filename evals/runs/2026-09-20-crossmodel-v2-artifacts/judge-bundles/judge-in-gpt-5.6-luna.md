=== OUTPUT W ===

## Verdict

**NOT VERIFIED**  
**BLOCKING: yes**

## Independence

**INDEPENDENT** — the artifact was supplied finished in the request; I did not produce or revise it.

## Observable evidence

❌ **HIGH — forbidden field exposed.** The `SELECT` includes `i.customer_id`, and the handler returns `invoice` directly via `res.json(invoice)`. Therefore the response contains `customer_id`, explicitly forbidden by the contract.

✅ Organization scoping is enforced by `i.org_id = $2`, using `req.user.org_id`.

✅ Missing invoices and invoices outside the caller’s organization both produce the same `404` response because both yield no row.

✅ Basic invalid values such as non-numeric strings, zero, negatives, `NaN`, and `Infinity` are rejected before the database query.

## Assessment

The single damaging defect is the direct exposure of `customer_id`. This is a concrete contract breach, not a style issue. The artifact is therefore blocked.

## Defects

- ❌ **HIGH — `customer_id` leaks in the InvoiceDTO —** remove it from the selected columns or construct an explicit response DTO. Demonstrate with any valid invoice request and inspect the JSON body.
- ⚠️ **MEDIUM — malformed numeric forms are accepted —** `Number('1e2')`, `Number(' 42 ')`, and similar values pass validation and reach the database. They do not necessarily cause a 500, but they are not strict positive-integer path IDs. Demonstrate with `/api/invoices/1e2` and `/api/invoices/%2042%20`.

## Claimed vs. actual

The artifact claims to return “one invoice plus its customer's name” as the contract DTO. Actual output also includes `customer_id`.

## Confirm-these

- Whether the database driver or serializer adds any additional fields or transforms; the shown code already proves `customer_id` is exposed.
- Whether malformed accepted numeric forms can trigger a database-specific error; the `try/catch` converts such errors to `500`, so this should be tested explicitly.

## How each clean axis was checked

- **Organization authorization:** SQL predicate `AND i.org_id = $2` with parameter `req.user.org_id`.
- **Same 404 behavior:** `oneOrNone` returns no row, followed by `res.status(404)`.
- **Customer organization join:** `c.org_id = i.org_id`.
- **Error containment:** database exceptions are caught and converted to a generic 500 response.
- **Response leakage axis:** failed because `i.customer_id` is selected and the complete row is returned.


=== OUTPUT X ===

Does not fully satisfy the contract.

- Organization isolation and indistinguishable 404s are implemented correctly.
- Malformed numeric IDs are rejected before the database call, so they should not produce a 500.
- The response leaks `customer_id`, which is not part of `InvoiceDTO` and is explicitly forbidden.

Fix by removing `i.customer_id` from the `SELECT` list. Optionally validate IDs more strictly if only decimal path IDs are intended; `Number()` accepts forms such as `0x10` and scientific notation.


=== OUTPUT Y ===

Contract verification: **Fail**

The endpoint satisfies:

- Organization scoping via `i.org_id = $2`.
- Same 404 response for nonexistent or cross-organization invoices.
- Customer organization consistency via the join.
- Malformed IDs are rejected before the database, so they should not produce a 500.

Violation:

- The query selects `i.customer_id`, and `return res.json(invoice)` exposes it. `customer_id` is explicitly forbidden and is not part of `InvoiceDTO`.

Fix by removing `i.customer_id` from the `SELECT` list, or explicitly constructing the response DTO:

```js
return res.json({
  id: invoice.id,
  number: invoice.number,
  amount_cents: invoice.amount_cents,
  status: invoice.status,
  due_date: invoice.due_date,
  customer_name: invoice.customer_name,
});
```

After that change, the artifact conforms to the stated contract.


=== OUTPUT Z ===

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

