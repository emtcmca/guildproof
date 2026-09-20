## VERDICT
**NOT VERIFIED** — BLOCKING: YES

---

## INDEPENDENCE
**INDEPENDENT.** The artifact arrived finished (pasted into the conversation); I did not produce or revise it.

---

## OBSERVABLE EVIDENCE

### ❌ **Critical Defect: `customer_id` leaks in the response**

**The SELECT clause includes a field that the contract forbids:**

```js
SELECT i.id,
       i.number,
       i.amount_cents,
       i.status,
       i.due_date,
       i.customer_id,              // ← LINE 10: LEAKS
       c.name AS customer_name
  FROM invoices i
```

**The contract specifies InvoiceDTO as:** `{ id, number, amount_cents, status, due_date, customer_name }`

**No `customer_id`.**

**The response at line 25 returns the entire `invoice` object:**
```js
return res.json(invoice);
```

This means every successful call leaks the internal `customer_id` to the caller. A client with this ID can:
- Probe the `/api/customers/:id` endpoint (if it exists) to enumerate other customers in their org
- Correlate customers across external systems using the internal ID as a cross-reference key
- Construct IDOR attacks on other endpoints by re-using the discovered ID

**How to demonstrate:** Call `GET /api/invoices/1` and observe the response includes a `customer_id` field.

---

## AXES CHECKED ✅

| Axis | Finding | Check Method |
|------|---------|--------------|
| **Authorization/IDOR** | ✅ Correct | Line 12: `c.org_id = i.org_id` + Line 14: `i.org_id = $2` double-check that customer belongs to the invoice's org, and invoice belongs to the caller's org. No leakage across orgs. |
| **Malformed IDs** | ✅ Safe | Lines 6–9: `Number.isInteger(id) \|\| id <= 0` check prevents 500 on bad input; returns 400 instead. |
| **404 opacity** | ✅ Correct | Lines 20–22: missing invoice and other-org invoice both return 404. No information leakage about which case. |
| **Sensitive fields suppressed** | ✅ Mostly clean | No `email`, `tax_id`, `payment_token`, `portal_password_hash`, `org_id` in the SELECT. But `customer_id` **should not be in the SELECT at all**. |
| **SQL injection** | ✅ Safe | Parameterized query ($1, $2); no string interpolation. |
| **Auth gate** | ✅ Gated | `requireSession()` middleware blocks unauthenticated access. |
| **500 error suppression** | ✅ Clean | Try-catch returns 500 only on unexpected DB failures, not on validation failures. |

---

## DEFECTS

**❌ MEDIUM severity — `customer_id` information leak**
- **Contract breach:** The InvoiceDTO spec lists six fields; the response includes seven.
- **Real attack surface:** Internal customer IDs can be enumerated, correlated, or reused to attack other endpoints.
- **Impact:** Breaks the stated data boundary of the endpoint.
- **Fix:** Remove `i.customer_id` from the SELECT clause (line 10).

---

## CLAIMED VS. ACTUAL

| Claim | Reality |
|-------|---------|
| "No sensitive fields leave the server" | ✅ Mostly true, but `customer_id` (an internal identifier) leaks. |
| "Only invoices in the caller's org are visible" | ✅ Correct isolation enforced in the WHERE and JOIN. |
| "Malformed ids never produce a 500" | ✅ Correct; bad input → 400. |

---

## CONFIRM-THESE

None. The contract is explicit, the code is readable, and the defect is observable on every invocation.

---

## HOW CLEAN AXES WERE CHECKED

- **Authorization:** Verified `org_id` is checked in both the JOIN (line 12) and WHERE (line 14) against `req.user.org_id` (line 15, parameter $2).
- **Malformed IDs:** Confirmed `Number.isInteger()` check at line 7 gates the DB call; non-integer input returns 400 (line 8).
- **404 opacity:** Verified both missing and other-org invoices hit the `if (!invoice)` condition (line 20), returning the same 404 response.
- **Sensitive fields:** Line-by-line check of SELECT clause — no email, tax_id, payment_token, portal_password_hash, org_id. Only `customer_id` violates the contract.
- **SQL injection:** Query uses `$1`, `$2` placeholders; `req.user.org_id` is from the session context, not user input.

---

**This endpoint must have the `customer_id` field removed from the SELECT before shipping.**
