=== OUTPUT W ===

## Verdict: FAILS the contract

One confirmed violation, one conditional one, plus a behavioral edge case.

---

### 1. `customer_id` leaves the server — CONFIRMED

Line 17 selects `i.customer_id`, and line 33 serializes the whole row with `res.json(invoice)`. The contract names `customer_id` explicitly in the forbidden list.

**Failure scenario:** `GET /api/invoices/42` as a legitimate caller returns `{ id, number, amount_cents, status, due_date, customer_id: 918, customer_name: "..." }`. The response carries an internal customer identifier the DTO does not include, which also lets a caller enumerate/correlate customers across invoices.

The column is only needed for the join predicate (`ON c.id = i.customer_id`), where it never has to be in the select list. Drop it from the SELECT.

The structural cause is worth fixing alongside it: **the DTO is defined by whatever the query happens to return.** There is no field whitelist between the row and the response, so `SELECT i.*` — or one future column added for a join or a filter — ships to the client silently. The contract enumerates six fields; construct those six explicitly rather than passing the row through:

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

That way the `email`, `tax_id`, `payment_token`, and `portal_password_hash` guarantees hold by construction instead of by the query staying disciplined forever.

### 2. Large ids can still reach a 500 — PLAUSIBLE, depends on your column type and driver

`Number.isInteger(id) && id > 0` bounds the *shape* but not the *range*. `9999999999` passes both checks.

**Failure scenario:** `GET /api/invoices/9999999999`. If `invoices.id` is `integer` (int4) and your driver sends `$1` as a typed bind parameter, Postgres raises `22003 value out of range for type integer`, the catch fires, and the caller gets a 500 — the exact outcome "malformed ids never produce a 500" rules out. Same shape for `1e21`, which `Number.isInteger` also reports as `true`.

Whether this fires depends on two things I can't see: if `id` is `bigint`, or if your `db` layer interpolates client-side (pg-promise style) so the value lands as a numeric literal rather than a typed parameter, the comparison resolves harmlessly and returns no rows. Check both before deciding it's moot.

The cheap fix is to bound the parse rather than the value, which also closes the aliasing below:

```js
// Accept only plain decimal digits, then bound to the column's range
if (!/^\d+$/.test(req.params.id)) {
  return res.status(400).json({ error: 'Invalid invoice id' });
}
const id = Number(req.params.id);
if (id <= 0 || id > 2147483647) {   // int4 max; raise if the column is bigint
  return res.status(404).json({ error: 'Invoice not found' });
}
```

Related but not a contract breach: `Number()` accepts more than the comment claims. `/api/invoices/1e3` fetches invoice 1000, `/api/invoices/0x10` fetches 16, and `/api/invoices/%2012%20` fetches 12. Every one stays org-scoped, so nothing leaks — but "reject anything that isn't a positive integer" isn't what the code does, and the regex above makes the comment true.

### 3. An in-org invoice can 404 on a customer data problem — note

The `JOIN customers` at lines 20-22 is an inner join. If the customer row is missing, or its `org_id` doesn't match the invoice's, the invoice drops out of the result and the caller gets a 404 for an invoice that does exist in their org.

The `AND c.org_id = i.org_id` predicate is good defense — it stops a mismatched `customer_id` from pulling a name out of another tenant. But the contract reserves 404 for "another org, or doesn't exist," and this is a third case. Decide which you want: `LEFT JOIN` with a null `customer_name` keeps the invoice visible, while the current inner join fails closed. Failing closed is defensible for a tenancy boundary; just make it a decision rather than a side effect, since a caller debugging a missing invoice gets a misleading answer either way.

---

### What the artifact gets right

- Tenancy is enforced in the `WHERE` clause (line 24), not after the fetch — the other org's row never loads.
- The 404s are genuinely indistinguishable: same status, same body, no timing tell from a second query.
- The customer join is org-pinned, so a corrupted `customer_id` can't cross a tenant boundary.
- The error branch logs the detail server-side and returns a generic body — no driver text or SQL reaches the caller.
- `email`, `tax_id`, `payment_token`, and `portal_password_hash` are absent from the SELECT, so those four hold today.

