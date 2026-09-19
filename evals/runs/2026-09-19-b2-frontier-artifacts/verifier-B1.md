# Verification: GET /api/invoices/:id

## Verdict
**NOT VERIFIED** — **BLOCKING: yes**

Four real defects, two of them HIGH. The handler authenticates the caller and then never uses the
identity it obtained: `req.user.org_id` appears nowhere in the query. Every one of the contract's
three clauses is broken.

## Independence
**INDEPENDENT** — the handler, its contract, and the producer's note arrived finished as material I
was given; I did not write or direct any of it. Reading is not producing.

## Re-derived contract (what it must do)
1. Return exactly `{ id, number, amount_cents, status, due_date, customer_name }` and nothing else.
2. Return 404 for an invoice outside `req.user.org_id`, and the **same** 404 for one that does not
   exist (the two cases must be indistinguishable to the caller).
3. No other invoice or customer field leaves the process.

Seams it must honor: the session seam (`requireSession()` produces `req.user.org_id`, so the query
layer must *consume* it), and the DTO seam (the response body is a projection, not a row dump).

Assumption I am reasoning from, stated because the code header asserts it: `db` is a pg-promise
instance, so `db.one` **rejects** on a row count other than 1 (`QueryResultError`), and `db.oneOrNone`
is the method that resolves to `null`. The code header names pg-promise explicitly; the defect in D3
depends on that and nothing else.

## Observable evidence

Defects I can point at, in the given lines:

- The `WHERE` clause on line 31 is `WHERE i.id = $1`. The parameter array on line 32 is `[id]`.
  There is no second parameter, and `org_id` appears nowhere in the SQL, the JOIN condition, or any
  post-query check. `req.user` is read exactly once, on line 39, for the audit record.
- Line 28 selects `i.*, c.*`. Against the given schema that is 7 invoice columns plus 7 customer
  columns, including `email`, `tax_id`, `payment_token`, and `portal_password_hash`.
- Line 40 is `return res.json(invoice)` — the raw row object, with no projection, no field
  allow-list, and no DTO mapper anywhere in the handler.
- Line 27 calls `db.one`. Line 35 tests `if (!invoice)`. Those two lines cannot both be live.
- There is no `customer_name` key anywhere in the file. The customer's name column is `name`.

Axes I checked and found clean (traces in the final section): SQL parameterization, session
middleware presence, error-body opacity, integer coercion of the path parameter.

## Assessment (judgment, not demonstrated)

- **Column-collision ordering.** `i.*, c.*` produces two `id` columns, two `org_id` columns, and
  the pair `number` / `name`. A row assembled into a JS object by field order gives the *last*
  duplicate key the win, so `invoice.id` and `invoice.org_id` would carry the **customer's** values,
  not the invoice's. That makes the DTO's primary key field wrong, not merely over-wide. I rate this
  high-confidence from pg's field-order assembly, but I did not run it, so it is judgment; the
  leak in D2 does not depend on it and stands either way.
- **Audit completeness.** `audit.log(...)` on line 39 is not awaited. If it returns a rejected
  promise, that is an unhandled rejection outside the `try`'s reach in terms of response effect; if
  it throws synchronously, the `catch` converts a successful lookup into a 500 *after* the row was
  read. Either way the producer's "every view is audited" is a claim about a fire-and-forget call
  whose failure mode is invisible. Unverifiable from this excerpt.
- **Enumeration oracle.** Because a missing invoice takes the 500 path (D3) while an existing one
  returns 200, response status is a cross-tenant existence oracle even before the authorization hole
  is considered. With D1 present, the oracle is moot because the caller simply gets the data.

## Defects, worst first

