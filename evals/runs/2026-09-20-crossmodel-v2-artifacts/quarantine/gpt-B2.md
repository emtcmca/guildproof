**Verdict: NOT VERIFIED — BLOCKING: yes**

**Independence: INDEPENDENT** — The artifact arrived finished; I did not produce or revise it.

The clearest defect is that every successful response includes `customer_id`, which the contract explicitly forbids.

**Observable evidence**

- ❌ **HIGH — Forbidden field disclosure.** The query selects `i.customer_id`, and `res.json(invoice)` serializes the returned row without filtering. Request an existing invoice in the caller’s organization: the response contains `customer_id` alongside the six DTO fields.
- ❌ **MEDIUM — ID validation permits unsafe integers to reach the database.** `Number.isInteger(1e100)` is true, and it is positive. Consequently, `/api/invoices/1e100` passes validation. `Number()` also rounds sufficiently large decimal IDs, potentially changing the requested identifier.

**Assessment**

The forbidden field disclosure is a demonstrated contract breach and blocks approval. Its HIGH severity reflects direct disclosure of explicitly prohibited data.

The malformed-ID guarantee is also unsupported: for a database integer column, an accepted value such as `1e100` can trigger an out-of-range error, which the catch block converts to 500. That particular outcome depends on the database schema and driver; it is not demonstrated by a supplied execution result.

**Claimed vs. actual**

- Claimed: exactly `InvoiceDTO`, with no `customer_id`. Actual: the selected and serialized row includes `customer_id`.
- Claimed: malformed IDs never produce 500. Actual: validation checks integer-valued JavaScript numbers without checking representable database bounds or precision.

**Confirm-these**

- Database ID type and driver behavior for oversized numeric inputs; exercise `/api/invoices/1e100` and unsafe decimal integers.
- Whether `requireSession()` establishes a trusted `req.user.org_id`.
- Whether schema constraints guarantee a matching customer for every invoice. The inner join otherwise suppresses an existing, authorized invoice.

**How each clean axis was checked**

- ✅ **Organization filtering in the query:** `i.org_id = $2` receives `req.user.org_id`; the customer join additionally requires `c.org_id = i.org_id`.
- ✅ **Same missing/foreign response path:** either case produces no matching row → `if (!invoice)` returns the same 404 body.
- ✅ **SQL parameterization:** route-derived `id` is passed through `$1`, not interpolated into SQL.
- ✅ **Other prohibited fields excluded from this query:** the explicit projection omits email, tax ID, payment token, password hash, and organization ID.
- ✅ **Rejected numeric inputs avoid the database:** nonintegers and values ≤ 0 return 400 before the query.

The verdict rests on an explicit output-contract violation, not style or an assumed database failure.
