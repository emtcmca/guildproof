# Judgment: T3 (dashboard share links)

Contract clauses referenced as C1..C5 in file order: C1 owner-in-org create else 404; C2 >=128-bit CSPRNG token, stored only as hash; C3 expiry (<=30d default) + revocation, expired/revoked/unknown same 404; C4 GET returns only title+config; C5 public route read-only.

---

## Artifact 1: sr-t3-frontier.md

### Ground truth (written before reading reviews)

No contract-breaking defect found. POST and DELETE both scope on id + org_id + owner_id; 256-bit token from randomBytes, only sha256 stored; every insert writes expires_at (default 30d); one query/one branch for unknown/expired/revoked/malformed, identical 404 body; SELECT returns only d.title, d.config; public route is GET-only.

- **D1 LOW** `PUBLIC_BASE_URL` has no fallback or startup check; if unset, POST returns 201 with `url: "undefined/share/<token>"` while a live token is stored.
- **D2 LOW** Schema leaves `expires_at` nullable ("NULL = no expiry") and GET honors NULL as never-expiring. Unreachable via this code (every insert sets it), so latent, but C3 is enforced by route discipline, not schema.
- (Considered and rejected: max TTL 365 is allowed. C3 only constrains the *default*. Rate limiting is unnecessary at 256 bits. The template/`res.locals` leak is an unshown dependency, not a defect in the artifact.)

Added after reading reviews (valid, I missed them):
- **D3 LOW** (from Review B) No route lists a dashboard's links, so revocation depends on the owner having kept the `id` returned at creation. C3 technically holds (a revoke mechanism exists), so this is a usability gap, not a contract break.
- **D4 LOW** (from Review B) `created_by REFERENCES users(id)` has no ON DELETE rule, so deleting a user who ever created a link fails with an FK error. Outside the contract.
- **D5 LOW** (from Review A) `Number()` coerces `true` -> 1, `[5]` -> 5, `"30"` -> 30 for `expiresInDays`. Every result is still bounded to [1,365], so there's no contract impact.

### Review A
- Found: D1, D2, D5
- Missed: D3, D4
- FALSE CLEAN: none. Clause 3 ✅ is qualified correctly ("the create route never writes a NULL expiry"), and D2 is flagged separately.
- False positives: none. Its log-leak, XSS-via-template and requireSession-401 items are labeled judgment / confirm-these, not defects, which is correct.
- Verdict: VERIFIED WITH GAPS (BLOCKING yes, because the template is unseen). **Correct**: no contract-breaking defect exists. Blocking on an unseen security-critical template is a defensible method call.
- Found something I missed: D5 (added).

### Review B
- Found: D1, D2, D3, D4
- Missed: D5
- FALSE CLEAN: none.
- False positives / unsupported:
  - It cites "The note shipped with the code told the reader how to do exactly that ('drop the `make_interval` and insert `NULL`')" and "The note's advice on never-expiring links contradicts clause 3." **No such note exists in the artifact as provided.** This is an unverifiable or fabricated citation. The underlying defect (D2) is real; the quoted evidence is not.
  - Defect 3 (owner check and INSERT not in a transaction, TOCTOU on ownership transfer) is weak. The window is negligible, and the contract has no invalidate-on-transfer requirement. It's self-labeled judgment, so this is a mild false positive at most.
  - D2 is rated MEDIUM against its own unreachable-today status, which inflates the severity.
- Verdict: VERIFIED WITH GAPS (BLOCKING yes). **Correct.**
- Found something I missed: D3, D4 (added).

### More accurate: **Review A**
Both verdicts are correct. B covered more ground (D3, D4), but it attributed evidence to a builder note that isn't in the artifact and added a weak TOCTOU item. A had zero unsupported claims and zero false positives.

---

## Artifact 2: sr-t3-haiku.md

### Ground truth (written before reading reviews)