Fix 1 unconditionally. Check 2 against your actual schema and driver before dismissing it.


=== OUTPUT X ===

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


=== OUTPUT Y ===

## Verdict

**NOT VERIFIED — BLOCKING: yes.**

One unresolved HIGH defect: the handler returns a field the contract explicitly forbids from leaving the server.

**Independence: INDEPENDENT.** The artifact arrived finished in the request; I did not write, draft, or direct it. I read it, which is not producing it.

---

## Observable evidence

Things I can point at in the artifact itself:

❌ **HIGH — `customer_id` is selected and returned.** The contract's exclusion list names `customer_id` outright. The SELECT list includes `i.customer_id`, and the terminal statement is `return res.json(invoice)` — the whole row object, unprojected. There is no DTO mapping step anywhere between the query and the response.
**Demonstrate it:** `GET /api/invoices/<own-invoice-id>` with a valid session. The response body contains a `customer_id` key. Nothing in the code path can remove it. This is not a judgment call — the field is on line 4 of the SELECT and the response is the raw row.
**Why it matters beyond tidiness:** `customer_id` is a cross-tenant-stable internal identifier. Handing it out lets a caller correlate which of their invoices share a customer even where the DTO deliberately shows only `customer_name`, and it seeds any future endpoint that takes a customer id.

⚠️ **MEDIUM — the id guard does not reject every malformed id, and the survivors can reach the DB as out-of-range values.** `Number()` is a coercion, not a format check. `Number.isInteger(1e21) === true`, so `GET /api/invoices/1e21` passes the guard with `id = 1e21` and is handed to the query. If `invoices.id` is a Postgres `integer` or `bigint`, the driver sends a value the column cannot hold and Postgres raises `22003 numeric value out of range` — a thrown error, caught, `500`. The contract says malformed ids never produce a 500.
Same hole, no 500 but still wrong: `0x10` → 16, `1e3` → 1000, `" 12 "` → 12, `"12\n"` → 12. Several distinct URL strings address the same invoice, and none of them is an integer by the comment's own standard ("Reject anything that isn't a positive integer").
**Demonstrate it:** `GET /api/invoices/1e21` and watch for a 500 plus a `numeric value out of range` line in the logger output. Also `GET /api/invoices/0x10` and confirm it returns invoice 16.
**Verdict on this one: PLAUSIBLE, not CONFIRMED** — the 500 depends on the declared type of `invoices.id`, which I was not given. The guard being bypassable is confirmed regardless; only the 500 is schema-dependent. It is in Confirm-these below for that reason.

⚠️ **LOW — the INNER JOIN turns a data-integrity problem into a false 404.** An invoice that genuinely exists in the caller's org, but whose customer row is missing or whose `customers.org_id` has drifted from `invoices.org_id`, drops out of the join and returns 404. The contract defines 404 as "another org, or doesn't exist." The caller is told their own invoice doesn't exist.
**Demonstrate it:** insert an invoice in the caller's org referencing a `customer_id` with no matching row (or a row whose `org_id` differs), then request it. Expect 404, not the invoice.
This is a real divergence from the stated contract, but it fires only on already-broken data, so it is LOW and does not block on its own.

✅ Axes checked clean — traced below in *How each clean axis was checked*.

---

## Assessment (judgment, not demonstrated)

