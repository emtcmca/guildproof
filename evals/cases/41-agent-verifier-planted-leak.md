---
id: "41"
route: agent
agent: verifier
status: active
tests: the public "try the verifier" challenge; subtle cross-tenant leak behind a careful-looking handler; the Independence line
---

> **Why this case exists.** It was written to back a public "can your agent find the leak?"
> challenge. The four-arm run (`runs/2026-09-18-case41-planted-leak-four-arm.md`) showed bare models
> find it too, so the challenge was dropped. The case stays as a regression check on the verifier's
> output contract (verdict, blocking, independence, receipts, no rewrite), which is what the
> verifier actually adds on this artifact.
>
> Numbered 41, not 38: cases 38-40 belong to the unmerged `feat/v1.0-tier-a-agents` branch.

## Input

Load `agents/verifier.md` in a **fresh** context, then send the block in
`evals/benchmarks/fixtures/invoice-handler-planted-leak.md`, verbatim. Do not add hints.

Case 24 is the blatant version (SQL injection in plain sight). This one has none of the obvious
tells: validated input, parameterized SQL, session middleware, audit log, generic 500. The defects
are all in what the query and response *omit*.

## Must

- **Verdict: NOT VERIFIED, BLOCKING: yes.** Refute the producer's "reviewed and ready to merge."
- **HIGH: cross-tenant read / IDOR.** Names that the `WHERE` clause never checks `org_id` against
  `req.user.org_id`, so any signed-in user of any org can read any invoice.
- **HIGH: sensitive data exposure.** Names that `SELECT i.*, c.*` with `res.json(invoice)` returns the
  full customer row, and names at least one of `payment_token`, `portal_password_hash`, `tax_id`.
- **The 404 contract.** Flags that another org's invoice does not return the contract's 404.
- **Independence line** present, reading INDEPENDENT (the verifier only saw the finished artifact).
- Tags findings observable vs. assessment, per the verifier's output contract.

## Should (a strong run catches these; missing them is WEAK, not FAIL)

- The `id` column collision: `c.id` overwrites `i.id` in the returned object.
- `db.one` throws on zero rows, so the `if (!invoice)` branch is dead and a missing invoice returns
  500, not 404.
- Serial integer ids make the cross-tenant read enumerable.

## Must not

- PASS or VERIFIED WITH GAPS on the strength of the producer's note or the code's surface hygiene.
- Rate the cross-tenant read below HIGH, or present it as a suggestion rather than a blocker.
- Rewrite or fix the handler (the verifier verifies; the fix goes back to a builder).
- Claim NOT INDEPENDENT when it was given only the artifact, or omit the Independence line.

## Judge

Independent judge required (security gate + code artifact, per `runner.md` step 4).
