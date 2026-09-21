**NOT VERIFIED**

Two contract violations:

- **Forbidden field disclosure:** The query selects `i.customer_id`, and `res.json(invoice)` sends it to the caller. Remove it from the query and explicitly construct the six-field `InvoiceDTO`.
- **Malformed IDs can produce a 500:** `Number.isInteger()` accepts unsafe integers and values outside the database column’s range. For example, `1e100` passes this check but can cause a database integer overflow, which the catch block returns as 500. Validate the raw ID’s decimal syntax and enforce the database column’s supported positive range before querying.

The organization predicates correctly scope both the invoice and customer. Missing invoices and invoices outside the caller’s organization follow the same 404 response path.

This verdict is based on static inspection of the supplied artifact; no runtime tests were performed.
