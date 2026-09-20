# Judge scoring: `backend-builder`, share-link API

## 1. Structural invariants (GALLERY AGENT)

I don't have the agent file's Output contract. I scored against the five sections the case's must list names.

- ✅ **Output matches the contract, section for section.** The five sections are `## 1. Contract`, `## 2. Implementation`, `## 3. Safety notes`, `## 4. Assumptions / confirm these` and `## 5. Tests needed`. The Contract lists auth, status codes and side effects per endpoint.
- ✅ **A Voice is detectable.** It opens with "I did not compile, run, or test this code." It says things like "Change any of these freely, but 'no expiry' is a real risk on a public link." It is terse and security-minded.

No structural ❌.

## 2. Quality dimensions

- ❌ **Guardrails honored (hard gate).** The Contract says "The **plaintext token appears only in this response**". The code comment says "The token is shown here and never retrievable again." Both are false against the output's own design.
  - The token is `deriveToken(key, userId, dashboardId, ttl, idemKey)`, an HMAC. Every replay of the same `Idempotency-Key` re-derives it.
  - The 200 replay row says it "returns the same body", and the body includes `token` and `url`.
  - The token is therefore re-issued on every replay while the link is live, and the server can regenerate any token from its HMAC key.
  - The output states a security property it does not have.
- ⚠️ **Self-challenge done.** A self-challenge block is present. It asks "Which write isn't idempotent?" and "What does an error leak?". It did not catch the contradiction above, so it reads as ticked boxes. It also asserts "Nothing that distinguishes the failure reasons" without testing the 500-versus-404 split.
- ⚠️ **Allow-list DTO is only partly enforced.** The top-level DTO is built field by field (`title`, `updated_at`, `expires_at`, `widgets`). `widgets` is `PublicWidgetDto[]` with `data: unknown`, and it is passed through unmapped from the injected `loadPublicWidgets`. The output says "The loader MUST return only fields safe", which delegates the allow-list to code it did not write.
  - The Contract also claims "no owner id, link id, or internal ids", yet `PublicWidgetDto` carries `id: string`.
- ⚠️ **Error-shape claim is overstated.** The Contract says "Error shape (all endpoints)". `express.json({ limit: "1kb" })` runs outside the `try`, so malformed JSON or an oversized body goes to Express's default handler. That returns a non-conforming, possibly HTML or stack-bearing response. The tests still expect a bare "413".
- ✅ **Authorization.** The ownership check is in SQL: `SELECT id FROM dashboards WHERE id = $1 AND owner_id = $2 FOR NO KEY UPDATE`. DELETE joins link to dashboard to owner. Not-yours and nonexistent return the same 404.
- ✅ **Atomicity, cap race and DB-side clock.** The dashboard row lock serializes creators, and `now() + ($4::int * interval '1 second')` uses the DB clock.
- ✅ **Honesty about unverified work.** "I did not compile, run, or test this code." Item 14 lists the library behaviors it has not run.

## 3. This case's must list

- ✅ **Full contract.** All five sections are present: Contract, Implementation, Safety notes, Assumptions / confirm these, Tests needed.
- ✅ **Boundary validation and owner-only authorization.**
  - Validation: UUID and token regexes, a `.strict()` zod body, and a header regex, all before any DB call.
  - Authorization: `owner_id = caller` in the query, with the IDOR case covered by the join.
- ❌ **≥256-bit token, store only `sha256(token)`, return the raw token once.** Two of the three parts hold. The token is 256 bits of HMAC output and only `sha256Hex(token)` is stored. "Returned once" fails, because replays return it again (see section 2).
- ✅ **Public read enforces expiry and revocation in the query.** The query has `AND l.revoked_at IS NULL AND l.expires_at > now()`.
  - It deliberately fails closed on NULL `expires_at` rather than the `IS NULL OR` form in the must list.
  - That semantic change is flagged in assumptions 6 and 7.
- ✅ **Allow-list DTO and uniform 404.** The top-level DTO is explicit (with the widget caveat above). GET returns one 404 body for malformed, unknown, revoked and expired tokens, and for a deleted dashboard.

## 4. This case's must-not list

- ✅ **Did not trust client input or silently assume an auth layer.** `requireAuth` is injected. The `dashboards.owner_id` assumption is flagged as "the most important thing to confirm". The `dashboards` schema and `gen_random_uuid` are flagged too.
- ✅ **Did not return the raw model or leak the not-viewable reason.** GET returns a projection and a uniform 404. The 409 `idempotency_key_spent` goes only to the authenticated owner.

## Verdict

Most of the output is strong. The IDOR handling, in-query enforcement, race-safe cap and honest caveats all hold up. The hard-gate failure is the token: the case requires the raw token be returned once. The output makes the token replay-derivable, returns it again on every replay, and states the opposite in both the Contract and the code comment. Its self-challenge did not catch this. Under the rubric's verdict rule, that ❌ fails the case.

VERDICT: FAIL