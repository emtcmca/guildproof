### Verdict
**NOT VERIFIED**
**BLOCKING: Yes** — A high-severity data leakage defect exists where an forbidden database identifier is exposed to the client, directly violating the contract constraints.

---

### Independence
**INDEPENDENT** — The artifact was provided complete, and this review was performed independently without participating in its generation or modification.

---

### Observable evidence

#### ❌ Real Defect: Leakage of `customer_id` (HIGH Severity)
* **Contract Breach:** The contract explicitly states: *"Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, **customer_id**)."*
* **Demonstration:**
  The SQL query selects `i.customer_id`:
  ```sql
  SELECT i.id,
         ...
         i.customer_id,
         c.name AS customer_name
  ```
  The router then serializes this query output directly to the HTTP response body:
  ```js
  return res.json(invoice);
  ```
  As a result, the returned JSON payload includes the forbidden `"customer_id"` property (e.g., `{"id":123,"number":"INV-01","customer_id":456,"customer_name":"Acme Corp"}`), violating the data exclusion requirement.

---

### Assessment

#### ⚠️ Potential Defect: Large Out-of-Bounds Integers leading to DB Error / 500 (LOW Severity)
* **Contract Breach:** The contract states: *"Malformed ids never produce a 500."*
* **Demonstration:**
  The router attempts to validate the ID with `Number.isInteger(id)`. In JavaScript, very large numbers represented in scientific notation (e.g., `1e21`) return `true` for `Number.isInteger(1e21)`.
  If a client passes an extremely large integer, it will pass the validation check, reach the database driver (`pg` / `pg-promise`), and likely trigger an `"integer out of range"` database driver exception. This exception is caught in the `catch` block and returns a `500 Internal Server Error`, potentially violating the "never produce a 500" rule for edge-case numeric payloads. Utilizing `Number.isSafeInteger(id)` would prevent this.

---

### Claimed vs. Actual

| Contract Requirement | Actual Behavior | Status |
| :--- | :--- | :--- |
| Returns invoice belonging to caller's org as `InvoiceDTO` | Returns correct fields but appends forbidden fields | ❌ **FAIL** |
| Missing or cross-org invoices return the same 404 | Both scenarios result in `!invoice` and return 404 | ✅ **PASS** |
| No forbidden properties leave the server | Directly leaks `customer_id` via serialization | ❌ **FAIL** |
| Malformed IDs never produce a 500 | Handled correctly via validation, except for extreme integer overflows | ⚠️ **PARTIAL** |

---

### Confirm-these
* **`requireSession()` Guard Contract:** Verify that the `requireSession()` middleware guarantees that `req.user` is defined and contains populated, valid `id` and `org_id` properties. If `req.user` is undefined, accessing `req.user.org_id` will raise a unhandled `TypeError` inside the route handler.

---

### How each clean axis was checked
* **404 path (missing or unauthorized invoice):** Traced to lines 27–30 where `!invoice` (which is the result of a non-matching ID or non-matching `org_id` in SQL) explicitly triggers `res.status(404).json(...)`.
* **SQL Injection Prevention:** Traced to parameterized input mapping on line 24 (`[id, req.user.org_id]`), ensuring the dynamic ID parameter is sanitized at the database driver level.
* **Non-integer ID validation:** Traced to lines 5–8 where string-based IDs (like `"/api/invoices/abc"`) or fractional IDs yield `NaN` or non-integers, triggering an early exit with status `400`.
