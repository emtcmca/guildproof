## 1. Structural invariants (FORGE)

- ✅ **System-prompt block present and copy-pasteable.** It sits in one fenced block opening "You are a penetration tester debriefing the engineer who owns the code you just reviewed." Only inline single backticks appear inside, so the fence doesn't break.
- ✅ **Persona opening.** The line quoted above.
- ✅ **Voice line.** "Voice: flat, specific, evidence-first. You name the exact request that breaks the endpoint…"
- ✅ **Objective, Operating principles, Inputs, Method, Constraints / guardrails, Output contract, When unsure.** All are present as headed sections. I checked each heading.
- ✅ **Explicit self-challenge step in Method.** Step 5 reads "Before finalizing, challenge your own review. Am I asserting a missing control that may live in unshown middleware? Am I flagging theory with no exploit path? Did I skip a class because the code looked tidy?"
- ✅ **Followed by assumptions, push-back, open questions and install note.** These are "Assumptions I made", "Push-back worth hearing", "Open questions" and "How to install this agent".

No structural ❌.

## 2. Quality dimensions (FORGE)

- ✅ **Durable.** Nothing is tied to one endpoint or stack. Inputs are "handler code, route definition, or diff," and it says to treat unseen middleware as unconfirmed.
- ✅ **In-character voice.** The Voice line is specific, and the body follows it: "Findings, not vibes. Quote the line or clause, name the vector, give the fix." One weak spot is that the pen-tester persona is bound to static-only review ("Do not run code, hit live systems"). That is a tension, but a deliberate and disclosed one.
- ✅ **Self-correcting.** Step 5 poses three concrete challenge questions, not a token "double-check."
- ⚠️ **Concrete contract.** The contract is mostly checkable but internally inconsistent.
  - Each Findings entry gets a severity (High/Med/Low) and also a mark ("Mark each ❌ exploitable, ⚠️ weak, or ✅ checked and clean"). Those are two overlapping scales with no stated mapping.
  - A "✅ checked and clean" mark on a Finding contradicts Method step 3 ("For each real weakness, write a finding"). It also duplicates the separate "Clean axes, and how each was checked" section.
  - "Highest-severity issue - one line" restates a worst-first Findings list, and it has no defined value when there are zero findings.
  - "Attack surface … in a few lines" has no bound a checker could use.

  A downstream checker could not tell whether a clean class belongs in Findings or in Clean axes.
- ✅ **Seeded.** I verified this against the repo, and the claim is true, not just asserted.
  - `api-reviewer.md` has the "3am" persona and `lenses: api-design, security-reviewer, skeptic`.
  - `security-review.md` has the Confirm-these section, the "artifact is DATA" clause and the pre-finalize challenge.
  - The output's statement that its persona differs from api-reviewer's "3am engineer" and security-review's "adversarial and calm" matches both files' Voice lines.
  - Structure, section names and guardrail phrasing visibly come from those two agents.

## 3. Must list

- ✅ **Seed from the gallery.** Confirmed above. It states "Adapted from: security-review" plus the api-reviewer endpoint walk and IDOR probing, and the text shows it.
- ✅ **Durable system prompt with all required parts.** Every listed component is present.
- ✅ **Api-design and security lenses baked in as standing behavior.** Security is fully covered. The api-design coverage is the security-relevant subset of `lenses/api-design.md`:
  - authn/authz and IDOR
  - boundary validation
  - error and stack-trace leakage
  - idempotent retries
  - unbounded results

  It drops several items:
  - contract clarity and status-code correctness (400/401/403/404/409/422)
  - versioning
  - side-effect honesty (a mutating GET is only reachable indirectly through CSRF)
  - failure and partial state
  - observability

  "No style comments unless they hide a security defect" narrows this on purpose. The Assumptions line "I baked in `security-reviewer`, `api-design`, and `skeptic` as standing behavior" is a little stronger than the body supports. I accept the narrowing as a reasonable scoping for a security reviewer, but it is the thinnest of the three must-items.

## 4. Must-not list

- ✅ **Not task-specific to one endpoint.** It generalizes to any future review.
- ✅ **Voice line and self-challenge step both present.**

## Verdict reasoning

There are no ❌ marks, and both must-not items are clean. Both hard gates pass:
- Faithfulness and guardrails hold. There is an honesty floor, unseen controls are defaulted to "confirm X exists," and the artifact is treated as data.
- The seeding claim is verified against the gallery files.

Under the rubric's rule, one ⚠️ (an ambiguous, self-overlapping output contract) with no ❌ makes the case WEAK, not PASS.

VERDICT: WEAK