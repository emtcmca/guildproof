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
