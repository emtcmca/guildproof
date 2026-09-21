=== OUTPUT U ===

## Verdict: NOT VERIFIED — 2 contract violations, 1 behavioral divergence

### 1. `customer_id` leaves the server (leak, contract line 3)

The query selects `i.customer_id`, and the handler returns the raw row with `res.json(invoice)`. There is no projection step between the DB row and the response, so every column the query selects is a response field.

`customer_id` is on the contract's explicit prohibited list.

**Failure:** `GET /api/invoices/42` returns `{ id, number, amount_cents, status, due_date, customer_id, customer_name }` — seven fields where the DTO names six, and the extra one is named in the ban list. A caller can enumerate internal customer IDs by walking their own invoices.

The comment above the handler says it returns "one invoice plus its customer's name," which is what the author intended; the `customer_id` column was pulled in to satisfy the JOIN and never removed from the select list. It isn't needed — the JOIN condition can reference `i.customer_id` without projecting it.

Fix: drop `i.customer_id` from the SELECT, or build the DTO explicitly:

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

An explicit projection is the stronger fix: it fails closed when someone later adds a column to the query.

### 2. Out-of-range numeric ids produce a 500 (contract line 4)

`Number.isInteger()` is the wrong guard. It accepts any integer-*valued* float, including values far outside any SQL integer column:

- `Number("99999999999")` → `99999999999`, `Number.isInteger` → `true`, `> 0` → passes validation
- Postgres compares it against `i.id`. If `id` is `int4`, that's `value out of range for type integer`; if `bigint`, the same happens above ~9.2e18. Past 1e21 the driver serializes it as `1e+21` and you get `invalid input syntax for type integer`.
- Either way the driver throws, the `catch` fires, and the caller gets **500**.

**Failure:** `GET /api/invoices/99999999999` → 500, on an `int4` id column. The validation block exists precisely to prevent this and doesn't.

Fix: `Number.isSafeInteger(id) && id > 0 && id <= 2147483647` (match the actual column type), keeping the 400. The 400 itself is fine — the contract only forbids a 500 for malformed ids, and it doesn't reveal existence.

### 3. Minor — an inner JOIN turns a data-integrity problem into a 404

`JOIN customers c ON c.id = i.customer_id AND c.org_id = i.org_id` is an inner join. If an invoice in the caller's own org has a deleted customer row, or a customer whose `org_id` drifted, the row drops out and the caller gets 404 for an invoice that is genuinely theirs.

That is safe (it fails closed, no leak) but it diverges from "returns one invoice that belongs to the caller's organization," and it's the kind of thing that gets debugged as a phantom permissions bug. A `LEFT JOIN` with `customer_name` nullable, or an explicit integrity check, makes the failure legible. Judgment call — flagging, not asserting it's wrong.

### What the artifact gets right

- **The 404 conflation is correct.** Nonexistent and other-org both hit `!invoice` and return the identical body. No timing or status-code oracle for ID probing.
- **Org scoping is in the WHERE clause, not applied after the fetch.** `i.org_id = $2` means another org's row never enters the process.
- **The customer is org-scoped too** (`c.org_id = i.org_id`), so a mismatched `customer_id` can't pull a name across the tenant boundary.
- **Parameterized query** — no injection surface.
- **The error log stays server-side**; the 500 body is generic.

The two violations are both one-line fixes. Neither is an auth hole — the tenant boundary itself holds.


=== OUTPUT V ===

## Verdict: FAILS the contract — one confirmed leak, one confirmed 500 path

