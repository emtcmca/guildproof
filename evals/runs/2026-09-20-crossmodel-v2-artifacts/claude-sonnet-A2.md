**Verdict: NOT VERIFIED.** Two contract failures, both read from the code. My attempt to write and run the file (`node --check`) was declined, so nothing below was executed.

**1. The file has a syntax error, so the route can't load.**
- The line ending `AND i.org_id = $2`,            -- and the invoice must be in the caller's org` closes the template literal before the comment.
- The `--` comment therefore lands in JavaScript, where `--` is the decrement operator.
- The apostrophe in `caller's` also opens an unterminated string.
- The comment belongs inside the SQL string, or should be a `//` comment.

**2. `customer_id` leaks, which the contract names as forbidden.**
- `i.customer_id` is in the `SELECT`, and `res.json(invoice)` sends the raw row, so it goes out in the response.
- The contract lists `customer_id` in the "nothing else leaves the server" bullet, and the InvoiceDTO doesn't include it.
- The join doesn't need it selected, because `ON c.id = i.customer_id` works without it.
- Removing it fixes today's leak. A safer fix is to build the DTO explicitly, so a column added to the query later can't leak:
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

**3. Oversized ids may return a 500. I couldn't confirm this from the artifact.**
- `Number.isInteger(Number('1e20'))` is `true`, so `/api/invoices/1e20` passes the guard.
- Whether it then throws depends on things not shown: the `db` driver and the `id` column type.
- With bound parameters against an int4 column, Postgres raises "out of range", the `catch` runs, and the client gets a 500.
- With pg-promise's client-side formatting it probably just returns no rows and a 404.
- The guard also accepts `1e3`, `0x10` and ` 5`, which alias other ids, and it rounds anything above 2^53.
- A check on the raw string, `/^[1-9]\d{0,9}$/` (adjusted to the column width), closes all of these.

**What holds**
- Both the not-found and other-org cases return the identical 404, with the same status and body.
- Org scoping is enforced in SQL from the session's `org_id`.
- The 500 body is generic.
- `email`, `tax_id`, `payment_token`, `portal_password_hash` and `org_id` are never selected.

**Design note, not a violation.** The inner join on `customers` means an invoice in your own org whose customer row is missing or in another org returns 404. That is defensible, but it isn't stated in the contract.

The session-start hook also asked me to check whether this scratch directory should be registered as a memory project. I skipped it. Say if you want it registered as `b2-run`.
