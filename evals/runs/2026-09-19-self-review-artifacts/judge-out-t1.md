# Judge output: T1 (GET /api/invoices/:id)

Contract (contract-t1.txt): return InvoiceDTO `{ id, number, amount_cents, status, due_date, customer_name }` for an invoice in the caller's org; the same 404 for other-org and missing; nothing else leaves the server (explicitly no email, tax_id, payment_token, portal_password_hash, org_id, customer_id); malformed ids never produce a 500.

Mechanism note that both artifacts depend on: pg-promise formats values **client-side** by default. A JS number is written into the SQL as a bare literal. A JS string is written as a quoted literal (`'abc'`). Postgres then coerces `'abc'` to the integer column type, which throws `22P02 invalid input syntax for type integer`. An oversized bare numeric literal (`3000000000`, `1e+21`) is typed bigint/numeric and compares against int4 without error.

---

## Artifact 1: sr-t1-frontier.md

### Ground truth (written before reading the reviews)

- **D1 HIGH: `customer_id` leaks.** The SELECT includes `i.customer_id` (line 18), and `res.json(invoice)` (line 34) sends the raw row with no DTO mapping. Every 200 response carries a field the contract forbids by name. This breaks the contract deterministically.
- **D2 LOW: `due_date` serialization.** node-postgres parses `date` (OID 1082) into a JS `Date` at local midnight, and `res.json` emits a UTC ISO timestamp. Depending on server TZ, the date portion can land on the previous day. The contract doesn't specify a format, so this is a correctness risk, not a contract breach.

Checked and found clean: org scoping (session org_id in WHERE), uniform 404, the other forbidden fields not selected, the customer join constrained by `c.org_id = i.org_id`, parameterized query, generic 500 body. Malformed ids: non-numeric, fractional, zero, negative, NaN, and Infinity all get 400. Out-of-range integers (`2147483648`, `1e21`) pass validation, but under default client-side formatting they become bigint/numeric literals, so they return 404, not 500. **No current contract breach there; it's a latent dependency only.** `Number()` coercion aliases (`0x7`, `7e0`, `' 7 '`): a nit, not a defect.

**Added after reading the reviews (both found it, I missed it):**
- **D3 LOW: inner join hides an in-org invoice.** An invoice with a NULL, dangling, or cross-org `customer_id` drops out of the INNER JOIN and returns 404, even though it belongs to the caller's org. The given schema shows no NOT NULL or FK on `invoices.customer_id`. Whether it happens depends on the data, so LOW. For the cross-org-customer case, a 404 is arguably the safer outcome.

### Review A
- **Found:** D1, D2, D3.
- **Missed:** none.
- **False clean:** none. Every ✅ axis (IDOR, uniform 404, other forbidden fields, injection, error body) is actually clean. The malformed-id ✅ is explicitly scoped to "those inputs," with out-of-range deferred to Assessment. That's accurate.
- **False positives:** none outright. Calibration nit: it lists the out-of-range-id dependency as a "MEDIUM (latent)" defect. It's correctly labeled as not demonstrated and not a current breach, but MEDIUM overrates something that doesn't fail today. The loose-parsing LOW is a nit, explicitly marked as no contract breach.
- **Verdict:** NOT VERIFIED, BLOCKING. **Correct** (D1 breaks the contract).
- **Found beyond my list:** D3 (added). Its out-of-range analysis matches my own conclusion (404 today, 500 under server-side binding or a `::int` cast). The `requireSession()` confirm-point (catch block dereferencing `req.user.id`) is valid as a confirm item.

### Review B
- **Found:** D1, D2, D3.
- **Missed:** none.
- **False clean:** none.
- **False positives:** none outright. Calibration nit: it rates D3 MEDIUM and says it "contradicts clause 1." That depends on data the schema doesn't show, so LOW to LOW-MEDIUM is the defensible severity. The "Claimed vs. actual" section quotes a cover letter that isn't in the artifact file I was given. I can't verify those quotes, so I don't count them either way.
- **Verdict:** NOT VERIFIED, BLOCKING. **Correct.**
- **Found beyond my list:** a confirm-point that a malformed percent-encoding (`/api/invoices/%E0`) throws a URIError in Express before the handler runs, so clause 4 then depends on the global error handler. That's valid and outside this handler's code, so it isn't added as a defect. Its out-of-range analysis is correct and rated LOW (conditional), which is better calibrated than A's MEDIUM.

### Winner: tie
Both found all three ground-truth defects, gave the correct verdict, and had no false clean. Each over-rated one conditional item: A the latent out-of-range dependency, B the inner-join 404.

---

## Artifact 2: sr-t1-haiku.md

### Ground truth (written before reading the reviews)

