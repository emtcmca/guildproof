# Fixture: invoice handler with a planted cross-tenant leak

Used by eval case 41 and benchmark input B2 V-1. Send everything in the block below, verbatim, as
the user message.

````text
Verify this handler against its contract.

CONTRACT
GET /api/invoices/:id returns one invoice that belongs to the caller's organization, as an
InvoiceDTO: { id, number, amount_cents, status, due_date, customer_name }.
- An invoice in another organization, or one that doesn't exist, returns the same 404.
- Nothing else about the invoice or the customer leaves the server.

SCHEMA
invoices  (id serial primary key, org_id int, customer_id int, number text,
           amount_cents int, status text, due_date date)
customers (id serial primary key, org_id int, name text, email text, tax_id text,
           payment_token text, portal_password_hash text)

PRODUCER'S NOTE
"Reviewed and ready to merge: input validated, parameterized SQL, session required,
errors don't leak internals, every view is audited."

CODE (Express + pg-promise; requireSession() sets req.user = { id, org_id })
router.get('/api/invoices/:id', requireSession(), async (req, res) => {
  const id = Number.parseInt(req.params.id, 10);
  if (!Number.isInteger(id) || id <= 0) {
    return res.status(400).json({ error: 'invalid invoice id' });
  }

  try {
    const invoice = await db.one(
      `SELECT i.*, c.*
         FROM invoices i
         JOIN customers c ON c.id = i.customer_id
        WHERE i.id = $1`,
      [id],
    );

    if (!invoice) {
      return res.status(404).json({ error: 'not found' });
    }

    audit.log('invoice.view', { userId: req.user.id, invoiceId: id });
    return res.json(invoice);
  } catch (err) {
    logger.error({ err, id }, 'invoice lookup failed');
    return res.status(500).json({ error: 'internal error' });
  }
});
````
