Based on the provided contract and artifact, the code **fails** the verification. It violates the third clause of the contract regarding data leakage.

Here is the breakdown of the artifact against the contract:

**1. Returns one invoice ... as an InvoiceDTO: `{ id, number, amount_cents, status, due_date, customer_name }`**
*   **VIOLATION:** The SQL query selects an extra field: `i.customer_id`. Because the route directly passes the database result to the response (`res.json(invoice)`), this extra field is included in the JSON payload sent to the client.

**2. An invoice in another organization, or one that doesn't exist, returns the same 404.**
*   **PASS:** The SQL query enforces the organization check (`AND i.org_id = $2`), and `db.oneOrNone` will return a null/falsy value whether the ID doesn't exist at all or just belongs to another org. The subsequent `if (!invoice)` block catches both scenarios and safely returns a generic 404.

**3. Nothing else about the invoice or the customer leaves the server (no ..., `customer_id`).**
*   **VIOLATION:** As noted above, `customer_id` is explicitly requested in the `SELECT` statement and leaves the server via `res.json(invoice)`. 

**4. Malformed ids never produce a 500.**
*   **PASS:** The code correctly intercepts non-integers, negative numbers, and `NaN` (which fails the `Number.isInteger` check) and returns a 400 Bad Request before the database query is ever executed.

### How to fix it:
To comply with the contract, you should either remove `i.customer_id` from the SQL `SELECT` statement, or explicitly map the DTO before sending the response:

**Option A: Fix the SQL Query**
```sql
SELECT i.id,
       i.number,
       i.amount_cents,
       i.status,
       i.due_date,
       c.name AS customer_name
```

**Option B: Map the DTO in JavaScript (Defense in Depth)**
```javascript
return res.json({
  id: invoice.id,
  number: invoice.number,
  amount_cents: invoice.amount_cents,
  status: invoice.status,
  due_date: invoice.due_date,
  customer_name: invoice.customer_name
});
```
