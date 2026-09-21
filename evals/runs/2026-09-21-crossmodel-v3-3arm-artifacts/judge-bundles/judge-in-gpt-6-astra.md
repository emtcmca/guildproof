=== OUTPUT U ===

**NOT VERIFIED**

Two contract violations:

- **`customer_id` leaks in successful responses.** The query selects `i.customer_id`, and `res.json(invoice)` returns it. The contract explicitly forbids this field. Remove it from the selection and construct the response using only the six `InvoiceDTO` fields.
- **ID validation can allow malformed IDs to reach the database and produce a 500.** `Number.isInteger` accepts integers outside JavaScript’s safe range, including `1e100`. If the database rejects that value as out of range, the catch block returns 500. `Number()` also accepts noncanonical forms such as `0x10` and `1e3`. Validate the raw string as positive decimal digits and enforce the database ID type’s range before querying.

The organization filter and customer join enforce the stated organization boundaries. Missing and other-organization invoices take the same 404 path. The query does not select the other prohibited fields.

This is a static review of the supplied code; runtime behavior and database types were not provided or tested.


=== OUTPUT V ===

**Verdict: NOT VERIFIED**  
BLOCKING:yes  
**Independence: INDEPENDENT** — The artifact arrived finished; I did not produce it.

The decisive defect is that successful responses expose `customer_id`, which the contract explicitly forbids.

**Observable evidence / defects**

- ❌ **HIGH — Forbidden field disclosure.** The query selects `i.customer_id`, and `res.json(invoice)` serializes the returned row without filtering. Request an existing invoice in the caller’s organization: its response includes `customer_id` alongside the six DTO fields.
- ⚠️ **MEDIUM — ID validation does not enforce a database-safe integer range.** `Number.isInteger` accepts values such as `1e100`. That value reaches the database; if the ID column is a conventional integer type, its conversion can fail and the catch block returns 500. The missing schema prevents confirming that specific failure here.

**Assessment**

The disclosure is a demonstrated contract breach. The malformed-ID guarantee is additionally unconfirmed: JavaScript integer validation alone does not establish compatibility with the database’s accepted ID range.

**Claimed vs. actual**

The contract permits exactly six response fields. The successful response contains seven, including explicitly prohibited `customer_id`.

**How each clean axis was checked**

- ✅ **Organization filtering:** `WHERE i.id = $1 AND i.org_id = $2`, bound to `[id, req.user.org_id]`, excludes other organizations’ invoices, assuming trusted session context.
- ✅ **Customer organization boundary:** `c.id = i.customer_id AND c.org_id = i.org_id` prevents joining a customer from another organization.
- ✅ **Same absent/foreign response:** Both produce no matching row and reach `404 { error: 'Invoice not found' }`.
- ✅ **SQL parameterization:** Request-derived values are passed as `$1` and `$2`, not interpolated into SQL.
- ✅ **Other prohibited fields:** The explicit projection excludes email, tax ID, payment token, password hash, and organization ID.

**Confirm-these**

- Database ID type and behavior for oversized numeric inputs; verify they cannot trigger 500.
- `requireSession()` establishes a trusted `req.user.org_id`.
- Schema guarantees the inner join cannot hide an otherwise valid caller-owned invoice because its customer is missing or belongs to another organization.

These gaps do not soften the verdict: the response-field disclosure already refutes the contract.


=== OUTPUT W ===

**Verdict — NOT VERIFIED**  
BLOCKING:yes — explicit data disclosure and a correctness-critical validation gap.

**Independence — INDEPENDENT** — This review evaluates supplied code; I did not author it.

**Observable evidence**

- The query selects `i.customer_id`, and `res.json(invoice)` returns the query result without filtering.
- The invoice lookup requires `i.org_id = req.user.org_id`; the customer join also requires matching organizations.
- Invalid numeric values and nonpositive integers return 400 before the query.
- `Number.isInteger` does not enforce safe integer precision or the database column’s numeric range.

**Assessment — judgment**

The organization predicates appear correct, assuming `requireSession()` provides a trustworthy organization identity. ID validation cannot establish the promised absence of malformed-ID 500 responses without the database type and accepted ID syntax.

**Defects — worst first**

- ❌ **HIGH — Forbidden `customer_id` disclosure and incorrect DTO shape —** Fetch an existing invoice in the caller’s organization: `i.customer_id` is selected and the whole row is returned. The contract explicitly forbids this field.
- ⚠️ **MEDIUM — ID validation permits values outside typical database integer ranges —** `"1e100"` becomes a positive value for which `Number.isInteger(id)` is true. If the database rejects it as out of range, the catch returns 500. The database-dependent failure remains unconfirmed.
- ✅ **Organization scoping and shared 404 branch —** The query excludes other organizations; absent query results use one response.
- ✅ **Other prohibited fields excluded by the explicit projection —** Email, tax ID, payment token, password hash, and organization ID are not selected.

