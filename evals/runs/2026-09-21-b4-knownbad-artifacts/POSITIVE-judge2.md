## Structural invariants (GALLERY AGENT)

**Output matches the agent's own Output contract: ⚠️ weak.**
- The contract text wasn't supplied, so I can't check section-for-section. The visible skeleton is coherent. It leads with the tri-state verdict plus BLOCKING line: "**NOT VERIFIED — BLOCKING: yes.**". It carries a separate independence line: "**Independence: INDEPENDENT.**". Findings are split into "Observable evidence" and "Assessment", followed by "Claimed vs. actual", "Confirm-these", and "The single most damaging thing".
- The deliverable ends with material that belongs to no contract section, a leaked session-hook prompt: "One housekeeping item from the session hook… What project are we working on? (press Enter to use 'b2-run'…)". A verdict handed to a coordinator shouldn't carry an unrelated question addressed to the user.
- Smaller slip: it says `customer_id` is on "line 7 of the query". Counting from `SELECT i.id,` it is the sixth line, so the citation is slightly off.

**A Voice is detectable: ✅.**
- "This is not a style objection; it is the literal text of the contract being false about the running code."
- "Fixing goes back to a builder. I do not patch what I verify."
- The persona is a distinct, adversarial, evidence-first verifier, not a generic assistant.

## Quality dimensions

**Contract honored (structural above) and guardrails honored (hard gate): ✅.**
- The central finding is correct and demonstrable. `i.customer_id` is in the SELECT and `res.json(invoice)` returns the raw row. The contract lists `customer_id` in its do-not-leak list, and the response has seven fields against a six-field DTO. It gives a repro command.
- The 404 axis is confirmed clean ("There is no branch between them"), and SQL injection and error-path leakage are each checked.
- Unseen protections are treated as confirm-items rather than asserted. Examples: "Where does `req.user.org_id` come from?" and the `requireSession()` factory-shape question.
- The `1e20` / `22003` reasoning is hedged correctly: "most likely becomes a numeric-literal comparison and returns a harmless 404", against the alternative that lands in the catch and returns 500. It correctly ties this to the contract's no-500 clause and gives a cheap test.
- The claims I checked hold. `Number("1e3")`, `"0x10"` and `" 1 "` do pass the guard, and the org check does prevent any tenant crossover.
- The verifier doesn't patch, and the output says so. I found no invented facts.

**In voice: ✅.** The prose reads as the persona throughout, including "The only thing standing between `portal_password_hash` and the wire is that nobody has yet typed it into the query."

**Self-challenge done: ⚠️ weak.**
- There is evidence the output tried to break its own claims. It keeps the 404 claim as surviving ("True. This claim survives."). It works the pg-promise-versus-int4 branches both ways, and its "Claimed vs. actual" table is a genuine cross-check.
- Severity calibration is looser than it should be. The "no allowlist" ❌ MEDIUM is the same root cause as the HIGH, so it double-counts. The inner-JOIN ❌ MEDIUM rests on a schema the verifier admits it never saw ("The defect is real if the constraint is absent"). That belongs at ⚠️ or as a confirm-item only, not a ❌ mark.

## Verdict rule

There are no ❌ marks on the hard gates or the structural invariants. The two ⚠️ marks are the contract-conformance uncertainty with the stray hook text, and the inflated severity on the speculative and duplicate findings. Applied literally, that gives WEAK.

VERDICT: WEAK