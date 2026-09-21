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
