## Verdict: fails the contract on two clauses

**1. `customer_id` leaves the server — direct violation of the no-leak clause.**

The SELECT list includes `i.customer_id`, and the handler returns the raw row with `res.json(invoice)`. `customer_id` is named explicitly in the contract's forbidden list, so every 200 response ships a field it shouldn't. The comment above the route says "Returns one invoice plus its customer's name," which is what the author intended; the column list is what actually ships.

It's in the query because the JOIN predicate reads `c.id = i.customer_id` — but a join predicate doesn't require the column in the projection. Drop the line:

```js
`SELECT i.id,
        i.number,
        i.amount_cents,
        i.status,
        i.due_date,
        c.name AS customer_name
   FROM invoices i
   JOIN customers c
     ON c.id = i.customer_id
    AND c.org_id = i.org_id
  WHERE i.id = $1
    AND i.org_id = $2`
```

The deeper issue is that `res.json(invoice)` hands back whatever the query selected. Any future column added to the SELECT ships automatically. An explicit DTO mapping (`res.json({ id: invoice.id, number: ..., customer_name: ... })`) makes the leak impossible rather than merely absent today.

**2. A numerically-large id produces a 500 — violates "malformed ids never produce a 500."**

The guard is `Number.isInteger(id) && id > 0`. `Number("99999999999999999999")` is `1e20`, which **passes** both checks — `Number.isInteger` is true for any float with no fractional part, including ones far past `Number.MAX_SAFE_INTEGER`. That value reaches the DB, and if `invoices.id` is `integer`, Postgres raises `22003 numeric_value_out_of_range`, the catch block fires, and the caller gets a 500.

`GET /api/invoices/99999999999999999999` is the reproduction. Add an upper bound:

```js
if (!Number.isSafeInteger(id) || id <= 0 || id > 2147483647) {
  return res.status(400).json({ error: 'Invalid invoice id' });
}
```

Related and lower-stakes: `Number()` also accepts `"1e5"`, `"0x10"`, `"+5"`, and `" 5 "`, so several non-canonical strings alias to the same invoice. Not a contract breach — no leak, no 500 — but a regex like `/^[1-9]\d{0,9}$/` on `req.params.id` handles both this and the overflow in one check.

## Clauses that hold

- **Same 404 for cross-org and nonexistent.** `i.org_id = $2` is in the WHERE clause, both cases fall to the same `if (!invoice)` branch, same status and same body. No enumeration oracle. The malformed-id 400 doesn't open one either, since those inputs aren't valid ids in the first place.
- **The other forbidden fields** — `email`, `tax_id`, `payment_token`, `portal_password_hash`, `org_id` — are all absent from the projection, and there's no `SELECT *`.
- **All six DTO fields are present.**
- **Parameterized query**, no string interpolation into SQL.
- **The error path** logs internally and returns a generic message; no driver detail reaches the client.

## One thing to confirm against your schema

`JOIN customers` is an inner join, so an invoice whose `customer_id` is NULL — or whose customer row was deleted, or sits in a different org through a data inconsistency — returns 404 even though the invoice exists and belongs to the caller. If invoices can exist without a customer (drafts, for instance), that's a valid invoice the contract says should be returned, and a `LEFT JOIN` with `customer_name` nullable is the fix. If `customer_id` is `NOT NULL` with an FK, the inner join is correct as written.