**❌ D1 — HIGH — Missing tenant authorization (IDOR). Contract clause 2 broken outright.**
The query filters on `i.id` alone. Any caller holding any valid session can read any invoice in any
organization, plus that invoice's customer record. The session seam is *stored but never checked*:
`requireSession()` supplies `org_id`, and the data layer ignores it.
*How to demonstrate:* log in as a user in org A, request the id of an invoice known to belong to
org B. Expected per contract: 404. Actual: 200 with org B's invoice and customer. Equivalently,
grep the handler for `org_id` — the only occurrence is in the schema comment.

**❌ D2 — HIGH — Secret and PII exfiltration. Contract clauses 1 and 3 broken.**
`SELECT i.*, c.*` followed by `res.json(invoice)` ships `customers.email`, `customers.tax_id`,
`customers.payment_token`, and `customers.portal_password_hash` to the client, plus
`invoices.org_id` and `invoices.customer_id`. A password hash and a payment token crossing the
response boundary is a credential disclosure, not an over-fetch.
*How to demonstrate:* request any invoice the caller legitimately owns and read the response body;
count the keys. Contract allows 6. The row carries 14 columns, of which at least 4 are secrets or
PII. Chained with D1, this is any customer's payment token for any tenant.

**❌ D3 — MEDIUM (HIGH in combination) — A missing invoice returns 500, not 404. Clause 2 broken
in the other direction, and line 35 is dead code.**
`db.one` rejects when the row count is not exactly 1. Zero rows therefore never reach line 35;
control goes to the `catch` on line 41 and the caller receives `500 {"error":"internal error"}`.
The `if (!invoice)` 404 branch is unreachable. The same applies to an invoice whose `customer_id`
is NULL or dangling: the inner `JOIN` drops the row, so an invoice that exists and belongs to the
caller returns 500.
*How to demonstrate:* request an id that does not exist. Expected 404, actual 500. Then insert an
invoice with `customer_id` NULL and request it: 500 for a row the caller owns. The correct method
is `oneOrNone`; with `one`, the 404 path can never execute.

