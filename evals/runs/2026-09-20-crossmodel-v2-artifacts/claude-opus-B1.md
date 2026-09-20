## Verdict

**NOT VERIFIED — BLOCKING: yes.**

One unresolved HIGH defect: the endpoint returns a field the contract explicitly forbids, on every successful response.

**Independence: INDEPENDENT.** The artifact arrived finished, pasted into this conversation. I did not write, draft, or direct any part of it, and there is no producer cover note in view to be misled by.

---

## Observable evidence

These I can point at in the artifact itself.

**❌ HIGH — `customer_id` leaves the server on every 200.**
The `SELECT` list includes `i.customer_id` (line 7 of the query), and the success path is `return res.json(invoice)` — the raw database row, unmapped. The contract names `customer_id` in its own do-not-leak list, and the declared `InvoiceDTO` has six fields; this response has seven.

How to demonstrate it, on any invoice the caller legitimately owns:

```powershell
$r = Invoke-RestMethod -Uri "https://<host>/api/invoices/123" -Headers @{ Cookie = "<session cookie>" }
$r | ConvertTo-Json
```

The body contains `customer_id`. There is no conditional, no environment flag, no edge case — it is in the projection, so it is in the response, 100% of the time. This is not a style objection; it is the literal text of the contract being false about the running code.

**❌ MEDIUM — the "nothing else leaves" property is not enforced anywhere; it is incidental.**
Same root cause, stated as a structural fact rather than one bad field. The response shape is defined by whatever the `SELECT` list happens to contain at any given moment. No DTO constructor, no field allowlist, no serializer, no schema on the way out. The only thing standing between `portal_password_hash` and the wire is that nobody has yet typed it into the query. The current leak is the proof that this control does not hold — the comment on line 2 claims the endpoint "returns one invoice plus its customer's name," and it already returns more than that. A future `SELECT c.*` or an added column repeats this defect silently, and no test of the current code would catch it.

**✅ The 404 indistinguishability axis is clean.**
Both a nonexistent invoice and another org's invoice fail the same `WHERE i.id = $1 AND i.org_id = $2` predicate, produce `null` from `oneOrNone`, hit the same `if (!invoice)`, and return the identical status code and identical body `{ error: 'Invoice not found' }`. There is no branch between them. A caller cannot probe which IDs exist.

**✅ SQL injection is not reachable here.**
`id` is coerced through `Number()` and gated by `Number.isInteger`, so it cannot carry a string into the query at all. `req.user.org_id` is passed as a bound parameter in the `[id, req.user.org_id]` array, not interpolated. No string concatenation anywhere in the query.

**✅ The error path does not leak.**
The `catch` logs `err` server-side and returns a fixed generic `'Internal server error'` string. No stack, no driver message, no row data reaches the client. The log line carries only `invoiceId` and `userId` — no customer PII.

---

## Assessment

My judgment, where I could not fully demonstrate it from what I was given.

**❌ MEDIUM — the inner `JOIN` can 404 an invoice the caller actually owns.**
The contract's first sentence is that the endpoint returns an invoice belonging to the caller's org. The query cannot do that unless a matching `customers` row also exists with a matching `org_id`. If `invoices.customer_id` is nullable, or a customer row is soft-deleted, or a customer's `org_id` was ever migrated while its invoices were not, the join yields nothing and the caller gets a 404 for an invoice that is genuinely theirs. That is a wrong answer, and it is the *confusing* kind of wrong answer, because the 404 is deliberately indistinguishable from "does not exist" — so the bug reports itself as missing data rather than as a join failure.

I label this assessment rather than observable because whether it can actually happen depends on the schema I was not given (a `NOT NULL` + foreign key on `customer_id`, plus whether customers are ever hard-deleted or re-orged). The defect is real if the constraint is absent. `LEFT JOIN` with a null-safe `customer_name` is the shape that matches the stated contract, if a customer-less invoice is a legal state.

**⚠️ LOW — `Number()` accepts id forms the guard was written to reject.**
The comment says "Reject anything that isn't a positive integer," but `Number()` is a lenient coercion, not an integer parser. `/api/invoices/1e3` becomes `1000`. `/api/invoices/0x10` becomes `16`. `/api/invoices/%201%20` becomes `1`. These all pass the guard and query a real row. No contract clause is breached — the org check still holds, so nothing crosses a tenant boundary — but the code does not do what its own comment says, and that gap is how a future change that *does* matter gets made on a false premise. `Number.isSafeInteger` plus an explicit upper bound is the tighter guard.

---

## Claimed vs. actual

| The artifact says | What it actually does |
|---|---|
| `// Returns one invoice plus its customer's name` (line 2) | Returns the invoice, the customer's name, **and the internal `customer_id`** |
| `// Reject anything that isn't a positive integer before it reaches the DB` | Rejects most non-integers; accepts `1e3`, `0x10`, and whitespace-padded and out-of-range integer-valued forms |
| `// A missing invoice and another org's invoice both return 404` | True. This claim survives. |

---

## Confirm-these

Each of these is an axis I could not close from the artifact alone. None of them is a reason to unblock; the HIGH above stands regardless.

1. **Where does `req.user.org_id` come from?** The entire tenant-isolation guarantee of this endpoint rests on that single value, and `requireSession()` is opaque to me. If it is derived server-side from a signed session record, the isolation holds. If any part of it is populated from a client-supplied header, body, or token claim that is not verified against server-side membership, then the `AND i.org_id = $2` clause is attacker-controlled and this endpoint reads any org's invoices. **This is the most security-critical unconfirmable item here — verify it before trusting the 404 result above.**
2. **What happens if `req.user.org_id` is `undefined`** for a valid session (a user not yet assigned an org, or a service account)? Under a driver that inlines params this likely degrades to `org_id = null` → no rows → 404, which is safe. Under one that binds and type-checks, it may throw into the `catch` → 500. Confirm which, and consider failing closed explicitly.
3. **Is `invoices.id` an `integer` column, and does the driver bind or inline?** `Number.isInteger(1e20)` is `true`, so a value far outside `int4` range passes the guard and reaches the database. Under `pg-promise`'s client-side formatting this most likely becomes a numeric-literal comparison and returns a harmless 404. Under a path where Postgres infers `int4` for the parameter, it raises `22003 numeric_value_out_of_range`, which lands in the `catch` and returns **500 — breaching the contract's "malformed ids never produce a 500" clause directly.** Cheap to settle: `curl` the endpoint with `99999999999999999999` and read the status code.
4. **`requireSession()` invocation shape.** It is called as a factory (`requireSession()`), so it must return middleware. If it is itself the middleware, this registers `undefined` and the route has no auth at all. Almost certainly fine, but it is one character of difference between "authenticated" and "open."
5. **Is `invoices.customer_id` `NOT NULL` with an enforced foreign key?** This decides whether finding 3 above is a live bug or a non-issue.

---

## The single most damaging thing

Strip everything else away: **the contract's central promise is that a fixed set of six fields leaves the server, and the code has no mechanism that makes that true.** It returns a database row directly. `customer_id` is today's instance of that; the absence of any output allowlist is why there will be another one. The fix is not deleting one line from the `SELECT` — it is building the DTO explicitly, so that the next person who adds a column to this query cannot leak it by accident.

Fixing goes back to a builder. I do not patch what I verify.

---

One housekeeping item from the session hook, unrelated to the above: this directory has no saved memory yet. What project are we working on? (press Enter to use 'b2-run', name another memory folder, or say 'skip') — given it's a temp scratchpad, 'skip' is probably right.
