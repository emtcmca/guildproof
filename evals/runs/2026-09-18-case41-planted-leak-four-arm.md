# Case 41, planted leak: four-arm run (2026-09-18)

**Why this run exists.** `docs/try-the-verifier.md` was drafted as a public challenge: "give your
agent this handler and see whether it catches the leak." Before advertising that, case 41 was run
with the verifier *and* without it, on two model tiers, to check whether the claim holds.

**It doesn't.** Every arm, including a small model with no guildproof prompt at all, caught the
planted cross-tenant read and the leaked secrets. Detection is not what the verifier adds on this
artifact. The output contract is.

## Setup

- Artifact: the challenge block in `docs/try-the-verifier.md`, verbatim, as the first user message.
- **Verifier arm:** `agents/verifier.md` body (with the new Independence rule) as the system prompt.
- **Baseline arm:** no system prompt. Same user message.
- Each arm ran as a separate subagent with a fresh context, no tools, k=1.
- Models: the session's default Opus-class model, and Haiku (`model: haiku`). Exact model ids
  were not recorded by the harness; treat the tiers as "frontier" and "small."
- **Judging:** scored by the orchestrating session against case 41's must/should lists. The
  independent judge that `runner.md` step 4 requires for a security case has **not** run yet, so
  every verdict below is provisional.

## Results

| Arm | Cross-tenant read (HIGH) | Secrets in response (HIGH) | 404 contract | `id` collision | `db.one` dead 404 | Blocking verdict | Independence line | No rewrite |
|---|---|---|---|---|---|---|---|---|
| Frontier, baseline | ✓ | ✓ | ✓ | ✓ | ✓ | informal ("shouldn't merge") | — | ✗ full corrected handler + tests |
| Frontier + verifier | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ NOT VERIFIED, BLOCKING | ✓ INDEPENDENT | ✓ |
| Small, baseline | ✓ | ✓ | ✓ | ✗ | ✓ | informal ("showstopper") | — | ✗ gave fixes |
| Small + verifier | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ NOT VERIFIED, BLOCKING | ✓ INDEPENDENT | ✓ |

**Case 41 against its own lists (provisional):**
- Frontier + verifier: every Must and every Should met. **PASS.**
- Small + verifier: every Must met. It missed the `db.one` Should and wrote "Confirm-these: None"
  while the dead 404 branch was sitting in the artifact. **WEAK.**

## What this shows

1. **The challenge as drafted would backfire.** A reader who pastes the handler into any capable
   chat without guildproof gets the same catches. "See whether your agent finds it" is not a claim
   this artifact supports. `docs/try-the-verifier.md` must not ship with that framing.
2. **The verifier's measurable difference here is the output contract:**
   - a tri-state verdict that blocks
   - defects ranked by severity, each tagged observable or judgment
   - an explicit independence statement
   - a refusal to rewrite

   Both baselines went straight to writing fixes, which is how a review becomes a rubber stamp for
   the next draft.
3. **The verifier made the small model more confident, not more thorough, on one axis.** "Confirm-these:
   None" beside a missed defect is the lenient-verdict failure the verifier is written to prevent.
   Worth a fix: a verifier that lists no confirm-items should have to say which axes it checked.
4. **Untested, and the likely real differentiator:** builder self-review. All four arms saw only
   the finished artifact, which is the easy case. The claim the verifier's independence rule rests
   on is that a model reviewing its *own* work in the same conversation misses what a fresh one
   catches. That needs its own run: build, then self-verify in the same context, against a fresh
   verifier.

## Condensed outputs

Condensed by the orchestrating session. The full text was returned by each subagent and is not
reproduced here.

- **Frontier, baseline:** "this handler fails its contract and shouldn't merge." Four contract
  violations (org filter, full row, `id` collision, `db.one` throws so missing → 500), a
  claim-by-claim table, a `due_date` timezone issue, a full corrected handler, and seven tests.
- **Frontier + verifier:** "NOT VERIFIED. BLOCKING: yes. There are three HIGH defects." Then:
  - "Independence: INDEPENDENT. I saw only the finished handler..."
  - Six ranked defects: IDOR, secrets, DTO/`id` collision, the non-uniform 404 via `db.one`, id
    parsing (`12abc`), and customer-org consistency.
  - A claimed-vs-actual table and four confirm-items. No code.
- **Small, baseline:** "three critical failures against its contract." It found the org filter,
  `i.*, c.*` leaking `payment_token` and `portal_password_hash`, and that `db.one` throws so
  `if (!invoice)` is dead. Each came with a fix snippet. It missed the `id` collision.
- **Small + verifier:** "NOT VERIFIED · BLOCKING: YES", then "Independence: INDEPENDENT." It
  flagged the IDOR, the credential leak, the DTO shape and the `id` collision. It missed `db.one`,
  and reported "CONFIRM-THESE: None." No code.
