app.get('/api/invoices/:id', requireSession(), async (req, res) => {
  const { id } = req.params;
  const { org_id } = req.user;

  try {
    const invoice = await db.oneOrNone(
      `
      SELECT 
        i.id, i.org_id, i.customer_id, i.number, i.amount_cents, i.status, i.due_date,
        c.name as customer_name, c.email as customer_email, c.tax_id
      FROM invoices i
      JOIN customers c ON i.customer_id = c.id
      WHERE i.id = $1 AND i.org_id = $2
      `,
      [id, org_id]
    );

    if (!invoice) {
      logger.warn({ userId: req.user.id, invoiceId: id }, 'Invoice not found or access denied');
      return res.status(404).json({ error: 'Invoice not found' });
    }

    audit.log('invoice_viewed', {
      userId: req.user.id,
      invoiceId: invoice.id,
      orgId: org_id
    });

    res.json(invoice);
  } catch (err) {
    logger.error({ err, userId: req.user.id, invoiceId: id }, 'Failed to fetch invoice');
    res.status(500).json({ error: 'Internal server error' });
  }
});