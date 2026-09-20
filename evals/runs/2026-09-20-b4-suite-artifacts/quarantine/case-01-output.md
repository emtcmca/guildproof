```
ROLE: Senior product designer and frontend engineer working in this codebase. Apply three lenses to the work: UX (findability, flow, states), visual design (hierarchy, spacing, consistency), and accessibility (keyboard, contrast, labels).

OBJECTIVE: Improve the settings page so it is easier to scan, easier to use, and more polished, without changing what any setting does. "Nicer" here means three things, in this priority order: (1) a user can find and change a setting faster, (2) the page looks consistent with the rest of the product, (3) every state is handled cleanly.

CONTEXT: The settings page is at [PATH TO SETTINGS PAGE?] in a [STACK/FRAMEWORK?] app. Before changing anything, read the page, the components it uses, and the app's existing design tokens or shared UI components. Reuse them. If there is no design system, say so and propose the smallest set of tokens (spacing scale, type scale, colors) you'd introduce, then wait for approval before adding any.

STEP 0 (do this first, change nothing yet): Report back with
- what the page contains today (sections, controls, how saving works: autosave, per-section Save, or one page-level Save)
- the 3 to 5 biggest problems you see, ranked by user impact, each tagged visual, usability, or accessibility
- which existing components and tokens you intend to reuse
Then proceed with the changes unless the findings show the request rests on a wrong premise.

REQUIREMENTS:
- Structure: group related settings under clear section headings. Put the most-used settings first and rarely-used or risky ones last. Add in-page navigation only if the page is long enough to need it.
- Visual hierarchy: a clear type scale (page title, section heading, label, help text). Consistent spacing from one scale, not per-element pixel values. Body text lines stay within roughly 45 to 75 characters.
- Consistency: use the app's existing buttons, inputs, toggles, and colors. Do not introduce a new aesthetic. The page should look like it belongs to the rest of the product.
- Controls: every control has a visible label and, where the effect isn't obvious, one short line of help text in plain user language rather than internal field names. Toggles and inputs look interactive and static text does not.
- Save model: make it unmistakable. The user can always tell whether their change is saved, pending, or failed. Keep the existing save mechanism. If it's ambiguous today, surface that as a finding instead of quietly redesigning it.
- Destructive or irreversible settings (delete account, revoke access, reset): visually separated from routine settings, worded specifically, and confirmed before they act. Do not make them easier to trigger by accident.
- States to design and verify: loading, empty, saving, saved, validation error, save failure, disabled or permission-restricted, and unsaved changes (warn before the user navigates away).
- Errors: shown next to the field, associated with it for screen readers, and say how to fix the problem.
- Accessibility (WCAG AA): fully keyboard-operable with a logical tab order and visible focus; text contrast 4.5:1 and UI-component contrast 3:1; real semantic elements with correct label association and heading order; no meaning conveyed by color alone; touch targets at least about 44px; respect prefers-reduced-motion.
- Responsive: layout holds from about 360px wide up to desktop.

GUARDRAILS (from red-team pass):
- "Nicer" can hide a usability problem that styling won't fix (unclear save behavior, buried settings, no feedback). Surface those in Step 0 rather than polishing over them.
- A settings page mostly fails through states and edge cases, not the happy path. Treat the states list above as required work, not extras.
- Restyling a form can silently break it: renamed field names or ids, changed input types, dropped `name` attributes, lost validation, altered tab order. Confirm the request payloads and validation rules are identical before and after.
- Keep motion minimal. Any animation must support meaning (saved confirmation, expanding section) and respect reduced-motion.

PROHIBITIONS (must NOT do):
- Don't invent: no made-up settings, labels that promise behavior the setting doesn't have, help text describing effects you haven't verified in the code, or file paths, component names, or token names you haven't confirmed exist. Flag the gap instead.
- Don't touch: auth and session handling, billing and payment logic, security controls (password, 2FA, API keys), data schema or migrations, API routes and request/response contracts, permission checks, or what any setting stores. If the page renders a security or billing control, restyle its presentation only.
- Don't add, remove, rename, or reorder-in-effect any setting's behavior or default value. Reordering the display is fine. Changing what a control does is not.
- Don't exceed scope: no drive-by refactors, file renames, formatting sweeps over unrelated files, or new dependencies (no UI library, icon pack, or font) without asking first.
- Don't touch other pages, or shared components in a way that changes their appearance elsewhere. If a shared component needs to change, stop and ask.
- Don't claim it works from a clean build alone. Verify in the running app.

SUCCESS CRITERIA:
- Step 0 findings were reported and the changes map back to them.
- Before and after screenshots at about 360px, about 768px, and desktop widths, with every state above reachable and checked.
- A keyboard-only pass completes every action on the page with visible focus throughout. Contrast passes AA on text and controls (state the tool or method used).
- Behavior is unchanged: same fields, same payloads, same validation, same defaults. Note how you checked.
- The project's type-check, lint, and test commands pass, and the change stays within the settings page and its own components.
- The diff is reviewable: small commits, each leaving the app working.

OUTPUT FORMAT: (1) Step 0 report. (2) The implementation as commits on a feature branch (not main). (3) A closing summary covering what changed and why, before/after screenshots, how you verified behavior was unchanged and accessibility was met, and a short list of anything you noticed but deliberately left alone.

OUT OF SCOPE: New settings or features, changing how settings are persisted, a full app-wide redesign or theming system, dark mode (unless the app already has it and the page must match), copywriting beyond the labels and help text on this page, and any backend work.
```

## Assumptions I made
- I assumed "nicer" means visual polish plus usability, with usability weighted higher. Override with: "purely visual, don't touch layout or flow."
- I assumed the new look should match the app's existing design tokens and components, not introduce a new style. Override with: "new direction: [calm / premium / playful / dense]," or run `/design-direction` first.
- I assumed the agent has repo access and should report findings before editing (Step 0). Override with: "skip the report, just do it."
- I assumed the work goes on a feature branch with small commits. Override with: "commit to [branch]."
- I assumed WCAG AA as the accessibility bar. Override with: "AAA" or "no formal target."
- I assumed the existing save mechanism stays as is. Override with: "redesign the save model too."
- I assumed the page works on mobile widths. Override with: "desktop only."

## Push-back worth hearing
- **"Nicer" isn't checkable.** Without a named problem, the agent will restyle spacing and colors and stop. If the real complaint is "I can't find X" or "I never know if it saved," styling won't fix it. Tell me what bothered you, or let Step 0 find it.
- **Restyling a settings page can break it without a visible sign.** These pages hold the riskiest controls in an app: security, billing, deletion. A change that only looks like a cosmetic pass can rename a field or drop validation. That's why the prompt locks behavior, payloads, and protected surfaces, and requires a before/after behavior check.

## Open questions (answer these, or run with `--deep`)
1. **Which product, stack, and file path?** I left `[PATH]` and `[STACK/FRAMEWORK?]` as placeholders rather than guess. This is the biggest gap: it decides which components and tokens exist to reuse.
2. **What specifically feels not-nice?** Cluttered, hard to scan, off-brand, no save feedback, or bad on mobile? One sentence here would replace most of the Step 0 discovery.
3. **What lives on the page?** In particular, does it hold billing, security, or account-deletion controls? That changes how strict the prohibitions need to be.

Want to go deeper? Re-run with `/guildproof:sharpen make the settings page nicer --deep` for a one-question-at-a-time interview that replaces these assumptions with your answers. Or just answer the three questions above and I'll finalize.