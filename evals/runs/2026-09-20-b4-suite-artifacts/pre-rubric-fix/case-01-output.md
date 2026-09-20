```
ROLE: You are a senior product designer and frontend engineer working in this codebase. You apply three review lenses to the work: UX (findability, flow, all states), visual design (hierarchy, spacing, consistency), and accessibility (keyboard, contrast, labels).

OBJECTIVE: Improve the existing settings page so it's easier to scan, easier to use, and visually consistent with the rest of the product. This is a polish and usability pass. The page must do exactly what it does today.

CONTEXT:
- Page location: [path or route of the settings page?]. Locate it yourself if not given.
- Stack and styling approach: [stack?]. Read the existing code and match its conventions. Don't assume a framework.
- Design system: [tokens / component library / brand reference?]. If one exists, it is the source of truth. If none exists, derive tokens from the app's most-used existing pages.
- Before changing anything, read the page and its neighboring components. Then write a 5-10 line audit of what is actually wrong, in terms of hierarchy, grouping, spacing, control styles, and missing states. Base the audit on what you saw.

REQUIREMENTS:
- Structure: group related settings under clear section headings, ordered by how often users need them. Each setting gets a plain-language label and, where it isn't self-evident, one line of helper text in the user's language rather than the system's.
- Hierarchy: establish a visible type scale (page title, section heading, label, helper text). Use a consistent spacing scale with even rhythm and alignment. Keep body and helper text lines to roughly 45-75 characters.
- Controls: use the product's existing input, toggle, select, and button components. If they don't exist, make the controls consistent among themselves. Make the primary action (e.g. Save) obvious, and secondary and destructive actions visually distinct from it.
- Danger zone: any destructive or irreversible action (delete, disconnect, reset) is visually separated from routine settings and keeps or gains a confirm step.
- All states: cover loading, saving, save-success, save-error (with a message saying how to fix it), disabled, and empty or not-configured for every section.
- Unsaved changes: if the page already has an explicit save model, show clearly when there are unsaved changes.
- Tone and feel: calm, clear, unfussy. Restraint over decoration. Every visual element must earn its place. Unless the product's existing style says otherwise, use the modern-minimal family: muted palette, generous whitespace, soft but consistent corner radius, minimal motion.
- Accessibility (a requirement, not a finishing pass):
  - Everything is operable by keyboard, with a logical tab order and a visible focus ring.
  - Text and UI meet WCAG AA contrast (4.5:1 text, 3:1 large text and UI).
  - Every input, toggle, and icon button has an accessible name. Use real semantic elements with headings in order.
  - Errors are announced and tied to their field. Meaning is never conveyed by color alone.
  - Touch targets are at least ~44px. Respect prefers-reduced-motion.
- Responsive: the layout holds at 320px width with no horizontal scroll, and touch targets stay usable.

GUARDRAILS (from red-team pass):
- Treat "nicer" as a hypothesis. If the audit shows the real problem is findability or structure and not looks, fix that first and say so.
- A settings page is where irreversible actions live. Confirm after your change that every setting is still present, still reachable, and still writes the same value to the same place.
- Reordering or regrouping is allowed. Removing, merging, or renaming a setting is not, without a flag to the user.
- Keep the diff reviewable. Prefer changing the page and its styles over editing shared components. If a shared component must change, name every other place that uses it and confirm they still render correctly.

PROHIBITIONS (must NOT do — negative space):
- Don't invent: no new setting names, copy claims, config keys, API routes, file paths, or component names. If something you need is missing, flag it as `[missing: …]` and leave it out.
- Don't touch: auth and session handling, the data schema or migrations, billing and payment flows, security controls (including any permission checks on this page), public API contracts, or any setting's stored key or value format.
- Don't change behavior: no switching between autosave and explicit save, no changes to validation rules, no changes to what a control submits.
- Don't exceed scope: no drive-by refactors, renames, formatting sweeps of unrelated files, or new dependencies. No redesign of other pages, navigation, or the global theme.
- Don't add features (search, import/export, new sections, dark mode) unless they already exist.

SUCCESS CRITERIA:
- A first-time user can find any given setting and the save action in a few seconds, without reading the whole page.
- Every setting present before is present after, with the same stored key and value format, and the same save behavior. State how you verified this.
- Loading, saving, success, error, and disabled states all render for each section.
- Keyboard-only walk-through works end to end, focus is visible, and contrast meets AA. State how you checked it.
- No horizontal scroll at 320px.
- The type check, lint, existing tests, and production build pass. Paste the actual output. If you couldn't run one, say UNVERIFIED and don't claim it passed.
- The result looks like it belongs to the same product as the pages around it.

OUTPUT FORMAT:
1. The audit (5-10 lines), before any code.
2. The code changes, committed on a feature branch and not on the default branch.
3. A short summary: what changed and why, and the verification evidence for each success criterion.
4. Any assumptions you made and anything you flagged but did not change.

OUT OF SCOPE: Changing what settings exist or what they do; new features; other pages; global theme or design-system overhaul; backend or data changes; copywriting beyond labels and helper text on this page.
```

## Assumptions I made
- **"Nicer" means visual polish plus layout and usability, not new features.** Override with: tell me it's purely cosmetic (drop the grouping and copy requirements) or that you want structural changes too.
- **The product's existing design system governs.** If none exists, I fall back to modern-minimal: muted, airy, restrained. Override with: name a different feel, such as denser, warmer, or more editorial. Two or three adjectives are enough.
- **Scope is this one settings page.** The rest of the app is untouched. Override with: say so if you want a shared component or global tokens changed.
- **Behavior is frozen.** That covers save model, validation, stored keys, and what each control submits. Override with: say so if the save model itself is part of what bothers you.
- **The stack is not assumed.** The agent reads the code and matches it. I left `[stack?]`, `[path…?]`, and `[design system?]` as placeholders. Filling them in makes the prompt tighter.
- **Accessibility is included even though you didn't ask.** A UI pass must not skip contrast, keyboard, and focus. Override with: tell me if it's already covered elsewhere.

## Push-back worth hearing
- **"Nicer" can't be tested, so the agent will guess.** The likeliest real complaints are that settings are hard to find, the page is cluttered, or it's inconsistent with the rest of the app. Each needs a different fix, and a restyle only solves one. I forced an audit step first for this reason. Your answer to open question 1 will change the result more than any other detail.
- **The main risk is a regression, not an ugly page.** Settings pages hold destructive and irreversible actions. A "prettier" pass that quietly moves a delete button next to Save, or changes an autosave toggle into a save-button flow, is worse than the page you have now. That's why the prohibitions and the "every setting still writes the same value" check are heavy.

## Open questions (answer these, or run with `--deep`)
1. **What specifically bothers you about the page today?** For example: cluttered, can't find things, looks dated, inconsistent with the rest of the app, bad on mobile. This one changes the output most.
2. **Is there a design system, brand reference, or example page to match?** A screenshot or a link to the page it should feel like would replace my modern-minimal default.
3. **Does the page have a danger zone or anything that must not move?** For example: delete account, billing links, or a save model (autosave or explicit) other code depends on.

Want a deeper pass? Rerun with `--deep`, or just answer the three questions above. With `--deep` I ask them one at a time and rebuild the prompt from your real answers instead of my assumptions.