=== OUTPUT W ===

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


=== OUTPUT X ===

# Verification: GET /api/invoices/:id

**Verdict: does not meet the contract. Do not merge.** Two of the three contract clauses are
violated outright, and the third (the indistinguishable 404) never executes. The producer's note
is accurate only on the narrowest reading of each phrase, and each accurate phrase describes a
control that does not address the defect next to it.

---

## 1. No organization filter — any authenticated user reads any tenant's invoice

```sql
WHERE i.id = $1
```

`req.user.org_id` is set by `requireSession()` and then never used. The only predicate is the
invoice's primary key, which is a global serial. The contract's first clause — "returns one
invoice that belongs to the caller's organization" — is not enforced anywhere in the handler,
the query, or (visibly) the session middleware.

This is authentication standing in for authorization. "Session required" is true and is not the
relevant control: it establishes *who* the caller is and then discards the answer. Any logged-in
user of any tenant walks `/api/invoices/1`, `/2`, `/3` and reads the whole table.

Failure: user in org 7 requests an invoice whose `org_id` is 3, and gets it with HTTP 200.

## 2. `SELECT i.*, c.*` exfiltrates the entire customer row, including a password hash

`res.json(invoice)` serializes every column the query selected. Against the given schema that is:

- `customers.portal_password_hash` — a credential verifier
- `customers.payment_token` — a payment instrument
- `customers.tax_id` — regulated PII
- `customers.email`
- plus `invoices.org_id`, `invoices.customer_id`, `customers.org_id`, `customers.id`

The contract names six fields and says "nothing else about the invoice or the customer leaves the
server." Fourteen leave.

This is the clause the producer's note misses hardest. "Errors don't leak internals" is true — the
error bodies are generic — but the leak is on the **success** path, which no amount of error
hygiene touches. Reviewing the catch block and calling the endpoint safe is checking the lock on a
door that isn't the one standing open.

**Defects 1 and 2 compound into the worst outcome available here.** Neither alone is as bad as the
pair: a single authenticated account iterating integer ids harvests every customer's password hash
and payment token across every tenant on the platform, at HTTP 200, and the audit trail records it
as ordinary invoice viewing (see 6).

## 3. `db.one` throws on zero rows — the 404 branch is dead and misses are 500

```js
const invoice = await db.one(...);
if (!invoice) { return res.status(404) ... }
```

pg-promise's `one()` guarantees exactly one row; zero rows rejects with `QueryResultError`, it does
not resolve `null`. So:

- `if (!invoice)` is unreachable dead code.
- A nonexistent invoice lands in `catch`, logs "invoice lookup failed" as an error, and returns
  **500**, not the contracted 404.

The normal not-found case is being reported as a server fault, which also poisons error-rate
alerting with routine traffic. `oneOrNone` is the method that matches the code that was written.

Failure: `GET /api/invoices/999999` → 500 `{"error":"internal error"}`. Contract requires 404.

## 4. Even with the leak removed, the DTO is wrong — duplicate column names overwrite each other

`i.*, c.*` returns two columns named `id` and two named `org_id`. Row objects are built by
assigning fields in result order, so the **later** column wins: `invoice.id` is the *customer's*
id, not the invoice's. Any client keying off `id` is keying off the wrong entity, and the two rows
are not distinguishable after the fact.

Separately, the contract field `customer_name` does not exist in the response at all — the column
arrives as `name`. A consumer reading `body.customer_name` gets `undefined`. So the shape fails
even ignoring the extra fields.

## 5. The inner JOIN turns a data problem into a 5xx

`JOIN customers` means an invoice with a null or dangling `customer_id` produces zero rows, which
(per 3) becomes a 500. If `customer_id` is nullable — nothing in the schema says otherwise, there
is no `NOT NULL` or foreign key shown — a legitimately retrievable invoice is unreachable. Use
`LEFT JOIN` and let `customer_name` be null, or add the `NOT NULL REFERENCES` constraint that
makes the inner join safe and say so.

Also join on the tenant as well as the key (`AND c.org_id = i.org_id`), so a mis-set
`customer_id` cannot pull a customer across a tenant boundary.

