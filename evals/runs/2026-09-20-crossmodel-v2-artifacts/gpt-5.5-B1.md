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
