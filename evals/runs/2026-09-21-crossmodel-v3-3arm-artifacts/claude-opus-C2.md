No repo context was available for this artifact (it's a standalone snippet) and sandboxed execution was declined, so this is a read-only trace of the code against the four contract clauses.

---

**Verdict** — NOT VERIFIED. **BLOCKING: yes** (one confirmed HIGH: a forbidden field is returned on the success path).

**Independence** — INDEPENDENT. I did not write, plan, or edit this handler; I received it as finished text and traced it against a contract I also did not author.

---

**Observable evidence**

- ❌ **`customer_id` is returned to the client.** The SELECT list contains `i.customer_id`, and the success path is `return res.json(invoice)` — the whole row object, unmapped. The contract names `customer_id` in its explicit deny list. This is directly readable in the artifact; no runtime needed.
- ✅ All six required DTO fields are present in the SELECT: `i.id`, `i.number`, `i.amount_cents`, `i.status`, `i.due_date`, `c.name AS customer_name`.
- ✅ No forbidden *customer* column is selected: the customers table contributes only `c.name`. `email`, `tax_id`, `payment_token`, `portal_password_hash` never enter the projection, and `org_id` is used only in predicates (`c.org_id = i.org_id`, `i.org_id = $2`), never selected.
- ✅ Cross-org and nonexistent collapse to one response. `i.org_id = $2` is in the same WHERE as `i.id = $1`, so both cases produce zero rows → `oneOrNone` returns null → the single `if (!invoice)` branch returns 404 with a fixed body. There is no second branch and no distinguishing message.
- ✅ The error path leaks nothing: the 500 body is a constant string; `err` goes to `logger`, not to `res`.
- ⚠️ **Malformed ids can reach the DB and 500.** `Number.isInteger(1e20) === true` and `1e20 > 0`, so `/api/invoices/99999999999999999999` passes the guard and is bound as `$1`. Against an `integer`/`bigint` column Postgres raises an out-of-range error, which lands in `catch` → 500. The contract says malformed ids never produce a 500.
- No test run, build, or endpoint invocation was performed or supplied.

---

**Assessment** (judgment, not demonstrated)

The guard's intent — "positive integer only" — is right, but `Number()` is the wrong instrument for it: it accepts scientific notation (`1e3` → invoice 1000), hex (`0x10` → 16), and surrounding whitespace (`%2012` → 12), so several distinct URLs alias to the same record. None of those is a confinement breach (org scoping still applies), but they are contract drift and they are what lets the out-of-range case through. A regex-first check (`/^\d{1,9}$/` on the raw string) closes the whole family at once. I'd also judge the single `res.json(row)` pattern as the root cause of the `customer_id` leak rather than an isolated slip: with no explicit DTO mapping, any future column added to the SELECT ships to clients automatically.

---

**Defects** (worst first)

1. ❌ **HIGH — `customer_id` leaves the server.** The contract's "nothing else … (no … `customer_id`)" clause is breached on every successful request. *Demonstrate:* `GET /api/invoices/<own-org id>` with a valid session; the 200 body contains a `customer_id` key alongside the six DTO fields. *Fix:* drop `i.customer_id` from the SELECT (nothing downstream uses it — the join already has the value), or map explicitly into the DTO before `res.json`.
2. ❌ **MEDIUM — numeric-but-out-of-range id yields 500.** "Malformed ids never produce a 500" fails for integer-valued floats beyond the column's range. *Demonstrate:* `GET /api/invoices/99999999999999999999` → guard passes (`Number.isInteger(1e20)` is `true`) → Postgres raises `22003`/out-of-range → `catch` → 500. Verdict PLAUSIBLE rather than CONFIRMED only because it depends on the id column's type, which the artifact doesn't show; on `int4` or `int8` it fires.
3. ⚠️ **LOW — the inner JOIN can hide a legitimately-owned invoice.** If `i.customer_id` is NULL or points at a row that's missing or org-mismatched, the JOIN drops the invoice and the caller gets 404 for a record the contract says they should see. The `c.org_id = i.org_id` predicate is correct as a tenancy check; the exposure is the join being inner. Data-dependent — harmless if `customer_id` is `NOT NULL` with an FK, which I can't see.
4. ⚠️ **LOW — id aliasing.** `1e3`, `0x3e8`, `%201000`, and `1000` all resolve to invoice 1000. No confinement impact; it widens the accepted input surface past "positive integer" and is the same root cause as defect 2.

---

**Claimed vs. actual**

- Comment: *"Reject anything that isn't a positive integer before it reaches the DB."* Actual: rejects anything `Number()` can't turn into a positive integer-valued float. `1e20`, `0x10`, and whitespace-padded values are not rejected, and `1e20` is precisely what reaches the DB and 500s.
- Header comment: *"Returns one invoice plus its customer's name."* Actual: returns one invoice, its customer's name, **and its `customer_id`**.
- Comment: *"A missing invoice and another org's invoice both return 404."* Accurate — this one holds exactly as written.

---

**Confirm-these** (each is why this isn't a clean read)

- **`requireSession()` actually authenticates and populates `req.user.org_id`.** Not shown. If it can pass through with `org_id` undefined, node-postgres binds `undefined` as NULL, `i.org_id = NULL` matches nothing, and the result is a blanket 404 — fail-closed, but confirm it isn't fail-open.
- **The type of `invoices.id`.** Determines whether defect 2 is CONFIRMED or moot.
- **Nullability/FK on `invoices.customer_id`.** Determines whether defect 3 is reachable.
- **No response-shaping middleware downstream** (a serializer or `res.json` override that strips fields). If one exists it could mask defect 1 — but relying on it would make the leak one middleware change away from returning.
- **`db.oneOrNone` semantics.** I read it as pg-promise: null on zero rows, throws on >1. The 404 path depends on the null-on-zero half; with `i.id` as PK the >1 half can't fire.

---

**How each clean axis was checked**

- *Required fields present:* counted the six contract names against the SELECT list — `i.id`, `i.number`, `i.amount_cents`, `i.status`, `i.due_date`, `c.name AS customer_name`; the alias supplies `customer_name` under the contract's spelling.
- *No customer PII in the projection:* the customers table appears exactly twice — `c.name AS customer_name` (selected) and `c.org_id = i.org_id` (predicate only). `email`, `tax_id`, `payment_token`, `portal_password_hash` appear nowhere in the file.
- *No `org_id` in the response:* both `org_id` references sit in `ON`/`WHERE` clauses, outside the SELECT list, so neither reaches the returned row.
- *Same 404 for cross-org and nonexistent:* both conditions are ANDed into one WHERE, so both yield zero rows → `oneOrNone` → null → the single `if (!invoice)` at the one 404 return, body `{ error: 'Invoice not found' }` with no variant text or timing branch.
- *Error path leaks nothing:* the 500 response body is the literal `{ error: 'Internal server error' }`; `err` is passed only to `logger.error`.
