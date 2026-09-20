## 1. Structural invariants (SHARPEN)

- ✅ **All 9 blocks present and filled.** ROLE, OBJECTIVE, CONTEXT, REQUIREMENTS, GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA, OUTPUT FORMAT and OUT OF SCOPE are all there. STEP 0 is an extra block.
- ✅ **PROHIBITIONS and OUT OF SCOPE are distinct.**
  - PROHIBITIONS lists actions tied to the task: "Don't touch: auth and session handling, billing and payment logic…" and "no drive-by refactors… or new dependencies".
  - OUT OF SCOPE lists work not being done this pass: "New settings or features, changing how settings are persisted, a full app-wide redesign… dark mode".
  - The two are not merged and not boilerplate.
- ❌ **No unfilled placeholders remain.** The CONTEXT block, inside the paste-ready prompt, reads "The settings page is at **[PATH TO SETTINGS PAGE?]** in a **[STACK/FRAMEWORK?]** app."
  - The rubric names `<...>`, and these are square brackets, but they are still unfilled placeholders in the copy-paste block.
  - The output confirms it: "I left `[PATH]` and `[STACK/FRAMEWORK?]` as placeholders rather than guess."
  - A prose fallback such as "locate the settings page in the repo; path and stack were not provided" would have flagged the gap without leaving a fill-in slot.
- ✅ **Prompt is in one copy-pasteable block, with assumptions, push-back and open questions after it.** Correct order.
- ✅ **Each assumption has an explicit "Override with:".** All seven do.

Structural gate: **❌**, on the placeholders.

## 2. Quality dimensions

- ✅ **Push-back is real.** "**'Nicer' isn't checkable.** Without a named problem, the agent will restyle spacing and colors and stop." The second point, that restyling can silently break a form, is also a genuine risk. Neither is flattery.
- ❌ **Named concreteness.**
  - The rubric requires tone and feel adjectives to be named explicitly.
  - The prompt defines "nicer" as "easier to scan… more polished" and "consistent". These are outcomes, not target adjectives, and "polished" is exactly the vague word the case is testing.
  - The only tone adjectives appear as an unchosen menu in an override: "[calm / premium / playful / dense]".
  - No feel is committed to in the prompt.
- ✅ **Faithfulness (hard gate).**
  - It invents no domain facts. Security, billing and delete controls are framed conditionally: "If the page renders a security or billing control…".
  - "autosave, per-section Save, or one page-level Save" is offered as something to discover.
  - The design-token assumption is labeled and hedged: "If there is no design system, say so… wait for approval".
- ✅ **Lens fit.**
  - ROLE names "UX… visual design… accessibility".
  - The checklists show up in REQUIREMENTS: the states list, "4.5:1 and UI-component contrast 3:1", the type scale, spacing scale and keyboard operability.
- ⚠️ **Would steer.**
  - Mostly yes, and STEP 0 is a sound gate.
  - The literal bracket placeholders would sit in the pasted prompt.
  - "reorder-in-effect" is muddled wording.
  - "GUARDRAILS (from red-team pass)" leaks process meta into the agent's prompt.
  - The prompt is very long for a one-line request.

## 3. This case's must list

- ✅ **Gap-fill with labeled, reversible assumptions.** Seven labeled assumptions, each with an override, and no stalling. Audience was never assumed, and stack was left as a placeholder rather than a labeled default, which is a small gap.
- ✅ **Auto-pick UI lenses and reflect their checklists in REQUIREMENTS.** UX, visual and accessibility, as above.
- ✅ **Push-back names that "nicer" is unmeasurable and forces concreteness.** "'Nicer' isn't checkable", followed by the ask "What specifically feels not-nice?".
- ❌ **Name target adjectives explicitly.** No target feel is named, such as calm, ordered or trustworthy. Only "polished" and "consistent" appear, and the adjective menu sits unchosen in an override.

## 4. This case's must-not list

- ✅ **Invent product facts as if known.** Not violated. Framework, components and tokens are all flagged as unknown.
- ❌ **Leave any placeholder unfilled.** `[PATH TO SETTINGS PAGE?]` and `[STACK/FRAMEWORK?]` are unfilled, and the output says so itself. This is a hard-gate failure.

## Verdict

There is a structural ❌, a must-not ❌ (a hard gate), a must-list ❌ (no named adjectives) and a quality ❌ (named concreteness). The output is otherwise strong on push-back, lens fit and prohibition design, but the rubric's gates decide the verdict.

VERDICT: FAIL