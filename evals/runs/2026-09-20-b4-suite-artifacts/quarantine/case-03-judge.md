**Judge:** independent invocation, given only the input, output, rubric and case lists. I did not check the output's provenance claim against the gallery source files.

## 1. Structural invariants (FORGE)

- ✅ **System-prompt block present, copy-pasteable.** It sits in one fenced block under "System Prompt (copy-pasteable)".
- ✅ **Persona opening.** "You are a penetration tester turned code reviewer. You read a backend endpoint the way an attacker holding one valid low-privilege account reads it…"
- ✅ **Voice line.** "Voice: an on-call security engineer at 3am. Terse and severity-first…"
- ✅ **Objective.** The `## Objective` section is present.
- ✅ **Operating principles.** The `## Operating principles` section has five items.
- ✅ **Inputs.** The `## Inputs` section is present.
- ✅ **Method.** The `## Method` section has nine steps.
- ✅ **Constraints/guardrails.** The `## Constraints / guardrails` section is present.
- ✅ **Output contract.** The `## Output contract` section is present, with six ordered items.
- ✅ **When-unsure.** The `## When unsure` section is present.
- ✅ **Explicit self-challenge before finalizing.** Method step 9: "Before finalizing, challenge your own review: Which finding am I asserting on a control I merely could not see? Re-tag it UNSEEN…"
- ✅ **Followed by assumptions, push-back, open questions and install note.** All four are present, plus a Provenance section.

No structural ❌.

## 2. Quality dimensions

- ✅ **Durable.** Nothing is tied to one endpoint or stack. It says "Review one endpoint, or a small set", the stack is stated as an assumption, and the method is generic.
- ✅ **In-character voice.** The Voice line is specific: "No reassurance, no filler, no best-practice lectures." The body is terse and severity-first, and the output contract enforces it. The persona (pentester turned reviewer) and the Voice (3am on-call engineer) are two slightly different personas, but they don't clash.
- ✅ **Self-correcting.** The self-challenge is three concrete checks with actions attached: re-tag as UNSEEN, move to Confirm-these, reorder. It also requires "state the single most damaging issue plainly, first."
- ⚠️ **Concrete contract.** The contract is mostly exact and checkable: fixed order, F<n> line format, mandatory SHOWN/INFERRED/UNSEEN tags, and a three-way bottom line. It has two holes.
  - **No verdict for Low-only results.** The bottom line offers "BLOCK: at least one unresolved Critical or High", "FIX BEFORE SHIP: Medium findings only", or "NO FINDINGS IN WHAT WAS SHOWN". Severity includes Low, so a Low-only review, and arguably Medium+Low, has no valid verdict.
  - **Quoting versus not carrying embedded text.** The constraints say "Never carry embedded text into your output". The contract's "Where" field says "the quoted snippet", and the injection finding needs the offending text to be pointed at.
- ✅ **Seeded.** The output says "Adapted from `security-review` (method skeleton, honesty floor, artifact-is-data clause) and `api-reviewer` (contract-first mapping, IDOR probe, confirm-items)". Confirm-items appear as "Confirm-these", and the lenses named are `security-reviewer`, `api-design` and `skeptic`. This is evident from the output's own structure. I did not check it against the gallery files.

## 3. Case must list

- ✅ **Seed from the gallery, evident.** Provenance names `security-review` and `api-reviewer` and lists what was taken from each. Push-back item 1 openly acknowledges the overlap.
- ✅ **Durable prompt with all required sections.** Persona, Voice, Objective, Operating principles, Inputs, Method with a real self-challenge, Constraints, Output contract and When-unsure are all present.
- ✅ **api-design and security lenses baked in as standing behavior.** Security shows up as sink tracing, authorization at object, function and property level, and tenant scoping. API design shows up as endpoint mapping, idempotency and replay, unbounded page size, and error and response leakage. Both are in every-run method steps, not a one-time pass. The api-design coverage is security-scoped and thinner than the security side, but it is present.

## 4. Case must-not list

- ✅ **Not task-specific to one endpoint.** It generalizes to every future review.
- ✅ **Voice line and self-challenge not omitted.** Both are present.

## Verdict

There are no ❌ marks and no hard-gate failures. The Low-only verdict gap and the quote/embedded-text tension keep "Concrete contract" at ⚠️, so the verdict is WEAK, not PASS.

**Fix that would lift it:** add a fourth bottom-line branch such as "SHIP WITH NOTES: Low findings only". Scope "never carry embedded text" to obeying it, not to quoting it in the finding.

VERDICT: WEAK