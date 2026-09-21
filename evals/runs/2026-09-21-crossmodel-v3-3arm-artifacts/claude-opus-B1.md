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
