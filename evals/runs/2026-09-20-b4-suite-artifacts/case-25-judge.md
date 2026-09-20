# Scoring: `agent` route, `evaluator`

Judge note: I'm a separate invocation from the producer. I read `agents/evaluator.md` only to check the Output contract.

## 1. Structural invariants (gallery agent)

- ✅ **Rubric used, stated first.** "Rubric used (derived, not supplied)" comes before the scores, with the scale and six criteria. It also says "Correct it before trusting the grades."
- ✅ **Scores worst-first, one line per criterion.** The order is ❌ Spam, ❌ Specificity, ⚠️ Actionability, ⚠️ Set coherence, ⚠️ Tone, ✅ Length. The line format is bold-and-period rather than the contract's `criterion — reason`, which is cosmetic.
- ✅ **Hard gates section present.** "Failed: no all-caps urgency or stacked exclamation marks (line 3)."
- ✅ **Verdict with a justification.** "WEAK (1 ✅ · 3 ⚠️ · 2 ❌…)". I recounted the marks and they are correct.
- ✅ **Top 3 fixes, each with the change and the score it recovers.** "lifts spam-pattern risk from ❌ to ✅", "lifts specificity from ❌ toward ✅", "lifts set coherence from ⚠️ to ✅".
- ✅ **Voice detectable.** It reads as a grader: it quotes the lines, marks against stated criteria, and ends with a Skip line.

No structural ❌.

## 2. Quality dimensions

- ⚠️ **Contract honored.** All sections are present, but the verdict logic is not stated. The derived rubric says the verdict is "PASS, WEAK or FAIL" and never gives the mapping. It then returns WEAK with two ❌ and a failed hard gate, "capped by the hard-gate failure". A cap that lands on the middle label is unexplained. The user can't correct a rule they were never shown.
- ✅ **Guardrails honored (hard gate).**
  - It does not rewrite. The last line says "I don't rewrite the lines myself."
  - The derived criteria and the hard gate are both stated.
  - The assumptions are declared: "I don't know… the product, the audience seniority, the brand voice, or any send data."
  - No performance figures are asserted.
  - One soft spot: "B2B recipients tend to read that pattern as phishing or a dunning notice" is an unsourced generalization. It is hedged and does not breach the floor.
- ⚠️ **Marks are earned: length ✅ is not fully earned.** The ✅ on "Length and front-loading" comes with its own defect: "the all-caps prefix uses the first ~16 characters, so the actual ask may fall past the cut-off." A criterion with a stated miss on line 3 should be ⚠️. The caveat is also admitted as "a rule of thumb, not something measured."
- ⚠️ **Marks are earned: the same defect is docked repeatedly.**
  - Genericness is counted under Specificity ("Any SaaS could send these three"). It is counted again under Actionability ("doesn't say which").
  - It is counted a third time under Tone ("celebratory framing carries no information").
  - Line 3 is counted twice: once under Spam risk and once as the derived hard gate.
  - This inflates the ❌ and ⚠️ count.
- ⚠️ **Defect versus preference.**
  - Tone is marked ⚠️ although the output calls the emoji and "Welcome aboard!" "a risk flag, not a defect: it depends on your brand voice."
  - The Skip line calls the emoji "brand-voice preference."
  - The output contradicts itself here, and this is the taste-docking the agent's own principles forbid.
- ⚠️ **Specificity ❌ is over-reach.** "None of the three names a product, a first-name token…" Both are unknowns the output admits it lacks. A first-name token is personalization, not specificity. "Your account is ready" does carry a concrete state.
- ⚠️ **Fix leverage.** Fix 3 ("Define each subject's job in the sequence: its trigger and timing") changes send logic, not the copy. Re-grading the same three lines would leave Set coherence at ⚠️. The claim that it "lifts set coherence from ⚠️ to ✅" is not shown. Fixes 1 and 2 are sound and correctly ordered.
- ⚠️ **Self-challenge visible.** There is some (defect versus preference, the Skip list, "I don't know…"). The Tone and Length marks above show it did not fully take effect. The verdict line also calls the set "clear" when no clarity criterion was scored.

## 3. Case must list

- ✅ **Derived rubric stated first**, with dimensions and scale.
- ✅ **Each criterion scored with a reason that quotes the artifact.** Line 3 is flagged for "all-caps, a triple exclamation and a bare urgency claim" and for overstating its case if setup isn't blocking anything.
- ✅ **Top 3 fixes ranked by leverage**, each naming the score it recovers.
- ✅ **Verdict rendered:** WEAK.

## 4. Case must-not list

- ✅ **No rewrite of the subject lines.** The fixes are directional and it delegates the rewrite.
- ✅ **No unstated criterion.** Every criterion and the hard gate are declared. The unstated verdict mapping is a legibility gap, not a hidden criterion. The Tone dock is tied to a named criterion, though the reasoning is inconsistent (see above).
- ✅ **No open or click-rate numbers asserted.** It says "Nothing here says how the lines will inbox or perform."

## Verdict

There are no ❌ on the structure, the must list, the must-not list, or the guardrails. There are several ⚠️, mainly on marks that aren't fully earned, double-counted deductions, and an unstated verdict rule.

VERDICT: WEAK