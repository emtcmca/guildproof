# Review: Public Dashboard Share Links

**Verdict:** NOT VERIFIED  
**Blocking:** yes  
**Independence:** NOT INDEPENDENT — I wrote this code earlier in the same conversation, inheriting all embedded assumptions and blind spots. A fresh independent review is required before merge.

---

## Contract (derived from stated requirements)

1. Only the dashboard's owner, in the dashboard's organization, can create a link. Anyone else gets 404.
2. Tokens are unguessable (≥128 bits from CSPRNG) and stored **only as a hash**.
3. Links expire (≤30 days by default) and can be revoked. Expired, revoked, and unknown tokens all return 404.
4. GET /share/:token returns only title and config — nothing about owner, organization, or other dashboards.
5. Public route is read-only.

---

## Observable Evidence — Defects

### ❌ HIGH: Missing organization check on share creation

**Location:** POST /api/dashboards/:id/share, ownership check
```javascript
const dashboard = await db.one(
  'SELECT * FROM dashboards WHERE id = $1 AND owner_id = $2',
  [id, user.id]
);
```

**Defect:** The query checks owner_id only. It does not check that the dashboard's org_id matches the user's org_id (which exists on req.user per requireSession()). In a multi-tenant system, if auth leaks or session isolation fails, a user from org B could create shares for dashboards in org A, provided they somehow learned the correct dashboard ID.

**Demonstrate:** A user with id=5, org_id=2 can create a share for dashboard id=99 (owned by user id=10, org_id=1) if that dashboard exists and user 5 is not the owner — the query fails and returns 404. Correct. But if user 10 in org 1 creates a dashboard, user 5 in org 2 should not be able to create shares for it even if user 10's id matches some other context. The query does not enforce org isolation.

**Assessment:** In a single-tenant or siloed environment this may be a non-issue. In a true multi-tenant system, this is an authorization bypass.

---

### ❌ HIGH: Tokens stored in plaintext, not hashed

**Location:** Table schema
```sql
token VARCHAR(32) NOT NULL UNIQUE,
```

**Defect:** The contract requires tokens "stored only as a hash." The code stores the raw 32-character hex token in plaintext. The GET route does not hash the incoming :token before querying:
```javascript
WHERE ds.token = $1 AND ds.is_active = TRUE
```

**Demonstrate:** If the database is breached, every share link's token is exposed. An attacker can then access every shared dashboard without guessing anything. The token generation is cryptographically sound (128 bits), but the storage destroys that property.

**Correct implementation:** Hash the token (e.g., SHA-256) before storage. On GET, hash the incoming token parameter and query against the hash column. This way a DB breach does not expose all active links.

---

### ❌ HIGH: No expiration logic

**Location:** Table schema and GET route
```sql
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
```

The table stores created_at but the GET route never checks it:
```javascript
WHERE ds.token = $1 AND ds.is_active = TRUE
```

**Defect:** The contract requires links to expire in 30 days or less by default. The code never enforces an expiration. A share link created 6 months ago will still work if is_active is true.

**Demonstrate:** Create a share link on day 1. Wait 40 days. GET /share/:token still returns the dashboard. Expected: 404 after 30 days.

---

### ❌ MEDIUM: Owner information leaked in GET response

**Location:** GET /api/dashboards/:id/share route, SELECT and response
```javascript
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
  owner: share.owner_name,  // ← leaked
  shared: true
});
```

**Defect:** The contract requires "nothing about the owner, the organization, or other dashboards." The response includes `owner: share.owner_name`, which leaks the owner's name to anyone with the share link. The owner_id is also selected (though not returned in this response).

**Demonstrate:** Call GET /share/:token. Response body includes "owner": "<name>". Expected: no owner field.

---

### ✅ Axis checked and clean

- **Token generation:** crypto.randomBytes(16).toString('hex') is 128 bits from a CSPRNG. ✅
- **Read-only public route:** GET /share/:token does not mutate state. ✅
- **Revocation flag honored:** GET route checks `is_active = TRUE`. ✅
- **404 on missing token:** Query returns 404 if token not found. ✅

---

## Claimed vs. Actual

- **Claimed:** Tokens are unguessable and stored only as a hash.  
  **Actual:** Tokens are unguessable but stored in plaintext.

- **Claimed:** Links expire (30 days or less by default).  
  **Actual:** Links never expire; expiration logic is absent.

- **Claimed:** GET /share/:token returns only title and config.  
  **Actual:** GET /share/:token also returns owner name.

---

## Confirm-these

1. **Org_id on requireSession():** Verify that req.user includes org_id and that it's the correct org the user belongs to. The code assumes it exists but never uses it.
2. **Database isolation:** Confirm that a single dashboards table doesn't allow cross-tenant access at the schema or middleware layer (e.g., RLS). If that's missing, the missing org_id check is catastrophic.
3. **Hashing library available:** Confirm which hashing library is in use (bcrypt, scrypt, argon2) and whether it's available in this codebase.

---

## Summary

The code has three blocking defects:

1. **Plaintext token storage** — A compromise of the database exposes all active shares.
2. **Missing expiration logic** — Shares persist forever, violating the contract.
3. **Missing org_id validation** — In a multi-tenant system, cross-org access is possible.

All three are real contract breaches, not style issues. The fourth defect (leaking owner name) is moderate but still a breach.

**Do not merge. Return to builder for remediation on all four defects.**
