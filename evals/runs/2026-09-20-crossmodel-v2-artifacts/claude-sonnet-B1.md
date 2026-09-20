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