**Claimed vs. actual**

The artifact claims to return an invoice with its customer’s name, but also returns the customer’s ID. Its validation comment promises rejection of anything other than a positive integer, yet numeric conversion also accepts representations such as `"0x10"` and `"1e3"`; whether those are malformed requires an explicit ID syntax.

**Confirm-these**

- Database ID type, range, and driver behavior for oversized values: required to resolve the correctness-critical malformed-ID guarantee.
- `requireSession()` implementation: confirm that callers cannot choose or tamper with `req.user.org_id`.
- Schema integrity: the inner join suppresses an otherwise existing invoice if its matching customer is missing; confirm constraints prevent this.
- No execution or test results were supplied.

**How each clean axis was checked**

- **Organization scoping/shared 404:** `WHERE i.id = $1 AND i.org_id = $2`, with `$2 = req.user.org_id`, excludes foreign invoices → `if (!invoice)` returns the same 404 body; `c.org_id = i.org_id` scopes the customer join.
- **Other prohibited fields excluded:** traced the explicit `SELECT` list through `res.json(invoice)`; among the forbidden fields, only `customer_id` appears.


=== OUTPUT X ===

**Verdict — NOT VERIFIED**  
BLOCKING:yes

**Independence — INDEPENDENT** — I did not author the supplied artifact; this review uses only the supplied contract and code.

**Observable evidence**

- The query selects `i.customer_id`, and `res.json(invoice)` returns the complete row.
- The query restricts invoices with `i.org_id = $2`, bound to `req.user.org_id`.
- A null query result produces the same `404` response regardless of why no row matched.
- Validation uses `Number.isInteger`, which does not enforce safe integers or a database-compatible range.
- No test or build results were supplied.

**Assessment — judgment**

The response demonstrably violates the confidentiality contract. The malformed-ID guarantee is also unconfirmed: some oversized values pass validation and can trigger database errors that this handler converts to `500`.

**Defects**

1. ❌ **HIGH — Forbidden `customer_id` leaves the server** — Request any accessible invoice with a matching customer. The selected `i.customer_id` is included in `res.json(invoice)`, exceeding the six-field InvoiceDTO.
2. ⚠️ **Potential HIGH — ID validation does not establish the no-500 guarantee** — An ID such as `1e100` converts to a positive value for which `Number.isInteger(id)` is true. It reaches the database; if the ID column rejects that out-of-range value, the catch returns `500`. Confirm against the actual database type and driver.

**Claimed vs. actual**

- “One invoice plus its customer's name” also includes the explicitly forbidden customer identifier.
- The validation comment implies unsuitable IDs are rejected before database access. Oversized integers pass, and coercion also accepts forms such as `0x10` and `1e3`.

**Confirm-these**

- **Correctness-critical:** Database ID type, driver parameter handling, and intended ID syntax/range. Check oversized, unsafe, and nondecimal inputs to establish that malformed IDs never yield `500`.
- **Security-critical:** `requireSession()` must supply a trusted, authenticated `req.user.org_id`; its implementation is absent.
- **Correctness:** Schema constraints must guarantee that an existing invoice has exactly one matching customer in its organization. Otherwise the inner join can hide an existing invoice or produce multiple rows.

**How each clean axis was checked**

- ✅ **Organization filter in the query:** `WHERE i.id = $1 AND i.org_id = $2` → parameters `[id, req.user.org_id]`.
- ✅ **Customer organization matching:** join requires both `c.id = i.customer_id` and `c.org_id = i.org_id`.
- ✅ **Identical absent-row response:** `if (!invoice)` → `404` with `{ error: 'Invoice not found' }` for either missing or organization-filtered rows.
- ✅ **Six required fields selected:** explicit projection contains `id`, `number`, `amount_cents`, `status`, `due_date`, and `customer_name`.
- ✅ **Other named sensitive fields excluded from the projection:** no email, tax ID, payment token, password hash, or organization ID is selected.
- ✅ **Rejected numeric inputs return 400 before database access:** `!Number.isInteger(id) || id <= 0` → immediate `400`. This covers only inputs satisfying that rejection condition.


=== OUTPUT Y ===

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


=== OUTPUT Z ===

**NOT VERIFIED**

Two contract violations:

- **Forbidden field disclosure:** The query selects `i.customer_id`, and `res.json(invoice)` sends it to the caller. Remove it from the query and explicitly construct the six-field `InvoiceDTO`.
- **Malformed IDs can produce a 500:** `Number.isInteger()` accepts unsafe integers and values outside the database column’s range. For example, `1e100` passes this check but can cause a database integer overflow, which the catch block returns as 500. Validate the raw ID’s decimal syntax and enforce the database column’s supported positive range before querying.

The organization predicates correctly scope both the invoice and customer. Missing invoices and invoices outside the caller’s organization follow the same 404 response path.

This verdict is based on static inspection of the supplied artifact; no runtime tests were performed.

