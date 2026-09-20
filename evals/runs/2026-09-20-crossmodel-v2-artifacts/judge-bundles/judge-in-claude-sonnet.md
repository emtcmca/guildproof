=== OUTPUT W ===

## Verdict: NOT VERIFIED. BLOCKING: yes

**Independence:** INDEPENDENT. The artifact arrived finished and I didn't write it.

**Execution:** none. Every tool call that would run code or write a file was refused, so nothing below was run. The findings come from reading the artifact against the JS grammar and the contract. Findings 1 and 2 are directly visible in the text. Finding 3 rests on a stated schema assumption.

## Defects, worst first

**1. HIGH, observable: the handler is a syntax error and the module won't load.**
- The template literal closes at the backtick after `AND i.org_id = $2`.
- The text that follows is JavaScript, not SQL: `, -- and the invoice must be in the caller's org`.
- In JS, `--` is the decrement operator, not a comment.
- The apostrophe in `caller's` opens a string that never terminates.
- So the file fails to parse. The route never registers, or the process crashes on import. Nothing in the contract is met.
- The first comment, `-- customer must be in the same org…`, sits inside the template literal and is fine. The second is the trap.
- To demonstrate: run `node --check` on the handler as pasted.

**2. HIGH, observable: `customer_id` is returned to the caller.**
- The query selects `i.customer_id`, and `res.json(invoice)` serializes the raw row with no field mapping.
- The contract lists `customer_id` by name as something that must not leave the server. The DTO has no such field.
- The header comment ("invoice plus its customer's name") is not what the code does.
- The handler never builds an `InvoiceDTO`. Any column added to this SELECT later will leak the same way. That structural point is my judgment.

**3. HIGH against the contract, conditional on schema (`id` is an integer type; not shown): some well-formed-looking ids still produce a 500.**
- The guard is `Number.isInteger(id) && id > 0`. There is no `isSafeInteger` check and no upper bound.
- `"99999999999999999999"` becomes `1e20` and passes. `"2147483648"` passes. `"1e21"` passes.
- pg serializes these into an integer-typed parameter. Out-of-range values (22003) and `1e+21` (22P02) throw.
- The `catch` turns that into `500 Internal server error`. The contract says "Malformed ids never produce a 500".
- Schema-independent leniency: `Number()` also accepts `"1e3"`, `"0x10"`, `" 12 "` and `"+5"`. Several non-canonical strings alias one invoice. LOW, not a gate.

**4. LOW, assessment: the INNER JOIN with `c.org_id = i.org_id` drops rows.** An in-org invoice whose customer is null or in a different org returns 404. That is defensible, but it's a silent behavior the contract doesn't mention.

## Claimed vs. actual
- "Returns one invoice plus its customer's name": it returns the invoice plus `customer_id` plus the name.
- "Reject anything that isn't a positive integer before it reaches the DB": true only for safe-range integers.
- "Callers can't probe which IDs exist": true for cross-org versus missing, but see finding 3.

## Axes checked clean (✅)
- **Cross-org isolation:** `WHERE i.id = $1 AND i.org_id = $2` with `$2 = req.user.org_id`. An invoice in another org returns no row, so `oneOrNone` gives null and the handler returns 404.
- **Same 404 for missing and cross-org:** both go through the single `if (!invoice)` branch with an identical body.
- **SQL injection:** `id` is coerced by `Number()` and bound as `$1`. Org is bound as `$2`. There is no string concatenation.
- **Error leakage:** the catch returns a generic message. `err` goes only to the logger.

## Confirm-these
- Whether `requireSession()` guarantees `req.user.org_id` comes from the session and not from client input.
- The `invoices.id` column type. Finding 3 assumes `int4` or `int8`.
- Any global response middleware or serializer that might strip `customer_id`. Even then, I would not accept "some other layer strips it" as meeting the contract.
- Whether `amount_cents` and `due_date` serialize as the DTO's types. For example, pg returns `int8` as a string.

The most damaging defect is #1, because the artifact doesn't run. Once it parses, #2 still breaks an explicit contract line. This goes back to the builder.


=== OUTPUT X ===

**Verdict: NOT VERIFIED.** The artifact breaks the contract in two places. A third defect means it won't run at all.


### 1. It fails "nothing else leaves the server": `customer_id` is returned
The `SELECT` includes `i.customer_id`, and the handler sends the row straight back with `res.json(invoice)`. The contract lists `customer_id` by name as forbidden. The response is `{id, number, amount_cents, status, due_date, customer_id, customer_name}`, which is not an `InvoiceDTO`.

- **Fix:** remove `i.customer_id` from the `SELECT`. The join doesn't need it in the output.
- **Hardening:** map the row to the six DTO fields explicitly before `res.json`. Then a column added to the query later can't leak.

### 2. It fails "malformed ids never produce a 500"
The guard is `Number.isInteger(id) && id > 0`. It has no upper bound, so these pass it and go to the database:

| Input | Passes guard? | What the DB receives |
|---|---|---|
| `99999999999` | yes | 11 digits, out of range for an `int4` column |
| `9999999999999999999` | yes | rounds to `1e19`, out of range for `bigint` |
| `1e21` | yes | stringifies as `"1e+21"`, invalid `bigint` input |

Postgres raises an error for each one (numeric out of range, or invalid input syntax). The `catch` block turns it into a 500. Whichever integer type the `id` column uses, some input gets through, which breaks the third bullet of the contract.

- **Fix:** validate the raw string instead of `Number(...)`. For example, check `/^[1-9]\d{0,9}$/` and then that the value is at most 2147483647 (or your column's max).
- **Side effect:** `Number()` also accepts `1e3`, `0x10`, `" 12 "` and `+5` as ids 1000, 16, 12 and 5. These aren't 500s, but they are odd inputs to accept as valid. The regex closes that too.

### 3. It won't parse
The `$2` line ends the template literal early:

```js
AND i.org_id = $2`,            -- and the invoice must be in the caller's org
```

The closing backtick comes before the `--`. After that point `--` is JavaScript's decrement operator rather than a SQL comment. The apostrophe in `caller's` also opens an unterminated string. So `node --check` on this file would report a SyntaxError, and the route module wouldn't load. Nothing else in the artifact can pass until this is fixed.

- **Fix:** move that comment inside the backticks, or delete it. The other `--` comment (the `c.org_id` line) is inside the template and is fine.

### What holds up
- **Same 404 for cross-org and missing:** a single query filters on `i.id` and `i.org_id`, and the not-found branch is the only 404. Nothing in the response tells the two cases apart.
- **No other forbidden fields:** the `SELECT` names only `id`, `number`, `amount_cents`, `status`, `due_date`, `customer_id` and `customer_name`. Apart from `customer_id`, none of `email`, `tax_id`, `payment_token`, `portal_password_hash` or `org_id` are selected.
- **The join's extra org check** (`c.org_id = i.org_id`) is sound. A mismatched customer produces a 404 rather than a leak.
- **The 400 for bad ids** doesn't contradict the contract, which only forbids 500s for them.

### Unverified
If `invoices.customer_id` can be null, the inner `JOIN` returns 404 for a real invoice in the caller's org. I can't tell from the artifact whether it can be null.

Verdict: NOT VERIFIED. Fix items 1 to 3, then re-check.


=== OUTPUT Y ===

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


=== OUTPUT Z ===

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

