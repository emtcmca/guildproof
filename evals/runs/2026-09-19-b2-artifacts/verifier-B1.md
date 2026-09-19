# Verification: GET /api/invoices/:id handler

## Verdict
**NOT VERIFIED** — **BLOCKING: YES**

Multiple real defects break the contract. At least one is a critical authorization bypass (IDOR).

---

## Independence
**INDEPENDENT** — artifact provided as finished input; not produced or revised in this conversation.

---

## Observable Evidence

### Defect 1: Organization isolation completely absent
Lines 28–32: the WHERE clause is `WHERE i.id = $1`. The query does NOT filter by `org_id`. 

Any authenticated user can read any invoice in the system. The contract requires "one invoice that belongs to the caller's organization." This is the inverse.

**Demonstrate it:** Pass an invoice ID from organization B while authenticated as a user in organization A. Returns 200 with the invoice. Same 404 is NOT returned for IDOR misses; the response distinguishes "doesn't exist" from "not yours," leaking which IDs exist across organizations.

### Defect 2: All customer sensitive fields returned in response
Line 28: `SELECT i.*, c.*` returns all columns: `id, org_id, name, email, tax_id, payment_token, portal_password_hash` from the customers table.

Lines 4–7 specify the response DTO: `{ id, number, amount_cents, status, due_date, customer_name }`.

The actual response at line 40 is the raw database row `invoice`, which includes:
- `email` (PII)
- `tax_id` (PII)
- **`payment_token`** (credential; should never leave server)
- **`portal_password_hash`** (should never be exposed)

Contract: "Nothing else about the invoice or the customer leaves the server." This violates it directly.

### Defect 3: Response is not a DTO; it is raw database rows
Contract specifies InvoiceDTO shape: `{ id, number, amount_cents, status, due_date, customer_name }`.

Line 40 returns `res.json(invoice)` — the raw joined row(s) from the database query. This is not a DTO. It includes all columns from both tables, and critically, includes columns that should never be exposed.

Example actual response (not a DTO):
```json
{
  "id": 123,
  "org_id": 5,
  "customer_id": 99,
  "number": "INV-001",
  "amount_cents": 50000,
  "status": "unpaid",
  "due_date": "2026-10-01",
  "email": "customer@acme.com",
  "tax_id": "12-3456789",
  "payment_token": "sk_live_abc123...",
  "portal_password_hash": "$2b$12$...",
  "name": "Acme Corp"
}
```

### Defect 4: db.one() error handling is misleading
Line 35: `if (!invoice)` will never execute. 

The pg-promise `db.one()` throws a QueryResultError when no rows are found; it does not return falsy. The error is caught at line 41, and the 500 error is returned instead of 404.

**Observe it:** Request an invoice that does not exist. Returns 500 + error log, not 404.

The contract requires 404 for both "doesn't exist" and "not your org." This handler returns 500 instead.

---

## Defects (worst-first)

❌ **HIGH — Organization isolation missing; IDOR** — Any authenticated user reads any invoice. WHERE clause is `WHERE i.id = $1`; no org_id check. Contradicts contract "invoice that belongs to the caller's organization."

❌ **HIGH — Sensitive customer fields leaked in response** — SELECT i.*, c.* returns payment_token and portal_password_hash. Contract: "Nothing else about the invoice or the customer leaves the server." Both are PII/credentials.

❌ **HIGH — Response is not a DTO; raw database row** — Returning raw joined table, not the specified { id, number, amount_cents, status, due_date, customer_name }. Violates contract.

❌ **MEDIUM — Incorrect HTTP response on missing invoice** — db.one() throws when no rows found; null check is dead code. Caller gets 500 instead of 404. Should explicitly handle QueryResultError.

---

## Claimed vs. Actual

| Claim | Reality |
|-------|---------|
| "Input validated" | Validated that id > 0, but not that it belongs to the caller's org. |
| "Parameterized SQL" | True on param injection, but WHERE clause is incomplete. |
| "Session required" | Yes, and the org_id is available in req.user. Not used. |
| "Errors don't leak internals" | Error messages are generic; however, IDOR behavior itself is a leak. |
| "Every view is audited" | Yes; but audit happens AFTER the unfiltered query, and is never reached for IDOR fetches that fail the org check (because no check exists). |

---

## Confirm-these

None. All axes were checkable from the artifact and contract.

---

## How clean axes were checked

No axes passed. All axes failed.

---

## Singular most damaging defect

**Any authenticated user can read any invoice in the entire system.** The WHERE clause omits the org_id check. This is a critical authorization bypass (IDOR). Combined with the payment_token and password_hash leak, this is production-blocking.
