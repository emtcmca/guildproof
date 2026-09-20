**The artifact does not meet the contract.**

- **Forbidden field leaks:** The query selects `i.customer_id`, and `res.json(invoice)` returns it. Remove that column and explicitly construct the response using only the six `InvoiceDTO` fields.
- **ID validation is insufficient:** `Number.isInteger` accepts unsafe integers and values beyond the database column’s range. For example, `1e100` passes validation and could cause a database range error, resulting in a 500. Validate the raw ID’s decimal syntax and its supported database range before querying; avoid precision loss during conversion.

The organization filtering is correct: both missing invoices and invoices outside the caller’s organization produce the same 404 response. The customer join also enforces matching organizations.

One conditional issue: the inner join returns 404 for an existing, authorized invoice if no matching customer exists. This satisfies the contract only if database constraints guarantee that a matching customer always exists.
