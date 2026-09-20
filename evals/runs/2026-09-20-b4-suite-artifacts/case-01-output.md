```
ROLE: You are a senior product designer and front-end engineer, working through three lenses: UX designer, visual designer, and accessibility specialist. You improve existing interfaces without changing what they do.

OBJECTIVE: Make the settings page easier to scan, easier to use, and more polished, while its behavior, data, and settings stay exactly as they are. "Nicer" here means calm, clear, and trustworthy: a user should find the setting they came for in a few seconds and know whether their change took effect.

CONTEXT:
- Stack and framework: [stack?]. Read the repo to find out. Do not assume one.
- Settings page location: [path?]. Find it, and report where you found it before you change anything.
- Existing design language: reuse the app's existing tokens, components, spacing scale, and type scale. If there is no design system, derive a small one from what the app already does and name it. Do not import a new look.

STEP 0, BEFORE ANY EDIT:
Read the page and its components. Report back in 10 lines or fewer:
1. The sections and controls it currently contains.
2. The save model: autosave, explicit save button, or per-field save.
3. Which controls are destructive or irreversible (delete account, revoke access, reset).
4. The three biggest problems you see, ranked by how much they hurt a first-time user.
Then proceed. Base the redesign on those findings, not on generic taste.

REQUIREMENTS:
- Structure: group related settings under clear section headings. Put the most-used settings first. Keep a consistent label, control, and help-text pattern across every row. One job per section.
- Visual: define a clear type hierarchy (page title, section heading, label, help text). Use the existing spacing scale consistently. Keep the palette restrained. Keep body text and help text to a readable line length (roughly 45-75 characters). Give the primary action one obvious visual weight, and keep everything else quieter.
- Copy: labels and help text should use the user's language, not internal field names. Rewrite only text that is unclear, and list each rewrite so it can be reviewed.
- All states, designed and checked: default, hover, focus, disabled, loading, saving, saved, error, and empty (for example, no connected accounts).
- Feedback: every change gives immediate, legible confirmation (saved, failed and why). Errors sit next to the field and say how to fix it.
- Destructive actions: keep them visually separated from routine settings, keep or add confirm-on-destruct, and never make them easier to trigger by accident than they are today.
- Accessibility (WCAG AA): full keyboard operation with a visible focus ring and logical tab order; text contrast of at least 4.5:1 (3:1 for large text and UI boundaries); real labels on every input; semantic headings and landmarks; no meaning conveyed by color alone; touch targets of about 44px; respect prefers-reduced-motion.
- Responsive: layout holds at 375px and 1280px wide, with no horizontal scroll and no clipped controls.

GUARDRAILS:
- Preserve the existing save model. Do not turn explicit-save into autosave or the reverse. If you think it should change, say so in your report and leave it alone.
- Keep the form working during the redesign: fields keep their names, ids, and validation, and existing tests, analytics hooks, and any e2e selectors keep working. If a selector must change, list it.
- If a setting's purpose is unclear from the code, ask or flag it. Do not guess at a friendlier label that might change its meaning.
- Prefer removing visual noise over adding decoration. Every new element must earn its place.

PROHIBITIONS (must NOT do):
- Don't invent: no new settings, features, API endpoints, config keys, or copy that makes claims about behavior you haven't confirmed in the code. Flag any gap instead.
- Don't touch: auth and session handling, the data schema and migrations, billing and payments, permissions and security controls, public API contracts, and the settings' stored values, defaults, and persistence logic.
- Don't exceed scope: no changes outside the settings page and the components it uses exclusively. No drive-by refactors, renames, dependency additions, or formatting sweeps. If a shared component must change, stop and list every other place it is used first.
- Don't remove or hide any existing setting, even one that looks unused. Flag it.

SUCCESS CRITERIA:
- A keyboard-only pass reaches and operates every control in a sensible order, and focus is always visible.
- Automated contrast and accessibility checks (axe or Lighthouse, whichever the project has) report no new violations, and text and UI contrast meets AA.
- Every state in the requirements list is demonstrably reachable and looks intentional.
- Before and after screenshots at 375px and 1280px are provided.
- The existing test suite, type-check, and production build all pass, and the diff contains no changes to persistence, validation, or API calls.
- The diff is limited to files under the settings page and its exclusive components.

OUTPUT FORMAT:
1. The Step 0 findings, then a short plan (what you will change and why, at most 8 bullets), before editing.
2. The implementation, in small commits that each leave the app working.
3. A closing report with: before/after screenshots, the list of copy changes, the check results with the commands you ran, and a "Noticed but did not change" list (save-model concerns, unused settings, shared-component issues, anything else out of scope).

OUT OF SCOPE: New settings or features, a redesign of navigation or the rest of the app, dark mode (unless the app already supports it and the page breaks in it), a settings search feature, internationalization, and any backend change.
```

## Assumptions I made
- I assumed "nicer" means visual polish plus scannability and clarity. Override with: "It's purely visual, don't reorganize sections," or "the real problem is findability, prioritize structure."
- I assumed the page should conform to the app's existing look, not get a new aesthetic (modern-minimal, calm, restrained). Override with: name the direction, such as "warmer and friendlier" or "denser and more technical."
- I assumed the current save behavior stays as it is. Override with: "Switch to autosave" (or the reverse), which is a behavior change and should be scoped separately.
- I assumed no new settings and no removals. Override with: list what should be added or cut.
- I assumed desktop and mobile widths both matter (375px and 1280px). Override with: "desktop only."
- I left the stack and file path as `[stack?]` and `[path?]` placeholders. The prompt tells the agent to find them instead of guessing.

## Push-back worth hearing
- "Nicer" can't be checked, so an agent asked for it will produce a generic restyle: more padding, softer corners, and a new color or two. The Step 0 findings and the checkable success criteria in the prompt are there to prevent that. The most useful thing you can add is one sentence on what bugs you about the page today.
- Settings pages hold the riskiest controls in an app (delete account, revoke access, change email). A visual pass that moves or restyles them can make a destructive action easier to hit by accident, or quietly change what a save does. The prompt therefore separates destructive controls and freezes persistence, but you should still check the diff for changes to save behavior.

## Open questions (answer these, or run with `--deep`)
1. What's wrong with it now: it looks dated, it's hard to find things, it's too long, or it feels untrustworthy? This changes the priority order more than anything else.
2. What's the stack and where does the page live, and is there an existing design system or component library the page should follow?
3. Does the page autosave or use a Save button, and does it contain destructive settings (delete, reset, disconnect)?

Run `/guildproof:sharpen make the settings page nicer --deep` and I'll ask these one at a time, then rebuild the prompt with your answers instead of assumptions.