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