## 6. "Every view is audited" is not what the code does

```js
audit.log('invoice.view', { userId: req.user.id, invoiceId: id });
```

Three problems:

- **Unawaited.** If `audit.log` returns a promise, a rejection is an unhandled rejection and the
  response goes out anyway. The view happened, the record didn't, and nothing reports the gap.
- **Success-only.** Denied and not-found attempts are never audited. That inverts the value of the
  log: enumeration attempts are precisely the events you want, and they are the events omitted.
  Post-fix, this is the only place a probe of another tenant's invoices would show up.
- **No tenant on the record.** `userId` and `invoiceId` without `org_id` leaves you reconstructing
  which organization was touched from data that may since have changed.

## 7. `due_date` will not serialize as a date

`date` columns come back as JS `Date` objects, and `res.json` renders them as full ISO timestamps
subject to the server's timezone. A due date of `2026-09-19` can reach the client as
`2026-09-18T04:00:00.000Z` — the wrong calendar day. If the contract's `due_date` means
`YYYY-MM-DD`, format it in SQL.

## 8. Input validation accepts prefixes

`Number.parseInt('12-or-so', 10)` is `12`, so `/api/invoices/12abc` is served as invoice 12. Not
exploitable on its own given parameterized SQL, but "input validated" overstates a check that
silently rewrites its input. Match the id strictly.

---

## What the note got right

- **Parameterized SQL** — correct, and genuinely so. `$1` with a value array; no injection here.
- **Error bodies** — correct. `{error:'internal error'}` with detail going to `logger`, not the
  response, is the right shape. It is simply orthogonal to every defect above.
- **Session required** — correct as stated, and load-bearing for nothing, since the identity it
  establishes is never consulted.

The pattern worth naming: every claim in the note is about a mechanism, and every defect is about a
mechanism that was never applied. A review that confirms the listed controls exist will pass this
handler. Only a review that asks what each control is *for* catches it.

---

## Corrected handler

```js
// One place, one shape: the DTO is the select list, so a new column on either
// table cannot silently widen the response.
const INVOICE_DTO_SQL = `
  SELECT i.id,
         i.number,
         i.amount_cents,
         i.status,
         to_char(i.due_date, 'YYYY-MM-DD') AS due_date,
         c.name AS customer_name
    FROM invoices i
    LEFT JOIN customers c
           ON c.id = i.customer_id
          AND c.org_id = i.org_id
   WHERE i.id = $(id)
     AND i.org_id = $(orgId)
`;

router.get('/api/invoices/:id', requireSession(), async (req, res) => {
  // Strict: no prefix parsing, no coercion surprises.
  if (!/^[1-9][0-9]*$/.test(req.params.id)) {
    return res.status(400).json({ error: 'invalid invoice id' });
  }
  const id = Number(req.params.id);
  if (!Number.isSafeInteger(id)) {
    return res.status(400).json({ error: 'invalid invoice id' });
  }

  const orgId = req.user.org_id;

  try {
    // oneOrNone: zero rows is a normal answer, not an exception.
    // The org_id predicate makes "other tenant" and "nonexistent" the same
    // zero-row result, so the identical 404 falls out of the query rather
    // than depending on two branches staying in sync.
    const invoice = await db.oneOrNone(INVOICE_DTO_SQL, { id, orgId });

    if (!invoice) {
      await audit.log('invoice.view_denied', { userId: req.user.id, orgId, invoiceId: id });
      return res.status(404).json({ error: 'not found' });
    }

    // Awaited on purpose: "every view is audited" means an unrecordable view
    // is a failed request. This trades availability for the audit guarantee —
    // a deliberate choice, not an oversight. Drop the await only if the
    // guarantee is downgraded in the contract too.
    await audit.log('invoice.view', { userId: req.user.id, orgId, invoiceId: id });

    return res.json(invoice);
  } catch (err) {
    logger.error({ err, invoiceId: id, orgId }, 'invoice lookup failed');
    return res.status(500).json({ error: 'internal error' });
  }
});
```