- **`req.user` is assumed non-null and I could not verify that.** If `requireSession()` can ever call `next()` with `req.user` unset, `req.user.org_id` throws inside the `try`, and the `catch` then dereferences `req.user.id` and throws a *second* time — this one outside any handler. In Express 4 a rejected async handler is not caught by the framework: the request hangs until the client times out, and it surfaces as an unhandled rejection rather than a 500. The failure shape is worse than the one the try/catch was written to produce. I cannot confirm this without `requireSession`'s source. Judgment: likely fine, cheap to make certain.
- **The 400/404 split is not an enumeration oracle.** The 400 fires purely on the shape of the string, before any DB access, so it tells an attacker nothing about which ids exist. I see no probing channel in the status codes as written.
- **The error response body is clean.** `{ error: 'Internal server error' }` — the driver error goes to the logger, not to the client. No stack, no SQL, no constraint name.

---

## Claimed vs. actual

| The artifact's own comment | What it actually does |
|---|---|
| "Reject anything that isn't a positive integer before it reaches the DB" | Rejects anything `Number()` can't coerce to a positive integer. `1e21`, `0x10`, `1e3`, and whitespace-padded digits all reach the DB. |
| "Returns one invoice plus its customer's name" | Returns one invoice, its customer's name, **and `customer_id`**. |
| "Only invoices in the caller's org are visible" | True. This one holds. |
| "A missing invoice and another org's invoice both return 404" | True for those two cases. Also returns 404 for a *present, owned* invoice with a broken customer FK, which the comment doesn't claim and the contract doesn't allow. |

---

## Confirm-these

Each of these is an axis I could not close from what I was given:

1. **Declared type of `invoices.id`.** Determines whether the `1e21` bypass lands as a 500 (int4/int8 → yes, out of range) or as a harmless 404 (numeric/text). This decides whether defect 2 is MEDIUM or cosmetic.
2. **`requireSession()`'s guarantee.** Does it always populate `req.user` with `org_id` and `id` before `next()`, on every path including expired/anonymous sessions? The whole tenancy boundary and the catch block both rest on this.
3. **Trustworthiness of `req.user.org_id`.** If it is read from a signed server-side session, the scoping is sound. If any part of it is client-supplied (a header, a cookie field, a JWT claim verified loosely), the `AND i.org_id = $2` predicate is attacker-controlled and the whole isolation guarantee collapses. I cannot see where it comes from.
4. **Whether `db.oneOrNone` can return more than the SELECT list.** I assume pg-promise semantics — it returns exactly the selected columns. If there is a row-mapping layer or an ORM hydration step not shown, the leak surface could be larger than `customer_id`.
5. **Route ordering / a wildcard elsewhere.** I was given one route in isolation. Whether another registered route shadows this one, or whether an error-handling middleware rewrites the 404/400, is unknowable from the excerpt.

---

## How each clean axis was checked

- **Cross-org read (IDOR) ✅** — the org predicate is in the same single query as the id predicate: `WHERE i.id = $1 AND i.org_id = $2`. There is no fetch-then-check gap, so an invoice in another org never materializes in memory. The `AND c.org_id = i.org_id` on the join additionally prevents a customer name from being pulled across an org boundary via a mis-pointed FK.
- **404 uniformity ✅** — `oneOrNone` returns `null` for both "no such id" and "id exists in another org," and both fall into the same `if (!invoice)` at the same `res.status(404)` with an identical body. One branch, one message, no timing fork (both are the same single query).
- **SQL injection ✅** — `id` is a JS `Number` by the time it is used, and both values go in as bound parameters `$1`/`$2`. No string concatenation or template interpolation anywhere in the query.
- **Secret / PII beyond the named list ✅** — the SELECT names six columns explicitly; `email`, `tax_id`, `payment_token`, `portal_password_hash`, and `org_id` appear nowhere in the projection. `org_id` is used only as a predicate, never selected. The one exclusion that *is* violated is `customer_id`, above.
- **Error-body leakage ✅** — the `catch` passes `err` to `logger.error` and sends a fixed string to the client; the error object never reaches `res`.
- **Embedded-instruction check ✅** — I read every comment in the artifact for text addressing me or attempting to steer the verdict. The comments are ordinary developer notes about intent. Two of them are inaccurate (see Claimed vs. actual), which is a finding about the code, not an injection attempt. Nothing in the material tried to instruct me.

