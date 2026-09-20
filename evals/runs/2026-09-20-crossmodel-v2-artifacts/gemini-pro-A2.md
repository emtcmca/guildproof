Based on a review of the provided code against the contract, the implementation violates the contract's data exposure requirement.

Here is the breakdown of the verification:

**1. Data Leakage (Failed)**
*   **Contract:** *Nothing else about the invoice or the customer leaves the server (no email, tax_id, payment_token, portal_password_hash, org_id, customer_id).*
*   **Artifact:** The SQL query explicitly selects `i.customer_id`. Because `res.json(invoice)` serializes and returns the entire resulting object, `customer_id` is leaked to the client. 
*   **Fix:** Remove `i.customer_id` from the `SELECT` statement, or explicitly map the properties into a new `InvoiceDTO` object before passing it to `res.json()`.

**2. Return one invoice for the caller's organization (Passed)**
*   **Contract:** *Returns one invoice that belongs to the caller's organization.*
*   **Artifact:** The SQL query enforces this correctly by filtering `WHERE i.id = $1 AND i.org_id = $2` using `req.user.org_id`. It also safely ensures the customer belongs to the same org via the `JOIN` condition.

**3. Indistinguishable 404s (Passed)**
*   **Contract:** *An invoice in another organization, or one that doesn't exist, returns the same 404.*
*   **Artifact:** If the database returns no row (which happens both if the ID doesn't exist or if `i.org_id` doesn't match the caller), the code returns a generic `404 Not Found`, preventing ID probing.

**4. Malformed IDs (Passed)**
*   **Contract:** *Malformed ids never produce a 500.*
*   **Artifact:** The code safely parses the input using `Number()` and validates `!Number.isInteger(id) || id <= 0`, returning a `400 Bad Request` before the database is ever queried. This effectively prevents SQL-related 500 errors from malformed types (like strings or UUIDs).
