=== OUTPUT W ===

## Attack Surface

**Untrusted inputs:** `:id` (dashboard ID), `:token` (share token) from URL params. No request body validation shown in create endpoint.

**Trust boundary:** Authenticated share creators ↔ unauthenticated public consumers. The public GET endpoint requires only a token string; no authentication or rate limiting is visible.

**Data flow:** `requireSession()` gates both create and revoke; the public read endpoint has zero gates. Any user knowing a valid token can read the full dashboard plus its config field. Database is the sink; parameterized queries are present.

---

## Findings

**⚠️ HIGH — Uncontrolled data exposure in config field**
- **Vector:** Public GET /share/:token returns `d.config` unfiltered to unauthenticated users.
- **Impact:** If config contains API keys, secrets, or sensitive settings, they are readable by anyone holding the token. No indication of what config contains or whether it should be redacted.
- **Fix:** Validate and filter the config field before returning it on the public endpoint. Define what is safe to expose in a shared view and strip the rest. Document the filtering rule.

**⚠️ HIGH — No permission granularity on share links**
- **Vector:** Share links grant unrestricted read access to the entire dashboard (and implicitly, any fields that might carry write permissions if the frontend is the only authz gate).
- **Impact:** No support for read-only shares, expiring shares, or field-level access control. A leaked token grants full visibility forever.
- **Fix:** Add a `permission_level` enum column to `dashboard_shares` (e.g., READ, EDIT) and enforce it in both endpoints. Return only the fields appropriate to the permission level.

**⚠️ MEDIUM — No rate limiting on public share access**
- **Vector:** GET /share/:token has no rate limit visible; returns 404 if not found, signaling whether a token is valid.
- **Impact:** Enables enumeration attacks (testing thousands of tokens to find valid shares) and DoS via high-volume valid requests. The 128-bit token space is large, but the *number of shares in existence* is much smaller; an attacker can discover them.
- **Fix:** Implement rate limiting on the GET endpoint (per IP or global). Consider returning 403 Forbidden instead of 404 to avoid leaking validity. Log access attempts.

**⚠️ MEDIUM — Share links persist indefinitely**
- **Vector:** No expiration timestamp on shares; they remain valid until manually revoked.
- **Impact:** If a share token is leaked or becomes stale, it remains accessible. No automatic cleanup of old shares.
- **Fix:** Add `expires_at` timestamp to `dashboard_shares`. Extend the DELETE endpoint to also mark shares as expired if `expires_at < NOW()`. Return 404 for expired shares.

**⚠️ MEDIUM — No audit logging for share access**
- **Vector:** The GET /share/:token endpoint has no logging; who accessed the share, when, and from where is unrecorded.
- **Impact:** No visibility into whether a share link has been abused, leaked, or accessed unexpectedly. Security incidents involving shared dashboards cannot be investigated.
- **Fix:** Log all requests to GET /share/:token with timestamp, IP, and token (hashed). Alert on unusual access patterns (many requests in short time, access from unexpected geography).

---

## Highest-Severity Issue

The public share endpoint returns the dashboard's full config field without filtering or validation, exposing any secrets embedded in it to anyone holding the token.

---

## Confirm-These

- Does the `config` field contain secrets, API keys, credentials, or other sensitive data that should not be public?
- Is there middleware-level rate limiting on the GET /share/:token endpoint?
- Are share tokens cryptographically random via crypto.randomBytes (answer: yes, visible in code)?
- Is there audit logging for share access (logging not shown in the provided code)?
- Is the dashboard config redacted or filtered before being returned to public users?
- Should shares expire after a time period, or is indefinite validity intentional?
- Is the `/share/:token` endpoint protected by a CORS policy, or can cross-origin requests read it?


=== OUTPUT X ===

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


=== OUTPUT Y ===

## Attack Surface

**Untrusted inputs:** URL token parameter (32-char hex), dashboard IDs in params.  
**Trust boundary:** Public GET endpoint (no auth required) vs. authenticated POST/DELETE (require session).  
**Bearer model:** The token is the sole credential for accessing a shared dashboard; possession = access.

