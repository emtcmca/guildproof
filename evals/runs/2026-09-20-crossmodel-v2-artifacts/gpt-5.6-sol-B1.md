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
