=== REVIEW A ===
# Verification — GET /api/invoices/:id

## Verdict
**NOT VERIFIED** — **BLOCKING: yes.**
The handler returns `customer_id` in every successful response. The contract names `customer_id` explicitly among the fields that must never leave the server.


## Observable evidence
- **Contract breach (field leak):** the SELECT list includes `i.customer_id` (line 18), and the row goes straight out through `return res.json(invoice)` (line 34) with no mapping to the DTO. Every 200 response therefore has the shape `{ id, number, amount_cents, status, due_date, customer_id, customer_name }`. The contract's InvoiceDTO has six fields. This response has seven, and the seventh is on the contract's deny list by name.
- **Org scoping (IDOR):** `WHERE i.id = $1 AND i.org_id = $2` with `$2 = req.user.org_id` (lines 24–26). The org comes from the session, not the request. Checked clean.
- **Uniform 404:** a missing row and another org's row both produce `!invoice` and return the identical `404 { error: 'Invoice not found' }` (lines 30–32). Both cases run the same single query, so there's no branch that could separate them. Checked clean.
- **Other forbidden fields:** `email`, `tax_id`, `payment_token`, `portal_password_hash`, and `org_id` are not selected. Only `c.name` comes from `customers`. Checked clean.
- **Cross-org customer name:** `AND c.org_id = i.org_id` (line 23) stops another org's customer name from joining onto an in-org invoice. Checked clean.
- **Injection:** the id goes through `Number()` and is validated as an integer before binding. Both values are bound through pg-promise `$1`/`$2`. No string concatenation reaches the query. Checked clean.
- **Malformed ids and 500:** non-numeric input, `0`, negatives, fractions, `Infinity`, and `NaN` fail `Number.isInteger(id) && id > 0` and get a 400 (lines 6–9). Checked clean for those inputs. The out-of-range case is covered under Assessment.
- **Error body:** the catch returns a generic `500 { error: 'Internal server error' }`. No DB error text reaches the client. The logged fields (`err`, `invoiceId`, `userId`) stay server-side. Checked clean.

## Assessment (judgment, not demonstrated)
- **Out-of-range integer ids (e.g. `/api/invoices/2147483648`, `/api/invoices/99999999999999999999`):** these pass the positive-integer check but exceed `int4`. By default pg-promise formats values into the query text on the client instead of sending typed bind parameters. The literal then arrives as a `bigint`/`numeric` constant, `int4 = bigint` is a legal comparison, no row matches, and the result is a 404, not a 500. My judgment is that this holds **only while** the query uses pg-promise's default formatter. Moving it to `PreparedStatement`/`ParameterizedQuery`, to raw `pg` with server-side binds, or to an explicit `$1::int` cast would make Postgres raise `22003 integer out of range`. The catch block would turn that into a 500 on a malformed id, which breaks the contract. The defense against this input class is accidental, not designed. I did not run it.
- **Loose id parsing:** `Number()` accepts non-canonical forms: `' 7 '`, `'7.0'`, `'0x7'`, `'7e0'`, `'0b111'` all resolve to invoice 7. No 500 and no cross-org access, so no contract breach. It does contradict the code comment's claim (see Claimed vs. actual) and aliases one resource to many URLs. LOW.
- **In-org invoice hidden by the inner join:** the schema shows no foreign key and no `NOT NULL` on `invoices.customer_id`. An in-org invoice with a NULL, dangling, or cross-org `customer_id` falls out of the `JOIN` and gets a 404, even though it belongs to the caller's org. The contract says an in-org invoice is returned. It doesn't say what `customer_name` should be when there is no valid customer, so I treat this as a possible correctness gap, not a proven breach. LOW–MEDIUM, depending on data integrity I can't see.
- **`due_date` serialization:** node-postgres parses a `date` column into a JS `Date` at local midnight by default, so `res.json` emits a full ISO timestamp in UTC. On a server west of UTC that string carries the *previous* calendar day's date portion only if a client truncates it naively. It's a format or off-by-one risk, not a breach, because the contract doesn't specify the `due_date` format.