## Findings

**🔴 HIGH — Token brute-force / DoS without rate limiting**  
Vector: GET /share/:token endpoint has no rate limit. An attacker can spam requests with random tokens to enumerate valid shares or trigger DoS.  
Impact: Discovery of shared dashboards, service degradation.  
Likelihood: High; no auth gate, trivial to automate.  
Fix: Add per-IP rate limiting (e.g., 10 requests/minute) to GET /share/:token. Return 429 when exceeded.

**🔴 HIGH — No token expiration; indefinite access from leaked tokens**  
Vector: Tokens are valid forever unless manually revoked via DELETE. A leaked token grants permanent access.  
Impact: Long-lived credentials increase blast radius of compromise. User has no automatic recourse if a share link becomes known.  
Likelihood: Medium; depends on token leakage paths (logs, URLs in email, screenshots, etc.).  
Fix: Add `expires_at` timestamp and check it in the GET query. Recommend short TTL (24–72 hours) with optional manual extension.

**🟡 MEDIUM — Timing attack on token validation**  
Vector: The database lookup for token detection takes measurable time. An attacker can distinguish "token not found" from "token found but inactive" by measuring response timing.  
Impact: Leaks which tokens have been created/used, reducing the effective entropy of the brute-force space.  
Likelihood: Low; requires timing precision and network stability, but feasible.  
Fix: Use constant-time token comparison and ensure the 404 response takes the same time regardless of lookup result (e.g., always query the database, use `EXISTS` rather than `COUNT`).

**🟡 MEDIUM — Dashboard config and metadata exposure without input validation**  
Vector: The GET endpoint returns the full `config` object and `owner_name` publicly. No validation that config is safe for public disclosure.  
Impact: If `config` contains secrets (API keys, webhook URLs, auth tokens), they are exposed to anyone with the token. Owner identity is revealed.  
Likelihood: Medium; depends on what application stores in config and whether it sanitizes before rendering.  
Fix: Return only non-sensitive fields (title, owner_name if desired). Explicitly exclude config, or return a sanitized subset. If config must be returned, document that it is public and audit it for secrets.

**🟡 MEDIUM — No CSRF protection on authenticated endpoints**  
Vector: POST /api/dashboards/:id/share and DELETE endpoint use session auth but show no CSRF token validation or SameSite cookie enforcement.  
Impact: A malicious site can trick an authenticated user into creating/deleting share links without their knowledge.  
Likelihood: Medium; depends on cookie SameSite settings and whether CSRF tokens are validated elsewhere (unshown code).  
Fix: Confirm `SameSite=Strict` or `SameSite=Lax` on session cookies. If not, add CSRF token validation to POST and DELETE endpoints.

**🔵 LOW — Error message leakage in DELETE endpoint**  
Vector: The catch-all returns `err.message` directly to the client.  
Impact: Internal error details (SQL errors, stack traces) could leak implementation information.  
Likelihood: Low; depends on what errors are actually thrown.  
Fix: Replace `err.message` with a generic error message and log the real error server-side.

## Highest-Severity Issue

**No rate limiting + no expiration = indefinite brute-force window.** An attacker can spam GET /share/:token forever, and if they guess a valid token, the access is permanent until manually revoked.

## Confirm These

- **CSRF protection:** Is `SameSite=Strict/Lax` enforced on session cookies? Are CSRF tokens validated on POST/DELETE?
- **Rate limiting:** Is rate limiting applied at the middleware layer (not shown in this snippet)?
- **Config contents:** What fields does the `config` column contain? Does it store secrets that shouldn't be public?
- **Token predictability:** Is `crypto.randomBytes()` properly seeded, or could the RNG be predictable?
- **Deployment model:** Is this endpoint fronted by a WAF or load balancer that might provide rate limiting?


=== OUTPUT Z ===

# Security Review: Dashboard Share Links

## Critical Issues

