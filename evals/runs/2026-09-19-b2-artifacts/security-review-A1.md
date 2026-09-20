# Security Review: Dashboard Share Links

## High-Risk Findings

### 1. No Rate Limiting on Token Guessing
**Severity: HIGH**

The `/share/:token` endpoint accepts any token without rate limiting. An attacker can brute-force 32-character hex tokens at scale.

**Fix:** Implement rate limiting per IP/session:
- Rate limit `/share/:token` to 5-10 requests per minute per IP
- Track failed attempts; ban after N failures
- Use Redis or in-memory cache for DDoS resistance

### 2. No Token Expiration
**Severity: MEDIUM-HIGH**

Share links persist indefinitely unless manually revoked. If a token leaks, it remains valid forever.

**Fix:** Add expiration to `dashboard_shares`:
```sql
ALTER TABLE dashboard_shares ADD COLUMN expires_at TIMESTAMP;
ALTER TABLE dashboard_shares ADD COLUMN expiration_days INTEGER DEFAULT 30;

-- In retrieval query:
AND (ds.expires_at IS NULL OR ds.expires_at > CURRENT_TIMESTAMP)
```

### 3. No Share Link Access Logging
**Severity: MEDIUM**

No audit trail of who accessed a shared link. Impossible to detect if a token was compromised.

**Fix:** Create an `access_log` table:
```sql
CREATE TABLE share_access_log (
  id SERIAL PRIMARY KEY,
  share_id INTEGER REFERENCES dashboard_shares(id),
  accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ip_address INET,
  user_agent TEXT
);

-- Log on GET /share/:token:
INSERT INTO share_access_log (share_id, ip_address, user_agent) 
VALUES ($1, $2, $3)
```

---

## Medium-Risk Findings

### 4. Missing CSRF Protection on Revoke
**Severity: MEDIUM**

The DELETE endpoint uses `requireSession()` but CSRF tokens aren't shown in the code. Cross-site requests could revoke shares.

**Fix:** Ensure CSRF token validation is applied:
```javascript
app.delete('/api/dashboards/:id/share/:token', 
  requireSession(), 
  validateCsrfToken(), // Must be present
  async (req, res) => { ... }
);
```

### 5. No Visibility into Share Ownership
**Severity: MEDIUM**

Users cannot list or manage all shares they've created. A compromised session could have created shares unknown to the user.

**Fix:** Add endpoint to list all shares:
```javascript
app.get('/api/dashboards/:id/shares', requireSession(), async (req, res) => {
  const shares = await db.any(
    `SELECT id, token, created_at, is_active 
     FROM dashboard_shares 
     WHERE dashboard_id = $1 
     AND dashboard_id IN (SELECT id FROM dashboards WHERE owner_id = $2)`,
    [req.params.id, req.user.id]
  );
  res.json(shares);
});
```

### 6. Information Disclosure via Error Messages
**Severity: LOW-MEDIUM**

The catch block at line 74-76 returns generic "Share link not found or expired" for all errors. This is actually good — no information leakage — but any database error would leak to the client at line 94. 

**Fix:** Log errors server-side only:
```javascript
} catch (err) {
  console.error('Revoke share error:', err);
  res.status(500).json({ error: 'Failed to revoke share' });
}
```

---

## Low-Risk Findings

### 7. No Share Link Rotation
**Severity: LOW**

If a token becomes known, there's no way to rotate it without deleting and recreating (downtime).

**Fix:** Add rotation endpoint that generates a new token while keeping old one briefly active.

### 8. Missing Content Security Policy for Shared Dashboards
**Severity: LOW**

Shared dashboards inherit `dashboard.config` without validation. If `config` contains user input, XSS is possible.

**Fix:** Validate and sanitize `config` on both retrieval paths:
```javascript
const config = JSON.parse(share.config);
// Sanitize config before sending to client
res.json({
  ...share,
  config: sanitizeConfig(config) // Implement sanitizer
});
```

---

## Recommendations (Priority Order)

1. **Immediate:** Add rate limiting to `/share/:token`
2. **Immediate:** Add token expiration (default 30 days, configurable per share)
3. **Soon:** Implement share access logging
4. **Soon:** Add endpoint to list and manage created shares
5. **Soon:** Verify CSRF protection is in place
6. **Ongoing:** Audit `dashboard.config` for XSS vulnerabilities

---

## What's Working Well

- ✓ Parameterized SQL queries (no SQL injection)
- ✓ Ownership verification before share creation
- ✓ Proper session requirement on authenticated endpoints
- ✓ Safe error messages on public endpoints
- ✓ Soft delete via `is_active` flag (allows audit recovery)
