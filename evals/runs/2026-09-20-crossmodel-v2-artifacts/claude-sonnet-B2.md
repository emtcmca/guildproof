## Verdict: NOT VERIFIED. BLOCKING: yes

**Independence:** INDEPENDENT. The artifact arrived finished and I didn't write it.

**Limit on my own testing:** I tried to run `node --check` and a coercion probe. The sandbox denied file writes and piped node input, so nothing below was executed. The defects are read from the source and follow from the JavaScript spec and the contract text. Confirm #1 with `node --check` before trusting my word.

## Defects (worst first)

**1. HIGH, ❌: the file is not valid JavaScript, so the endpoint can't exist (static; observable in the source).**
- The closing line of the query call is:
  ```
  AND i.org_id = $2`,            -- and the invoice must be in the caller's org
  [id, req.user.org_id]
  ```
- The template literal has already closed at the backtick. The `-- and the invoice…` text is therefore plain JS, not SQL.
- `--` is the decrement operator. The parser reads `-- and`, then hits `the` with no operator between them, which is a SyntaxError. The `'` in `caller's` also opens an unterminated string.
- The earlier `-- customer must be…` comment sits inside the template literal and is harmless. Only this second one breaks.
- Effect: the module fails at load. The route isn't registered, and depending on how the router is loaded, the app may not boot.
- Every claim about behaviour below is conditional on this being fixed.

**2. HIGH, ❌: `customer_id` leaks, and the contract forbids it by name (observable).**
- The SELECT includes `i.customer_id`.
- The handler returns `res.json(invoice)` with no DTO mapping, so `customer_id` goes out in the response body.
- The contract's exclusion list names it explicitly: "no email, tax_id, payment_token, portal_password_hash, org_id, customer_id".
- The response shape is `{id, number, amount_cents, status, due_date, customer_id, customer_name}`, which is not the `InvoiceDTO`.
- The only thing keeping other fields out is the column list in the SQL. Adding a column to that SELECT later leaks it silently, because there is no allow-list at the response boundary.

**3. MEDIUM, ⚠️: id validation accepts inputs that aren't well-formed ids (judgment, from `Number()` semantics).**
- `Number()` coerces `"1e3"` to 1000, `"0x10"` to 16, and `" 7 "` to 7. All pass `isInteger && > 0`, so several URLs alias one invoice.
- `"9007199254740993"` rounds to `…992` before it reaches the DB, so it can hit a different id.
- The comment says "Reject anything that isn't a positive integer". It rejects non-integers, but it doesn't check that the string is a canonical decimal integer.
- Whether an oversized id produces a 500 depends on the id column type (int4 or bigint) and on how the driver binds `$1`. I can't see either. That is the "never a 500" clause, and it stays unconfirmed.

**4. LOW, ⚠️: the inner join on `c.org_id = i.org_id` can hide invoices the caller owns (judgment).**
- If an invoice in the caller's org has a `NULL` `customer_id`, or a customer row whose `org_id` differs (data drift), the join drops it.
- That returns 404 for a legitimate invoice. It fails closed, not open, and I couldn't tell whether the contract intends this.

## Claimed vs. actual
| Claim in artifact | Actual |
|---|---|
| "Returns one invoice plus its customer's name" | Also returns `customer_id`, which the contract forbids. |
| "Reject anything that isn't a positive integer" | Rejects non-integers only. Hex, exponent and padded strings are accepted and coerced. |
| Implicit: "this is the endpoint" | Doesn't parse (#1). |

## Checked clean, with the line traced
- **Cross-org and missing invoices return the same 404.** The WHERE clause has `i.org_id = $2`, and a null row hits the single `!invoice` branch, which returns one 404 body. Both cases are indistinguishable, assuming #1 is fixed.
- **No SQL injection.** `id` is a JS number and `org_id` comes from the session. Both are bound values, and there is no string concatenation.
- **No stack or DB error text reaches the client.** The catch block returns a fixed `'Internal server error'`, and the details go to `logger` only.
- **Logging carries no PII.** It logs only the error, `invoiceId` and `userId`.
- **No other forbidden column is selected.** The SELECT lists `id, number, amount_cents, status, due_date, customer_id, name`. There are no `email`, `tax_id`, `payment_token`, `portal_password_hash` or `org_id`. The only leak is `customer_id`.

## Confirm-these
- **`requireSession()`.** I couldn't see it. If `req.user.org_id` isn't derived from the server-side session, the org scoping fails. This is security-critical and unverified.
- **The id column type and the driver.** These determine whether an out-of-range id gives a 500.
- **Whether `customer_id` is nullable, and whether `customers.org_id` can differ from `invoices.org_id`.** This decides #4.
- **The parse failure in #1.** Run `node --check` on the file to confirm it.

## Most damaging defect
The file doesn't parse (#1). Even once fixed, the handler ships `customer_id` (#2), which the contract names as forbidden. Send both back to the builder. I won't rewrite anything.

One housekeeping note: a session hook wants me to ask which project this scratch directory belongs to for vault memory. I skipped that mid-verification. It can be answered separately.
