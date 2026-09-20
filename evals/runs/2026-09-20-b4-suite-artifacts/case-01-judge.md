## 1. Structural invariants (SHARPEN)

- ✅ **All 9 blocks present and filled.** ROLE, OBJECTIVE, CONTEXT, REQUIREMENTS, GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA, OUTPUT FORMAT and OUT OF SCOPE all appear. The extra "STEP 0" block is additive and does not displace any of them.
- ✅ **PROHIBITIONS and OUT OF SCOPE are distinct.**
  - PROHIBITIONS names actions tied to this task: "Don't touch: auth and session handling… the settings' stored values, defaults, and persistence logic" and "Don't remove or hide any existing setting".
  - OUT OF SCOPE names work not being done this pass: "New settings or features… dark mode… a settings search feature, internationalization, and any backend change."
  - Some overlap in flavor, but neither is collapsed or generic boilerplate.
- ✅ **No unfilled `<...>` slots.** `[stack?]` and `[path?]` are square-bracket gap flags, which the rubric scores as correct behavior. No angle-bracket slots remain.
- ✅ **One copy-pasteable block, with assumptions, push-back and open questions after it.** The prompt sits in one block, followed by "Assumptions I made", "Push-back worth hearing" and "Open questions".
- ✅ **Each assumption has "Override with:".** Assumptions 1–5 each carry one. Assumption 6 ("I left the stack and file path as `[stack?]` and `[path?]`") has none. It is a gap flag rather than an assumption, and open question 2 serves as its override, so I am not scoring it ❌. It is still an item sitting under the "Assumptions" heading without the required marker.

## 2. Quality dimensions

- ✅ **Push-back is real.** "'Nicer' can't be checked, so an agent asked for it will produce a generic restyle: more padding, softer corners, and a new color or two." It also warns that a visual pass can make a destructive action "easier to hit by accident, or quietly change what a save does". It names a concrete fix: "one sentence on what bugs you about the page today."
- ✅ **Named concreteness.**
  - The tone is named: "'Nicer' here means calm, clear, and trustworthy".
  - The prompt gives measurable targets: "4.5:1 (3:1 for large text…)", "roughly 45-75 characters", "about 44px", and 375px and 1280px widths.
- ✅ **Faithfulness (hard gate).**
  - Stack, path, design system and save model are all flagged or delegated: "Read the repo to find out. Do not assume one." and "If there is no design system, derive a small one".
  - Destructive controls appear only as examples ("for example, no connected accounts"). Nothing is asserted as an existing product fact.
- ✅ **Lens fit.**
  - The ROLE names "UX designer, visual designer, and accessibility specialist".
  - Their checklists show up in REQUIREMENTS:
    - Visual: type hierarchy and a restrained palette.
    - UX: the states list and error placement.
    - Accessibility: focus ring, contrast, real labels, headings, targets and reduced-motion.
- ⚠️ **Would steer.** Mostly strong, but there are weaknesses that could send a competent agent the wrong way:
  - **Contradiction on confirm-on-destruct.** The OBJECTIVE says "behavior, data, and settings stay exactly as they are". REQUIREMENTS says "keep or add confirm-on-destruct". PROHIBITIONS says "Don't invent… features". Adding a confirmation is a behavior change, and the prompt never says which rule wins.
  - **Unknowable ordering rule.** "Put the most-used settings first" assumes usage data the agent cannot get from the code.
  - **Bulk.** The prompt is very heavy for a three-word request. It is defensible, but it adds surface for such conflicts.

## 3. Case must list

- ✅ **Gap-fill with labeled, reversible assumptions.** Five labeled assumptions each carry an "Override with:", and the prompt proceeds rather than stalling.
- ✅ **Auto-pick UI lenses and reflect their checklists in REQUIREMENTS.** See lens fit above.
- ✅ **Push-back names that "nicer" is unmeasurable and forces concreteness.** It does so without flattery and points at Step 0 and the checkable success criteria.
- ✅ **Name target adjectives explicitly.** "calm, clear, and trustworthy".

## 4. Case must-not list

- ✅ **Invent product facts as if known.** Not violated. Everything about the existing app is conditional or delegated to Step 0.
- ✅ **Leave any `<placeholder>` unfilled.** Not violated. Only square-bracket gap flags are present, and they are correct behavior.

No ❌ anywhere, so no hard gate fails. One ⚠️ on "Would steer" (the confirm-on-destruct contradiction) keeps this from PASS.

VERDICT: WEAK