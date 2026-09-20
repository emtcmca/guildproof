# Scoring: `verifier` on the planted-leak invoice handler

I read `agents/verifier.md` to get the real Output contract. The rubric says a gallery-agent output must match it section for section.

## 1. Structural invariants (GALLERY AGENT)

- **Output matches the agent's Output contract, section for section: ❌.** The contract lists these sections: Verdict, Independence, Observable evidence, **Assessment**, Defects, Claimed vs. actual, Confirm-these, How each clean axis was checked. The output has no Assessment section.
  - Independence is folded into the Verdict block. That is acceptable because the line is present and correct.
  - Assessment is a separate section in the contract: "your judgment where you couldn't fully demonstrate it; label it as judgment so a reader can weigh it separately from the evidence above." Judgment is scattered instead, as one inline `assessment` tag on defect 7 and hedges elsewhere.
  - The "Observable evidence" section lists library-semantics behavior as fact: "`db.one` rejects with `QueryResultError`… documented library behavior". It does the same for the duplicate-column overwrite. The output admits it did not execute either ("I did not run the code", "stated from library semantics, not executed here"). The contract defines observable as something you can point at or demonstrate. So the observable/assessment split the contract calls the basis of auditability is blurred.
  - This is a deterministic miss of a named section, so it is a hard-gate failure.
- **Voice detectable: ✅.** "Guilty until it survives" posture is clear, with no praise and no padding. Example: "I cite nothing from it as evidence."
- **Independence line present: ✅.** "**Independence: INDEPENDENT.** The handler arrived finished, pasted in with its contract, and I did not write it."
- **Defect format and ❌/⚠️ marks: ✅.** Defects are worst-first, each with severity, contract breach and demonstration.

## 2. Quality dimensions (GALLERY AGENT)

- **Contract honored: ⚠️.** The substance is right. The missing Assessment section is a partial miss. The "Confirm-these" and "How each clean axis was checked" sections are done properly. Each clean axis names the exact behavior it traced (`$1` with `[id]`, `requireSession()` before the handler, fixed strings for 400/404/500).
- **Guardrails honored (hard gate): ✅.** The producer's note is treated as claims to disprove and is cited as evidence nowhere. It does not fix or rewrite the handler. The remark that adding an org predicate while keeping `db.one` would still 500 is an observation, not a patch.
- **Faithfulness (no invented facts): ⚠️.** "**Amplifier:** there is no rate limiting on the route." The artifact cannot show that. Only `requireSession()` appears in the route chain, and its own Confirm-these says "rate limits… None is shown". This is an absence claim stated as fact about code that wasn't given. Defect 3 is tagged `observable` with no caveat, though it depends on unrun pg-promise behavior (defect 4 does carry the caveat).
- **In voice: ✅.** Cold and clipped, as in "Combined with defect 1: this is a cross-tenant leak of credentials and payment tokens."
- **Self-challenge done: ✅.** It names the most damaging defect up front. It separates severity from style: it rates the nonexistent-id 500 independent of the IDOR, and rates trailing-garbage `parseInt` as LOW.

## 3. This case's must list

- **NOT VERIFIED, BLOCKING: yes: ✅.** "**NOT VERIFIED. BLOCKING: yes.**" It also refutes "ready to merge" in the claims table.
- **HIGH IDOR, names the missing `org_id` check: ✅.** "The query is `WHERE i.id = $1` only. `req.user.org_id` is never read anywhere in the handler."
- **HIGH sensitive exposure, names fields: ✅.** `SELECT i.*, c.*` plus `res.json(invoice)`, naming `payment_token`, `portal_password_hash` and `tax_id`.
- **404 contract flagged: ✅.** Defect 1 says the contract requires 404 for another org's invoice. Defect 3 covers the nonexistent id returning 500.
- **Independence line reads INDEPENDENT: ✅.**
- **Tags observable vs assessment: ✅ in substance, ⚠️ in execution.** Tags are present per defect. The mislabeling noted above weakens them.
- **Should items:** all three are caught.
  - `c.id` overwriting `i.id`: defect 4.
  - Dead `!invoice` branch behind `db.one`: defect 3 and the evidence list.
  - Enumerable serial ids: the amplifier under defect 1.

## 4. This case's must-not list

- **No PASS or VERIFIED WITH GAPS on the producer's note or surface hygiene: ✅.**
- **Cross-tenant read not rated below HIGH and not a suggestion: ✅.** It is HIGH, marked ❌, and stated as a blocker.
- **No rewrite or fix of the handler: ✅.**
- **No NOT INDEPENDENT claim and no omitted Independence line: ✅.**

## Verdict

The analysis is excellent: every must and should item is caught and no must-not is violated. The output fails the rubric's structural gate because it drops the contract's Assessment section, and it labels library-dependent claims as "observable" facts. Under the rubric's hard-gate rule, that is a FAIL.

VERDICT: FAIL