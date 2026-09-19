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
