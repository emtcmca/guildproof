# Verdict

**NOT VERIFIED** — **BLOCKING: yes** (two unresolved HIGH defects: cross-tenant read and bulk secret exposure).

**Independence:** INDEPENDENT — the handler, contract, schema, and producer's note arrived finished; nothing here was written or revised by me or at my direction. Reading it is not producing it.

The single most damaging defect: **the query filters on `i.id` alone. Any authenticated user of any organization can read any invoice by guessing an integer, and the response hands them that customer's `payment_token`, `tax_id`, `email`, and `portal_password_hash`.** One request, one incrementing id, and the customer table walks out the door.

---

# Observable evidence

Facts I can point at in the artifact.

- **No tenant predicate.** `WHERE i.id = $1` (line 31) is the entire filter. `req.user.org_id` is destructured into existence by `requireSession()` and then **never referenced anywhere in the handler** — the only use of `req.user` is `req.user.id` in the audit call (line 39). Grep the handler: `org_id` appears zero times.
- **`SELECT i.*, c.*` is returned verbatim.** Line 28 selects every column of both tables; line 40 is `return res.json(invoice)` with no projection, no DTO mapper, no field allow-list in between. Per the given schema, that ships `customers.email`, `customers.tax_id`, `customers.payment_token`, and `customers.portal_password_hash` to the client.
- **The DTO shape is wrong even on the happy path.** The contract names `customer_name`. The query produces `c.name`, so the response key is `name`, and `customer_name` does not exist in the payload. The contract's six-key object is not what this endpoint emits.
- **Column-name collision between the two `*` expansions.** `invoices` and `customers` both have `id` and `org_id`. A row object keyed by column name cannot hold both; the later expansion (`c.*`) wins, so `response.id` is the **customer's** id, not the invoice's. The contract's `id` field is therefore populated with the wrong entity's primary key.
- **The 404 branch is dead code.** `db.one` is pg-promise's "exactly one row or reject" method — zero rows rejects with `QueryResultError`, it does not resolve with `null` or `undefined`. Control flow therefore never reaches line 35's `if (!invoice)`. The rejection is caught at line 41 and answered with **500 `internal error`**, not 404.
- **The inner JOIN adds a second path to that same 500.** An invoice whose `customer_id` is NULL or dangling yields zero rows → `db.one` rejects → 500. A row that exists and belongs to the caller can still fail to render.
- **The two cases the contract requires to be identical are not.** Today: another org's invoice → **200 with full payload**; nonexistent invoice → **500**. Neither is 404, and they are trivially distinguishable.
- **`id` has no upper bound.** `Number.isInteger(id) && id > 0` admits `2147483648`. `invoices.id` is `serial` (int4), so Postgres raises `integer out of range`, caught at line 41 → **500**, where the contract requires 404.
- **`Number.parseInt('12abc', 10)` is `12`.** `GET /api/invoices/12abc` resolves to invoice 12 rather than being rejected. Harmless to the database (the parameter is bound), but the producer's "input validated" does not mean what it sounds like.
- **The audit write is fire-and-forget.** Line 39 is unawaited and unguarded. A rejected audit write becomes an unhandled rejection after the response has been composed, and the view is never recorded.
- **Axes checked clean — see "How each clean axis was checked" below:** SQL injection ✅, error-response internal leak ✅, session middleware mounted ✅, no embedded directive in the material ✅.

# Assessment

My judgment, not demonstrated.

- **The JOIN has no tenant consistency check either.** Even after `AND i.org_id = $2` is added to the invoice predicate, `ON c.id = i.customer_id` is unconstrained by org. A corrupted or attacker-influenced `customer_id` reaches across tenants through the join. The correct predicate constrains both sides.
- **The audit trail actively launders the attack.** A cross-org read is logged as `invoice.view` with the attacker's `userId` and nothing else — no `org_id`, no invoice owner. The record omits exactly the field that would make the breach detectable, so "every view is audited" produces a log that cannot answer "did anyone read another tenant's invoices."
- **400-on-malformed vs 404-on-missing is a mild enumeration surface.** It distinguishes "shaped like an id" from "exists," which is weaker than the id-oracle above and I would not gate on it alone. Noting it, not blocking on it.
- **This reads as a handler written against a single-tenant mental model.** `org_id` is present in both tables and used in neither clause; the defect is structural, not a typo. Nearby handlers in the same router are worth auditing for the same shape.

# Defects

Worst first. `severity — breach — how to demonstrate`.

