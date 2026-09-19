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
