NOT VERIFIED

- **Critical — data exposure:** The query selects `i.customer_id`, and `res.json(invoice)` returns it. The contract explicitly forbids `customer_id` from leaving the server. The response is therefore not an `InvoiceDTO`.

- **High — malformed IDs may produce 500:** Validation uses `Number.isInteger` instead of `Number.isSafeInteger` or strict decimal parsing. Inputs such as `999999999999999999999999` can pass validation but exceed the database column’s numeric range, potentially causing a query error and a 500. Forms such as `0x10`, `1e3`, and whitespace-padded numbers are also accepted despite not being conventional integer path IDs.

Verified aspects:

- The organization predicate prevents access to invoices outside `req.user.org_id`.
- Missing and cross-organization invoices use the same 404 response.
- The query does not select the other prohibited fields (`email`, `tax_id`, `payment_token`, `portal_password_hash`, or `org_id`).

Required fixes:

```js
if (!/^[1-9]\d*$/.test(req.params.id)) {
  return res.status(400).json({ error: 'Invalid invoice id' });
}

const id = Number(req.params.id);
if (!Number.isSafeInteger(id)) {
  return res.status(400).json({ error: 'Invalid invoice id' });
}
```

Remove `i.customer_id` from the `SELECT`, and preferably construct the DTO explicitly before responding:

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
