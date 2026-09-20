### Verdict
**NOT VERIFIED** | **BLOCKING: yes**

---

### Independence
**INDEPENDENT** — The artifact arrived finished in the prompt; it was not authored or revised in this conversation.

---

### Observable evidence
- **Leak of forbidden field `customer_id` (observable):** The SQL query explicitly selects `i.customer_id` on line 17, and line 32 returns `invoice` directly via `res.json(invoice)`. The response contains `{ id, number, amount_cents, status, due_date, customer_id, customer_name }`.
- **Org isolation (observable):** Parameterized query uses `$2` bound to `req.user.org_id` against `i.org_id` and checks `c.org_id = i.org_id`.
- **Missing/cross-org behavior (observable):** If no matching row is returned by `db.oneOrNone`, line 28 returns 404 unconditionally.
- **Malformed ID handling (observable):** Non-integer or non-positive strings fail `!Number.isInteger(id) || id <= 0` and return 400 before DB execution.

---

### Assessment
The artifact fails a strict negative requirement and its explicit DTO shape by over-fetching and directly serializing the database record to JSON without projection or stripping.

---

### Defects

❌ **HIGH — Forbidden field `customer_id` leaked in response**
- *Contract breach:* The contract explicitly mandates the response shape `{ id, number, amount_cents, status, due_date, customer_name }` and forbids `customer_id` ("Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id)").
- *Demonstration:*
  Line 17 selects `i.customer_id`:
  ```sql
  SELECT i.id,
         i.number,
         i.amount_cents,
         i.status,
         i.due_date,
         i.customer_id,
         c.name AS customer_name
  ```
  Line 32 sends the row object directly:
  ```js
  return res.json(invoice);
  ```
  The caller receives `customer_id` in the JSON payload.

---

### Claimed vs. actual

| Property / Claim | Claimed | Actual |
| :--- | :--- | :--- |
| **Response DTO shape** | `{ id, number, amount_cents, status, due_date, customer_name }` | `{ id, number, amount_cents, status, due_date, customer_id, customer_name }` |
| **Field exclusion** | `customer_id` never leaves server | `customer_id` is queried and emitted |
| **Org isolation / 404 behavior** | 404 on missing or foreign org | Matches claim |
| **Malformed ID guard** | 400 returned, never 500 | Matches claim |

---

### Confirm-these
*(None — the contract breach is fully demonstrable from the provided source code).*

---

### How each clean axis was checked
- **Org scoping:** Line 24 binds `req.user.org_id` to `$2` in `WHERE i.id = $1 AND i.org_id = $2`.
- **404 parity for non-existent vs foreign org:** Line 28 checks `!invoice` and returns 404 with identical payloads in both cases.
- **Malformed ID input validation:** Lines 5–8 parse and validate `req.params.id` with `Number.isInteger` and `<= 0`, returning 400 prior to SQL execution.
