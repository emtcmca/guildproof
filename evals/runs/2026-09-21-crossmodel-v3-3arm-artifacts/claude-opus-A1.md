## Verdict: FAILS the contract — one confirmed leak, one confirmed 500 path

Three of the four clauses hold. Org scoping is correct (both the invoice and the joined customer are constrained to the caller's org), and the indistinguishable-404 clause holds — a missing invoice and another org's invoice take the identical `!invoice` branch. Non-numeric garbage (`abc`, `../../etc`, `null`) is rejected at the 400 gate before it reaches the DB.

Here is what breaks.

---

### 1. `customer_id` leaves the server — explicitly banned by the contract

`i.customer_id` is in the SELECT list, and `res.json(invoice)` serializes the whole row. The contract names `customer_id` in the prohibited set. The column isn't used anywhere in the handler — it's selected and then shipped.

**Failure:** `GET /api/invoices/42` returns `{ id, number, amount_cents, status, due_date, customer_id: 8891, customer_name }`. The caller now has an internal customer identifier it was never supposed to see, and `customer_id` values are sequential and enumerable across the tenant.

**Fix — stop trusting the SELECT list to be the DTO.** Build the response explicitly, so a future column added to the query can't leak by default:

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

Dropping `i.customer_id` from the query also fixes today's instance, but the explicit DTO is what makes the clause hold permanently. The current code's contract compliance depends on nobody ever adding a column to that SELECT.

---

### 2. A numeric-but-out-of-range id produces a 500

`Number.isInteger()` only asks whether the value is an integer, not whether it fits the column. `Number("9999999999")` is `9999999999` — an integer, greater than zero, so it sails past the guard. node-postgres stringifies it and Postgres rejects it against an `int4` column with *"value out of range for type integer"*. That throws, hits the catch, and returns 500.

**Failure:** `GET /api/invoices/9999999999` → 500 Internal Server Error, plus an `logger.error` entry. Same for `GET /api/invoices/1e21`, where `Number()` yields `1e+21` and pg sends the literal string `"1e+21"` — Postgres errors with *"invalid input syntax for type integer"*. Both are malformed ids by any reasonable reading, and the contract says malformed ids never produce a 500.

This is also a cheap unauthenticated-ish noise generator: every request writes an error log line, so it's a log-flooding lever for anyone with a session.

**Fix — validate the string, then bound it:**

```js
// Match the wire format strictly, then check it fits the column.
// Number() is too permissive: it accepts "1e3", "0x10", " 12 ", and out-of-range values.
const MAX_INT4 = 2147483647;
if (!/^[1-9][0-9]*$/.test(req.params.id)) {
  return res.status(400).json({ error: 'Invalid invoice id' });
}
const id = Number(req.params.id);
if (id > MAX_INT4) {
  return res.status(400).json({ error: 'Invalid invoice id' });
}
```

If the column is `bigint`, swap the bound for `Number.MAX_SAFE_INTEGER` — or keep the id as a string and let Postgres parse it, which avoids the float-precision question entirely.

---

### 3. Lower confidence, depends on your schema: the inner JOIN can 404 an invoice the caller owns

`JOIN customers c` is an inner join. If `i.customer_id` is nullable — a draft invoice with no customer attached yet — or if the customer row was deleted, the join drops the row and the caller gets a 404 for an invoice that exists inside their own organization. The contract reserves 404 for "another organization, or one that doesn't exist."

The `AND c.org_id = i.org_id` predicate is good defense, but it's doing double duty: it's both a security check and a visibility filter, and when it fails you can't tell a cross-org data-integrity problem from a normal miss.

**Whether this is a defect is a schema question I can't answer from the artifact.** If `invoices.customer_id` is `NOT NULL` with an FK to `customers`, the inner join can never drop a row and this is a non-issue. If it's nullable, switch to `LEFT JOIN` and let `customer_name` come back null — and consider logging a warning when the invoice resolves but the customer doesn't, because that state means either a dangling reference or a cross-org row worth knowing about.

---

**One thing worth confirming rather than fixing:** `due_date` comes back as whatever pg maps the column to. A `date` column yields a JS `Date` at midnight UTC, which `res.json` serializes as `"2026-03-14T00:00:00.000Z"` — not the `"2026-03-14"` most DTO consumers expect from a field named `due_date`. The contract names the field but not its shape, so this isn't a violation; it's just the kind of thing that turns into a client-side bug later.
