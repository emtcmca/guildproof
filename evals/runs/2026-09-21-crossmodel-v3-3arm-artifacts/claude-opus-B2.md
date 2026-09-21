## Verdict

**NOT VERIFIED. BLOCKING: yes** (one HIGH contract breach that fires on every successful response, plus a 500 path the contract explicitly forbids).

**Independence:** INDEPENDENT. The artifact arrived finished in your message; I did not write, draft, or revise it, and no producer notes were in view. Reading it here is not producing it.

---

## Defects, worst first

**❌ HIGH — `customer_id` is returned to the client. Named in the contract's forbidden list.**
The SELECT list includes `i.customer_id`, and the handler does `res.json(invoice)` on the raw row with no DTO mapping or field allowlist. Every 200 response carries a seventh field the contract says must not leave the server.
*Demonstrate:* `GET /api/invoices/<any id you own>` and read the body. It is `{id, number, amount_cents, status, due_date, customer_id, customer_name}`. The contract's InvoiceDTO has six fields and lists `customer_id` by name under "nothing else leaves the server."
*Note the shape of the bug, not just the field:* the column is only there to satisfy the JOIN, which already has `i.customer_id` available server-side. It is in the projection by accident, and the response is the row rather than a mapped object, so the next column anyone adds leaks the same way.

**❌ MEDIUM — A malformed id produces a 500, which the contract forbids.**
`Number.isInteger()` is true for integer-*valued* floats of any magnitude, so the guard passes values no integer column can hold. They reach Postgres and raise a driver error, which the catch converts to 500.
*Demonstrate:* `GET /api/invoices/99999999999999999999`. `Number(...)` is `1e20`, `Number.isInteger(1e20) === true`, `1e20 > 0`, so the guard is satisfied and `$1` is bound. Postgres then fails on the cast (`22003 numeric_value_out_of_range` against int4/int8, or `22P02 invalid_text_representation` once JS stringifies at or above `1e21` as `"1e+21"`). Either path lands in the `catch` and returns `500`. The contract clause is "Malformed ids never produce a 500," and this is the id class the guard was written to stop.

**❌ MEDIUM — The inner JOIN turns a data-integrity gap into a 404 for an invoice the caller does own.**
`JOIN customers c ON c.id = i.customer_id AND c.org_id = i.org_id` is required, not optional. If `i.customer_id` is NULL, or the customer row was hard-deleted, or the customer legitimately sits in a different org, the row drops out of the result and `oneOrNone` returns null. The caller gets "Invoice not found" for an invoice that exists in their organization.
*Demonstrate:* `UPDATE invoices SET customer_id = NULL WHERE id = $own_id` (or delete the customer row), then `GET /api/invoices/$own_id` returns 404. The contract obligates the endpoint to return invoices that belong to the caller's org; it does not make visibility conditional on customer-row health. The org-equality predicate on the customer is a good instinct, but it belongs on a LEFT JOIN with the name nulled, not on the invoice's existence.

**⚠️ LOW — The input guard does not do what its comment claims, though authorization still holds.**
The comment says "Reject anything that isn't a positive integer." `Number()` accepts hex, exponent, signed, decimal-zero, and whitespace-padded forms: `0x10` → 16, `1e3` → 1000, `+7` → 7, `7.0` → 7, `"  7  "` → 7. So one invoice is addressable under many spellings. No authz consequence, because `i.org_id = $2` still runs on whatever integer comes out. Noted as a nitpick with a false comment attached, not a gate.

---

## Axes checked clean, and how

- **✅ SQL injection.** Both values are bound parameters (`$1`, `$2`), and `id` is a JS number before it is bound. No string concatenation anywhere in the template.
- **✅ Cross-org invoice read (IDOR).** `WHERE i.id = $1 AND i.org_id = $2` with `$2` bound to `req.user.org_id`, not to anything client-supplied. The org is never taken from the request body, query, or a header.
- **✅ 404 indistinguishability.** There is exactly one not-found exit: `if (!invoice) return res.status(404)...`. A nonexistent id and a foreign-org id both fall out of the same `oneOrNone` null and return the byte-identical body `{"error":"Invoice not found"}`. No branch distinguishes them.
- **✅ The named secret fields are absent from the projection.** The SELECT enumerates columns explicitly; `email`, `tax_id`, `payment_token`, `portal_password_hash`, and `org_id` appear nowhere in it. `org_id` is referenced only in predicates, never projected. This is why `customer_id` is the sole leak rather than one of several.
- **✅ Log line carries no PII.** `logger.error` receives the error, a numeric `invoiceId`, and `req.user.id`. No customer name, no email, no token.
- **✅ Error response body does not leak internals.** The 500 returns a fixed string, not `err.message`.

---

## Claimed vs. actual

| The artifact's comment says | What the code does |
|---|---|
| "Reject anything that isn't a positive integer before it reaches the DB" | Accepts `0x10`, `1e3`, `+7`, `7.0`, padded whitespace, and any integer-valued float up to `Infinity`, including magnitudes that make the DB throw |
| "Returns one invoice plus its customer's name" | Returns the customer's name **and** the customer's id |
| "A missing invoice and another org's invoice both return 404" | True, and correctly implemented. It also silently returns 404 for a present, owned invoice whose customer row is missing |

---

## Confirm these before trusting anything above as complete

1. **`requireSession()` is not shown, and the catch block depends on it.** If that middleware can ever let a request through with `req.user` unset (anonymous fall-through, expired session tolerated, a misconfigured mount), then `req.user.org_id` throws a TypeError inside the `try`, control reaches the `catch`, and the `catch` **itself** dereferences `req.user.id` and throws again. That second throw escapes the async handler, no response is ever sent, and in Express 4 it is not forwarded to error middleware. The request hangs and the rejection is unhandled. Read `requireSession` before you call this axis clean; the error handler assumes the thing that might be missing.
2. **`customers.id` uniqueness.** `oneOrNone` throws when the query returns more than one row. If `customers.id` is not a primary key or unique index, a duplicate customer id yields a 500 on a legitimate request. I cannot see the schema.
3. **The column type of `invoices.id`.** It changes which Postgres error the big-id case raises, not whether it 500s, but confirm it is not something exotic that swallows the overflow.
4. **Whether an outer error-handling middleware exists** that would catch what escapes in item 1.
5. **Whether `invoices.customer_id` is nullable**, which decides whether the JOIN defect is theoretical or live in your data today.

---

## Assessment (my judgment, not demonstrated)

The security thinking here is above average: the org predicate is on the invoice row where it belongs, the double-scoping of the customer to the invoice's org is a real defense against a mismatched-tenant join, and the single 404 exit is deliberate and correct. The failures are all of one kind, which is worth naming: **the handler trusts its own shapes.** It trusts that a row is a DTO, that `Number.isInteger` means "fits in an integer column," and that `req.user` exists at the moment the error handler runs. Two of those three are demonstrable today.

The single most damaging defect is the first one, and it is not subtle: the endpoint ships a field the contract names as forbidden, on every success, because the row was handed to `res.json` instead of being mapped. Fix that with an explicit projection into the six DTO fields, and the same edit removes `i.customer_id` from the SELECT.

I verify; I do not fix. These go back to a builder.
