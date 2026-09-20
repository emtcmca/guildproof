```js
// GET /api/invoices/:id
// Returns one invoice plus its customer's name. Only invoices in the caller's org are visible.
router.get('/api/invoices/:id', requireSession(), async (req, res) => {
  // Reject anything that isn't a positive integer before it reaches the DB
  const id = Number(req.params.id);
  if (!Number.isInteger(id) || id <= 0) {
    return res.status(400).json({ error: 'Invalid invoice id' });
  }

  try {
    const invoice = await db.oneOrNone(
      `SELECT i.id,
              i.number,
              i.amount_cents,
              i.status,
              i.due_date,
              i.customer_id,
              c.name AS customer_name
         FROM invoices i
         JOIN customers c
           ON c.id = i.customer_id
          AND c.org_id = i.org_id        -- customer must be in the same org as the invoice
        WHERE i.id = $1
          AND i.org_id = $2`,            -- and the invoice must be in the caller's org
      [id, req.user.org_id]
    );

    // A missing invoice and another org's invoice both return 404, so callers can't probe which IDs exist
    if (!invoice) {
      return res.status(404).json({ error: 'Invoice not found' });
    }

    return res.json(invoice);
  } catch (err) {
    logger.error({ err, invoiceId: id, userId: req.user.id }, 'Failed to fetch invoice');
    return res.status(500).json({ error: 'Internal server error' });
  }
});
```
