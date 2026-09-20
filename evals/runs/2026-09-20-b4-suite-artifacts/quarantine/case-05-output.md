## Lens findings: `SaveBar`

**Lenses:** `accessibility`, `visual-design` (built-in library).

**Aesthetic read:** The request doesn't state one. I read this as dark, muted, minimal UI. Nothing below penalizes the design for being restrained. Every finding is either a hard rule that holds in any aesthetic (contrast, operability, hierarchy, systematic spacing) or a defect inside that family.

**Contrast**, computed with the WCAG relative-luminance formula against the `#1f2430` bar. These are hand-computed, so confirm them with a checker.

| Element | Color | Ratio | Needs | Result |
|---|---|---|---|---|
| "Unsaved changes" (11px) | `#3a4150` | ≈1.5:1 | 4.5:1 | Fail (also fails the 3:1 floor for large text and UI) |
| "Save" (inherited ~16px, regular weight) | `#6b7280` | ≈3.2:1 | 4.5:1 | Fail |

### P0: blocks use

**1. The Save control can't be used from a keyboard or a screen reader.** *(accessibility: keyboard, semantics, labels)*
- Evidence: `<div onClick={save} …>`.
- A `div` isn't in the tab order, has no role, and doesn't respond to Enter or Space. Screen readers announce it as plain text, not a button.
- Requirement: use a native `<button type="button">`, which brings focus, activation and role for free.
- Requirement: give it a visible `:focus-visible` indicator with at least 3:1 contrast against the bar. Don't suppress the outline.

**2. "Unsaved changes" is effectively invisible.** *(accessibility: contrast; visual-design: readability)*
- Evidence: `color: "#3a4150", fontSize: 11` on `#1f2430`, about 1.5:1.
- This is the only signal that work is at risk, and it's the least legible thing on screen.
- Requirement: at least 4.5:1, which needs a text luminance of roughly 0.25 or higher against this bar. As one example, `#9ca3af` computes to about 6:1.
- Requirement: raise the size to 12px or more, and use `rem` rather than `px` so it follows the user's font-size setting.

**3. "Save" fails text contrast, and it's the primary action.** *(accessibility: contrast)*
- Evidence: `#6b7280` on `#1f2430`, about 3.2:1. This passes the 3:1 UI-component bar, but it's normal-weight text, so 4.5:1 applies.
- Requirement: at least 4.5:1 for the label. If the button gets a visible boundary, that boundary needs 3:1 as well.

### P1: real defects

**4. The saving state is silent and cryptic.** *(accessibility: screen reader, labels)*
- Evidence: `{saving ? "..." : "Save"}`.
  - The accessible name becomes "..." while saving, and the state is carried by a glyph alone.
  - Nothing announces "Unsaved changes", "Saving" or "Saved", because there's no live region.
  - The control stays clickable and shows `cursor: pointer` mid-save, so a double submit is possible.
- Requirement: put the status text in a `role="status"` (polite live) region. Use real words such as "Saving…", not an ellipsis.
- Requirement: block activation while saving. If the button holds focus when pressed, prefer `aria-disabled="true"` plus a guarded handler over `disabled`, so focus isn't dropped mid-action.
- Requirement: style the busy state visibly.

**5. The primary action has the lowest visual weight.** *(visual-design: visual weight, type hierarchy; accessibility: affordance)*
- Evidence: Save is bare gray text with no fill, border or padding, in the same cool-gray family as the bar.
- The status text is 11px and the action inherits ~16px, so the type sizes don't come from a scale.
- Nothing on the bar wins attention, and the one thing to click doesn't look clickable.
- Requirement: make Save clearly the dominant element, with a button-like shape and an emphasis level within the muted palette that outranks the status line.
- Requirement: draw sizes from a defined scale.

**6. The layout is unintended and unsystematic.** *(visual-design: spacing and alignment)*
- Evidence: `<span>` (inline) followed by `<div>` (block) with no flex or grid, so "Unsaved changes" and "Save" stack on two left-aligned lines. There's no gap between them.
- `padding: 6` is a one-off value on a bar 12px taller than its text.
- The `div` spans the full bar width, so the clickable area doesn't match the visible target (the word "Save").
- Requirement: an explicit row layout with status and action separated, spacing from a scale (4/8-based), and a hit area that matches what's drawn.

**7. The touch target is too small.** *(accessibility: targets)*
- Evidence: the clickable `div` is only about 18–19px of text height. The 6px padding belongs to the bar, not the control.
- Requirement: at least 44px in the smaller dimension by the lens's guidance (WCAG 2.2's floor is 24px), with the size on the button itself.

### P2: cleanup

**8. Inline styles can't express the states this control needs.** *(accessibility: keyboard, motion)*
- Inline `style` can't do `:hover`, `:active`, `:focus-visible`, disabled or busy styling, `prefers-reduced-motion` or `forced-colors` handling.
- Requirement: move these to a stylesheet or class-based styling.

**9. The color has no intent.** *(visual-design: color)*
- Evidence: three near-identical cool grays as hex literals, no tokens, and no distinct treatment for a pending or at-risk state.
- Requirement: define the bar, text, action and pending-state colors as named tokens.
- Requirement: keep "unsaved" distinguishable by text, not color alone.
- Requirement: don't add saturated color unless the intended aesthetic calls for it.

### Checked, no finding
- **Alt text, headings, forms:** not applicable, since there are no images, headings or inputs.
- **Motion:** not applicable, since nothing animates. It becomes relevant if a spinner is added for #4.
- **Color alone:** not violated today, because text carries both states.

### Outside the selected lenses (noted, not scored)
- **`save` is unbound.** It's a free identifier, not a prop or an import, so it throws a `ReferenceError` unless it happens to be in scope.
- **The status text is unconditional.** "Unsaved changes" renders even after a successful save, because the component has no `dirty` prop. Once it sits in a live region (#4), that false status would be announced.
- **No failure or success state exists.** Run `ux-designer` to cover this.

### Open questions
1. **Is the bar sticky or fixed?** If so, it needs a focus-not-obscured check and a 320px reflow check, which I can't assess from this snippet.
2. **Is there a target aesthetic or brand token set?** That decides how far the palette can move to reach 4.5:1 without leaving the intended look.

Re-run with `--fix` to get a corrected component, or add `ux-designer` for the state-closure gaps.