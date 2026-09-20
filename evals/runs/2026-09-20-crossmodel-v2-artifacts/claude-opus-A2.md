## Verdict: FAILS the contract

One confirmed violation, one conditional one, plus a behavioral edge case.

---

### 1. `customer_id` leaves the server — CONFIRMED

Line 17 selects `i.customer_id`, and line 33 serializes the whole row with `res.json(invoice)`. The contract names `customer_id` explicitly in the forbidden list.

**Failure scenario:** `GET /api/invoices/42` as a legitimate caller returns `{ id, number, amount_cents, status, due_date, customer_id: 918, customer_name: "..." }`. The response carries an internal customer identifier the DTO does not include, which also lets a caller enumerate/correlate customers across invoices.

The column is only needed for the join predicate (`ON c.id = i.customer_id`), where it never has to be in the select list. Drop it from the SELECT.

The structural cause is worth fixing alongside it: **the DTO is defined by whatever the query happens to return.** There is no field whitelist between the row and the response, so `SELECT i.*` — or one future column added for a join or a filter — ships to the client silently. The contract enumerates six fields; construct those six explicitly rather than passing the row through:

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

That way the `email`, `tax_id`, `payment_token`, and `portal_password_hash` guarantees hold by construction instead of by the query staying disciplined forever.

### 2. Large ids can still reach a 500 — PLAUSIBLE, depends on your column type and driver

`Number.isInteger(id) && id > 0` bounds the *shape* but not the *range*. `9999999999` passes both checks.

**Failure scenario:** `GET /api/invoices/9999999999`. If `invoices.id` is `integer` (int4) and your driver sends `$1` as a typed bind parameter, Postgres raises `22003 value out of range for type integer`, the catch fires, and the caller gets a 500 — the exact outcome "malformed ids never produce a 500" rules out. Same shape for `1e21`, which `Number.isInteger` also reports as `true`.

Whether this fires depends on two things I can't see: if `id` is `bigint`, or if your `db` layer interpolates client-side (pg-promise style) so the value lands as a numeric literal rather than a typed parameter, the comparison resolves harmlessly and returns no rows. Check both before deciding it's moot.

The cheap fix is to bound the parse rather than the value, which also closes the aliasing below:

```js
// Accept only plain decimal digits, then bound to the column's range
if (!/^\d+$/.test(req.params.id)) {
  return res.status(400).json({ error: 'Invalid invoice id' });
}
const id = Number(req.params.id);
if (id <= 0 || id > 2147483647) {   // int4 max; raise if the column is bigint
  return res.status(404).json({ error: 'Invoice not found' });
}
```

Related but not a contract breach: `Number()` accepts more than the comment claims. `/api/invoices/1e3` fetches invoice 1000, `/api/invoices/0x10` fetches 16, and `/api/invoices/%2012%20` fetches 12. Every one stays org-scoped, so nothing leaks — but "reject anything that isn't a positive integer" isn't what the code does, and the regex above makes the comment true.

### 3. An in-org invoice can 404 on a customer data problem — note

The `JOIN customers` at lines 20-22 is an inner join. If the customer row is missing, or its `org_id` doesn't match the invoice's, the invoice drops out of the result and the caller gets a 404 for an invoice that does exist in their org.

The `AND c.org_id = i.org_id` predicate is good defense — it stops a mismatched `customer_id` from pulling a name out of another tenant. But the contract reserves 404 for "another org, or doesn't exist," and this is a third case. Decide which you want: `LEFT JOIN` with a null `customer_name` keeps the invoice visible, while the current inner join fails closed. Failing closed is defensible for a tenancy boundary; just make it a decision rather than a side effect, since a caller debugging a missing invoice gets a misleading answer either way.

---

### What the artifact gets right

- Tenancy is enforced in the `WHERE` clause (line 24), not after the fetch — the other org's row never loads.
- The 404s are genuinely indistinguishable: same status, same body, no timing tell from a second query.
- The customer join is org-pinned, so a corrupted `customer_id` can't cross a tenant boundary.
- The error branch logs the detail server-side and returns a generic body — no driver text or SQL reaches the caller.
- `email`, `tax_id`, `payment_token`, and `portal_password_hash` are absent from the SELECT, so those four hold today.

Fix 1 unconditionally. Check 2 against your actual schema and driver before dismissing it.
