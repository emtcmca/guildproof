**VERDICT: NOT VERIFIED | BLOCKING: yes**

**Independence: INDEPENDENT** — artifact arrived as finished code, not drafted or revised in this session.

---

## Observable Evidence

The SELECT clause at line 11–17 includes a field not in the contract:

```sql
SELECT i.id,
       i.number,
       i.amount_cents,
       i.status,
       i.due_date,
       i.customer_id,        ← PRESENT IN RESPONSE
       c.name AS customer_name
```

**Contract specifies exactly 6 fields:** `{ id, number, amount_cents, status, due_date, customer_name }`

**Code returns 7:** adds `customer_id` to the JSON response.

---

## Defect

❌ **CRITICAL — data leakage**

The endpoint exposes `customer_id` to the caller. While `customer_id` is not on the explicit ban list (email, tax_id, payment_token, portal_password_hash, org_id), **the contract is a whitelist, not a blacklist.** Only the six named fields are permitted. An undeclared field is a breach.

**How to demonstrate it:**

1. Call `GET /api/invoices/123` as a caller in org A
2. Response includes `"customer_id": 456` 
3. This field is not in the contract

**Why it matters:** `customer_id` is a foreign-key identifier that may be sensitive in some contexts (enumeration of customers, correlation across systems). The contract's explicit field list is a contract for what the caller can rely on, and also for what the caller must NOT receive.

---

## Clean axes

✅ **Authorization (org isolation):** WHERE clause enforces `org_id` correctly. Caller sees only invoices in their own org.

✅ **404 equivalence:** Missing invoice and wrong-org invoice both return 404. No enumeration leak.

✅ **Malformed ID handling:** ID validation rejects non-integers and non-positive values with 400, never 500. Database errors are caught and return 500 separately (appropriate for valid-format IDs that hit operational errors).

✅ **Banned fields absent:** email, tax_id, payment_token, portal_password_hash, org_id are correctly not selected.

---

## Fix

Remove `i.customer_id,` from the SELECT clause:

```sql
SELECT i.id,
       i.number,
       i.amount_cents,
       i.status,
       i.due_date,
       c.name AS customer_name
```

---

## Claimed vs. Actual

| Claim | Reality |
|-------|---------|
| Returns InvoiceDTO with 6 fields | Returns 7 fields; `customer_id` is undeclared |
| No sensitive fields leak | `customer_id` is exposed; it is not on the explicit ban list but violates the whitelist contract |
