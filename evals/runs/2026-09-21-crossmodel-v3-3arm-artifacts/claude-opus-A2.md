## Verdict: NOT VERIFIED — 2 contract violations, 1 behavioral divergence

### 1. `customer_id` leaves the server (leak, contract line 3)

The query selects `i.customer_id`, and the handler returns the raw row with `res.json(invoice)`. There is no projection step between the DB row and the response, so every column the query selects is a response field.

`customer_id` is on the contract's explicit prohibited list.

**Failure:** `GET /api/invoices/42` returns `{ id, number, amount_cents, status, due_date, customer_id, customer_name }` — seven fields where the DTO names six, and the extra one is named in the ban list. A caller can enumerate internal customer IDs by walking their own invoices.

The comment above the handler says it returns "one invoice plus its customer's name," which is what the author intended; the `customer_id` column was pulled in to satisfy the JOIN and never removed from the select list. It isn't needed — the JOIN condition can reference `i.customer_id` without projecting it.

Fix: drop `i.customer_id` from the SELECT, or build the DTO explicitly:

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

An explicit projection is the stronger fix: it fails closed when someone later adds a column to the query.

### 2. Out-of-range numeric ids produce a 500 (contract line 4)

`Number.isInteger()` is the wrong guard. It accepts any integer-*valued* float, including values far outside any SQL integer column:

- `Number("99999999999")` → `99999999999`, `Number.isInteger` → `true`, `> 0` → passes validation
- Postgres compares it against `i.id`. If `id` is `int4`, that's `value out of range for type integer`; if `bigint`, the same happens above ~9.2e18. Past 1e21 the driver serializes it as `1e+21` and you get `invalid input syntax for type integer`.
- Either way the driver throws, the `catch` fires, and the caller gets **500**.

**Failure:** `GET /api/invoices/99999999999` → 500, on an `int4` id column. The validation block exists precisely to prevent this and doesn't.

Fix: `Number.isSafeInteger(id) && id > 0 && id <= 2147483647` (match the actual column type), keeping the 400. The 400 itself is fine — the contract only forbids a 500 for malformed ids, and it doesn't reveal existence.

### 3. Minor — an inner JOIN turns a data-integrity problem into a 404

`JOIN customers c ON c.id = i.customer_id AND c.org_id = i.org_id` is an inner join. If an invoice in the caller's own org has a deleted customer row, or a customer whose `org_id` drifted, the row drops out and the caller gets 404 for an invoice that is genuinely theirs.

That is safe (it fails closed, no leak) but it diverges from "returns one invoice that belongs to the caller's organization," and it's the kind of thing that gets debugged as a phantom permissions bug. A `LEFT JOIN` with `customer_name` nullable, or an explicit integrity check, makes the failure legible. Judgment call — flagging, not asserting it's wrong.

### What the artifact gets right

- **The 404 conflation is correct.** Nonexistent and other-org both hit `!invoice` and return the identical body. No timing or status-code oracle for ID probing.
- **Org scoping is in the WHERE clause, not applied after the fetch.** `i.org_id = $2` means another org's row never enters the process.
- **The customer is org-scoped too** (`c.org_id = i.org_id`), so a mismatched `customer_id` can't pull a name across the tenant boundary.
- **Parameterized query** — no injection surface.
- **The error log stays server-side**; the 500 body is generic.

The two violations are both one-line fixes. Neither is an auth hole — the tenant boundary itself holds.