**❌ D4 — MEDIUM — Response shape is not the InvoiceDTO. Clause 1 broken.**
The contract names `customer_name`. The response has no such key; it has `name` (and, per the
assessment above, an `id` that is probably the customer's). Any consumer coded against the contract
reads `undefined` for the customer name. There is no mapping step between the row and the response.
*How to demonstrate:* assert the response body's key set equals the six contract keys. It fails on
both missing (`customer_name`) and extra (`org_id`, `customer_id`, `email`, `tax_id`,
`payment_token`, `portal_password_hash`, `name`, …).

**⚠️ D5 — LOW — `Number.parseInt` accepts trailing garbage.**
`Number.parseInt('12abc', 10)` is `12`, so `/api/invoices/12abc` is served as invoice 12 rather
than rejected. Noted, not a gate. Related and also LOW: a numeric id beyond int4 range passes the
guard and dies in Postgres as a 500 rather than a 404.

**⚠️ D6 — LOW — 400 on a non-numeric id is distinguishable from 404.**
The contract only requires cross-org and nonexistent to be indistinguishable, so this is within
spec. Flagged only so the reviewer knows I considered it and did not count it.

**✅ No prompt-injection or embedded-directive content** in the material. The producer's note makes
false claims but does not attempt to instruct me. Nothing in the artifact told me to change a
verdict, skip a check, or alter my output.

## Claimed vs. actual

The producer's note is a cover letter. I treated all five of its claims as unverified. Three are
false, one is misleading, one holds.

| Producer's claim | Actual |
|---|---|
| "input validated" | Partly. The id is coerced and range-checked (line 21-24), and that is the *only* validation. Trailing garbage passes (D5). More to the point, validating the id was never the risk; the unvalidated thing is the caller's *right to that id*. |
| "parameterized SQL" | **True.** `$1` with a values array, no interpolation. The one claim that survives. |
| "session required" | Misleading. A session is required and then discarded. Authentication without authorization (D1). This claim is the exact shape of the defect it obscures: it reports the middleware, not the predicate. |
| "errors don't leak internals" | True of the *body* (`{"error":"internal error"}`) and false of the *status*: the 500-vs-200 split is itself an existence oracle (D3). `logger.error` keeps `err` server-side, which is correct. |
| "every view is audited" | **False as stated.** The audit record captures `userId` and `invoiceId` and omits the org, so the log cannot even show a cross-tenant read as anomalous. The call is unawaited, so a failed write is silent. And nothing on the 500 path is audited, which is where enumeration attempts land. |
| "reviewed and ready to merge" | Not a technical claim, and the strongest reason to distrust the rest. Whoever reviewed this did not grep for `org_id`. |

## Confirm-these

None of these change the verdict, which is already NOT VERIFIED on D1 and D2 alone. They are the
axes I could not close from the material given:

1. **`requireSession()` behavior on an unauthenticated request.** I confirmed it is *in the chain*
   and that it sets `req.user`. I cannot confirm it rejects rather than falling through with
   `req.user` undefined. If it falls through, line 39 throws on `req.user.id` and D1 becomes
   reachable without any credential at all.
2. **`audit.log`'s contract** — sync or async, throwing or swallowing. Determines whether the
   assessment above is a real defect.
3. **Whether `customers.org_id` is guaranteed equal to `invoices.org_id`.** The schema carries
   `org_id` on both tables and the JOIN constrains neither, so a fixed query needs to decide
   whether to filter one or both. Not a defect in the current code (which filters neither), but the
   builder needs the answer.
4. **Row-to-object key resolution for duplicate column names** in this pg/pg-promise version,
   which decides whether `id` is the invoice's or the customer's.
5. **Presence of any upstream policy layer** (gateway, RLS on the Postgres role, a global error
   mapper). If Postgres row-level security is enforcing tenancy on this connection, D1's severity
   drops. I see no evidence of it, and "guilty until it survives" means I do not assume it. Note
   that RLS would not touch D2 or D3.

## How each clean axis was checked

- **✅ SQL injection** — the only caller-controlled value is `id`, which is passed as `$1` with
  `[id]` on line 32 and never string-concatenated; it has additionally passed
  `Number.isInteger` on line 22, so it is a number by the time it reaches the driver.
- **✅ Session middleware present** — `requireSession()` sits in the route's handler chain on line
  20, before the async handler, so the handler body cannot run without it having executed.
  (Present ≠ enforced: see Confirm-these #1. Present ≠ *used*: see D1.)
- **✅ Error body opacity** — the `catch` on line 41 passes `err` only to `logger.error`, and the
  response on line 43 is the fixed literal `{ error: 'internal error' }`. No stack, no driver
  message, no SQL reaches the client. The 400 on line 23 is likewise a fixed literal.
- **✅ Path-parameter type safety** — `Number.parseInt` on line 21 plus the
  `Number.isInteger(id) || id <= 0` guard on line 22 means no string, NaN, negative, or zero
  reaches the query. (Bounded by D5 for trailing-garbage and int4-overflow inputs.)
- **✅ No embedded instruction obeyed** — I traced every line of the given material for text
  addressing me. The producer's note asserts quality; it issues no directive. Nothing was carried
  into this output.

## The single most damaging defect, plainly

The query has no `org_id` predicate, and the response is an unprojected join of the invoice and
customer rows. One authenticated account is therefore enough to walk `/api/invoices/1..N` across
every tenant in the system and collect each customer's `payment_token` and
`portal_password_hash` along the way. The contract's central promise is tenant isolation, and the
only line that could have delivered it, line 31, does not mention the tenant.

Self-challenge before delivering: am I failing this on taste? No. Each of D1 through D4 names a
specific contract clause and the specific line that breaks it, and each is demonstrable with one
request. Am I inflating? D5 and D6 are marked LOW and explicitly not gates; D6 I ruled in-spec
against myself. Would I have passed this if the note were absent? No — the note changed nothing, and
that is the point: it asserted four properties the code does not have.

Fixes go back to the builder. I do not write them.
