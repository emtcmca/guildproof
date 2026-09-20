NOT VERIFIED

- **High — Response leaks `customer_id`.** The query selects `i.customer_id`, and `res.json(invoice)` returns it. The contract permits exactly `{ id, number, amount_cents, status, due_date, customer_name }` and explicitly prohibits `customer_id`.

- **Medium — Some malformed/out-of-range IDs can produce 500.** `Number.isInteger(id)` accepts values outside JavaScript’s safe-integer range and exponential forms such as `1e100`. Passing such a value to an integer database column may trigger a database range/conversion error, which the catch block turns into 500.

The organization boundary and indistinguishable 404 behavior appear correctly implemented.

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

Also remove `i.customer_id` from the `SELECT`, or explicitly construct the DTO before responding:

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
