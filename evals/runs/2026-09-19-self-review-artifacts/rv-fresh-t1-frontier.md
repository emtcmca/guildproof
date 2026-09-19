# Verification — GET /api/invoices/:id

## Verdict
**NOT VERIFIED** — **BLOCKING: yes.**
The handler returns `customer_id` in every successful response. The contract names `customer_id` explicitly among the fields that must never leave the server.

## Independence
**INDEPENDENT.** I saw only the finished artifact and its contract. I did not write, draft, or revise it, and I never saw the builder's reasoning.

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
