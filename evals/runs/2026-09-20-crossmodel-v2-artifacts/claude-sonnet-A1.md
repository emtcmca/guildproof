**Verdict: NOT VERIFIED.** The artifact breaks the contract in two places. A third defect means it won't run at all.

I couldn't run anything. Both scratch-file writes were refused for lack of permission, so everything below comes from reading the code. I didn't run it against a database, so the schema-dependent points are reasoned rather than observed.

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

Separately, a startup hook asked me to prompt you about registering this scratchpad directory (`b2-run`) as a memory project. It has no saved memory yet, so: what project are we working on? You can press Enter to use `b2-run`, name another folder, or say `skip`. I haven't registered anything.
