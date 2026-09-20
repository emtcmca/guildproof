=== OUTPUT W ===

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


=== OUTPUT X ===

**Verdict — NOT VERIFIED**  
**BLOCKING: yes**

**Independence — INDEPENDENT.** The artifact arrived finished and was not produced or revised by this verifier.

**Most damaging defect:** The endpoint returns `customer_id`, a field the contract explicitly forbids from leaving the server.

### Observable evidence

❌ **HIGH — prohibited customer identifier is exposed**

The query selects:

```js
i.customer_id
```

The response returns the entire query result:

```js
return res.json(invoice);
```

Therefore the actual response contains:

```js
{
  id,
  number,
  amount_cents,
  status,
  due_date,
  customer_id,
  customer_name
}
```

This is not the required `InvoiceDTO` and directly violates the data-disclosure contract. Demonstration: request any accessible invoice and inspect the JSON response; `customer_id` will be present.

✅ **Organization isolation is enforced in the query**

`i.org_id = $2`, with `$2` supplied from `req.user.org_id`, restricts invoices to the caller’s organization. The customer join also requires `c.org_id = i.org_id`.

✅ **Missing and cross-organization invoices share the same response**

Both cases cause `db.oneOrNone(...)` to return no row, followed by the identical `404` response:

```js
{ error: 'Invoice not found' }
```

✅ **SQL injection through `id` is blocked**

The identifier is checked as a positive integer and passed through the `$1` parameter rather than interpolated into SQL.

✅ **Clearly nonnumeric IDs are rejected before database access**

Values for which `Number(req.params.id)` is not a positive integer return `400`, outside the `try` block, and cannot reach the database error path.

### Assessment

The `customer_id` disclosure is an observable contract breach, not a stylistic objection. Its presence may also expose a useful identifier for probing other customer-scoped endpoints. Because the contract explicitly establishes this as a confidentiality boundary, the defect is release-blocking.

JavaScript’s `Number()` accepts unusual forms such as `0x10`, `1e2`, and strings containing whitespace. The contract does not require malformed IDs to return `400`, only that they never produce `500`, so this is not independently a demonstrated breach. The intended ID grammar is nevertheless ambiguous.

### Claimed vs. actual

- **Claimed:** Returns exactly `{ id, number, amount_cents, status, due_date, customer_name }`.
- **Actual:** Also returns `customer_id`.
- **Claimed:** Nothing else about the invoice or customer leaves the server.
- **Actual:** A prohibited customer identifier leaves through direct serialization of the database row.

### Confirm-these

- Whether `requireSession()` always supplies a trustworthy `req.user.org_id`; its implementation is not provided.
- Whether the required ID grammar permits formats accepted by `Number()`, such as `0x10` and `1e2`.
- Whether application-wide middleware alters, wraps, or further exposes the response.
- Whether logger configuration safely handles `err`, `invoiceId`, and `userId`; its sinks and redaction behavior are absent.

### How each clean axis was checked

- **Tenant filtering:** traced `req.user.org_id` → query parameter `$2` → `WHERE i.org_id = $2`.
- **Customer/invoice organization consistency:** traced `c.org_id = i.org_id` in the join.
- **Indistinguishable 404:** traced both absent and inaccessible rows → `oneOrNone` returns no row → the same `if (!invoice)` response.
- **SQL injection resistance:** traced validated `id` → bound `$1` parameter.
- **Nonnumeric malformed input:** traced failed integer validation → immediate `400`, before database access.


=== OUTPUT Y ===

## Verdict

**NOT VERIFIED — BLOCKING: yes**

**Independence: INDEPENDENT** — the artifact arrived finished and was not produced or revised by this verifier.

Most damaging defect: the endpoint explicitly returns `customer_id`, which the contract explicitly prohibits from leaving the server.

## Observable evidence

❌ **HIGH — forbidden customer data is exposed**

The query selects:

```js
i.customer_id
```

The response returns the entire query result:

```js
return res.json(invoice);
```

Therefore, successful responses contain `customer_id`, violating both the exact `InvoiceDTO` shape and the explicit prohibition on exposing `customer_id`.

⚠️ **MEDIUM — malformed IDs may still reach the database and produce 500**

Validation accepts any positive integer representable by JavaScript:

```js
Number.isInteger(id) && id > 0
```

For example, `"100000000000000000000"` passes that check. If the database ID type has a smaller range, parameter coercion can fail and enter the catch block, returning 500. The database type was not provided, so this failure cannot be conclusively demonstrated from the artifact alone.

✅ **Organization isolation is enforced in the shown query**

The invoice is constrained by:

```sql
AND i.org_id = $2
```

with `$2` supplied as `req.user.org_id`.

✅ **Missing and cross-organization invoices share the same shown response**

Both produce no selected row, followed by:

```js
return res.status(404).json({ error: 'Invoice not found' });
```

## Assessment

The `customer_id` disclosure is a direct, observable contract breach, not a stylistic objection. It independently requires **NOT VERIFIED**.

The ID validation is insufficient to establish the stronger claim that every malformed ID avoids a 500. Its actual behavior depends on the database column and driver coercion.

## Defects

1. ❌ **HIGH — response leaks forbidden `customer_id` — request an accessible invoice and inspect the JSON; `customer_id` is selected and serialized.**
2. ⚠️ **MEDIUM — oversized numeric IDs can reach the database — submit an integer exceeding the database ID type’s range and observe whether parameter coercion returns 500.**

## Claimed vs. actual

- **Claimed:** Response is exactly `{ id, number, amount_cents, status, due_date, customer_name }`.
- **Actual:** It additionally contains `customer_id`.
- **Claimed:** Malformed IDs never produce 500.
- **Actual:** Syntax-level malformed values are rejected, but oversized positive integers are admitted to the database path.

## Confirm-these

- Database type and driver behavior for oversized invoice IDs.
- Whether `requireSession()` guarantees a valid `req.user.org_id` before this handler.
- Whether `logger.error` applies required redaction to database error contents.

## How each clean axis was checked

- **Tenant isolation:** `i.org_id = $2` → `$2` is `req.user.org_id`.
- **Indistinguishable 404:** absent or unauthorized row → `oneOrNone` yields no invoice → identical 404 branch.
- **Other listed sensitive fields:** `email`, `tax_id`, `payment_token`, `portal_password_hash`, and `org_id` are absent from the selected columns.


=== OUTPUT Z ===

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

