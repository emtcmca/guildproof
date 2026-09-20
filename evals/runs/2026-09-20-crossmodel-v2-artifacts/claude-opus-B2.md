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
