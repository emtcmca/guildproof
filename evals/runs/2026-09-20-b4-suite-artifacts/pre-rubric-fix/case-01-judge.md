## 1. Structural invariants (SHARPEN)

- ❌ **No unfilled placeholders remain.** The pasteable prompt still contains `[path or route of the settings page?]`, `[stack?]` and `[tokens / component library / brand reference?]`. The output's own assumptions section admits it: "I left `[stack?]`, `[path…?]`, and `[design system?]` as placeholders." The rubric's literal wording is `<...>`, but square brackets are the same defect, and the output itself calls them placeholders. Hard-gate failure.
- ✅ **All 9 blocks are present and filled.** ROLE, OBJECTIVE, CONTEXT, REQUIREMENTS, GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA, OUTPUT FORMAT and OUT OF SCOPE all appear.
- ✅ **PROHIBITIONS and OUT OF SCOPE are distinct.** PROHIBITIONS is tied to this task ("Don't touch: auth and session handling… any setting's stored key or value format"). OUT OF SCOPE lists work not being done ("Changing what settings exist… other pages… global theme"). There is some overlap (features, other pages), but PROHIBITIONS is not boilerplate.
- ⚠️ **One copy-pasteable block, with assumptions after it.** The order is correct: the prompt comes first, then Assumptions, Push-back and Open questions. The harness wrapper hides whether the prompt sits in its own fence, so I can't confirm this. I'm not marking it ❌.
- ✅ **Each assumption has "Override with:".** All six do. The stack one is weak ("Filling them in makes the prompt tighter"), but it is present.

## 2. Quality dimensions

- ✅ **Push-back is real.** "'Nicer' can't be tested, so the agent will guess" names the actual weakness. The regression-risk point ("quietly moves a delete button next to Save") is specific to settings pages.
- ✅ **Named concreteness.** "Tone and feel: calm, clear, unfussy. Restraint over decoration," plus the modern-minimal family (muted palette, generous whitespace, soft radius, minimal motion).
- ✅ **Faithfulness (hard gate).** Product facts are conditional rather than asserted: "use the product's existing… components. If they don't exist…", "If one exists, it is the source of truth", "if the page already has an explicit save model". Only preferences were assumed. The `[missing: …]` instruction in PROHIBITIONS tells the agent to flag gaps rather than invent them. Minor presumptions: that a type check, lint and a build exist, and that "the rest of the product" exists.
- ✅ **Lens fit.** UX, visual design and accessibility are named in ROLE. Their checklists appear in REQUIREMENTS: the type and spacing scale, and a bulleted accessibility block covering 4.5:1 and 3:1 contrast, focus ring, ~44px targets and reduced motion.
- ⚠️ **Would steer.** Mostly, but there are real internal contradictions.
  - REQUIREMENTS asks for "a plain-language label" for every setting, while GUARDRAILS says renaming a setting "is not [allowed], without a flag".
  - "keeps or gains a confirm step" and "cover loading, saving, save-success, save-error… for every section" both add behavior. PROHIBITIONS says "Don't change behavior" and "Don't add features".
  - Requiring helper text on each setting sits badly against "no… copy claims" (don't invent).
  - The CONTEXT bracket placeholders are questions the agent can't answer from the prompt alone.
  - "GUARDRAILS (from red-team pass)" leaks pipeline meta into the pasteable prompt.

## 3. Case must list

- ✅ **Gap-fill with labeled, reversible assumptions.** Six assumptions, each with an override. "Nicer" is defined as visual polish plus layout and usability, and it doesn't stall. Audience is only implicit ("a first-time user"), and the stack is deferred rather than assumed.
- ✅ **Auto-pick UI lenses.** "three review lenses… UX… visual design… and accessibility", reflected in REQUIREMENTS.
- ✅ **Push-back names that "nicer" is unmeasurable and forces concreteness.** It says so directly and adds an audit-first step and open question 1.
- ✅ **Name target adjectives.** "calm, clear, unfussy."

## 4. Case must-not list

- ✅ **Invent product facts as if known.** Not violated. Everything is conditional on what the existing code shows.
- ❌ **Leave any placeholder unfilled.** Violated. `[path or route…?]`, `[stack?]` and `[tokens / component library / brand reference?]` remain in CONTEXT, and the output acknowledges leaving them. Hard-gate failure.

## Verdict

The output is strong on push-back, lens fit, adjectives and assumptions. It fails on the explicit must-not and the structural invariant against unfilled placeholders, and it contains the internal contradictions noted above.

VERDICT: FAIL