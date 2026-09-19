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
