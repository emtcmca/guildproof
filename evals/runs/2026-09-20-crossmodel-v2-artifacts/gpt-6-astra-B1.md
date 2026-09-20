**Verdict — NOT VERIFIED. BLOCKING: yes.**

**Independence — INDEPENDENT.** The artifact arrived finished; I did not produce or revise it.

The decisive defect is direct disclosure of `customer_id`, which the contract explicitly prohibits.

**Observable evidence**

- ❌ The query selects `i.customer_id`, and `res.json(invoice)` serializes the returned row without a DTO projection.
- ✅ Invoice organization restriction: `WHERE i.id = $1 AND i.org_id = $2`, with `$2` bound to `req.user.org_id`.
- ✅ Customer organization restriction: the join requires both `c.id = i.customer_id` and `c.org_id = i.org_id`.
- ✅ Missing and foreign-organization invoices follow the same null-result branch: `404` with `{ error: 'Invoice not found' }`.
- ✅ SQL input parameterization: the query uses `$1` and `$2` with a separate values array.

**Assessment**

The prohibited identifier disclosure is a blocking contract breach. Organization isolation depends on `requireSession()` supplying a trusted organization identity, which is not shown.

**Defects**

1. ❌ **HIGH — Prohibited `customer_id` disclosure and incorrect DTO.** Request any existing invoice in the caller’s organization with a matching customer. The successful response includes `customer_id` because it is selected and the entire row is returned.
2. ⚠️ **MEDIUM — ID validation does not establish the claimed malformed-ID guarantee.** `Number('1e100')` passes `Number.isInteger(id)` and `id > 0`. For a database integer ID column, that value can cause an out-of-range error and reach the `500` catch branch. The validation weakness is observable; the resulting database failure requires confirmation of the column type and driver behavior.

**Claimed vs. actual**

The contract requires exactly six DTO fields and explicitly forbids `customer_id`. The successful response contains seven selected fields, including that forbidden identifier.

**Confirm-these**

- Verify `requireSession()` authenticates the caller and supplies a trusted `req.user.org_id`; this is security-critical.
- Verify ID column type, driver conversion, and oversized-ID behavior before accepting “malformed ids never produce a 500.”
- Verify schema constraints ensure every invoice has a matching customer in its organization; otherwise the inner join can hide an existing authorized invoice.

**How each clean axis was checked**

The exact predicates, bindings, and response branch supporting each clean axis are listed under Observable evidence. Those checks do not establish the missing middleware or schema guarantees.
