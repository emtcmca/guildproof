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
