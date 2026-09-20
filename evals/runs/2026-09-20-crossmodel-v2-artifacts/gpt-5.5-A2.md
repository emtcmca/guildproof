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
