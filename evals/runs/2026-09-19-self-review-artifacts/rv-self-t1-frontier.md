# Verification: GET /api/invoices/:id

## Verdict
**NOT VERIFIED. BLOCKING: yes.**

The biggest defect is that every 200 response includes `customer_id`. The contract names that field as one that must never leave the server. The handler breaks the contract on every successful call, so this is certain, not an edge case.

## Independence
**NOT INDEPENDENT.** I wrote this endpoint earlier in this same conversation, so I read the builder's reasoning and may share its blind spots. To get an independent check, paste the handler and the contract into a fresh conversation.

## Contract, as given
1. Returns one invoice that belongs to the caller's org, as InvoiceDTO `{ id, number, amount_cents, status, due_date, customer_name }`.
2. An invoice in another org and a missing invoice return the same 404.
3. Nothing else about the invoice or customer leaves the server: no `email`, `tax_id`, `payment_token`, `portal_password_hash`, `org_id` or `customer_id`.
4. A malformed id never produces a 500.

## Observable evidence
These can be shown directly from the code.
- The SELECT list is `i.id, i.number, i.amount_cents, i.status, i.due_date, i.customer_id, c.name AS customer_name`, and the handler sends the row unchanged (`res.json(invoice)`). The response therefore always includes `customer_id`, which breaks clause 3.
- The WHERE clause has `i.org_id = $2`, bound to `req.user.org_id`, and the join has `c.org_id = i.org_id`. Invoices are scoped to the caller's org, and the customer is scoped to the invoice's org.
- The query is parameterized (`$1`, `$2` with an array of values). User input is never concatenated into the SQL.
- A missing row and another org's row both reach the same `if (!invoice)` branch and get the same `404 { error: 'Invoice not found' }`. The status, body and code path are identical. Clause 2 holds as far as the response shows.
- `email`, `tax_id`, `payment_token`, `portal_password_hash` and `org_id` are not in the SELECT list. That part of clause 3 holds.
- Non-numeric and fractional ids (`abc`, `1.5`, `-3`, `0`, the empty string) fail `Number.isInteger(id) && id > 0` and return 400 before any database call.
- The catch block sends a generic `500 { error: 'Internal server error' }` and logs only `err`, `invoiceId` and `userId`. No row data goes into the response or the log.

## Assessment
This section is judgment, not something demonstrated.
- **Clause 4 for out-of-range ids depends on how pg-promise formats values.** `Number('2147483648')` and `Number('1e21')` both pass `Number.isInteger`. pg-promise's default behavior is to format values into the SQL text on the client, so the query would read `i.id = 2147483648` or `i.id = 1e+21`. Postgres accepts both as bigint or numeric literals, compares them without error, and returns no row, which gives a 404, not a 500. If the query is ever changed to use server-side binding (a PreparedStatement, or a `$1::int` cast), those ids would raise "value out of range for type integer", and the catch would return a 500. The handler has no upper-bound check, so it relies on the formatter's current behavior rather than guaranteeing clause 4.
- `Number()` also accepts `0x10`, `1e3` and ids with surrounding spaces, turning them into valid integers (16, 1000, 12). This does not break clause 4, because none of them causes a 500, but the handler is not validating a canonical id.
- `due_date` is a Postgres `date`. node-postgres parses it by default into a JS `Date` at local midnight, and JSON serializes that as an ISO timestamp. On a server running east of UTC, the serialized date falls on the previous calendar day. The contract doesn't specify a format, so I'm not counting this as a breach, but the invoices page could show the wrong due date.

## Defects, worst first
- ❌ **HIGH.** The response exposes `customer_id`, which clause 3 prohibits by name. To demonstrate: GET any invoice in your own org, and the 200 body contains `"customer_id": <n>`. The handler returns the query row as-is with no DTO mapping, so any column added to the SELECT later will also reach the client.
- ⚠️ **MEDIUM.** An invoice that belongs to the caller's org can return 404. The JOIN is an inner join on `c.id = i.customer_id AND c.org_id = i.org_id`. The schema as given has no NOT NULL or FK constraint on `invoices.customer_id`. An invoice whose customer is null, deleted, or recorded under a different org drops out of the join and returns 404, which contradicts clause 1. How likely this is depends on the data. To demonstrate: insert an invoice in your org with `customer_id = NULL` and GET it, and the response is 404.
- ⚠️ **LOW (conditional).** Clause 4 holds only because of pg-promise's client-side formatting (see Assessment). There is no range check on `id`, so a future switch to server-side binding would turn `/api/invoices/2147483648` into a 500.
- ⚠️ **LOW.** `due_date` can shift by one day depending on the server timezone and the pg type parser (see Assessment).
- ✅ Org scoping and IDOR: checked, clean.
- ✅ Identical 404 for another org's invoice and a missing one: checked, clean.
- ✅ SQL injection: checked, clean.
- ✅ Sensitive customer fields (`email`, `tax_id`, `payment_token`, `portal_password_hash`) and `org_id`: checked, not selected.
- ✅ Error responses: generic 500 body, no row data in logs.

## Claimed vs. actual
- **Claim:** "Only the customer's name comes back." **Actual:** of the customer's own columns, only `name` comes back, but the handler also returns `customer_id`, a foreign key the contract forbids. The cover letter left removing it as optional ("If the frontend doesn't need `customer_id`, remove it"). The contract makes removing it required.
- **Claim:** the explicit column list means nothing sensitive "can reach the browser, now or when someone adds a column later." **Actual:** that protects against columns being added to the tables, but not against columns being added to the SELECT. The handler has no DTO mapping step, so whatever is in the SELECT goes out.
- **Claim:** "Fetch `/api/invoices/abc`. You should get 400." **Actual:** true. But the cover letter implies every malformed id gets a 400, and out-of-range and hex ids are accepted and queried.

## Confirm-these
- **pg-promise formatting mode:** confirm the default client-side formatting is in use and no PreparedStatement or `::int` cast is applied. Clause 4 for out-of-range ids depends on it.
- **Express error handler:** a malformed percent-encoding in the path (for example `/api/invoices/%E0`) makes Express's param decoding throw a URIError with `status = 400` before this handler runs. If the app's global error handler ignores `err.status` and always sends 500, clause 4 breaks there. That handler wasn't provided.
- **`requireSession()` guarantees:** the review assumes `req.user.org_id` is always a non-null integer. If a user can have no org, `org_id` comes through as `undefined` or `null`, and how pg-promise formats `undefined` in an array parameter (error vs. `null`) decides whether the result is a 500 or a 404.
- **Schema constraints on `invoices.customer_id`:** NOT NULL and FK constraints would reduce the MEDIUM finding to a cross-org data-integrity case only.
- **Server TZ and the pg DATE type parser:** these determine whether the `due_date` shift can happen in production.
