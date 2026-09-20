**Fails the contract in two places:**

- **Leaks `customer_id`.** The query selects `i.customer_id`, and `res.json(invoice)` sends it to the caller. Remove it from the SELECT and explicitly construct the six-field `InvoiceDTO`.
- **Malformed IDs can reach the DB and produce a 500.** `Number.isInteger()` accepts unsafe integers such as `9007199254740993` after rounding, and large values such as `1e100`. Values outside the database ID type’s range can cause a database error that becomes a 500. `Number()` also accepts formats such as `1e2` and `0x10`. Validate the raw string as decimal digits and enforce the database ID range before querying.

**Passes:** The organization filter makes nonexistent and other-organization invoices return the same 404. The customer join also enforces organization consistency. No other prohibited fields are selected.

**Conditional issue:** The inner join returns 404 for an existing authorized invoice if its customer is missing or belongs to another organization. Returning every authorized invoice therefore depends on database constraints guaranteeing a matching customer.