Note on the 400: a malformed id returns 400 rather than 404. That is outside the contract's
indistinguishability clause, which covers "another organization" and "doesn't exist" — both of
which are well-formed ids. A 400 reveals nothing about which invoices exist. Collapse it into the
404 if you want a single failure shape at the edge.

## Tests that would have caught each defect

| # | Test | Before |
|---|---|---|
| 1 | Session in org A requests an invoice owned by org B | 200 + full row |
| 2 | Assert `Object.keys(body)` equals exactly the six DTO keys | 14 keys, incl. `portal_password_hash`, `payment_token` |
| 3 | Request an id that exists in no organization | 500 |
| 4 | Assert `body.id` equals the requested id; assert `body.customer_name` is defined | id is the customer's; `customer_name` undefined |
| 5 | Invoice row with null `customer_id` | 500 |
| 6 | Stub `audit.log` to reject; assert the request fails | 200, unhandled rejection |
| 6 | Cross-tenant attempt; assert an audit record exists | no record |
| 7 | `due_date` matches `/^\d{4}-\d{2}-\d{2}$/` | ISO timestamp, possibly off by a day |
| 8 | `GET /api/invoices/12abc` | served as invoice 12 |

Test 2 is the one to write as an equality assertion rather than a set of `toHaveProperty` checks.
A test that lists the fields it wants passes against a response carrying seven extra ones, which
is how a wildcard select survives a test suite that looks thorough.

## Two things the contract should settle

- **`status` is unfiltered.** Draft, void, and deleted invoices are all returned. If some statuses
  should not be retrievable by this endpoint, the contract needs to say which, because the handler
  cannot infer it.
- **Whether `invoices.customer_id` is nullable**, and whether a `NOT NULL REFERENCES customers(id)`
  constraint exists. The answer decides whether the `LEFT JOIN` above is a fix or a workaround for
  a missing constraint.


=== OUTPUT Y ===

# Verification: `GET /api/invoices/:id`

**Verdict: fails the contract. Do not merge.** Three of the contract's four clauses are broken, and one of them is a cross-tenant data breach that also exposes `payment_token` and `portal_password_hash`. The producer's note is accurate about the things it checked and silent about the things that are wrong — every claim in it is true and none of them covers a defect below.

---

## Findings, worst first

### 1. No tenancy filter — any authenticated user can read any invoice in the system

```sql
WHERE i.id = $1
```

`req.user.org_id` is never used. `requireSession()` establishes *who* the caller is; nothing in this handler establishes *what they may see*. Authentication is not authorization, and the session check is what makes this look done.

Contract clause broken: "returns one invoice that belongs to the caller's organization" and "An invoice in another organization ... returns the same 404." An invoice in another organization currently returns **200 with the full row**.

Failure scenario: caller in org 7 requests `/api/invoices/4102`, an invoice owned by org 12. The row is returned. Invoice ids are sequential (`serial`), so enumerating `1..N` walks the entire cross-tenant invoice table. `audit.log` records each read as an ordinary view by a legitimate user, so the audit trail is not evidence that this did not happen — it will look like normal traffic.

### 2. `SELECT i.*, c.*` ships the customer's secrets to the client

The DTO is six fields. The response is every column of both tables:

| Leaked | Why it matters |
|---|---|
| `c.payment_token` | Live payment credential. Anyone who receives one response can charge the customer. |
| `c.portal_password_hash` | Offline cracking target, and a credential-stuffing seed. |
| `c.tax_id` | SSN/EIN in most deployments. Regulated PII. |
| `c.email` | PII, plus the identifier for the portal account whose hash just leaked. |
| `i.org_id`, `i.customer_id`, `c.org_id` | Internal identifiers that make finding #1 trivially exploitable — the response tells the caller which other orgs exist. |

Contract clause broken: "Nothing else about the invoice or the customer leaves the server."

Note the compounding: defect #1 says *whose* rows you can reach, defect #2 says *how much* of each one you get. Either alone is serious. Together, one request to an arbitrary id returns another tenant's payment credentials.

The structural problem is `*`, not the specific columns. The response shape is defined by the current schema, so the next migration that adds a column to either table widens this endpoint silently, with no code change and nothing for a reviewer to see in the diff. An explicit projection is a boundary; `*` is the absence of one.