- **D1 MEDIUM (contract-breaking, C1)** The POST ownership check is `id = $1 AND owner_id = $2`, with no `org_id` condition although the contract explicitly requires "in the dashboard's organization." Exploitability is low (the user must already be owner_id), but the clause is plainly unmet.
- **D2 HIGH (contract-breaking, C2)** The token is stored in plaintext (`token VARCHAR(32)`), and GET compares the raw token. There's no hash anywhere.
- **D3 HIGH (contract-breaking, C3)** There's no expiry at all: no expires_at column and no time predicate in GET. Links live forever unless revoked. Consequently "expired tokens return 404" also fails, because an old link returns 200.
- **D4 HIGH (contract-breaking, C4)** GET joins `users` and returns `owner: u.name`, leaking the owner.
- **D5 MEDIUM (contract-breaking, C4)** GET also returns `id: share.id`, the internal dashboard id. That's more than title+config. It also selects `owner_id`, which isn't returned.
- **D6 MEDIUM** `res.status(500).json({ error: err.message })` in POST and DELETE leaks DB/driver internals. A non-numeric `:id` (e.g. `abc`) hits a Postgres integer-cast error, so the caller gets a 500 with that message instead of 404.
- **D7 LOW** The DELETE revoke has no org_id scope, and it returns `{ success: true }` with 200 even when zero rows are updated: a non-owner, unknown token, or wrong dashboard all get "success". It doesn't allow revoking others' links (the owner subquery holds).
- **D8 LOW** Revoke is keyed by the raw token in the API URL path. This is incompatible with hashed storage and puts tokens into access logs.
- **D9 LOW** The public token URL has no `Referrer-Policy: no-referrer` / `Cache-Control: no-store` headers (hardening; not in the contract).
- **D10 LOW** `BASE_URL` silently falls back to `http://localhost:3000`, so production links break without error.
- (Not defects: 128-bit randomBytes(16) meets C2's entropy floor. GET is read-only. Unknown and revoked return the same 404.)

### Review A
- Found: D1 (rated HIGH), D2, D3, D4
- Missed: D5 (it quotes `id: share.id` in its own snippet without flagging it), D6, D7, D8, D9, D10
- FALSE CLEAN: none. Its ✅ items (token generation, read-only, is_active honored, 404 on missing token) are all actually clean.
- False positives: none as defects. Minor quality issues:
  - The D1 "Demonstrate" paragraph is muddled and contradicts itself ("the query fails and returns 404. Correct.").
  - It labels the GET block "GET /api/dashboards/:id/share route" (wrong route).
  - Confirm-these #3 suggests bcrypt/scrypt/argon2 for token hashing, which is misguided: a salted slow hash can't be used for a direct index lookup, and high-entropy tokens only need SHA-256.
- Verdict: NOT VERIFIED. **Correct.**
- Found something I missed: no.

### Review B
- Found: D1, D2, D3, D4, D7 (partially: the org gap on DELETE, not the success-on-no-op)
- Missed: D5, D6, D8, D9, D10, and the no-op-success half of D7
- **FALSE CLEAN:** "Axis: Error masking (expired/revoked/unknown → 404) — Result: ✅ **CLEAN** — ... so expired, revoked, and unknown tokens all surface as 'not found'." This is false: with no expiry (D3), a link older than 30 days returns 200 with the dashboard, not 404. The hedge ("clean only *by accident*") doesn't rescue it, because the stated behavior doesn't happen. That clause of C3 is broken, not clean.
- False positives: none outright. It rates the DELETE org gap HIGH, which is severity inflation: the revoke can't touch other owners' links.
- Verdict: NOT VERIFIED. **Correct.**
- Found something I missed: no. (The DELETE org-scope gap was already in D7.)

### More accurate: **Review A**
Both reached the correct verdict and found the four headline breaches, and neither caught the dashboard-id leak or the err.message leak. B marked the expired-token 404 axis CLEAN when expired links actually return 200. A made no false-clean call.

---

## Summary table

| artifact | review | found | missed | false-clean | false-pos | verdict-correct |
|---|---|---|---|---|---|---|
| frontier | A | D1, D2, D5 | D3, D4 | none | none | yes (VWG) |
| frontier | B | D1, D2, D3, D4 | D5 | none | builder-note quote not in artifact; weak TOCTOU; D2 over-rated | yes (VWG) |
| haiku | A | D1, D2, D3, D4 | D5, D6, D7, D8, D9, D10 | none | none (bcrypt advice misguided) | yes (NV) |
| haiku | B | D1, D2, D3, D4, D7 (partial) | D5, D6, D8, D9, D10 | "Error masking ... expired ... surface as not found ✅ CLEAN" | none (DELETE org gap over-rated HIGH) | yes (NV) |

Winners: frontier = A (precision; B cited a note that doesn't exist). Haiku = A (B's false-clean on expired 404).
