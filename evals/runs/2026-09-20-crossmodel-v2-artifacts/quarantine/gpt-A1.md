**The artifact fails the contract in two places:**

1. **It exposes `customer_id`.** The query selects `i.customer_id`, and `res.json(invoice)` sends it to the caller. Remove it from the selection and explicitly construct the six-field `InvoiceDTO`.

2. **ID validation can allow database errors that become 500s.** `Number.isInteger` accepts integers beyond JavaScript’s safe range or the database column’s range. Such values can reach the database and cause an out-of-range error. `Number()` also accepts formats such as `1e3` and `0x10`, despite the comment’s stricter implication. Validate decimal syntax and the database ID range before querying; avoid lossy numeric conversion.

**What passes:** The invoice is scoped to `req.user.org_id`, the customer join enforces the same organization, and missing and other-organization invoices return the identical 404 response. The other prohibited fields are not selected.