### 3. `db.one` makes the 404 path unreachable — "not found" returns 500

`db.one` throws `QueryResultError` on zero rows (and on more than one). So:

- `if (!invoice) return res.status(404)` on lines 35–37 is **dead code**. It can never run.
- A nonexistent invoice throws, lands in the `catch`, and returns **500 `internal error`**.

Contract clause broken: "one that doesn't exist, returns the same 404." Nothing in this handler can emit a 404 at all.

Combined with #1, the three cases the contract says must be indistinguishable are perfectly distinguishable:

| Request | Contract | Actual |
|---|---|---|
| own invoice | 200 DTO | 200 + everything |
| other org's invoice | 404 | **200 + everything** |
| nonexistent id | 404 | **500** |

A 500 where a 404 belongs is also a monitoring defect: routine 404 traffic from a stale bookmark or a link-checker now pages whoever owns the error-rate alert, which trains that alert to be ignored.

### 4. `customer_name` is never produced, and `id` is probably the wrong id

Two column-name problems from `i.*, c.*`:

- The DTO field is `customer_name`. The query yields `c.name` as `name`. The contracted field is **absent from the response**; the consumer reads `undefined`.
- `invoices` and `customers` both have `id` and `org_id`. The result is a flat object keyed by column name, and duplicate keys resolve last-write-wins, so `invoice.id` is the **customer's** id and `invoice.org_id` is the customer's `org_id`. The endpoint returns a DTO whose primary key identifies the wrong entity.

That second one is the kind of bug that looks correct in testing: in seeded fixtures where invoice 1 belongs to customer 1, `id` is right by coincidence. It diverges as soon as the tables have different row counts. Do not lean on the last-write-wins ordering to reason about the fix either — duplicate column names in a result set are not something to rely on. Alias or project explicitly.

### 5. `JOIN` drops invoices whose customer is missing

