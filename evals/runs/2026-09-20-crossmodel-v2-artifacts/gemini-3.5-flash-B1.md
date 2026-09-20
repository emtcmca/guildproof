### Verdict
**NOT VERIFIED** — **BLOCKING: YES**  
The artifact fails its contract on two separate fronts: it leaks restricted information (`customer_id`) to the API caller, and it allows large integer inputs to bypass validation and trigger a `500 Internal Server Error` from the database.

### Independence
**INDEPENDENT** — The artifact and contract were provided externally; I had no role in drafting, authoring, or revising either.

---

### Observable evidence
1. **Data Leakage (`customer_id`):** 
   - Line 17 of the artifact explicitly queries `i.customer_id` from the database.
   - Line 31 directly returns the raw query result to the client via `res.json(invoice)`.
   - The contract explicitly states: *"Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id)."*

2. **Database Integer Overflow (Produces `500` status):**
   - Line 7 validates the ID parameter using `Number.isInteger(id)`. 
   - A value such as `2147483648` (exceeding standard PostgreSQL 32-bit signed integer limits) returns `true` for `Number.isInteger()`, passing the guard.
   - When executed by the database driver, the database throws a numeric out-of-range error (`22003`), triggering the `catch (err)` block on Line 33.
   - Line 35 responds with a `500 Internal Server Error` instead of a validation error or standard `404` status, violating the contract: *"Malformed ids never produce a 500."*

---

### Assessment
- It is highly probable that the database uses a standard 32-bit signed `INTEGER` for the primary key `id`. If so, any valid JS integer larger than `2147483647` and smaller than `Number.MAX_SAFE_INTEGER` will reliably trigger the DB-level range error and subsequent `500` response. 
- Even if the DB column type is a 64-bit `BIGINT`, a value exceeding standard limits or any JS integer value that loses precision (e.g., `99999999999999999999`) will trigger parser or binding errors inside the database driver before reaching PostgreSQL, generating a `500` response.

---

### Defects

#### ❌ HIGH — Direct Information Leakage of restricted attribute (`customer_id`)
- **Contract Breach:** The contract explicitly bans the transmission of `customer_id` outside of the server.
- **Demonstration:**
  An HTTP request is made to `GET /api/invoices/123`. The server queries the database, binds `customer_id` to the returned object, and responds with:
  ```json
  {
    "id": 123,
    "number": "INV-1001",
    "amount_cents": 5000,
    "status": "PAID",
    "due_date": "2023-12-31",
    "customer_id": 456,          // <--- LEAKED RESTRICTED FIELD
    "customer_name": "ACME Corp"
  }
  ```

#### ⚠️ MEDIUM — Database Error Leaking as a `500` status on out-of-range IDs
- **Contract Breach:** *"Malformed ids never produce a 500."*
- **Demonstration:**
  Make a request to `GET /api/invoices/2147483648`.
  - `Number.isInteger(2147483648)` evaluates to `true`.
  - The database query executes with `$1 = 2147483648`.
  - PostgreSQL throws `error: integer out of range`.
  - The exception is caught by the query try-catch block and logs an error, returning `500 Internal Server Error` to the user.

---

### Claimed vs. actual

| Feature / Behavior | Claimed by Contract | Actual Artifact Behavior |
| :--- | :--- | :--- |
| **Response Fields** | `{ id, number, amount_cents, status, due_date, customer_name }` | Also includes **`customer_id`** in the response. |
| **Exclusion of `customer_id`** | Strictly hidden from client. | Exposed directly. |
| **Out-of-range IDs** | Must not cause a `500` error. | Causes a `500 Internal Server Error` via database overflow exceptions. |

---

### Confirm-these
*Verify these assumptions in your deployment environment:*
1. **DB Column Types:** Confirm whether `invoices.id` is defined as a standard 32-bit `INTEGER` or a 64-bit `BIGINT`. If standard, the validation ceiling must be clamped to `2147483647` to avoid the database exception.
2. **Session Context:** Confirm that `requireSession()` ensures that `req.user` and `req.user.org_id` are always populated; otherwise, accessing `req.user.org_id` will throw a `TypeError` and crash the execution path into a `500` response.

---

### How each clean axis was checked
- **Organization Boundary Enforcement:** Checked lines 23-24 (`AND i.org_id = $2`) and matching line 25 parameter binding `req.user.org_id`. This correctly restricts results only to the caller's organization.
- **Uniform 404 Response:** Checked lines 28-30. If no record is found (whether due to nonexistence or organization mismatch), the returned query response is falsy and yields a `404 Not Found` payload.
- **Join Consistency:** Checked lines 19-22. It ensures customers are locked down to the same organization as the invoice during the join, preventing cross-tenant leakage of customer names.
