**NOT VERIFIED**

Two contract violations:

- **`customer_id` leaks in successful responses.** The query selects `i.customer_id`, and `res.json(invoice)` returns it. The contract explicitly forbids this field. Remove it from the selection and construct the response using only the six `InvoiceDTO` fields.
- **ID validation can allow malformed IDs to reach the database and produce a 500.** `Number.isInteger` accepts integers outside JavaScript’s safe range, including `1e100`. If the database rejects that value as out of range, the catch block returns 500. `Number()` also accepts noncanonical forms such as `0x10` and `1e3`. Validate the raw string as positive decimal digits and enforce the database ID type’s range before querying.

The organization filter and customer join enforce the stated organization boundaries. Missing and other-organization invoices take the same 404 path. The query does not select the other prohibited fields.

This is a static review of the supplied code; runtime behavior and database types were not provided or tested.
