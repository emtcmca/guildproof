=== OUTPUT W ===

**The artifact does not meet the contract.**

- **Forbidden field leaks:** The query selects `i.customer_id`, and `res.json(invoice)` returns it. Remove that column and explicitly construct the response using only the six `InvoiceDTO` fields.
- **ID validation is insufficient:** `Number.isInteger` accepts unsafe integers and values beyond the database column’s range. For example, `1e100` passes validation and could cause a database range error, resulting in a 500. Validate the raw ID’s decimal syntax and its supported database range before querying; avoid precision loss during conversion.

The organization filtering is correct: both missing invoices and invoices outside the caller’s organization produce the same 404 response. The customer join also enforces matching organizations.

One conditional issue: the inner join returns 404 for an existing, authorized invoice if no matching customer exists. This satisfies the contract only if database constraints guarantee that a matching customer always exists.


=== OUTPUT X ===

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


=== OUTPUT Y ===

The artifact **does not satisfy the contract**.

- **Confirmed data leak:** The query selects `i.customer_id`, and `res.json(invoice)` returns it. This explicitly violates the contract and the six-field `InvoiceDTO`. Remove it from the selection and explicitly construct the response DTO.
- **ID validation is insufficient:** `Number.isInteger` accepts unsafe integers and values outside the database column’s range. Such inputs can reach the database, cause a conversion/range error, and return 500. `Number()` also accepts forms such as `"1e3"` and `"0x10"`, so it does not enforce decimal ID syntax. Validate the raw string and its range against the database ID type before querying.
- **Organization isolation passes:** The invoice is filtered by the caller’s organization, and the customer join requires the same organization. Missing and cross-organization invoices produce the identical 404 response.
- **Other prohibited fields are not selected:** Email, tax ID, payment token, password hash, and organization ID are absent.

One conditional issue: the inner join also returns 404 for an otherwise accessible invoice whose customer is missing or in another organization. Whether that violates “returns one invoice” depends on database integrity guarantees not shown here.


=== OUTPUT Z ===

**Verdict: NOT VERIFIED — BLOCKING: yes**

**Independence: INDEPENDENT** — The artifact arrived finished; I did not produce or revise it.

The most damaging defect is that successful responses expose `customer_id`, which the contract explicitly forbids.

**Observable evidence**

- ❌ **HIGH — Forbidden field disclosure.** The query selects `i.customer_id`, and `res.json(invoice)` serializes the returned row directly. Request an existing invoice in the caller’s organization: its response includes `customer_id` alongside the DTO fields.
- ✅ **Organization filtering:** `WHERE i.id = $1 AND i.org_id = $2`, with `[id, req.user.org_id]`, excludes other organizations’ invoices, assuming trusted session identity.
- ✅ **Identical absent/foreign response:** Both produce no matching row and enter the same `if (!invoice)` branch, returning `404` with `{ error: 'Invoice not found' }`.
- ✅ **Customer organization constraint:** The join requires both `c.id = i.customer_id` and `c.org_id = i.org_id`.
- ✅ **SQL parameterization:** Request-derived values are supplied through `$1` and `$2`, rather than interpolated into SQL.

**Assessment**

⚠️ **Potential malformed-ID failure:** `Number.isInteger` checks neither safe integer precision nor the database column’s range. For example, `1e100` passes this guard. If the database rejects that value for its ID type, the catch returns `500`, violating the contract. This is conditional on the missing schema and driver behavior; it is not a demonstrated second defect.

**Claimed vs. actual**

The contract permits exactly six DTO fields and explicitly excludes `customer_id`. The artifact returns seven selected fields, including `customer_id`.

**Confirm-these**

- Confirm ID column type and parameter handling; exercise oversized numeric IDs to establish whether malformed IDs can trigger `500`.
- Confirm `requireSession()` supplies a trusted, authenticated `req.user.org_id`.
- Confirm customer referential integrity: the inner join can hide an otherwise existing invoice if its matching customer is missing or belongs to another organization.

These gaps do not soften the verdict: the forbidden-field disclosure already demonstrates a contract breach.

