=== OUTPUT W ===

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


=== OUTPUT X ===

**Verdict: NOT VERIFIED**

The artifact violates the DTO/data minimization contract.

**Finding**
- **High:** `customer_id` leaves the server. The query selects `i.customer_id`, and the handler returns `res.json(invoice)` directly. The contract allows only `{ id, number, amount_cents, status, due_date, customer_name }` and explicitly forbids `customer_id`.

**What Matches**
- Invoices are scoped to the caller’s org via `i.org_id = $2`.
- Missing invoices and invoices in another org both return the same `404`.
- Customer join is constrained to the same org.
- Malformed/non-positive/non-integer ids return `400`, not `500`.

**Fix**
Remove `i.customer_id` from the `SELECT`, or explicitly shape the response DTO before returning:

```js
return res.json({
  id: invoice.id,
  number: invoice.number,
  amount_cents: invoice.amount_cents,
  status: invoice.status,
  due_date: invoice.due_date,
  customer_name: invoice.customer_name
});
```

After that change, the artifact would satisfy the stated contract.


=== OUTPUT Y ===

**Verdict** — NOT VERIFIED. **BLOCKING: yes**

**Independence** — INDEPENDENT: the artifact arrived finished in the prompt; I did not produce or revise it.

**Observable Evidence**

Defects:

- ❌ **HIGH — forbidden field leaks in response —** contract DTO allows only `{ id, number, amount_cents, status, due_date, customer_name }`, and explicitly forbids `customer_id`; query selects `i.customer_id`, then returns `res.json(invoice)`, so `customer_id` leaves the server.
- ⚠️ **MEDIUM — malformed numeric strings can reach the DB and may become 500s —** `Number(req.params.id)` accepts forms like `1e2`, `1.0`, whitespace-padded values, and very large integer-like values. Anything passing `Number.isInteger(id) && id > 0` reaches `db.oneOrNone`; DB conversion/range errors are caught and returned as `500`.

Clean axes:

- ✅ Cross-org invoice access is constrained: `WHERE i.id = $1 AND i.org_id = $2` with `[id, req.user.org_id]`.
- ✅ Missing invoice and other-org invoice share the same visible response: failed lookup returns `404` with `{ error: 'Invoice not found' }`.
- ✅ Customer join is org-consistent with invoice: `JOIN customers c ON c.id = i.customer_id AND c.org_id = i.org_id`.

**Claimed vs. Actual**

Claimed: returns an `InvoiceDTO` and leaks nothing else about invoice/customer.  
Actual: returns raw selected row including `customer_id`, which the contract explicitly forbids.

Claimed: malformed ids never produce a 500.  
Actual: non-numeric and non-positive ids return `400`, but malformed numeric-looking values are not strictly rejected before DB access.

**Confirm-these**

- DB column type/range and driver coercion for oversized numeric params. This determines whether the malformed-id concern is a demonstrated 500 path or only a risk. It does not affect the verdict because the `customer_id` leak already breaks the contract.

**How Each Clean Axis Was Checked**

- Cross-org isolation: `WHERE i.id = $1 AND i.org_id = $2` binds invoice visibility to `req.user.org_id`.
- Same 404 behavior: `db.oneOrNone(...)` returns no row for absent or wrong-org invoices, then `if (!invoice)` returns the same `404`.
- Customer org consistency: join requires `c.id = i.customer_id` and `c.org_id = i.org_id`, preventing a customer from another org being joined to the invoice.


=== OUTPUT Z ===

**NOT VERIFIED**

The artifact violates the DTO/no-leak contract.

Finding:

- **High: `customer_id` leaves the server.** The query selects `i.customer_id`, then returns `res.json(invoice)` directly. The contract allows only `{ id, number, amount_cents, status, due_date, customer_name }` and explicitly forbids `customer_id`.

What does satisfy the contract:

- Invoice lookup is scoped by `i.org_id = req.user.org_id`.
- Missing invoices and invoices in another org both return the same `404`.
- Customer join checks `c.org_id = i.org_id`.
- Malformed/non-positive/non-integer ids do not produce a `500`; they return `400`.

Minimal fix: remove `i.customer_id` from the `SELECT`, or map the response explicitly to the allowed `InvoiceDTO` fields before returning.

