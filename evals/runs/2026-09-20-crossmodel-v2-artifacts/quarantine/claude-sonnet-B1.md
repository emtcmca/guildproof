**Verdict: NOT VERIFIED. BLOCKING: yes.**

**Assumption about what "this" is.** You sent no artifact or contract. The scratchpad has `inputs\v2-invoice-subtle.md`, and its line 1 is exactly "Verify this against its contract.", so I took that as the artifact and its CONTRACT block as the contract. `inputs\invoice-handler.md` is a different handler; I did not verify it. If you meant that one, say so.

**Independence:** INDEPENDENT. The artifact arrived as a finished file I did not write. I did not open the `out*` or `judge*` folders.

**Execution:** I could not run anything. `node` and a scratch-file write were both denied for permissions. Everything below is from reading the code, not from a run.

## Defects (worst first)

1. **HIGH, observable by reading: the artifact is a JavaScript SyntaxError, so the module cannot load.**
   - The template literal opens on line 24 and closes at the backtick after `$2` on line 36.
   - What follows is JS code, not SQL: `,            -- and the invoice must be in the caller's org`.
   - `--and` reads as a prefix decrement, and `the` is then an unexpected identifier. `caller's` also opens a string that is never closed. Either one is enough to fail parsing.
   - The comment on line 34 is inside the template literal, so it is valid SQL. Only the line-36 comment is misplaced.
   - Result: the route never registers, and every request gets the framework's default 404. That fails the contract outright.

2. **HIGH, observable: `customer_id` leaks to the client, which the contract forbids.**
   - The contract's forbidden list names `customer_id`, and the InvoiceDTO is `{ id, number, amount_cents, status, due_date, customer_name }`.
   - The SELECT includes `i.customer_id` (line 29).
   - Line 45 returns the raw row with `res.json(invoice)`, with no DTO mapping. `customer_id` goes out on every 200 response.
   - The task said "Nothing else … leaves the server", and the select-list-plus-passthrough design makes the leak certain, not conditional.

## Checked and clean

- **Cross-org and missing invoices return the same 404.** `oneOrNone` returns `null` for zero rows. Both cases hit the single branch at lines 41–43 with the same body.
- **Org scoping.** `AND i.org_id = $2` is bound to `req.user.org_id` (lines 36–37), so another org's row cannot match.
- **No wildcard select.** The select list is explicit, so `email`, `tax_id`, `payment_token`, `portal_password_hash` and `org_id` are not selected. Only `customer_id` escapes, per defect 2.
- **SQL injection.** `id` is a validated positive integer and the query is parameterized.
- **500 body.** The catch block returns a generic message. `err` goes only to the logger.
- **Comment claims.** "Only invoices in the caller's org are visible" is true of the SQL. The same-org customer join is true too.

## Assessment (judgment, not demonstrated)

- **Malformed ids and 500s: unconfirmed, probably not a breach.**
  - `Number()` lets through values like `99999999999` and `1e21`. On a server-side-parameterized driver, that overflows `serial` (int4) and throws, which the catch turns into a 500.
  - `db.oneOrNone` looks like pg-promise, which formats values into the SQL text client-side. In that case an out-of-range literal simply matches no rows and returns 404.
  - The driver is not stated in this artifact, so I am not asserting this defect.
- **Nitpick, not counted:** `Number()` also accepts `"0x10"`, `"1e3"` and `" 12 "` as ids 16, 1000 and 12. The contract does not forbid it.

## Claimed vs. actual

- The header comment and the join comment are accurate.
- The artifact never claims to return exactly the DTO fields. Its own SELECT and passthrough break that contract line.

## Confirm-these

- Whether the module parses. Run `node --check` on lines 13–50. I expect a SyntaxError at line 36.
- Which DB driver is in use, and what a 12-digit id returns.
- That `requireSession()` guarantees a defined `req.user.org_id`. An undefined value in pg-promise throws and produces a 500.
- How `due_date` serializes, since a `date` column may come back as a JS Date and be emitted as an ISO timestamp.

## Single most damaging defect

The handler is a syntax error, so nothing else about it can be exercised. Behind that, `customer_id` is a direct breach of an explicitly listed contract bullet.