Three of the four clauses hold. Org scoping is correct (both the invoice and the joined customer are constrained to the caller's org), and the indistinguishable-404 clause holds — a missing invoice and another org's invoice take the identical `!invoice` branch. Non-numeric garbage (`abc`, `../../etc`, `null`) is rejected at the 400 gate before it reaches the DB.

Here is what breaks.

---

### 1. `customer_id` leaves the server — explicitly banned by the contract

`i.customer_id` is in the SELECT list, and `res.json(invoice)` serializes the whole row. The contract names `customer_id` in the prohibited set. The column isn't used anywhere in the handler — it's selected and then shipped.

**Failure:** `GET /api/invoices/42` returns `{ id, number, amount_cents, status, due_date, customer_id: 8891, customer_name }`. The caller now has an internal customer identifier it was never supposed to see, and `customer_id` values are sequential and enumerable across the tenant.

**Fix — stop trusting the SELECT list to be the DTO.** Build the response explicitly, so a future column added to the query can't leak by default:

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

Dropping `i.customer_id` from the query also fixes today's instance, but the explicit DTO is what makes the clause hold permanently. The current code's contract compliance depends on nobody ever adding a column to that SELECT.

---

### 2. A numeric-but-out-of-range id produces a 500

`Number.isInteger()` only asks whether the value is an integer, not whether it fits the column. `Number("9999999999")` is `9999999999` — an integer, greater than zero, so it sails past the guard. node-postgres stringifies it and Postgres rejects it against an `int4` column with *"value out of range for type integer"*. That throws, hits the catch, and returns 500.

**Failure:** `GET /api/invoices/9999999999` → 500 Internal Server Error, plus an `logger.error` entry. Same for `GET /api/invoices/1e21`, where `Number()` yields `1e+21` and pg sends the literal string `"1e+21"` — Postgres errors with *"invalid input syntax for type integer"*. Both are malformed ids by any reasonable reading, and the contract says malformed ids never produce a 500.

This is also a cheap unauthenticated-ish noise generator: every request writes an error log line, so it's a log-flooding lever for anyone with a session.

**Fix — validate the string, then bound it:**

```js
// Match the wire format strictly, then check it fits the column.
// Number() is too permissive: it accepts "1e3", "0x10", " 12 ", and out-of-range values.
const MAX_INT4 = 2147483647;
if (!/^[1-9][0-9]*$/.test(req.params.id)) {
  return res.status(400).json({ error: 'Invalid invoice id' });
}
const id = Number(req.params.id);
if (id > MAX_INT4) {
  return res.status(400).json({ error: 'Invalid invoice id' });
}
```

If the column is `bigint`, swap the bound for `Number.MAX_SAFE_INTEGER` — or keep the id as a string and let Postgres parse it, which avoids the float-precision question entirely.

---

### 3. Lower confidence, depends on your schema: the inner JOIN can 404 an invoice the caller owns

`JOIN customers c` is an inner join. If `i.customer_id` is nullable — a draft invoice with no customer attached yet — or if the customer row was deleted, the join drops the row and the caller gets a 404 for an invoice that exists inside their own organization. The contract reserves 404 for "another organization, or one that doesn't exist."

The `AND c.org_id = i.org_id` predicate is good defense, but it's doing double duty: it's both a security check and a visibility filter, and when it fails you can't tell a cross-org data-integrity problem from a normal miss.

**Whether this is a defect is a schema question I can't answer from the artifact.** If `invoices.customer_id` is `NOT NULL` with an FK to `customers`, the inner join can never drop a row and this is a non-issue. If it's nullable, switch to `LEFT JOIN` and let `customer_name` come back null — and consider logging a warning when the invoice resolves but the customer doesn't, because that state means either a dangling reference or a cross-org row worth knowing about.

---

**One thing worth confirming rather than fixing:** `due_date` comes back as whatever pg maps the column to. A `date` column yields a JS `Date` at midnight UTC, which `res.json` serializes as `"2026-03-14T00:00:00.000Z"` — not the `"2026-03-14"` most DTO consumers expect from a field named `due_date`. The contract names the field but not its shape, so this isn't a violation; it's just the kind of thing that turns into a client-side bug later.


=== OUTPUT W ===

## Verdict

**NOT VERIFIED. BLOCKING: yes** — one HIGH defect (a field the contract explicitly forbids is returned on every success), plus a second path that produces the 500 the contract says can never happen.

## Independence

**INDEPENDENT.** I did not author or plan this handler, received no author rationale, and worked only from the contract text and the code as pasted. Caveat on strength: this is static review only — there is no repo, schema, `requireSession`, or DB here, so nothing was executed. Two findings are therefore CONFIRMED by reading and one is PLAUSIBLE pending the column type.

## Observable evidence

**Defects I can demonstrate from the text alone:**

- Line 17 selects `i.customer_id`, and line 33 returns the row object unmodified (`res.json(invoice)`). There is no DTO projection, pick, or allowlist between them. Every 200 response carries `customer_id`.
- Line 6's guard is `Number.isInteger(id) || id <= 0`. `Number.isInteger(1e30) === true` and `1e30 > 0`, so `GET /api/invoices/1e30` passes validation and reaches `$1`. No integer column accepts it.

**Axes I checked and found clean** (tracing in "How each clean axis was checked" below): cross-org 404 indistinguishability, injection surface, and the absence of email / tax_id / payment_token / portal_password_hash / org_id from the projection.

**Given test/build results:** none supplied. Nothing was run.

## Assessment

*(judgment, not demonstration)*

The handler's *access-control* reasoning is sound and the two-predicate scoping (`i.org_id = $2` plus `c.org_id = i.org_id`) is more careful than most code that meets this contract. The failures are at the edges: an over-broad projection and a validator that checks the *JavaScript* notion of a valid integer rather than the *database's*. My judgment is that the `customer_id` leak is the one that matters — it is silent, it is on the success path, and it hands a caller a stable internal identifier for a row they were only ever supposed to see the name of. The 500 path is lower-consequence but it is a flat contradiction of an explicit contract line, so it blocks too.

I also judge (weakly, cannot demonstrate) that returning the raw driver row is the structural cause of defect 1 rather than an oversight on one line. A future `SELECT i.*` or an added column reintroduces the leak with no code change at the response site. The fix that holds is an explicit DTO construction, not deleting line 17.

## Defects

❌ **HIGH — `customer_id` is returned on every success; the contract names it as a field that must not leave the server.** Line 17 puts it in the projection, line 33 serializes the row as-is. *Demonstrate:* `GET /api/invoices/<own-org id>` as any authenticated user and read the response body — `customer_id` is a top-level key alongside the six DTO fields. Compare against the contract's DTO shape `{ id, number, amount_cents, status, due_date, customer_name }`: seven keys, not six. Verdict: CONFIRMED.

❌ **HIGH — a syntactically valid but out-of-range id produces a 500, which the contract forbids for malformed ids.** `Number.isInteger` accepts any integral double, including `1e30`, `1e21`, and (on an `int4` column) anything above `2147483647`. The value reaches Postgres, the comparison against an integer column raises `integer out of range` / `numeric field overflow`, and the `catch` at line 34 returns 500. *Demonstrate:* `GET /api/invoices/1e30` → 500 rather than 400 or 404. `GET /api/invoices/2147483648` does the same if `invoices.id` is `int4`. Verdict: CONFIRMED for `1e30` (no integer column type accepts it); PLAUSIBLE for `2147483648`, which depends on `int4` vs `int8`.

⚠️ **MEDIUM — the inner `JOIN customers` can turn an invoice the caller owns into a 404.** Line 20's join is required, not optional, and line 22 adds `c.org_id = i.org_id`. If the customer row is soft-deleted, missing, or sits in a different org after a merge or re-parent, the query returns no row and line 30 reports "Invoice not found" for an invoice that exists in the caller's org. The contract says such an invoice is returned. *Demonstrate:* insert an invoice with `org_id = X` whose `customer_id` points at a customer with `org_id = Y`, then `GET` it as a user in org X → 404. Whether this is reachable depends on FK and deletion policy, so I am calling it weak rather than confirmed: if there is a composite FK `(customer_id, org_id)` and no soft deletes, it is unreachable.

⚠️ **LOW — `Number()` coercion silently aliases several id spellings to the same record.** `"1e3"`, `" 12 "`, `"0x10"`, `"12."`, and `"+12"` all pass line 6. *Demonstrate:* `GET /api/invoices/0x10` returns the same body as `GET /api/invoices/16`. No contract clause breaks (the contract only bars 500s), but it defeats log correlation, rate-limit keying, and any cache keyed on the raw path. Related: above 2^53 the coercion is lossy, so a caller could be served a neighboring row's data — that one is blocked in practice by the range failure in defect 2, which fires first.

✅ **Cross-org and nonexistent invoices return an identical 404.** Checked clean.

✅ **No injection surface.** Checked clean.

✅ **No email, tax_id, payment_token, portal_password_hash, or org_id in the projection.** Checked clean.

## Claimed vs. actual

| The artifact says | It actually does |
|---|---|
| Line 4: "Reject anything that isn't a positive integer before it reaches the DB" | Rejects anything that isn't a positive *JavaScript* integer. `1e30` is one; the database disagrees, and the disagreement surfaces as a 500. The comment states the intended postcondition, and the code enforces a weaker one. |
| Line 2: "Returns one invoice plus its customer's name" | Returns one invoice, its customer's name, **and the customer's id**. The header doc is the reason the extra field reads as intentional on a skim. |
| Line 28: "callers can't probe which IDs exist" | True for the 404 pair, and the comment is correct about that. But the handler emits three distinguishable statuses across the id space — 400, 404, 500 — and the 500 in defect 2 is itself a signal that a 404 is not. A caller can separate "id shape the DB rejects" from "id that does not exist." Narrow, but the comment claims more than the code delivers. |
| Contract: "Nothing else about the invoice or the customer leaves the server" | Seven fields leave, not six. |

## Confirm-these

Each of these is context I did not have. None of them can turn the two HIGH defects into non-defects, but the first two could change severity and the third decides whether defect 3 is real.

1. **`invoices.id` column type (`int4` vs `int8`).** Decides whether `2147483648` is a second reproducer for defect 2. `1e30` breaks either way, so the defect stands regardless.
2. **What `requireSession()` guarantees about `req.user`.** If it can call `next()` with `req.user` unset or lacking `org_id`, then line 25 throws, the catch fires, and *that* is another 500 — and worse, if `org_id` can be `undefined`, `i.org_id = NULL` matches nothing and every request 404s. I could not read the middleware.
3. **FK shape and deletion policy on `customers`.** Specifically whether `(customer_id, org_id)` is a composite FK and whether customers are ever soft-deleted or re-parented. This decides whether defect 3 is reachable.
4. **Whether an upstream error handler or response serializer strips fields.** If some `res.json` wrapper applies a DTO allowlist, defect 1 is already mitigated. Nothing in the pasted code suggests one exists, and I would not rely on it.
5. **`logger.error` sink and redaction.** The `err` object may carry the parameterized statement and values. Server-side only, so not a contract breach, but it is the kind of thing that ends up in a third-party log aggregator.

## How each clean axis was checked

- **Cross-org 404 == nonexistent 404:** both cases produce the same thing at the same place. `WHERE i.id = $1 AND i.org_id = $2` (lines 23–24) yields zero rows whether the id is absent from the table or present under a different org. `db.oneOrNone` maps zero rows to `null`, `!invoice` at line 29 is true in both cases, and line 30 is the single exit — same status, same body string, no branch between them. There is no timing or shape difference to separate the two.
- **No SQL injection:** `id` reaches the query only as `$1` (line 25) and only after passing `Number.isInteger` at line 6, so its runtime type at the boundary is `number`, not string. `req.user.org_id` reaches it only as `$2`. No template interpolation, no string concatenation anywhere in the statement — the SQL is a single static template literal with no `${}` in it.
- **No forbidden invoice/customer fields in the projection:** the select list is closed and enumerable at lines 12–18 — `i.id`, `i.number`, `i.amount_cents`, `i.status`, `i.due_date`, `i.customer_id`, `c.name AS customer_name`. No `*`, no `i.*`, no `c.*`. Checking the contract's prohibition list against that enumeration: `email` absent, `tax_id` absent, `payment_token` absent, `portal_password_hash` absent, `org_id` absent (it appears only in the `ON` and `WHERE` predicates at lines 22 and 24, which filter without projecting). `customer_id` is the one name on the prohibition list that *does* appear, which is defect 1 — the axis is clean for the other five.


=== OUTPUT X ===

## Verdict

**NOT VERIFIED** · **BLOCKING: yes** — one unresolved HIGH defect (an unconditional leak of a field the contract explicitly forbids), plus a MEDIUM breach of the "malformed ids never produce a 500" clause.

**Independence: INDEPENDENT.** The artifact arrived finished, pasted into this conversation. I did not write, draft, or direct any part of it; I only read it. The contract was supplied, so I did not have to re-derive it.

---

## Observable evidence

Facts I can point at in the artifact, not judgments:

- The `SELECT` list contains `i.customer_id` (line 16 of the artifact, between `i.due_date` and `c.name AS customer_name`).
- The success path is `return res.json(invoice)` — the raw row object, unmapped. There is no DTO projection, no field pick, no serializer between the query result and the response body.
- The id guard is `Number.isInteger(id) && id > 0`. `Number.isInteger` returns `true` for float-encoded large integers such as `1e30`, and `Number("1e30") === 1e30`.
- Both 404 paths are literally the same statement (`if (!invoice)`), same status, same body. There is only one `!invoice` branch, so an other-org invoice and a nonexistent invoice are indistinguishable by construction.
- The tenant predicate `i.org_id = $2` is bound to `req.user.org_id` — server-side session state, never a request parameter. No user-controllable path into the org filter exists.
- The query is fully parameterized (`$1`, `$2`); no string concatenation of `req.params` into SQL.

---

## Defects

**❌ HIGH — `customer_id` is returned on every successful response. The contract names it in the must-not-leak list.**

The contract's DTO is exactly `{ id, number, amount_cents, status, due_date, customer_name }`, and it separately enumerates `customer_id` as a field that must not leave the server. The code selects `customer_id` (it is needed for the join predicate in the `WHERE`/`ON` clauses — except it is *not*, the join already references `i.customer_id` directly) and then hands the entire row to `res.json`. This is not conditional, not an edge case, and not dependent on data: it happens on 100% of 200 responses.

*How to demonstrate it:* `GET /api/invoices/<any id in your own org>` with a valid session. Assert the response body's key set. Expected `['id','number','amount_cents','status','due_date','customer_name']`; actual includes `customer_id`. A single `expect(Object.keys(res.body).sort()).toEqual([...])` test fails today.

*Why the comment misleads:* the header comment says "Returns one invoice plus its customer's name," which is true of intent and false of the bytes on the wire. The shape of this defect — a `SELECT` list that drifted past the DTO, with no projection layer to catch it — is the one that recurs, because the next field someone adds to the query (`c.email` for a notification feature, `i.payment_token` for a debug session) also ships automatically. The defect is the missing projection, not just the one column.

**❌ MEDIUM — A malformed id produces a 500, which the contract forbids by name.**

`Number.isInteger(1e30)` is `true` and `1e30 > 0` is `true`, so `GET /api/invoices/1e30` passes the guard untouched. The value then reaches the driver, which stringifies a JS number as `"1e+30"`, and Postgres rejects that with `invalid input syntax for type bigint` (`22P02`). That throws inside the `try`, lands in the `catch`, and returns **500**. The same class of failure hits any `int4` id column at `2147483648` and above, where Postgres raises `numeric_value_out_of_range` (`22003`) instead. Either column type, same outcome.

*How to demonstrate it:* `GET /api/invoices/1e30` → expect 400 (or 404), observe 500, with a `Failed to fetch invoice` line in the error log. `GET /api/invoices/99999999999` reproduces it against an `int4` column. The guard is checking that the value is *an integer*; the contract needs it to be *an id*, and those diverge exactly where `Number` switches to exponent notation.

**⚠️ WEAK — The inner `JOIN customers` can 404 an invoice the caller is entitled to see.**

If an invoice in the caller's org has a `customer_id` that is null, dangling, or points at a row whose `org_id` differs (a bad backfill, a customer merge, a soft-deleted customer), the join yields no row and the caller gets 404 for an invoice that exists and belongs to them. The contract says such an invoice is returned. Whether this is reachable depends on schema constraints I was not given, which is why it is weak rather than a defect — see Confirm-these.

**⚠️ WEAK — No `Cache-Control: no-store` on a per-tenant authorized resource.**

Express sets no cache headers here. Any intermediary or browser cache keyed on URL alone can serve org A's invoice body for `/api/invoices/42` to org B. This is outside the contract's letter, which speaks about fields rather than transport, so I am not failing the artifact on it, but it is the cheapest remaining hole on a tenant-scoped GET.

**✅ Axes checked and clean** — see "How each clean axis was checked" below for the specific trace on each.

---

## Assessment (judgment, not demonstrated)

- The `1e30` path is judgment about *your* driver and schema, not about the artifact: I traced the JS semantics exactly (that part is observable), and then reasoned about `node-postgres` stringification and Postgres input parsing without running them. If you use a driver that sends numerics in binary, or a string-typed id column, the failure mode shifts, but the guard is still the wrong guard. Confirm by running the request.
- My read is that the single most damaging defect is not the leaked column but the **absence of a projection step**. The leak is the symptom that happens to be visible today. With `res.json(invoice)` returning whatever the query selected, the contract's must-not-leak list is enforced only by the discipline of whoever edits the `SELECT` next, and that is not enforcement.
- I judge the authorization design itself to be correct and, notably, well-built: org scoping in the `WHERE` rather than in a post-fetch `if`, the customer join constrained to the invoice's own org, and one shared 404 branch. Those are the parts that usually break, and they did not.

---

## Claimed vs. actual

| Claim (in the artifact's own comments) | Actual |
|---|---|
| "Reject anything that isn't a positive integer before it reaches the DB" | Rejects non-integers and non-positives. Accepts `1e30`, `0x10`, `" 12 "`, and any value above the id column's range — all reach the DB. |
| "Returns one invoice plus its customer's name" | Returns that, plus `customer_id`, which the contract forbids. |
| "customer must be in the same org as the invoice" | True, and correctly placed in the `ON` clause. This one holds. |
| "callers can't probe which IDs exist" | Holds for the 404 pair. Does *not* hold across the 400/404/500 boundary: `1e30` returning 500 while `1` returns 404 is a distinguishable response class, though it reveals nothing about which ids exist. |

---

## Confirm-these

Each of these is an axis I could not close from the material given. None of them changes the NOT VERIFIED verdict, which already rests on two defects I can demonstrate.

1. **What `requireSession()` actually guarantees.** If it only attaches `req.user` when a session exists and calls `next()` regardless, then an unauthenticated request makes `req.user.org_id` throw a `TypeError` inside the `try`, and the `catch` then dereferences `req.user.id` for the log line — throwing a second time, outside any handler, which is a different and worse failure than a 500. If it hard-rejects, none of this is reachable. Security-critical; confirm first.
2. **Whether `req.user.org_id` can ever be undefined for a valid session** (a user not yet assigned to an org, an admin/impersonation session, a service token). `undefined` binds as `NULL`, `i.org_id = NULL` matches nothing, so it fails closed to 404 — which is the right direction, but confirm there is no separate code path that treats a missing org as "all orgs".
3. **The id column's SQL type** (`int4` vs `int8` vs `uuid`/text). It sets which input triggers defect 2 and at what threshold. If ids are UUIDs, the entire `Number()` guard is wrong in a much larger way than described here.
4. **Schema constraints on `invoices.customer_id`** — `NOT NULL`, FK to `customers(id)`, and whether an invoice/customer org mismatch is prevented by constraint. This decides whether the weak JOIN finding is dead code or a live 404 bug.
5. **Whether `logger.error` serializes the full `err`,** and whether your Postgres error payloads can carry row values (constraint violation details sometimes do). If logs are lower-trust than the DB, that is a second leak path the contract's "nothing else leaves the server" clause arguably covers.

---

## How each clean axis was checked

- **SQL injection:** `id` is coerced by `Number()` and never interpolated; both values pass through the `[id, req.user.org_id]` parameter array to `$1`/`$2`. No template literal contains a request value. Clean.
- **IDOR / cross-tenant read:** the tenant predicate is `AND i.org_id = $2` inside the same `WHERE` as the id lookup, bound from `req.user.org_id`, which no request input can reach. A row for another org cannot be returned, because it cannot be selected. Clean.
- **Cross-tenant read via the join:** `ON c.id = i.customer_id AND c.org_id = i.org_id` constrains the customer to the invoice's org, and the invoice is already constrained to the caller's org, so `customer_name` is transitively caller-org-only. Clean.
- **404 indistinguishability:** there is exactly one `if (!invoice)` branch producing `404 {"error":"Invoice not found"}`. A missing row and a foreign row both arrive there as `null` from `oneOrNone`. Identical status and identical body by construction, not by two branches that happen to match. Clean.
- **Forbidden fields `email`, `tax_id`, `payment_token`, `portal_password_hash`, `org_id`:** none appears in the `SELECT` list; the only `customers` column selected is `c.name AS customer_name`. Clean. (`customer_id`, the sixth name on that list, is not — that is the HIGH defect.)
- **Non-numeric and empty malformed ids:** `Number("abc")` and `Number("")` give `NaN` and `0`; `Number.isInteger(NaN)` is `false` and `0 > 0` is `false`. Both return 400 before the `try`. No 500 on this subclass. Clean. (The exponent-notation subclass is not — that is the MEDIUM defect.)
- **Unhandled rejection from the DB call:** the `await db.oneOrNone` sits inside `try`, and the `catch` returns a response on every path, so a driver-level failure cannot hang the request or crash the process. Clean.

---

### One line for the builder

Project the row into the DTO explicitly (drop `customer_id` from the `SELECT`, and map the result rather than returning it), and validate the id with `/^\d{1,18}$/` on the raw string before `Number()`, so an out-of-range or exponent-notation id becomes a 400 instead of a 500.


=== OUTPUT Y ===

## Verdict

**NOT VERIFIED. BLOCKING: yes** (one HIGH contract breach that fires on every successful response, plus a 500 path the contract explicitly forbids).

**Independence:** INDEPENDENT. The artifact arrived finished in your message; I did not write, draft, or revise it, and no producer notes were in view. Reading it here is not producing it.

---

## Defects, worst first

**❌ HIGH — `customer_id` is returned to the client. Named in the contract's forbidden list.**
The SELECT list includes `i.customer_id`, and the handler does `res.json(invoice)` on the raw row with no DTO mapping or field allowlist. Every 200 response carries a seventh field the contract says must not leave the server.
*Demonstrate:* `GET /api/invoices/<any id you own>` and read the body. It is `{id, number, amount_cents, status, due_date, customer_id, customer_name}`. The contract's InvoiceDTO has six fields and lists `customer_id` by name under "nothing else leaves the server."
*Note the shape of the bug, not just the field:* the column is only there to satisfy the JOIN, which already has `i.customer_id` available server-side. It is in the projection by accident, and the response is the row rather than a mapped object, so the next column anyone adds leaks the same way.

**❌ MEDIUM — A malformed id produces a 500, which the contract forbids.**
`Number.isInteger()` is true for integer-*valued* floats of any magnitude, so the guard passes values no integer column can hold. They reach Postgres and raise a driver error, which the catch converts to 500.
*Demonstrate:* `GET /api/invoices/99999999999999999999`. `Number(...)` is `1e20`, `Number.isInteger(1e20) === true`, `1e20 > 0`, so the guard is satisfied and `$1` is bound. Postgres then fails on the cast (`22003 numeric_value_out_of_range` against int4/int8, or `22P02 invalid_text_representation` once JS stringifies at or above `1e21` as `"1e+21"`). Either path lands in the `catch` and returns `500`. The contract clause is "Malformed ids never produce a 500," and this is the id class the guard was written to stop.

**❌ MEDIUM — The inner JOIN turns a data-integrity gap into a 404 for an invoice the caller does own.**
`JOIN customers c ON c.id = i.customer_id AND c.org_id = i.org_id` is required, not optional. If `i.customer_id` is NULL, or the customer row was hard-deleted, or the customer legitimately sits in a different org, the row drops out of the result and `oneOrNone` returns null. The caller gets "Invoice not found" for an invoice that exists in their organization.
*Demonstrate:* `UPDATE invoices SET customer_id = NULL WHERE id = $own_id` (or delete the customer row), then `GET /api/invoices/$own_id` returns 404. The contract obligates the endpoint to return invoices that belong to the caller's org; it does not make visibility conditional on customer-row health. The org-equality predicate on the customer is a good instinct, but it belongs on a LEFT JOIN with the name nulled, not on the invoice's existence.

**⚠️ LOW — The input guard does not do what its comment claims, though authorization still holds.**
The comment says "Reject anything that isn't a positive integer." `Number()` accepts hex, exponent, signed, decimal-zero, and whitespace-padded forms: `0x10` → 16, `1e3` → 1000, `+7` → 7, `7.0` → 7, `"  7  "` → 7. So one invoice is addressable under many spellings. No authz consequence, because `i.org_id = $2` still runs on whatever integer comes out. Noted as a nitpick with a false comment attached, not a gate.

---

## Axes checked clean, and how

- **✅ SQL injection.** Both values are bound parameters (`$1`, `$2`), and `id` is a JS number before it is bound. No string concatenation anywhere in the template.
- **✅ Cross-org invoice read (IDOR).** `WHERE i.id = $1 AND i.org_id = $2` with `$2` bound to `req.user.org_id`, not to anything client-supplied. The org is never taken from the request body, query, or a header.
- **✅ 404 indistinguishability.** There is exactly one not-found exit: `if (!invoice) return res.status(404)...`. A nonexistent id and a foreign-org id both fall out of the same `oneOrNone` null and return the byte-identical body `{"error":"Invoice not found"}`. No branch distinguishes them.
- **✅ The named secret fields are absent from the projection.** The SELECT enumerates columns explicitly; `email`, `tax_id`, `payment_token`, `portal_password_hash`, and `org_id` appear nowhere in it. `org_id` is referenced only in predicates, never projected. This is why `customer_id` is the sole leak rather than one of several.
- **✅ Log line carries no PII.** `logger.error` receives the error, a numeric `invoiceId`, and `req.user.id`. No customer name, no email, no token.
- **✅ Error response body does not leak internals.** The 500 returns a fixed string, not `err.message`.

---

## Claimed vs. actual

| The artifact's comment says | What the code does |
|---|---|
| "Reject anything that isn't a positive integer before it reaches the DB" | Accepts `0x10`, `1e3`, `+7`, `7.0`, padded whitespace, and any integer-valued float up to `Infinity`, including magnitudes that make the DB throw |
| "Returns one invoice plus its customer's name" | Returns the customer's name **and** the customer's id |
| "A missing invoice and another org's invoice both return 404" | True, and correctly implemented. It also silently returns 404 for a present, owned invoice whose customer row is missing |

---

## Confirm these before trusting anything above as complete

1. **`requireSession()` is not shown, and the catch block depends on it.** If that middleware can ever let a request through with `req.user` unset (anonymous fall-through, expired session tolerated, a misconfigured mount), then `req.user.org_id` throws a TypeError inside the `try`, control reaches the `catch`, and the `catch` **itself** dereferences `req.user.id` and throws again. That second throw escapes the async handler, no response is ever sent, and in Express 4 it is not forwarded to error middleware. The request hangs and the rejection is unhandled. Read `requireSession` before you call this axis clean; the error handler assumes the thing that might be missing.
2. **`customers.id` uniqueness.** `oneOrNone` throws when the query returns more than one row. If `customers.id` is not a primary key or unique index, a duplicate customer id yields a 500 on a legitimate request. I cannot see the schema.
3. **The column type of `invoices.id`.** It changes which Postgres error the big-id case raises, not whether it 500s, but confirm it is not something exotic that swallows the overflow.
4. **Whether an outer error-handling middleware exists** that would catch what escapes in item 1.
5. **Whether `invoices.customer_id` is nullable**, which decides whether the JOIN defect is theoretical or live in your data today.

---

## Assessment (my judgment, not demonstrated)

The security thinking here is above average: the org predicate is on the invoice row where it belongs, the double-scoping of the customer to the invoice's org is a real defense against a mismatched-tenant join, and the single 404 exit is deliberate and correct. The failures are all of one kind, which is worth naming: **the handler trusts its own shapes.** It trusts that a row is a DTO, that `Number.isInteger` means "fits in an integer column," and that `req.user` exists at the moment the error handler runs. Two of those three are demonstrable today.

The single most damaging defect is the first one, and it is not subtle: the endpoint ships a field the contract names as forbidden, on every success, because the row was handed to `res.json` instead of being mapped. Fix that with an explicit projection into the six DTO fields, and the same edit removes `i.customer_id` from the SELECT.

I verify; I do not fix. These go back to a builder.


=== OUTPUT Z ===

No repo context was available for this artifact (it's a standalone snippet) and sandboxed execution was declined, so this is a read-only trace of the code against the four contract clauses.

---

**Verdict** — NOT VERIFIED. **BLOCKING: yes** (one confirmed HIGH: a forbidden field is returned on the success path).

**Independence** — INDEPENDENT. I did not write, plan, or edit this handler; I received it as finished text and traced it against a contract I also did not author.

---

**Observable evidence**

- ❌ **`customer_id` is returned to the client.** The SELECT list contains `i.customer_id`, and the success path is `return res.json(invoice)` — the whole row object, unmapped. The contract names `customer_id` in its explicit deny list. This is directly readable in the artifact; no runtime needed.
- ✅ All six required DTO fields are present in the SELECT: `i.id`, `i.number`, `i.amount_cents`, `i.status`, `i.due_date`, `c.name AS customer_name`.
- ✅ No forbidden *customer* column is selected: the customers table contributes only `c.name`. `email`, `tax_id`, `payment_token`, `portal_password_hash` never enter the projection, and `org_id` is used only in predicates (`c.org_id = i.org_id`, `i.org_id = $2`), never selected.
- ✅ Cross-org and nonexistent collapse to one response. `i.org_id = $2` is in the same WHERE as `i.id = $1`, so both cases produce zero rows → `oneOrNone` returns null → the single `if (!invoice)` branch returns 404 with a fixed body. There is no second branch and no distinguishing message.
- ✅ The error path leaks nothing: the 500 body is a constant string; `err` goes to `logger`, not to `res`.
- ⚠️ **Malformed ids can reach the DB and 500.** `Number.isInteger(1e20) === true` and `1e20 > 0`, so `/api/invoices/99999999999999999999` passes the guard and is bound as `$1`. Against an `integer`/`bigint` column Postgres raises an out-of-range error, which lands in `catch` → 500. The contract says malformed ids never produce a 500.
- No test run, build, or endpoint invocation was performed or supplied.

---

**Assessment** (judgment, not demonstrated)

The guard's intent — "positive integer only" — is right, but `Number()` is the wrong instrument for it: it accepts scientific notation (`1e3` → invoice 1000), hex (`0x10` → 16), and surrounding whitespace (`%2012` → 12), so several distinct URLs alias to the same record. None of those is a confinement breach (org scoping still applies), but they are contract drift and they are what lets the out-of-range case through. A regex-first check (`/^\d{1,9}$/` on the raw string) closes the whole family at once. I'd also judge the single `res.json(row)` pattern as the root cause of the `customer_id` leak rather than an isolated slip: with no explicit DTO mapping, any future column added to the SELECT ships to clients automatically.

---

**Defects** (worst first)

1. ❌ **HIGH — `customer_id` leaves the server.** The contract's "nothing else … (no … `customer_id`)" clause is breached on every successful request. *Demonstrate:* `GET /api/invoices/<own-org id>` with a valid session; the 200 body contains a `customer_id` key alongside the six DTO fields. *Fix:* drop `i.customer_id` from the SELECT (nothing downstream uses it — the join already has the value), or map explicitly into the DTO before `res.json`.
2. ❌ **MEDIUM — numeric-but-out-of-range id yields 500.** "Malformed ids never produce a 500" fails for integer-valued floats beyond the column's range. *Demonstrate:* `GET /api/invoices/99999999999999999999` → guard passes (`Number.isInteger(1e20)` is `true`) → Postgres raises `22003`/out-of-range → `catch` → 500. Verdict PLAUSIBLE rather than CONFIRMED only because it depends on the id column's type, which the artifact doesn't show; on `int4` or `int8` it fires.
3. ⚠️ **LOW — the inner JOIN can hide a legitimately-owned invoice.** If `i.customer_id` is NULL or points at a row that's missing or org-mismatched, the JOIN drops the invoice and the caller gets 404 for a record the contract says they should see. The `c.org_id = i.org_id` predicate is correct as a tenancy check; the exposure is the join being inner. Data-dependent — harmless if `customer_id` is `NOT NULL` with an FK, which I can't see.
4. ⚠️ **LOW — id aliasing.** `1e3`, `0x3e8`, `%201000`, and `1000` all resolve to invoice 1000. No confinement impact; it widens the accepted input surface past "positive integer" and is the same root cause as defect 2.

---

**Claimed vs. actual**

- Comment: *"Reject anything that isn't a positive integer before it reaches the DB."* Actual: rejects anything `Number()` can't turn into a positive integer-valued float. `1e20`, `0x10`, and whitespace-padded values are not rejected, and `1e20` is precisely what reaches the DB and 500s.
- Header comment: *"Returns one invoice plus its customer's name."* Actual: returns one invoice, its customer's name, **and its `customer_id`**.
- Comment: *"A missing invoice and another org's invoice both return 404."* Accurate — this one holds exactly as written.

---

**Confirm-these** (each is why this isn't a clean read)

- **`requireSession()` actually authenticates and populates `req.user.org_id`.** Not shown. If it can pass through with `org_id` undefined, node-postgres binds `undefined` as NULL, `i.org_id = NULL` matches nothing, and the result is a blanket 404 — fail-closed, but confirm it isn't fail-open.
- **The type of `invoices.id`.** Determines whether defect 2 is CONFIRMED or moot.
- **Nullability/FK on `invoices.customer_id`.** Determines whether defect 3 is reachable.
- **No response-shaping middleware downstream** (a serializer or `res.json` override that strips fields). If one exists it could mask defect 1 — but relying on it would make the leak one middleware change away from returning.
- **`db.oneOrNone` semantics.** I read it as pg-promise: null on zero rows, throws on >1. The 404 path depends on the null-on-zero half; with `i.id` as PK the >1 half can't fire.

---

**How each clean axis was checked**

- *Required fields present:* counted the six contract names against the SELECT list — `i.id`, `i.number`, `i.amount_cents`, `i.status`, `i.due_date`, `c.name AS customer_name`; the alias supplies `customer_name` under the contract's spelling.
- *No customer PII in the projection:* the customers table appears exactly twice — `c.name AS customer_name` (selected) and `c.org_id = i.org_id` (predicate only). `email`, `tax_id`, `payment_token`, `portal_password_hash` appear nowhere in the file.
- *No `org_id` in the response:* both `org_id` references sit in `ON`/`WHERE` clauses, outside the SELECT list, so neither reaches the returned row.
- *Same 404 for cross-org and nonexistent:* both conditions are ANDed into one WHERE, so both yield zero rows → `oneOrNone` → null → the single `if (!invoice)` at the one 404 return, body `{ error: 'Invoice not found' }` with no variant text or timing branch.
- *Error path leaks nothing:* the 500 response body is the literal `{ error: 'Internal server error' }`; `err` is passed only to `logger.error`.

