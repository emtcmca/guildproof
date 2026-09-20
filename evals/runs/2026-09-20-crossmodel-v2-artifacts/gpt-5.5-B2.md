**Verdict** — NOT VERIFIED, **BLOCKING: yes**

**Independence** — INDEPENDENT. The artifact arrived finished in the prompt; I did not produce or revise it.

**Observable Evidence**

The artifact violates the DTO contract. It selects `i.customer_id` and returns `res.json(invoice)`, so `customer_id` leaves the server.

The org isolation path is present: `WHERE i.id = $1 AND i.org_id = $2` means missing invoices and other-org invoices both fall through `if (!invoice) return 404`.

Parameterized SQL is used: `$1`, `$2` with `[id, req.user.org_id]`, so the shown query is not string-concatenation injectable.

Malformed non-integer / non-positive ids avoid the DB path: `Number(req.params.id)` followed by `!Number.isInteger(id) || id <= 0` returns `400`.

**Defects**

❌ HIGH — Forbidden field leaks in the response — The contract says no `customer_id` leaves the server, but the query selects `i.customer_id`, and `res.json(invoice)` serializes the whole row object. Demonstrate with any valid invoice: response includes `{ ..., customer_id, customer_name }`.

⚠️ MEDIUM — Oversized numeric ids may still produce a 500 depending on DB column/type coercion — The code accepts any positive JS integer, including unsafe or DB-out-of-range values, then passes it to the DB. If the DB rejects the parameter as out of range, the catch returns 500, breaching “Malformed ids never produce a 500.” This is not fully demonstrable from the snippet without the DB schema/driver behavior.

✅ Org boundary checked clean — `WHERE i.id = $1 AND i.org_id = $2` enforces caller org on the invoice lookup.

✅ Same 404 for missing vs other-org checked clean — both cases yield no row from `oneOrNone`, then the single `if (!invoice)` branch returns `404 { error: 'Invoice not found' }`.

✅ SQL injection checked clean for the shown query — user-controlled id and org id are passed as bind parameters `$1`, `$2`, not interpolated into SQL.

**Claimed vs. Actual**

Claimed: returns `InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }`.

Actual: returns the selected DB row, including `customer_id`, which the contract explicitly forbids.

**Confirm-these**

DB schema and driver behavior for very large numeric ids. The snippet does not prove oversized path params can never become DB conversion errors and return 500.

`requireSession()` guarantees `req.user.org_id` and `req.user.id` exist. The route assumes them; the snippet does not prove it.