### 1. Missing Rate Limiting on Public View Endpoint
**Severity: HIGH**
- The `GET /share/:token` endpoint has no rate limiting, allowing unlimited requests from any IP
- While the token uses 128 bits of entropy (strong), an attacker with sufficient resources could attempt brute force enumeration
- **Recommendation:** Implement rate limiting per IP address (e.g., 10 requests per minute), or per-token attempt limits with exponential backoff after failed attempts

### 2. No Token Expiration
**Severity: MEDIUM-HIGH**
- Share links remain active indefinitely unless manually revoked
- If a link is accidentally shared publicly or leaked, it provides permanent access to the dashboard
- No way to automatically invalidate old links
- **Recommendation:** Add optional `expires_at` TIMESTAMP column with configurable expiration (e.g., 7 days, 30 days, never). Implement a cleanup job to soft-delete expired links

### 3. No Access Audit Trail
**Severity: MEDIUM**
- The public view endpoint does not log who accessed the shared dashboard or when
- No way to detect if a shared link has been compromised
- Dashboard owners have no visibility into access patterns
- **Recommendation:** Create an `access_log` table to track `token`, `ip_address`, `user_agent`, `accessed_at`, and optionally `referer`

## Medium Issues

### 4. No Granular Access Controls
**Severity: MEDIUM**
- All shared links provide full read access to dashboard config
- No support for view-only vs. edit permissions
- No ability to restrict data or specific panels
- **Recommendation:** Add `permission_level` enum (VIEW, EDIT) and implement corresponding authorization checks

### 5. Missing Input Validation
**Severity: LOW-MEDIUM**
- Token parameter is not validated for format (should be exactly 32 hex characters)
- Dashboard ID in DELETE endpoint accepts any integer without validation
- **Recommendation:** Validate token format with regex before querying: `/^[a-f0-9]{32}$/i`

### 6. No CORS or Referrer Protection
**Severity: LOW-MEDIUM**
- Public endpoint could be embedded in cross-origin contexts
- No Referrer-Policy or X-Frame-Options headers mentioned
- **Recommendation:** Set `X-Frame-Options: DENY` or `SAMEORIGIN`, `X-Content-Type-Options: nosniff`, and appropriate Referrer-Policy

## Minor Issues

### 7. Generic Error Messages on Protected Routes
**Severity: LOW**
- The DELETE endpoint returns success without confirming the revocation occurred
- If update fails silently due to constraints, client won't know
- **Recommendation:** Verify row count affected before returning success (`res.json({ success: true, revoked: true })`)

### 8. No Share Limit Per Dashboard
**Severity: LOW**
- A user could create unlimited active share links for a single dashboard
- Could lead to accidental sprawl and management burden
- **Recommendation:** Consider adding a soft limit (e.g., max 10 active shares per dashboard) with user notification

### 9. Token Collision Not Explicitly Handled
**Severity: LOW**
- The UNIQUE constraint will throw an error if a collision occurs (cryptographically unlikely)
- Error handling should explicitly check for constraint violations
- **Recommendation:** Retry token generation on unique constraint error, or use a more explicit error response

## Positive Aspects

- Uses parameterized queries throughout (SQL injection safe)
- Proper ownership verification on DELETE endpoint
- Soft delete pattern with `is_active` flag (preserves audit trail)
- UNIQUE constraint on token prevents duplicates
- Ownership check prevents unauthorized dashboard access

## Recommended Action Items (Priority Order)

1. **Add rate limiting to GET /share/:token** - 1-2 hours
2. **Add token expiration with optional TTL** - 2-3 hours
3. **Implement access logging** - 2-3 hours
4. **Add token format validation** - 30 minutes
5. **Add security headers** - 30 minutes
6. **Add granular permissions (VIEW/EDIT)** - 4-6 hours
7. **Set per-dashboard share limits** - 1-2 hours

## Before Merge

- [ ] Rate limiting implemented
- [ ] Token expiration schema and logic added
- [ ] Access logging in place
- [ ] Security headers configured
- [ ] Input validation added
- [ ] Load testing with rate limiting enabled

