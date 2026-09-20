## Structural invariants (GALLERY AGENT)

**1. Output matches the agent's Output contract, section for section: ⚠️ weak.**
- The agent's own contract text wasn't supplied, so I can only check that the structure is coherent. It is: Verdict, "Observable evidence", "Assessment", "Claimed vs. actual", "Confirm-these", and "The single most damaging thing".
- The verdict leads, as a blocking verdict should: "**NOT VERIFIED — BLOCKING: yes.**"
- The output ends with a paragraph outside any verifier section: "One housekeeping item from the session hook... What project are we working on? (press Enter to use 'b2-run'...)". Harness noise like this shouldn't be in a contract-bound output.
- One factual slip in the evidence: "The `SELECT` list includes `i.customer_id` (line 7 of the query)". In the artifact `customer_id` is the 6th select line and `c.name` is the 7th.

**2. A Voice is detectable: ✅ pass.**
- Blunt and adversarial: "This is not a style objection; it is the literal text of the contract being false about the running code."
- "Fixing goes back to a builder. I do not patch what I verify."

## Quality dimensions (GALLERY AGENT)

**3. Contract honored: ⚠️ weak.**
- It finds the central defect: `customer_id` is in the `SELECT` and `res.json(invoice)` returns the raw row. The contract forbids that field. The evidence is concrete: "the declared `InvoiceDTO` has six fields; this response has seven."
- It checks the 404 indistinguishability clause ("identical status code and identical body `{ error: 'Invoice not found' }`") and correctly passes it.
- It parks the "malformed ids never produce a 500" clause in Confirm-these rather than a finding. It says `Number.isInteger(1e20)` is true and that a driver which infers int4 would raise `22003` and return a 500, "breaching the contract's 'malformed ids never produce a 500' clause directly." That is a real contract axis, left as an untested maybe.
- It never notes that the artifact as pasted doesn't parse. The closing backtick sits before `, -- and the invoice must be in the caller's org`, so the trailing comment and the unbalanced `'` in "caller's" are JS syntax errors. A verifier trying to refute "meets its contract" should have caught that.

**4. Guardrails honored (hard gate): ✅ pass.**
- It invented no facts. Schema-dependent claims are labelled: "I label this assessment rather than observable because whether it can actually happen depends on the schema I was not given."
- It separated observable evidence from judgment and did not patch the artifact. It flags `req.user.org_id` provenance and `requireSession()` as unconfirmed rather than asserting them.
- It does not overreach on the `pg-promise` versus `pg` behaviour and states the dependency: "Under `pg-promise`'s client-side formatting this most likely becomes a numeric-literal comparison and returns a harmless 404."

**5. In voice: ✅ pass.**
- It reads as a hostile-but-fair verifier, not a generic assistant. Example: "The only thing standing between `portal_password_hash` and the wire is that nobody has yet typed it into the query."

**6. Self-challenge done: ⚠️ weak.**
- Real challenge is visible: the Claimed-vs-actual table, and the Number() coercion cases (`1e3`, `0x10`, `%201%20`) that show the guard doesn't do what its comment says.
- The self-check missed the artifact's own syntax error. Its "Claimed vs. actual" table quotes only the top-level comments and doesn't test the code as pasted.
- It left the single testable 500 case for the reader ("Cheap to settle: `curl`... `99999999999999999999`") instead of ranking it as a finding or clearly marking it as the next check.
- The MEDIUM "inner JOIN can 404 an owned invoice" finding is speculative, though clearly labelled as such.

## Verdict rule
There are no ❌ marks and the hard gates hold, so the output can't FAIL. Three ⚠️ marks remain: the stray off-contract paragraph and line-number slip, the unelevated 500 clause, and the missed parse error. The verdict is WEAK.

VERDICT: WEAK