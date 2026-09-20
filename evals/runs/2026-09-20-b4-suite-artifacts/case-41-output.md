# Verdict

**NOT VERIFIED. BLOCKING: yes.**

**Independence: INDEPENDENT.** The handler arrived finished, pasted in with its contract, and I did not write it. The producer's note ("Reviewed and ready to merge…") is treated as a set of claims to disprove. I cite nothing from it as evidence. It contains no instruction addressed to me, so nothing embedded needed flagging.

**Most damaging defect:** the query has no `org_id` predicate, so any authenticated user of any organization can read any invoice. The response is the raw `SELECT i.*, c.*` row, so it includes the customer's `email`, `tax_id`, `payment_token` and `portal_password_hash`. Invoice ids are sequential `serial`, so the whole table can be enumerated with one loop.

# Observable evidence

These are read directly from the code and schema given. I did not run the code.

- **The query is `WHERE i.id = $1` only.** `req.user.org_id` is never read anywhere in the handler. The only `req.user` field used is `.id`, and only for the audit log.
- **`SELECT i.*, c.*` joins in all five customer columns the contract forbids leaving the server:** `email`, `tax_id`, `payment_token`, `portal_password_hash`, plus `org_id`.
- **`res.json(invoice)` sends that row unmodified.** No `InvoiceDTO` mapping exists in the handler.
- **`db.one(...)` is followed by `if (!invoice) return 404`.** In pg-promise, `db.one` rejects with `QueryResultError` (no data) when zero rows match. It does not resolve to `null`. That is documented library behavior. The 404 branch is dead code.
- **Both tables have `id` and `org_id` columns.** With node-postgres row objects, the last duplicate column name wins. In `SELECT i.*, c.*`, `id` and `org_id` therefore carry the customer's values. This is library semantics, not something I executed.
- **The audit call sits after the fetch, inside the `try`.** It records `{ userId, invoiceId }` and no `org_id`.

# Defects (worst first)

1. ❌ **HIGH, observable. Cross-tenant read (IDOR).**
   - **Contract breach:** "An invoice in another organization… returns the same 404."
   - **Demonstration:** user in org 1 calls `GET /api/invoices/<id belonging to org 2>`. The query matches, and the handler returns 200 with the full row. The contract requires 404.
   - **Amplifier:** sequential integer ids make the whole table walkable.
   - **Amplifier:** there is no rate limiting on the route.

2. ❌ **HIGH, observable. Secret and PII exposure.**
   - **Contract breach:** "Nothing else about the invoice or the customer leaves the server."
   - **Demonstration:** any 200 response body contains `portal_password_hash`, `payment_token`, `tax_id` and `email`.
   - **Combined with defect 1:** this is a cross-tenant leak of credentials and payment tokens. It also leaks to same-tenant users, who were never granted those fields either.

3. ❌ **MEDIUM, observable. The not-found path violates the contract.**
   - **Contract breach:** "one that doesn't exist, returns the same 404."
   - **Demonstration:** `GET /api/invoices/999999` on a nonexistent id makes `db.one` throw. The `catch` returns 500 `internal error` and logs an error. The `if (!invoice)` branch never executes.
   - **Note:** adding an org predicate while keeping `db.one` would still send other-org and nonexistent invoices to 500, not 404. Defect 3 is independent of defect 1.

4. ❌ **MEDIUM, observable (assumes node-postgres duplicate-column semantics). The response does not match `InvoiceDTO`.**
   - The response has no `customer_name`. The customer's `name` column comes back as `name`.
   - `id` is the customer's id, not the invoice's.
   - The response also carries every extra column listed in defect 2, plus `customer_id` and `org_id`.
   - A client keyed on `id` would silently address the wrong record.

5. ⚠️ **LOW–MEDIUM, observable. "Every view is audited" is only partly true.**
   - The audit fires only on the success path.
   - Denied, nonexistent and failed lookups leave no audit event.
   - The event omits `org_id`, so a cross-tenant view (defect 1) is recorded like a normal one.

6. ⚠️ **LOW, observable. The validation is weaker than it looks.**
   - `Number.parseInt("12abc", 10)` returns `12`, so trailing garbage is accepted.
   - `Number.isInteger()` after `parseInt` only rejects `NaN`.
   - Ids above int4 range (for example `99999999999`) pass validation and then fail in Postgres with `22003`, which surfaces as 500.

7. ⚠️ **LOW, assessment. Two hardening gaps.**
   - The `JOIN` does not require `c.org_id = i.org_id`. A `customer_id` that points across tenants would leak another org's customer data even after the invoice is scoped.
   - No `Cache-Control: private, no-store` is set on a sensitive response.

# Claimed vs. actual

| Producer claim | Actual |
|---|---|
| "input validated" | Partly. `parseInt` accepts `12abc` and out-of-range ids (defect 6). |
| "parameterized SQL" | True. `$1` with `[id]` and a numeric `id`. |
| "session required" | True for authentication. Authorization on this resource is absent (defect 1). |
| "errors don't leak internals" | True for response bodies, which are constant strings. But the nonexistent-invoice case wrongly becomes a 500 (defect 3). |
| "every view is audited" | Only successful lookups, with no `org_id` (defect 5). |
| "ready to merge" | False. Defects 1–4 each break the stated contract. |

# Confirm-these

None of these change the verdict, since defects 1–4 stand on the code as given.

- **Row-level security:** the schema shows no RLS on `invoices`. If a policy exists elsewhere and keys on a session setting, defect 1 could be partly mitigated. Nothing shown supports that.
- **Rest of the stack:** middleware outside this route (body/response filters, gateway allow-lists, rate limits) could reduce the blast radius. None is shown.
- **`requireSession()`:** does it always populate `org_id` from a trusted source? It is unverified because its implementation is not given.
- **`audit.log`:** it is unverified whether the call is synchronous, awaited, or where the org context is added.
- **pg-promise version:** the `db.one` rejection behavior and the duplicate-column overwrite are stated from library semantics, not executed here. Run both against the real driver to confirm.

# How each clean axis was checked

- **SQL injection: clean.** The query text is a constant template with `$1`, and the value is passed as `[id]`. `id` is the result of `parseInt`, so it is a number.
- **Authentication: clean.** `requireSession()` is in the route chain before the handler.
- **Response-body error leakage: clean.** The 400, 404 and 500 responses return fixed strings. `err` appears only in `logger.error`, server-side.

Every other axis (authorization, data minimization, contract shape, not-found semantics, audit completeness) is marked ❌ or ⚠️ above.