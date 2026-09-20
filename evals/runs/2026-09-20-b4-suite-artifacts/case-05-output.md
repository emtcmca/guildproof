Lenses run: `accessibility`, `visual-design` (both built-in; no project-local overrides in play). I computed contrast ratios by hand from the hex values, so confirm them with a checker before you cite them.

## accessibility

- ❌ **Keyboard and role.** `<div onClick={save}>` can't be focused with Tab and doesn't respond to Enter or Space. It also has no `button` role, so a screen reader announces plain text, not a control. This is the main defect. Fix: use `<button type="button">`.
- ❌ **Contrast, status text.** `#3a4150` on `#1f2430` is about **1.5:1** against the 4.5:1 required, at 11px. "Unsaved changes" is effectively invisible to many sighted users and impossible to read for low-vision users.
- ❌ **Contrast, Save.** `#6b7280` on `#1f2430` is about **3.2:1**. The 3:1 threshold applies only to large text or UI components. The text is default size (about 16px, no `fontSize` set) and isn't bold, so it needs 4.5:1. This is the primary action, so it must pass.
- ❌ **Accessible name while saving.** `{saving ? "..." : "Save"}` makes the control's name "...", which a screen reader reads as nothing or as punctuation. Fix: use the visible text "Saving…". Because `onClick={save}` has no `saving` guard, the control also stays clickable mid-save. Use `disabled` or `aria-disabled` on the button and `aria-busy` while it saves.
- ⚠️ **Status isn't announced or accurate.** "Unsaved changes" is a static `<span>`, always rendered, so it still says "unsaved" while saving. Nothing tells a screen-reader user that saving started, finished, or failed. Fix: put the status text in a `role="status"` region that exists in the DOM before its text changes. Also add a visible failure message. As written, a failed save is silent.
- ⚠️ **Inline styles can't carry the state styling.** `style={{…}}` can't express `:focus-visible`, `:hover`, `:disabled`, or `prefers-reduced-motion`. Once the control is a button, it needs a class so keyboard focus is visibly indicated.
- ⚠️ **Target size.** Save is about 18px tall (default text, no padding) inside a bar with 6px padding. That's well under the ~44px guideline. It may technically meet WCAG 2.2's 24px minimum through the spacing exemption, but that's a technicality. Give the button real padding and a `min-height`.
- ✅ Save has a visible text label when idle, not an icon alone.
- ✅ State is carried by text, not by color alone.
- ✅ No animation, so the motion check has nothing to apply to.

## visual-design

**Aesthetic read.** No adjectives or tokens were given. I inferred a dark, muted, minimal utility bar and judged style-relative items against that. If you meant something else, tell me; I won't score against my own taste. Contrast and hierarchy are hard rules, so they hold in any style.

Hard rules:
- ❌ **Legibility.** `"Unsaved changes"` is 11px in `#3a4150` at about 1.5:1. It fails on size and contrast together (overlaps `accessibility`; both apply).
- ❌ **Visual weight directs attention.** Save, the one thing this bar exists for, is dim gray text (`#6b7280`) with no fill, border, or weight change. Nothing separates it from a label, so the eye has nowhere to land. A muted palette is fine for this family; stripping the action's affordance is not.
- ⚠️ **Type hierarchy is accidental.** There are two sizes, 11px (explicit) and an unset inherited size. Neither comes from a scale, and the font family is unset, so the result depends on whatever the parent page defines.
- ⚠️ **Spacing and layout.** `padding: 6` is uniform on all sides and off a 4/8 scale unless your system uses 6. The `<span>` is inline and the `<div>` is block, so the two stack vertically, left-aligned, with no gap. If you meant a bar with status left and action right, it has no `display: flex` or `justify-content` to produce that.
- ⚠️ **Color intent.** `#1f2430`, `#3a4150`, and `#6b7280` are hardcoded, near-neutral, and untokenized. `#3a4150` seems to exist only to be quieter than `#6b7280`, which is how it became unreadable. `#6b7280` looks like Tailwind's gray-500; if the project uses Tailwind or a token file, use those.
- ⚠️ **No interactive states.** There's no hover, pressed, focus, or disabled styling, only `cursor: pointer`. The saving state is just the text "...", with no visual change.
- ✅ Line length and reading measure don't apply to a one-line bar.

Style-relative (judged within the inferred dark-minimal family):
- ✅ **Decoration, corner radius, motion.** Restraint suits dark-minimal, and I'm not penalizing the lack of radius or ornament.
- ⚠️ **Density.** Tight 6px padding and 11px type are within family, but they combine with the target-size finding above. Dense is fine; dense plus unreadable isn't.

## Top 3 fixes

1. **Make Save a real button and give it real states.** Use `<button type="button">`, disable it (or set `aria-disabled`) with `aria-busy` while saving, and show "Saving…" as visible text. Put the status text in a `role="status"` region and add a visible error message. Move styling to a class so `:focus-visible` and `:hover` exist. This resolves the keyboard, role, name, announcement, and focus findings.
2. **Raise both texts to at least 4.5:1 and at least 12px.** For example, `#9ca3af` on `#1f2430` is about 6:1 by my calculation. Use your own token if one exists, and drop the near-invisible `#3a4150`.
3. **Make Save the visually dominant element and fix the layout.** Give it a fill or border and a `min-height` near 44px. Lay the bar out with `display: flex` (status left, action right) and a consistent padding scale in place of `padding: 6`.

**Outside these two lenses (not scored).** `save` is a free identifier, so `onClick={save}` throws a `ReferenceError` unless `save` is defined in module scope. It's probably meant to be a prop. Also, "Unsaved changes" is never conditional on a dirty state. I left both as observations rather than findings.

Run `/guildproof:sharpen` with these findings to get a corrected version.