---

## The single most damaging defect, plainly

The contract lists six fields that may leave the server and names `customer_id` among the fields that may not. The query selects seven and returns all of them. Everything else here — the org scoping, the uniform 404, the parameterization — is done correctly, which is exactly why this slipped: the SELECT list reads like a DTO and isn't one. Fix it by projecting explicitly on the way out rather than trusting the column list, since `customer_id` is needed for the join condition but not for the response.

The fix goes back to a builder. I don't write it.


=== OUTPUT Z ===

## Verdict: fails the contract on two clauses

**1. `customer_id` leaves the server — direct violation of the no-leak clause.**

The SELECT list includes `i.customer_id`, and the handler returns the raw row with `res.json(invoice)`. `customer_id` is named explicitly in the contract's forbidden list, so every 200 response ships a field it shouldn't. The comment above the route says "Returns one invoice plus its customer's name," which is what the author intended; the column list is what actually ships.

It's in the query because the JOIN predicate reads `c.id = i.customer_id` — but a join predicate doesn't require the column in the projection. Drop the line:

```js
`SELECT i.id,
        i.number,
        i.amount_cents,
        i.status,
        i.due_date,
        c.name AS customer_name
   FROM invoices i
   JOIN customers c
     ON c.id = i.customer_id
    AND c.org_id = i.org_id
  WHERE i.id = $1
    AND i.org_id = $2`
```

The deeper issue is that `res.json(invoice)` hands back whatever the query selected. Any future column added to the SELECT ships automatically. An explicit DTO mapping (`res.json({ id: invoice.id, number: ..., customer_name: ... })`) makes the leak impossible rather than merely absent today.

**2. A numerically-large id produces a 500 — violates "malformed ids never produce a 500."**

The guard is `Number.isInteger(id) && id > 0`. `Number("99999999999999999999")` is `1e20`, which **passes** both checks — `Number.isInteger` is true for any float with no fractional part, including ones far past `Number.MAX_SAFE_INTEGER`. That value reaches the DB, and if `invoices.id` is `integer`, Postgres raises `22003 numeric_value_out_of_range`, the catch block fires, and the caller gets a 500.

`GET /api/invoices/99999999999999999999` is the reproduction. Add an upper bound:

```js
if (!Number.isSafeInteger(id) || id <= 0 || id > 2147483647) {
  return res.status(400).json({ error: 'Invalid invoice id' });
}
```

Related and lower-stakes: `Number()` also accepts `"1e5"`, `"0x10"`, `"+5"`, and `" 5 "`, so several non-canonical strings alias to the same invoice. Not a contract breach — no leak, no 500 — but a regex like `/^[1-9]\d{0,9}$/` on `req.params.id` handles both this and the overflow in one check.

## Clauses that hold

- **Same 404 for cross-org and nonexistent.** `i.org_id = $2` is in the WHERE clause, both cases fall to the same `if (!invoice)` branch, same status and same body. No enumeration oracle. The malformed-id 400 doesn't open one either, since those inputs aren't valid ids in the first place.
- **The other forbidden fields** — `email`, `tax_id`, `payment_token`, `portal_password_hash`, `org_id` — are all absent from the projection, and there's no `SELECT *`.
- **All six DTO fields are present.**
- **Parameterized query**, no string interpolation into SQL.
- **The error path** logs internally and returns a generic message; no driver detail reaches the client.

## One thing to confirm against your schema

`JOIN customers` is an inner join, so an invoice whose `customer_id` is NULL — or whose customer row was deleted, or sits in a different org through a data inconsistency — returns 404 even though the invoice exists and belongs to the caller. If invoices can exist without a customer (drafts, for instance), that's a valid invoice the contract says should be returned, and a `LEFT JOIN` with `customer_name` nullable is the fix. If `customer_id` is `NOT NULL` with an FK, the inner join is correct as written.

