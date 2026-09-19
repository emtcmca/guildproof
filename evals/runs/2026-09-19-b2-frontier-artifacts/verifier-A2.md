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
