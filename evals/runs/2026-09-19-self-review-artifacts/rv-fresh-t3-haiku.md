# VERIFICATION REVIEW — sr-t3-haiku

## Verdict

**NOT VERIFIED** · **BLOCKING: YES**

## Independence

**INDEPENDENT** — This review reads only the finished artifact and the stated contract; the builder's reasoning was not observed.

---

## Observable Evidence

### Defect 1: Tokens stored in plaintext ❌

**Contract requirement:** "Tokens are unguessable (at least 128 bits from a CSPRNG) and stored **only as a hash**."

**What the code does:** 
- Line 31: `const token = crypto.randomBytes(16).toString('hex');` generates 128 bits via CSPRNG ✅
- Lines 35–38: The token is inserted into the database as plaintext VARCHAR(32):
  ```javascript
  INSERT INTO dashboard_shares (dashboard_id, token, created_by)
  VALUES ($1, $2, $3)
  [id, token, user.id]
  ```

**The defect:** The token value is stored directly in the database without hashing. Anyone with database read access (admin, compromised DB account, backup exposure) can read all active tokens and immediately access any shared dashboard.

**Impact:** Complete breach of token confidentiality. The entire security model depends on tokens being secret; plaintext storage destroys this.

**Severity: CRITICAL** — This is a standard-breaking security defect that violates the explicit contract.

---

### Defect 2: No expiration implemented ❌

**Contract requirement:** "Links expire (30 days or less by default) and can be revoked."

**What the code does:**
- Schema (lines 1–9): The `dashboard_shares` table has `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`, but **no `expires_at` or `expiration_date` column**.
- GET query (lines 58–64): Checks `ds.is_active = TRUE` but **does not check any expiration condition**:
  ```sql
  WHERE ds.token = $1 AND ds.is_active = TRUE
  ```

**The defect:** Links never expire by time. A revoked link (is_active = FALSE) will return 404, but a link created 6 months ago will still work forever.

**Observable:** Add a link on day 1, revoke it never, and it will still work on day 365+. No timestamp comparison in the query.

**Severity: HIGH** — Contract violation; security control is missing.

---

### Defect 3: Response leaks owner identity ❌

**Contract requirement:** "GET /share/:token returns only the dashboard's title and config: **nothing about the owner**, the organization, or other dashboards."

**What the code does:**
- Line 59: Selects `u.name as owner_name` into the query result
- Lines 71: Returns `owner: share.owner_name` in the JSON response:
  ```javascript
  res.json({
    id: share.id,
    title: share.title,
    config: share.config,
    owner: share.owner_name,  ← VIOLATES CONTRACT
    shared: true
  });
  ```

**The defect:** The public response includes the dashboard owner's name. The contract forbids returning "nothing about the owner"; this returns owner identity to anyone with a valid token.

**Observable:** Any request to GET /share/:token will include an `owner` field in the response.

**Severity: MEDIUM** — Information disclosure; violates the contract's explicit bound on response scope.

---

### Defect 4: No organization isolation on share creation ⚠️

**Contract requirement:** "Only the dashboard's **owner, in the dashboard's organization**, can create a link."

**What the code does:**
- Lines 25–28: Verifies ownership only:
  ```sql
  SELECT * FROM dashboards WHERE id = $1 AND owner_id = $2
  ```
  
**No check that `dashboards.org_id = users.org_id`.**

**The defect:** The code verifies that the requesting user owns the dashboard, but does not verify that the user and dashboard belong to the same organization. If a user somehow owns a dashboard in a different org (a data inconsistency or bug in dashboard creation), this authorization fails to catch it.

**This is an assessment:** The defect is only observable if org_id is required to match. However, the schema shows both `dashboards.org_id` and `users.org_id` exist, and the contract explicitly names it, so the absence of this check is a gap.

**Severity: HIGH** — Defensive programming: the authorization check should be explicit about org boundaries, not implicit in (assumed-correct) foreign keys.

---

### Defect 5: DELETE endpoint lacks org isolation check ⚠️

