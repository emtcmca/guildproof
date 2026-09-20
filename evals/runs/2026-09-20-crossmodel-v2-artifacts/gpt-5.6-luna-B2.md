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
