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
