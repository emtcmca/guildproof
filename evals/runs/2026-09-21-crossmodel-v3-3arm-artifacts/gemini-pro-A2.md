Based on a review of the provided artifact against the contract, the implementation **fails** to strictly meet the contract requirements due to a data leakage issue. 

Here is the breakdown of the verification:

### 1. Data Contract & Leakage Prevention: ❌ FAILS
*   **Contract:** The endpoint must return an `InvoiceDTO` with exactly `{ id, number, amount_cents, status, due_date, customer_name }`. It explicitly states that **nothing else leaves the server** (including `customer_id`).
*   **Implementation:** The SQL query explicitly selects `i.customer_id`, and the endpoint passes the raw database result directly to the client via `return res.json(invoice);`. 
*   **Fix:** Remove `i.customer_id` from the `SELECT` statement, or explicitly map the properties into a new DTO object before sending the JSON response.

### 2. Cross-Organization / Missing Invoice Handling: ✅ PASSES
*   **Contract:** Invoices from other organizations or non-existent invoices must return the exact same `404`.
*   **Implementation:** By enforcing `i.org_id = $2` directly in the parameterized database query, the database will return `null` (or equivalent) for both missing invoices and unauthorized invoices. The application identically handles the missing row (`if (!invoice)`) by returning a generic `404 Not Found`, successfully preventing ID enumeration/probing.

### 3. Error Handling for Malformed IDs: ⚠️ PASSES (with a minor caveat)
*   **Contract:** Malformed IDs never produce a `500`.
*   **Implementation:** The code uses `Number.isInteger(id)` and `id <= 0` to catch floats, strings, negative numbers, and `NaN`, safely returning a `400 Bad Request`.
*   *Caveat:* JavaScript's `Number.MAX_SAFE_INTEGER` is `9,007,199,254,740,991`. If the database schema uses a standard 32-bit `INTEGER` for the `id` column (max value `2,147,483,647`), a user passing a perfectly valid integer like `3000000000` will pass the Express validation but throw an "out of range" error in the database. This would be caught by the `catch` block and result in a `500 Internal Server Error`. If the DB uses a 32-bit int, you should add an upper-bound check (e.g., `id > 2147483647`).