## Defects (worst first)
- ❌ **HIGH — `customer_id` leaves the server on every successful response.** The contract lists `customer_id` explicitly among forbidden fields, and the DTO omits it. To demonstrate: authenticate as any org user, `GET /api/invoices/<an id in that org>`, and the JSON body contains `"customer_id": <int>`. The root cause is structural. The handler serializes the DB row instead of building the six-field DTO explicitly, so any column later added to the SELECT will leak the same way. I rate it HIGH because it's deterministic (100% of 200s) and it violates an enumerated contract prohibition on the data-exposure axis. That severity rating is my judgment. The breach itself is observable.
- ⚠️ **MEDIUM (latent) — the "no 500 on malformed id" guarantee depends on pg-promise's client-side formatting.** The validator admits integers above `2147483647`. Today they produce a 404 through literal formatting. Under server-side binding or an `::int` cast they produce a 500. There's no upper-bound check. (Assessment, not demonstrated.)
- ⚠️ **LOW–MEDIUM — the inner join returns 404 for an in-org invoice whose customer is NULL, missing, or in another org.** This depends on data integrity the schema doesn't enforce. (Assessment.)
- ⚠️ **LOW — non-canonical id strings are accepted and aliased** (`0x7`, `7e0`, `' 7 '`, `7.0`).
- ⚠️ **LOW — `due_date` is emitted as a timezone-shifted ISO timestamp, not a date.** The format isn't contracted.
- ✅ Org scoping and authorization (IDOR): clean.
- ✅ Uniform 404 for missing and cross-org rows: clean.
- ✅ `email`, `tax_id`, `payment_token`, `portal_password_hash`, `org_id` not exposed: clean.
- ✅ SQL injection: clean.
- ✅ Error responses and logging: no client-facing leak.

## Claimed vs. actual
- Comment (line 3): *"Returns one invoice plus its customer's name."* **Actual:** it returns one invoice, its customer's name, **and its `customer_id`**.
- Comment (line 5): *"Reject anything that isn't a positive integer before it reaches the DB."* **Actual:** it accepts strings that aren't integer literals (`0x7`, `7e0`, `7.0`, padded whitespace) because `Number()` coerces them. It also accepts integers the `int` column can't hold, which reach the DB unrejected.
- Comment (line 29): *"A missing invoice and another org's invoice both return 404."* **Actual:** true. It also returns 404 for an in-org invoice with no valid same-org customer, which the comment doesn't mention.

## Confirm-these
- **`requireSession()` failure path:** not shown. Confirm that it rejects with 401 and never calls the handler with `req.user` undefined. Without that, `req.user.org_id` throws a TypeError in the `db.oneOrNone` argument list, inside the `try`. That yields a 500, and the catch's `req.user.id` would itself throw inside the catch, which becomes an unhandled rejection.
- **Query formatting mode:** confirm that this call runs through pg-promise's default client-side formatter and not through a prepared or parameterized query. The out-of-range id → 404 behavior depends on it.
- **Referential integrity of `invoices.customer_id`:** confirm whether a FK and `NOT NULL` exist, and whether cross-org `customer_id` values are possible. That decides whether the inner-join 404 is reachable.
- **`due_date` wire format:** confirm what consumers expect, and whether a type parser for OID 1082 is configured.

**Single most damaging defect:** the handler returns the raw DB row, so `customer_id` (a field the contract explicitly forbids) ships in every successful response.

=== REVIEW B ===
# Verification: GET /api/invoices/:id

## Verdict
**NOT VERIFIED. BLOCKING: yes.**

The biggest defect is that every 200 response includes `customer_id`. The contract names that field as one that must never leave the server. The handler breaks the contract on every successful call, so this is certain, not an edge case.


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