**Revoke endpoint** (lines 80–96): Same issue as creation — checks ownership but not org_id:
```sql
WHERE token = $1 AND dashboard_id = $2
AND dashboard_id IN (SELECT id FROM dashboards WHERE owner_id = $3)
```

No `org_id` match required.

**Severity: HIGH** — Same as defect 4.

---

### Axis: Token unguessability

**Result:** ✅ **CLEAN** — `crypto.randomBytes(16)` (128 bits) from a CSPRNG is cryptographically sound. Entropy is sufficient. The defect is not in generation; it's in storage.

---

### Axis: Error masking (expired/revoked/unknown → 404)

**Result:** ✅ **CLEAN** — The GET endpoint returns 404 on any error (line 75), so expired, revoked, and unknown tokens all surface as "not found". However, this is clean only *by accident*: since expiration is not checked, there is no actual difference between an expired token (doesn't exist as far as the code knows) and an unknown one. The correctness is accidental, not structural.

---

### Axis: Read-only public route

**Result:** ✅ **CLEAN** — The GET /share/:token endpoint accepts only GET and has no side effects. It is read-only.

---

## Assessment (Judgment, not directly observable)

- **Token strength is solid in generation, catastrophic in storage.** A 128-bit CSPRNG token is correct; storing it in plaintext negates every bit of that security.
- **Revocation works as a gate (is_active flag), but expiration does not exist at all.** The contract promises both; only one is delivered.
- **The code assumes org isolation is inherited from initial dashboard creation.** This is not defensive. If a permission bug exists upstream, this endpoint should catch it explicitly, not rely on upstream correctness.

---

## Claimed vs. Actual

| Claim (from contract) | Actual implementation | Status |
|---|---|---|
| Tokens stored as hash | Stored as plaintext | ❌ VIOLATES |
| Links expire by default (≤30d) | No expiration implemented | ❌ VIOLATES |
| Response contains only title, config | Response includes owner name | ❌ VIOLATES |
| Creator must be in same org | No org_id check | ⚠️ GAP |

---

## Confirm-these (gaps that couldn't be checked)

- **Runtime token hashing:** Does any middleware or ORM layer hash tokens before storage? (The code shown does not; if a wrapper exists, it is not visible here.)
- **Database schema migration:** Are there any pending migrations that add expiration columns? (The SQL schema shown has none.)
- **Org boundary enforcement:** Is org isolation enforced elsewhere (e.g., in the middleware `requireSession()`)? If `requireSession()` enforces org context, the share endpoints might inherit it — but the code does not show this, so it must be confirmed.

If any of these are true, some defects may be masked. **Verify against the full system, not just the artifact shown here.**

---

## Defects (ranked by severity)

1. **❌ CRITICAL** — Plaintext token storage. **Contract breach:** tokens must be hashed. **How to demonstrate:** Read `dashboard_shares.token` from the database; it is human-readable plaintext. Any share link can be compromised by DB access.

2. **❌ HIGH** — No expiration check. **Contract breach:** links must expire ≤30 days by default. **How to demonstrate:** Create a share link, wait 31 days (or mock the timestamp), and it still works because the query has no date comparison.

3. **❌ HIGH** — No org_id verification on create/revoke. **Contract requirement:** "in the dashboard's organization." **How to demonstrate:** Check the SQL queries at lines 25–28 and 88; no `org_id` clause exists. This should include `AND d.org_id = users.org_id` or equivalent.

4. **❌ MEDIUM** — Response includes owner name. **Contract breach:** "nothing about the owner." **How to demonstrate:** GET /share/:token returns `"owner": "<owner_name>"` in the JSON body.

---

## Single most damaging defect

Plaintext token storage. Everything else can be mitigated (add expiration logic, hide owner field, add org checks); but if tokens are readable in the database, every shared dashboard is compromised. This is the load-bearing failure.

---

## Verdict Detail

**NOT VERIFIED** — The code fails the contract on four distinct axes: token confidentiality, expiration, org isolation, and response scope.

**BLOCKING: YES** — The plaintext token storage is a CRITICAL security defect that halts release. Tokens must be hashed before being stored; the current code stores them in plaintext, defeating the purpose of using cryptographic randomness.
