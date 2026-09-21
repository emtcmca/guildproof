**Verdict: NOT VERIFIED**  
**BLOCKING:yes**

**Independence: INDEPENDENT** — The artifact arrived finished; I did not produce or revise it.

The decisive defect is that the successful response includes `customer_id`, which the contract explicitly prohibits.

**Observable evidence / defects**

- ❌ **HIGH — Prohibited field disclosure.** The query selects `i.customer_id`, and `res.json(invoice)` serializes that row without filtering. Requesting an existing invoice in the caller’s organization returns `customer_id` alongside the six DTO fields.
- ⚠️ **Assessment: malformed-ID handling is unconfirmed.** `Number.isInteger` accepts unsafe integers such as `1e100`. That value reaches the database; if it exceeds the database ID type’s range, the catch block returns 500. The schema and driver behavior are missing, so this is a correctness-critical gap, not a demonstrated second defect.

**Claimed vs. actual**

The contract requires exactly six fields and expressly excludes `customer_id`. The implementation selects and returns seven fields.

**How each clean axis was checked**

- ✅ **Organization filtering in the query:** `i.org_id = $2` binds `req.user.org_id`; the customer join additionally requires `c.org_id = i.org_id`.
- ✅ **Same response for missing and filtered-out invoices:** Both yield no row and follow `if (!invoice)` to the identical 404 body.
- ✅ **SQL parameterization:** The ID and organization enter through `$1` and `$2`, not SQL string interpolation.
- ✅ **Other prohibited response fields:** The explicit SELECT omits email, tax ID, payment token, password hash, and organization ID.
- ✅ **Basic invalid-ID rejection:** Nonintegers and nonpositive values return 400 before the database call.

**Confirm-these**

- Database ID type and driver behavior for unsafe or out-of-range integers; verify these cannot produce 500.
- Whether `requireSession()` supplies an authenticated, trusted `req.user.org_id`.
- Whether every invoice has a matching customer in the same organization; otherwise the inner join can hide an existing caller-owned invoice.

**Assessment**

The disclosure alone establishes a contract breach and blocks verification. The missing context does not weaken or excuse that finding.
