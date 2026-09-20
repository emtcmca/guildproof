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
