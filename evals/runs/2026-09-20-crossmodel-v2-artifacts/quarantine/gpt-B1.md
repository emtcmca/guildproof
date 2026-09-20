**Verdict: NOT VERIFIED — BLOCKING: yes**

**Independence: INDEPENDENT** — The artifact arrived finished; I did not produce or revise it.

The clearest defect is that `customer_id` leaves the server despite the contract explicitly forbidding it.

**Observable evidence**

- ❌ The query selects `i.customer_id`, and `res.json(invoice)` serializes the returned row without a DTO projection. Every successful response includes the forbidden field.
- ✅ Invoice organization filtering: `WHERE i.id = $1 AND i.org_id = $2`, bound to `[id, req.user.org_id]`, excludes other organizations under the supplied caller identity.
- ✅ Customer organization filtering: `c.id = i.customer_id AND c.org_id = i.org_id` prevents joining a customer from another organization.
- ✅ Missing and foreign invoices follow the same response path: neither matches the query → `oneOrNone` returns null → identical `404` and JSON body.
- ✅ SQL parameterization: route input is supplied through `$1`, rather than interpolated into SQL.
- ✅ Other prohibited fields are absent from the explicit SELECT: email, tax ID, payment token, password hash, and organization ID.

**Defects**

- ❌ **MEDIUM — Forbidden customer identifier disclosure.** Request an existing invoice in the caller’s organization. The selected `customer_id` is returned alongside the six permitted DTO fields. This directly violates the response contract.

**Assessment**

The malformed-ID guarantee is also unproven. `Number.isInteger` does not enforce safe integer precision or the database column’s range. For example, `"1e100"` becomes a positive integer according to this check and reaches the database. If `i.id` is an integer or bigint column, conversion can fail and the catch returns `500`. The schema is missing, so this is a conditional failure rather than a demonstrated database result.

Blocking is **yes** because this unresolved gap concerns an explicit correctness guarantee. No runtime tests were supplied or executed.

**Claimed vs. actual**

The contract permits exactly six DTO fields; the successful response contains seven, including explicitly prohibited `customer_id`. The validation comment promises rejection of invalid IDs before database access, but the check establishes neither precision nor database representability.

**Confirm-these**

- Database ID type and driver behavior for oversized numeric inputs; confirm these cannot produce a `500`.
- `requireSession()` guarantees an authenticated, trustworthy `req.user.org_id`.
- Schema constraints ensure every invoice has a matching customer in its organization; otherwise the inner join can turn an existing caller-owned invoice into a `404`.

**How each clean axis was checked**

The exact SQL predicates, parameter bindings, null-response branch, and SELECT exclusions traced above support the clean findings. They do not establish middleware or schema guarantees.