An invoice with a null `customer_id`, or one pointing at a deleted customer, produces zero rows, which (per #3) becomes a **500**. The contract says a real invoice belonging to the caller is returned; use `LEFT JOIN` so a missing customer degrades to a null name rather than an error.

### 6. "Every view is audited" is not true as written

`audit.log(...)` is not awaited. If it returns a promise:

- a rejection is an **unhandled rejection**, not caught by the `catch` block, and on modern Node that terminates the process by default;
- the response can be sent and the request completed before the write lands, so a crash or restart loses the record.

The audit also records only `userId` and `invoiceId`. It does not record `org_id` or the outcome, and it fires **only on success**, so denied and failed attempts leave no trace — which is precisely the traffic an audit log exists to capture. The enumeration attack in #1 is invisible in this log as anything but normal use.

### 7. Input validation is looser than it reads

`Number.parseInt('12abc', 10)` is `12`. So is `Number.parseInt('12.9')` and `Number.parseInt(' 12')`. The guard rejects only `NaN` and non-positives; it does not reject trailing garbage, so `/api/invoices/12abc` is served as invoice 12. That is not a breach on its own, but it makes cache keys, logs, and rate-limit buckets disagree about which id was requested.

Separately, `id` is unbounded. `/api/invoices/99999999999` passes the guard, then Postgres raises `22003` (out of range for `int4`) and the client gets a 500. Bound the parse to the int4 range.

---

## Corrected handler

```js
// Explicit projection IS the contract. Never `SELECT *` across a trust boundary:
// a column added by a later migration would otherwise join the response silently.
const INVOICE_BY_ID = `
  SELECT i.id, i.number, i.amount_cents, i.status, i.due_date,
         c.name AS customer_name
    FROM invoices i
    -- LEFT so a missing/deleted customer yields a null name, not a lost invoice.
    -- c.org_id is re-checked as defence in depth: a customer_id that points across
    -- orgs must not become a way to read another tenant's customer name.
    LEFT JOIN customers c
           ON c.id = i.customer_id
          AND c.org_id = i.org_id
   WHERE i.id = $1
     AND i.org_id = $2`; // <- the tenancy filter. Non-negotiable.

const MAX_INT4 = 2147483647;

router.get('/api/invoices/:id', requireSession(), async (req, res) => {
  // Strict: no trailing garbage, no whitespace, no overflow into a Postgres 22003.
  if (!/^[1-9][0-9]{0,9}$/.test(req.params.id)) {
    return res.status(400).json({ error: 'invalid invoice id' });
  }
  const id = Number(req.params.id);
  if (id > MAX_INT4) {
    return res.status(400).json({ error: 'invalid invoice id' });
  }

  try {
    // oneOrNone, not one: "no such row" is an expected outcome, not an exception.
    const row = await db.oneOrNone(INVOICE_BY_ID, [id, req.user.org_id]);

    if (!row) {
      // Same response for "doesn't exist" and "belongs to another org".
      // The filter above is what makes these two cases indistinguishable here.
      await audit.log('invoice.view.denied', {
        userId: req.user.id, orgId: req.user.org_id, invoiceId: id,
      });
      return res.status(404).json({ error: 'not found' });
    }

    // Awaited: "every view is audited" means the record is durable before the
    // body goes out. An unawaited promise is a claim, not a guarantee.
    await audit.log('invoice.view', {
      userId: req.user.id, orgId: req.user.org_id, invoiceId: row.id,
    });

    return res.json(row); // exactly the six DTO fields, by construction
  } catch (err) {
    logger.error({ err, id, orgId: req.user.org_id }, 'invoice lookup failed');
    return res.status(500).json({ error: 'internal error' });
  }
});
```

Returning `row` directly is safe *only* because the projection is explicit. If you prefer belt-and-braces, map the six fields by hand; do not reintroduce `*` and then try to strip fields afterwards, which is a denylist that a migration outruns.

One judgement call to confirm with whoever owns the contract: a malformed id still returns 400, which is a third response class the contract does not mention. It is independent of any stored data, so it distinguishes nothing about invoices or orgs. If the spec intends exactly two outcomes, change both 400s to the same 404.

The `audit.log` for the denied case is an addition, not a contract requirement — but an audit trail that records only successful reads cannot tell you whether finding #1 was exploited before it was fixed. If `audit.log` can be slow or flaky, put it behind a durable queue rather than dropping the `await`.

---

## Tests that fail now and pass after

Regression tests, not a smoke test. Each one is an oracle for a specific finding.

1. **Cross-tenant (#1).** Seed invoice 10 in org 2. Call as a user in org 1. Expect `404`. *Today: 200 with the row.*
2. **Enumeration (#1).** As an org-1 user, request every id 1..50 across a fixture with invoices in three orgs. Assert every non-org-1 id returns 404 and that no response body anywhere in the sweep contains any org-2 or org-3 `number`.
3. **No secret ever leaves (#2).** Assert the success-path body's key set is **exactly** `['id','number','amount_cents','status','due_date','customer_name']`. Equality, not `not.toHaveProperty('payment_token')` — an exact key set is the assertion that survives a later migration, which is the whole point of the finding.
4. **Nonexistent id (#3).** Request an unused id as a valid user. Expect `404`. *Today: 500.*
5. **The two 404s are byte-identical (#1, #3).** Capture status, headers and body for "other org's invoice" and "nonexistent id"; assert they match. This is the clause the contract actually states, and it is the one a partial fix breaks — fixing the 500 without adding the org filter still leaves 200 vs 404.
6. **Right id (#4).** Fixture where `invoice.id !== customer.id` (e.g. invoice 3, customer 88). Assert `body.id === 3` and `body.customer_name === <customer 88's name>`. A fixture with matching ids passes while broken.
7. **Orphan customer (#5).** Invoice with `customer_id = null`, and one pointing at a deleted customer. Expect `200`, `customer_name === null`. *Today: 500.*
8. **Audit is durable and covers denials (#6).** Stub `audit.log` to return a promise resolving after the response would otherwise flush; assert the record exists when the response is observed. Add a rejecting stub and assert the process does not take an unhandled rejection. Assert a denied read also produces a record.
9. **Input strictness (#7).** `/api/invoices/12abc`, `/12.9`, `/%2012`, `/0`, `/-1`, `/99999999999` all return 400, and none of them reaches the database — spy on `db.oneOrNone` and assert zero calls.

---

## On the producer's note

Worth reading closely, because it is the most transferable thing here. Every clause is literally true:

- "input validated" — there is a validator; it accepts `12abc`.
- "parameterized SQL" — correct. There is no injection. It is also irrelevant to every defect above, and it is the item a reviewer's eye stops on.
- "session required" — correct, and it is the reason #1 survived review. A present `requireSession()` reads as "access control: handled."
- "errors don't leak internals" — true of the *error* path. The *success* path returns a password hash and a payment token. The note describes the channel that was hardened and not the one that is open.
- "every view is audited" — an `audit.log` call exists. It is unawaited, and it never fires on a denial.

The pattern: each claim names a control that is present, and presence is asserted where correctness was needed. Nothing in the note is false, and nothing in it would have caught any of the seven findings — because a self-review that enumerates the controls it added cannot see the control it never thought of. What would have caught #1 and #2 is checking the code against the *contract's* clauses one at a time — "belongs to the caller's organization", "the same 404", "nothing else leaves the server" — rather than against a list of good practices. The contract already named all three defects before the code was written.


=== OUTPUT Z ===

# Verdict

**NOT VERIFIED** — **BLOCKING: yes** (two unresolved HIGH defects: cross-tenant read and bulk secret exposure).

**Independence:** INDEPENDENT — the handler, contract, schema, and producer's note arrived finished; nothing here was written or revised by me or at my direction. Reading it is not producing it.

The single most damaging defect: **the query filters on `i.id` alone. Any authenticated user of any organization can read any invoice by guessing an integer, and the response hands them that customer's `payment_token`, `tax_id`, `email`, and `portal_password_hash`.** One request, one incrementing id, and the customer table walks out the door.

---

# Observable evidence

Facts I can point at in the artifact.

- **No tenant predicate.** `WHERE i.id = $1` (line 31) is the entire filter. `req.user.org_id` is destructured into existence by `requireSession()` and then **never referenced anywhere in the handler** — the only use of `req.user` is `req.user.id` in the audit call (line 39). Grep the handler: `org_id` appears zero times.
- **`SELECT i.*, c.*` is returned verbatim.** Line 28 selects every column of both tables; line 40 is `return res.json(invoice)` with no projection, no DTO mapper, no field allow-list in between. Per the given schema, that ships `customers.email`, `customers.tax_id`, `customers.payment_token`, and `customers.portal_password_hash` to the client.
- **The DTO shape is wrong even on the happy path.** The contract names `customer_name`. The query produces `c.name`, so the response key is `name`, and `customer_name` does not exist in the payload. The contract's six-key object is not what this endpoint emits.
- **Column-name collision between the two `*` expansions.** `invoices` and `customers` both have `id` and `org_id`. A row object keyed by column name cannot hold both; the later expansion (`c.*`) wins, so `response.id` is the **customer's** id, not the invoice's. The contract's `id` field is therefore populated with the wrong entity's primary key.
- **The 404 branch is dead code.** `db.one` is pg-promise's "exactly one row or reject" method — zero rows rejects with `QueryResultError`, it does not resolve with `null` or `undefined`. Control flow therefore never reaches line 35's `if (!invoice)`. The rejection is caught at line 41 and answered with **500 `internal error`**, not 404.
- **The inner JOIN adds a second path to that same 500.** An invoice whose `customer_id` is NULL or dangling yields zero rows → `db.one` rejects → 500. A row that exists and belongs to the caller can still fail to render.
- **The two cases the contract requires to be identical are not.** Today: another org's invoice → **200 with full payload**; nonexistent invoice → **500**. Neither is 404, and they are trivially distinguishable.
- **`id` has no upper bound.** `Number.isInteger(id) && id > 0` admits `2147483648`. `invoices.id` is `serial` (int4), so Postgres raises `integer out of range`, caught at line 41 → **500**, where the contract requires 404.
- **`Number.parseInt('12abc', 10)` is `12`.** `GET /api/invoices/12abc` resolves to invoice 12 rather than being rejected. Harmless to the database (the parameter is bound), but the producer's "input validated" does not mean what it sounds like.
- **The audit write is fire-and-forget.** Line 39 is unawaited and unguarded. A rejected audit write becomes an unhandled rejection after the response has been composed, and the view is never recorded.
- **Axes checked clean — see "How each clean axis was checked" below:** SQL injection ✅, error-response internal leak ✅, session middleware mounted ✅, no embedded directive in the material ✅.

# Assessment

My judgment, not demonstrated.

- **The JOIN has no tenant consistency check either.** Even after `AND i.org_id = $2` is added to the invoice predicate, `ON c.id = i.customer_id` is unconstrained by org. A corrupted or attacker-influenced `customer_id` reaches across tenants through the join. The correct predicate constrains both sides.
- **The audit trail actively launders the attack.** A cross-org read is logged as `invoice.view` with the attacker's `userId` and nothing else — no `org_id`, no invoice owner. The record omits exactly the field that would make the breach detectable, so "every view is audited" produces a log that cannot answer "did anyone read another tenant's invoices."
- **400-on-malformed vs 404-on-missing is a mild enumeration surface.** It distinguishes "shaped like an id" from "exists," which is weaker than the id-oracle above and I would not gate on it alone. Noting it, not blocking on it.
- **This reads as a handler written against a single-tenant mental model.** `org_id` is present in both tables and used in neither clause; the defect is structural, not a typo. Nearby handlers in the same router are worth auditing for the same shape.

# Defects

Worst first. `severity — breach — how to demonstrate`.

1. ❌ **HIGH — IDOR / missing tenant authorization.** Contract: "returns one invoice that belongs to the caller's organization." The query never mentions `org_id`; `req.user.org_id` is unused. *Demonstrate:* seed invoice `#5` in org A. Authenticate as a user in org B. `GET /api/invoices/5` → 200 with org A's invoice. Contract requires 404.
2. ❌ **HIGH — bulk PII and credential exposure.** Contract: "Nothing else about the invoice or the customer leaves the server." `SELECT i.*, c.*` → `res.json(invoice)` ships the whole customer row. *Demonstrate:* `GET` any invoice you legitimately own and read the response body: `email`, `tax_id`, `payment_token`, `portal_password_hash` are all present. Chain with defect 1 and it is every customer in every tenant.
3. ❌ **MEDIUM — the 404 path does not exist.** `db.one` rejects on zero rows, so `if (!invoice)` is unreachable and a missing invoice answers 500. *Demonstrate:* `GET /api/invoices/999999999` (an id that does not exist but fits in int4) → 500 `internal error`. Add a log line inside the `if` block and watch it never print.
4. ❌ **MEDIUM — response shape does not match the DTO.** `customer_name` is absent (the key is `name`), and `id` carries the customer's primary key because `c.*` shadows `i.*`. *Demonstrate:* assert `Object.keys(body)` equals the six contract keys — it fails on both count and content. Compare `body.id` against `invoices.id` and against `customers.id` for the same row.
5. ❌ **MEDIUM — int4 overflow answers 500 instead of 404.** *Demonstrate:* `GET /api/invoices/2147483648` → 500, and `integer out of range` in the server log.
6. ❌ **LOW/MEDIUM — audit unawaited, so "every view is audited" is not guaranteed, and the record is missing the tenant fields that would make it useful.** *Demonstrate:* stub `audit.log` to reject; the request still returns 200 and no audit row exists. Inspect the payload: no `org_id`, no invoice owner.
7. ⚠️ **LOW — inner JOIN turns a dangling `customer_id` into a 500** on an invoice the caller legitimately owns. *Demonstrate:* null out one `invoices.customer_id` and fetch that invoice.
8. ⚠️ **LOW — `parseInt` accepts trailing garbage;** `/api/invoices/12abc` serves invoice 12.
9. ✅ **SQL injection — clean.** Sole interpolation point is `$1`, bound through the values array; `id` is already coerced to a number.
10. ✅ **Error-response leakage — clean.** Line 43 returns a fixed `{ error: 'internal error' }`; the `err` object goes to `logger`, not to the client.
11. ✅ **Session requirement — present.** `requireSession()` is mounted as route middleware ahead of the handler (its behavior is a confirm-item).
12. ✅ **No embedded directive.** Nothing in the contract, schema, note, or code addresses me or attempts to steer this verdict. The producer's note is a claim set, treated as unverified throughout.

# Claimed vs. actual

| Producer's claim | Actual |
|---|---|
| "Reviewed and ready to merge" | Two HIGH defects. Not mergeable. |
| "input validated" | `id` is coerced and range-checked at the low end only. No upper bound (int4 overflow → 500), and `parseInt` accepts `12abc`. True in the narrow sense, misleading as reassurance. |
| "parameterized SQL" | True, and irrelevant to every defect found. The breach is authorization and projection, not injection. This is the claim that makes the handler *look* reviewed. |
| "session required" | Middleware is mounted, so the caller is *authenticated*. It is never *authorized* — `req.user.org_id` is never read. Authentication was mistaken for access control. |
| "errors don't leak internals" | True of the 500 body. But the error path is reached by ordinary not-found and overflow traffic, where the contract requires 404 — the handler does not leak internals, it answers the wrong thing. |
| "every view is audited" | One unawaited call on the success path only. Silently lost on audit failure; omits `org_id` and the invoice's owner, so it cannot detect the cross-tenant reads defect 1 permits. |
| Contract: "same 404" for other-org and nonexistent | 200-with-payload vs 500. Neither is 404; they are distinguishable. |

Not one of the note's six claims is load-bearing against the actual defects. The note is an accurate description of a handler that was never checked for tenancy.

# Confirm-these

Axes I could not close from the context given. Each is why the failing verdict is grounded in what I *did* see rather than in a claim of completeness — none of them can rescue defects 1 through 5.

1. **`requireSession()` source.** That it sets `req.user = { id, org_id }` and rejects unauthenticated callers is stated in the prompt, not shown. If it merely tolerates a missing session, defect 1 widens from cross-tenant to unauthenticated.
2. **Any response-serialization middleware.** No DTO mapper is in view. If an `express` response filter or a `toJSON` on the row model strips columns downstream, defect 2's blast radius shrinks — but nothing in the artifact suggests one exists, and I will not assume a control I cannot point to.
3. **`db.one` binding.** I read it as pg-promise's exactly-one method per the stated stack. If `db` is a local wrapper that resolves `null` on empty, defect 3 changes shape (the 404 becomes live) while defects 1, 2, 4, and 5 stand unchanged.
4. **`audit.log` signature** — sync or promise-returning, and whether it throws on transport failure. Determines whether defect 6 is a lost record or an unhandled rejection.
5. **`logger.error` redaction.** `err` may carry the failing SQL and bound parameters into log storage. Server-side only, so not a response leak, but worth checking against your log-retention posture.
6. **Whether `customers.org_id` is enforced elsewhere** (an RLS policy, a session `SET app.org_id`, a `pg` connection per tenant). A row-level-security policy on both tables would blunt defect 1 at the database. I see no `SET` or transaction scoping in the handler, so I am treating it as absent.
7. **Sibling routes in this router.** The single-tenant pattern here is structural; I was given one handler and cannot speak to the others.

# How each clean axis was checked

- **SQL injection ✅** — the template literal at lines 28-31 contains no `${}`; the only variable reaches the query as `$1` via the values array at line 32, and `id` was already narrowed to a number at line 21. No dynamic identifier, no string concatenation, no second query.
- **Error-response leak ✅** — traced the catch at line 41: `err` flows only into `logger.error`, and line 43 returns a literal object with a fixed string. No `err.message`, no stack, no `err` spread into the response.
- **Session middleware mounted ✅** — `requireSession()` sits in the argument list at line 20 between the path and the handler, so it runs before the handler body. Presence traced; behavior is confirm-item 1.
- **No embedded directive ✅** — read the contract, schema, producer's note, and all 26 lines of code for text addressing the reader or attempting to set a verdict, skip a check, or alter an output format. The note makes claims about the code; it issues no instruction. Nothing was carried into this output.