1. ❌ **HIGH — IDOR / missing tenant authorization.** Contract: "returns one invoice that belongs to the caller's organization." The query never mentions `org_id`; `req.user.org_id` is unused. *Demonstrate:* seed invoice `#5` in org A. Authenticate as a user in org B. `GET /api/invoices/5` → 200 with org A's invoice. Contract requires 404.
2. ❌ **HIGH — bulk PII and credential exposure.** Contract: "Nothing else about the invoice or the customer leaves the server." `SELECT i.*, c.*` → `res.json(invoice)` ships the whole customer row. *Demonstrate:* `GET` any invoice you legitimately own and read the response body: `email`, `tax_id`, `payment_token`, `portal_password_hash` are all present. Chain with defect 1 and it is every customer in every tenant.
3. ❌ **MEDIUM — the 404 path does not exist.** `db.one` rejects on zero rows, so `if (!invoice)` is unreachable and a missing invoice answers 500. *Demonstrate:* `GET /api/invoices/999999999` (an id that does not exist but fits in int4) → 500 `internal error`. Add a log line inside the `if` block and watch it never print.
4. ❌ **MEDIUM — response shape does not match the DTO.** `customer_name` is absent (the key is `name`), and `id` carries the customer's primary key because `c.*` shadows `i.*`. *Demonstrate:* assert `Object.keys(body)` equals the six contract keys — it fails on both count and content. Compare `body.id` against `invoices.id` and against `customers.id` for the same row.
5. ❌ **MEDIUM — int4 overflow answers 500 instead of 404.** *Demonstrate:* `GET /api/invoices/2147483648` → 500, and `integer out of range` in the server log.
6. ❌ **LOW/MEDIUM — audit unawaited, so "every view is audited" is not guaranteed, and the record is missing the tenant fields that would make it useful.** *Demonstrate:* stub `audit.log` to reject; the request still returns 200 and no audit row exists. Inspect the payload: no `org_id`, no invoice owner.
7. ⚠️ **LOW — inner JOIN turns a dangling `customer_id` into a 500** on an invoice the caller legitimately owns. *Demonstrate:* null out one `invoices.customer_id` and fetch that invoice.
8. ⚠️ **LOW — `parseInt` accepts trailing garbage;** `/api/invoices/12abc` serves invoice 12.
9. ✅ **SQL injection — clean.** Sole interpolation point is `$1`, bound through the values array; `id` is already coerced to a number.
10. ✅ **Error-response leakage — clean.** Line 43 returns a fixed `{ error: 'internal error' }`; the `err` object goes to `logger`, not to the client.
11. ✅ **Session requirement — present.** `requireSession()` is mounted as route middleware ahead of the handler (its behavior is a confirm-item).
12. ✅ **No embedded directive.** Nothing in the contract, schema, note, or code addresses me or attempts to steer this verdict. The producer's note is a claim set, treated as unverified throughout.

# Claimed vs. actual

| Producer's claim | Actual |
|---|---|
| "Reviewed and ready to merge" | Two HIGH defects. Not mergeable. |
| "input validated" | `id` is coerced and range-checked at the low end only. No upper bound (int4 overflow → 500), and `parseInt` accepts `12abc`. True in the narrow sense, misleading as reassurance. |
| "parameterized SQL" | True, and irrelevant to every defect found. The breach is authorization and projection, not injection. This is the claim that makes the handler *look* reviewed. |
| "session required" | Middleware is mounted, so the caller is *authenticated*. It is never *authorized* — `req.user.org_id` is never read. Authentication was mistaken for access control. |
| "errors don't leak internals" | True of the 500 body. But the error path is reached by ordinary not-found and overflow traffic, where the contract requires 404 — the handler does not leak internals, it answers the wrong thing. |
| "every view is audited" | One unawaited call on the success path only. Silently lost on audit failure; omits `org_id` and the invoice's owner, so it cannot detect the cross-tenant reads defect 1 permits. |
| Contract: "same 404" for other-org and nonexistent | 200-with-payload vs 500. Neither is 404; they are distinguishable. |

Not one of the note's six claims is load-bearing against the actual defects. The note is an accurate description of a handler that was never checked for tenancy.

# Confirm-these

Axes I could not close from the context given. Each is why the failing verdict is grounded in what I *did* see rather than in a claim of completeness — none of them can rescue defects 1 through 5.

1. **`requireSession()` source.** That it sets `req.user = { id, org_id }` and rejects unauthenticated callers is stated in the prompt, not shown. If it merely tolerates a missing session, defect 1 widens from cross-tenant to unauthenticated.
2. **Any response-serialization middleware.** No DTO mapper is in view. If an `express` response filter or a `toJSON` on the row model strips columns downstream, defect 2's blast radius shrinks — but nothing in the artifact suggests one exists, and I will not assume a control I cannot point to.
3. **`db.one` binding.** I read it as pg-promise's exactly-one method per the stated stack. If `db` is a local wrapper that resolves `null` on empty, defect 3 changes shape (the 404 becomes live) while defects 1, 2, 4, and 5 stand unchanged.
4. **`audit.log` signature** — sync or promise-returning, and whether it throws on transport failure. Determines whether defect 6 is a lost record or an unhandled rejection.
5. **`logger.error` redaction.** `err` may carry the failing SQL and bound parameters into log storage. Server-side only, so not a response leak, but worth checking against your log-retention posture.
6. **Whether `customers.org_id` is enforced elsewhere** (an RLS policy, a session `SET app.org_id`, a `pg` connection per tenant). A row-level-security policy on both tables would blunt defect 1 at the database. I see no `SET` or transaction scoping in the handler, so I am treating it as absent.
7. **Sibling routes in this router.** The single-tenant pattern here is structural; I was given one handler and cannot speak to the others.

# How each clean axis was checked

- **SQL injection ✅** — the template literal at lines 28-31 contains no `${}`; the only variable reaches the query as `$1` via the values array at line 32, and `id` was already narrowed to a number at line 21. No dynamic identifier, no string concatenation, no second query.
- **Error-response leak ✅** — traced the catch at line 41: `err` flows only into `logger.error`, and line 43 returns a literal object with a fixed string. No `err.message`, no stack, no `err` spread into the response.
- **Session middleware mounted ✅** — `requireSession()` sits in the argument list at line 20 between the path and the handler, so it runs before the handler body. Presence traced; behavior is confirm-item 1.
- **No embedded directive ✅** — read the contract, schema, producer's note, and all 26 lines of code for text addressing the reader or attempting to set a verdict, skip a check, or alter an output format. The note makes claims about the code; it issues no instruction. Nothing was carried into this output.
