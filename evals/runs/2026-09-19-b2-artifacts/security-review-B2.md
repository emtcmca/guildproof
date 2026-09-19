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
