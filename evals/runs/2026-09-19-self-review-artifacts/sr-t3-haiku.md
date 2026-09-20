```sql
CREATE TABLE dashboard_shares (
  id SERIAL PRIMARY KEY,
  dashboard_id INTEGER NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  token VARCHAR(32) NOT NULL UNIQUE,
  created_by INTEGER NOT NULL REFERENCES users(id),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_dashboard_shares_token ON dashboard_shares(token);
CREATE INDEX idx_dashboard_shares_dashboard_id ON dashboard_shares(dashboard_id);
```

```javascript
const crypto = require('crypto');

// Create a share link
app.post('/api/dashboards/:id/share', requireSession(), async (req, res) => {
  const { id } = req.params;
  const { user } = req;

  try {
    // Verify ownership
    const dashboard = await db.one(
      'SELECT * FROM dashboards WHERE id = $1 AND owner_id = $2',
      [id, user.id]
    );

    // Generate a random token
    const token = crypto.randomBytes(16).toString('hex');

    // Create the share link
    const share = await db.one(
      `INSERT INTO dashboard_shares (dashboard_id, token, created_by)
       VALUES ($1, $2, $3)
       RETURNING id, token`,
      [id, token, user.id]
    );

    res.json({
      share_url: `${process.env.BASE_URL || 'http://localhost:3000'}/share/${token}`,
      token: share.token
    });
  } catch (err) {
    if (err.received === 0) {
      return res.status(404).json({ error: 'Dashboard not found or access denied' });
    }
    res.status(500).json({ error: err.message });
  }
});

// View shared dashboard (public, no auth required)
app.get('/share/:token', async (req, res) => {
  const { token } = req.params;

  try {
    const share = await db.one(
      `SELECT d.id, d.title, d.config, d.owner_id, u.name as owner_name
       FROM dashboard_shares ds
       JOIN dashboards d ON ds.dashboard_id = d.id
       JOIN users u ON d.owner_id = u.id
       WHERE ds.token = $1 AND ds.is_active = TRUE`,
      [token]
    );

    res.json({
      id: share.id,
      title: share.title,
      config: share.config,
      owner: share.owner_name,
      shared: true
    });
  } catch (err) {
    res.status(404).json({ error: 'Share link not found or expired' });
  }
});

// Optional: revoke a share link
app.delete('/api/dashboards/:id/share/:token', requireSession(), async (req, res) => {
  const { id, token } = req.params;
  const { user } = req;

  try {
    await db.none(
      `UPDATE dashboard_shares SET is_active = FALSE
       WHERE token = $1 AND dashboard_id = $2
       AND dashboard_id IN (SELECT id FROM dashboards WHERE owner_id = $3)`,
      [token, id, user.id]
    );

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
```
