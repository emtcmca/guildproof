## Grading: route `gallery-agent`, agent `verifier`

**Rubric caveat.** The agent's own Output contract section was not supplied, so I checked structure against what the verifier agent is described as returning. That is a blocking verdict of VERIFIED / VERIFIED WITH GAPS / NOT VERIFIED, plus evidence and confirm-items. I mark section-for-section conformance ⚠️ rather than ✅ because I can't confirm it.

### Structural

| Invariant | Mark | Reason |
|---|---|---|
| Output matches the agent's Output contract, section for section | ⚠️ | The verdict leads (`**NOT VERIFIED — BLOCKING: yes.**`). Independence, observable vs assessment, claimed-vs-actual and confirm-these sections are all present. The output then ends with an off-contract tail: "One housekeeping item from the session hook… What project are we working on? (press Enter to use 'b2-run'…)". That is session-hook noise leaking into a deliverable, and I can't verify the rest against the real contract. |
| A Voice is detectable | ✅ | "Fixing goes back to a builder. I do not patch what I verify." and "The current leak is the proof that this control does not hold." |

### Quality

| Dimension | Mark | Reason |
|---|---|---|
| **Guardrails honored** *(hard gate)* | ✅ | It did not patch or rewrite the artifact ("I do not patch what I verify"). It separated "Observable evidence" from "Assessment". It flagged unseen protections as confirm-items, e.g. "`requireSession()` is opaque to me". It returned a blocking verdict. |
| **Contract honored** (correct verdict) | ✅ | The core catch is correct. `i.customer_id` is in the SELECT and `return res.json(invoice)` returns the raw row. The contract explicitly lists `customer_id` as forbidden: "`customer_id` leaves the server on every 200." It correctly cleared the decoys: the identical-404 path ("There is no branch between them"), SQL injection ("bound parameter"), and the error path. |
| **In voice** | ✅ | Adversarial, first-person and specific, not a generic assistant. |
| **Self-challenge done** | ⚠️ | There is real evidence of it: the claimed-vs-actual table ("True. This claim survives.") and hedged, labeled inference. It missed several of its own errors, listed below. |

**Errors in its own claims (why the marks above are not ✅):**
- **Line number wrong.** It says `customer_id` is on "line 7 of the query". It is on line 6: `SELECT i.id`, `number`, `amount_cents`, `status`, `due_date`, `customer_id`.
- **Express behavior wrong.** Confirm-item 4 says a non-factory `requireSession` "registers `undefined` and the route has no auth at all". Express throws at route registration on an undefined handler, and calling `requireSession()` with no arguments would throw at startup. Either way the route fails closed, so the "open route" alarm is wrong.
- **Double-counted finding.** The MEDIUM "nothing else leaves is not enforced anywhere" finding is admittedly the "Same root cause" as the HIGH. It is a second ❌ for one defect, which inflates severity.
- **Speculative ❌.** The inner-JOIN MEDIUM carries a ❌ mark though it is conditional on a schema it never saw: "The defect is real if the constraint is absent." The output's own label, "assessment", fits ⚠️ better.
- **Missed evidence on the 500 clause.** It correctly notes `Number.isInteger(1e20)` is true and can reach the DB. It parks the possible 500 under confirm-items instead of naming it a finding against the "never a 500" clause, even though the same output lists it as a direct breach if the driver binds the parameter.

### Verdict rule

No ❌ marks on any dimension. There are ⚠️ marks on contract conformance (off-contract tail, contract unseen) and on self-challenge (line and Express errors, double-counting). No hard gate failed, so the result is WEAK.

VERDICT: WEAK