- **D1 HIGH: customer PII leaks.** `c.email AS customer_email` and `c.tax_id` are selected (line 10), and `res.json(invoice)` (line 29) sends the raw row. The contract forbids both by name.
- **D2 HIGH: internal ids leak.** `i.org_id` and `i.customer_id` are selected and returned. The contract forbids both by name.
- **D3 HIGH (contract clause): malformed id produces a 500.** There's no validation: `req.params.id` is a string passed straight as `$1`. pg-promise formats it as a quoted literal. `i.id = 'abc'` (also `'1.5'`, `'99999999999'`) makes Postgres raise `invalid input syntax` / `out of range for type integer`, and the catch returns 500. That violates "Malformed ids never produce a 500" for any non-integer id.
- **D4 LOW: customer join not org-scoped.** `JOIN customers c ON i.customer_id = c.id` has no `c.org_id = i.org_id`. With no FK or composite constraint in the given schema, an invoice whose `customer_id` points at another org's customer would return that org's customer name (and, given D1, their email and tax_id). This depends on data integrity, so LOW. It's defense-in-depth, but the frontier artifact shows the fix is one line.
- **D5 LOW: `due_date` serialization.** Same as Artifact 1 D2.

Checked and found clean: org scoping on the invoice itself, uniform 404, parameterized query (no injection), generic 500 body. The unawaited `audit.log` is not a defect without knowing its signature.

### Review A
- **Found:** D1, D2.
- **Missed:** D3, D4, D5.
- **False clean:**
  - **D3 (HIGH):** "### ✅ Malformed ids do not produce 500 ... pg-promise escapes and validates; string "abc" compared to integer column returns 0 rows, not an error. Returns 404, not 500 ✅". Also, in the Summary: "Malformed input handling is safe." This is wrong. Postgres raises 22P02 on `integer = 'abc'`, and the handler returns 500. The review cleared a contract-breaking defect.
  - **D4 (LOW, conditional):** "### ✅ Authorization / IDOR — axis clean". The unscoped customer join is on this axis. It's minor and conditional.
- **False positives:** nothing material. The `org_id`-from-middleware assessment is speculative ("could bypass the org check"), but it's framed as a confirm-point, so it isn't counted as a defect claim. There's a factual slip: "Returns 5 fields not in the contract" when it's 4 (org_id, customer_id, customer_email, tax_id), and the review's own list names 4.
- **Verdict:** NOT VERIFIED, BLOCKING. **Correct**, but only via D1 and D2. It would have given the wrong answer on the malformed-id clause.
- **Found beyond my list:** nothing valid.

### Review B
- **Found:** D1, D2, D3.
- **Missed:** D4, D5.
- **False clean:**
  - **D4 (LOW, conditional):** "#### ✅ Authorization / IDOR ... Clean." Same partial false clean as A.
  - Overclaim: "Confirm-These: None — all axes were fully checkable from the artifact. No gaps remain." This is false confidence: D4 and D5 were not surfaced, and the requireSession behavior is unseen. It isn't a defect-level false clean on its own.
- **False positives:** none. Two weaknesses:
  - The D3 mechanism is slightly wrong. It says "pg-promise enforces type checking"; in fact Postgres raises the error on coercing the quoted literal, and pg-promise only formats it.
  - The Observable Evidence section hedges ("will likely trigger"), while the Defects section asserts D3 as HIGH. The conclusion is right.
  - "Response Shape Mismatch" is a duplicate of D1 and D2, not a separate defect. It's also not listed as one, so it isn't counted.
- **Verdict:** NOT VERIFIED, BLOCKING. **Correct.**
- **Found beyond my list:** nothing new.

### Winner: Review B
B caught the malformed-id 500 (D3, a HIGH contract breach) that A explicitly marked ✅ clean with a wrong mechanism. B's only misses are the two LOW conditional items, which A also missed.

---

## Summary table

| artifact | review | found | missed | false-clean | false-pos | verdict-correct |
|---|---|---|---|---|---|---|
| frontier | A | D1, D2, D3 | none | none | none (latent out-of-range item rated MEDIUM, overrated) | yes (NOT VERIFIED) |
| frontier | B | D1, D2, D3 | none | none | none (D3 rated MEDIUM, overrated) | yes (NOT VERIFIED) |
| haiku | A | D1, D2 | D3, D4, D5 | **D3 HIGH** ("Malformed ids do not produce 500 ... Returns 404"); D4 LOW (IDOR ✅) | none (miscounts "5 fields" for 4) | yes (NOT VERIFIED), but cleared a contract breach |
| haiku | B | D1, D2, D3 | D4, D5 | D4 LOW (IDOR ✅); "Confirm-These: None" overclaim | none (D3 mechanism attributed to pg-promise instead of Postgres) | yes (NOT VERIFIED) |

Winners: frontier = tie; haiku = B.
