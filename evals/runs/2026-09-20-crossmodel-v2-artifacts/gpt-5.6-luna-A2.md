Does not fully satisfy the contract.

- Organization isolation and indistinguishable 404s are implemented correctly.
- Malformed numeric IDs are rejected before the database call, so they should not produce a 500.
- The response leaks `customer_id`, which is not part of `InvoiceDTO` and is explicitly forbidden.

Fix by removing `i.customer_id` from the `SELECT` list. Optionally validate IDs more strictly if only decimal path IDs are intended; `Number()` accepts forms such as `0x10` and scientific notation.
