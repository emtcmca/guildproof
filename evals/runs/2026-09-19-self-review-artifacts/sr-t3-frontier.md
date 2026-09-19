**Migration**

```sql
CREATE TABLE dashboard_share_links (
  id            serial PRIMARY KEY,
  dashboard_id  int NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
  token_hash    text NOT NULL UNIQUE,          -- sha256 of the token, never the token itself
  created_by    int NOT NULL REFERENCES users(id),
  created_at    timestamptz NOT NULL DEFAULT now(),
  expires_at    timestamptz,                   -- NULL = no expiry
  revoked_at    timestamptz
);

CREATE INDEX dashboard_share_links_dashboard_id_idx ON dashboard_share_links (dashboard_id);
```

**Routes**

```js
const crypto = require('crypto');
const express = require('express');
const router = express.Router();

// The raw token only ever exists in the URL we hand back. The DB stores a hash,
// so a leaked DB dump or backup does not hand out working links.
const hashToken = (token) => crypto.createHash('sha256').update(token).digest('hex');

// 32 random bytes -> 43 base64url chars. Reject anything else before touching the DB.
const TOKEN_RE = /^[A-Za-z0-9_-]{43}$/;

const DEFAULT_TTL_DAYS = 30;
const MAX_TTL_DAYS = 365;

// Build links from config, not from req.get('host'). The Host header is
// client-controlled, and trusting it lets someone mint links pointing at their domain.
const PUBLIC_BASE_URL = process.env.PUBLIC_BASE_URL; // e.g. https://app.example.com

function parseId(value) {
  const n = Number(value);
  return Number.isSafeInteger(n) && n > 0 ? n : null;
}

// Create a share link. Owner only, inside the owner's org.
router.post('/api/dashboards/:id/share', requireSession(), async (req, res, next) => {
  try {
    const dashboardId = parseId(req.params.id);
    if (!dashboardId) return res.status(404).json({ error: 'Not found' });

    // Owner AND org both match. A non-owner gets the same 404 as a missing
    // dashboard, so the endpoint can't be used to probe which IDs exist.
    const dash = await db.oneOrNone(
      `SELECT id FROM dashboards
        WHERE id = $1 AND org_id = $2 AND owner_id = $3`,
      [dashboardId, req.user.org_id, req.user.id]
    );
    if (!dash) return res.status(404).json({ error: 'Not found' });

    let ttlDays = DEFAULT_TTL_DAYS;
    if (req.body && req.body.expiresInDays !== undefined) {
      const n = Number(req.body.expiresInDays);
      if (!Number.isInteger(n) || n < 1 || n > MAX_TTL_DAYS) {
        return res.status(400).json({ error: `expiresInDays must be 1-${MAX_TTL_DAYS}` });
      }
      ttlDays = n;
    }

    const token = crypto.randomBytes(32).toString('base64url');

    const link = await db.one(
      `INSERT INTO dashboard_share_links (dashboard_id, token_hash, created_by, expires_at)
       VALUES ($1, $2, $3, now() + make_interval(days => $4))
       RETURNING id, expires_at`,
      [dashboardId, hashToken(token), req.user.id, ttlDays]
    );

    res.status(201).json({
      id: link.id,
      url: `${PUBLIC_BASE_URL}/share/${token}`,
      expiresAt: link.expires_at,
    });
  } catch (err) {
    next(err);
  }
});

// Revoke a share link. Same owner check, done through the join.
router.delete('/api/dashboards/:id/share/:linkId', requireSession(), async (req, res, next) => {
  try {
    const dashboardId = parseId(req.params.id);
    const linkId = parseId(req.params.linkId);
    if (!dashboardId || !linkId) return res.status(404).json({ error: 'Not found' });

    const result = await db.result(
      `UPDATE dashboard_share_links l
          SET revoked_at = now()
         FROM dashboards d
        WHERE l.id = $1
          AND l.dashboard_id = $2
          AND l.revoked_at IS NULL
          AND d.id = l.dashboard_id
          AND d.org_id = $3
          AND d.owner_id = $4`,
      [linkId, dashboardId, req.user.org_id, req.user.id]
    );
    if (result.rowCount === 0) return res.status(404).json({ error: 'Not found' });
    res.status(204).end();
  } catch (err) {
    next(err);
  }
});

// Public read-only view. No session.
router.get('/share/:token', async (req, res, next) => {
  // Set these first so they also apply to the 404. The token is in the URL, so:
  //  - no-referrer stops it leaking to any external link or asset the page loads
  //  - no-store keeps it out of shared/proxy caches
  //  - noindex keeps crawlers that find the link from indexing the page
  res.set({
    'Referrer-Policy': 'no-referrer',
    'Cache-Control': 'no-store',
    'X-Robots-Tag': 'noindex, nofollow',
  });

  try {
    const { token } = req.params;
    if (!TOKEN_RE.test(token)) return res.status(404).send('Not found');

    // Select ONLY what the viewer should see. No owner_id, no org_id, and no
    // join to users, so names and emails can't leak through this route.
    const dash = await db.oneOrNone(
      `SELECT d.title, d.config
         FROM dashboard_share_links l
         JOIN dashboards d ON d.id = l.dashboard_id
        WHERE l.token_hash = $1
          AND l.revoked_at IS NULL
          AND (l.expires_at IS NULL OR l.expires_at > now())`,
      [hashToken(token)]
    );

    // Unknown, expired, and revoked all return the same 404, so the response
    // gives no hint about which tokens once existed.
    if (!dash) return res.status(404).send('Not found');

    res.render('dashboard-public', { title: dash.title, config: dash.config, readOnly: true });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
```
