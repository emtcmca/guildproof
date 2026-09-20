Lenses run: `accessibility`, `visual-design` (both built-in).

## accessibility
- ❌ **Save isn't operable without a mouse.** `<div onClick={save}>` isn't focusable, has no role, and doesn't respond to Enter or Space. Keyboard and screen-reader users can't reach it or tell it's a control. It has no tab stop, so it also has no focus indicator. Fix: use `<button type="button">` and keep a visible focus ring.
- ❌ **"Unsaved changes" fails contrast.** `#3a4150` on `#1f2430` is about 1.5:1, against 4.5:1 required for text. At `fontSize: 11` it's effectively invisible, and it's the only state indicator on the bar.
- ❌ **"Save" fails contrast.** `#6b7280` on `#1f2430` is about 3.2:1. That fails 4.5:1 for normal-size text, which this is (no size set, not bold). The button also reads as disabled.
- ❌ **The saving state is unusable.** `{saving ? "..." : "Save"}` gives a screen reader the accessible name "...", which says nothing. Nothing announces the state change either. Nothing stops a second click while `saving` is true, since `onClick={save}` has no guard. Fix: label it "Saving…", set `disabled` (or `aria-disabled`) while saving, and use `aria-busy` or a live region.
- ⚠️ **The status text isn't announced.** The `<span>` has no `role="status"` or `aria-live`, so a screen-reader user never hears that changes are unsaved. It also renders regardless of `saving`. If the parent only mounts the bar when changes exist, that's fine, but I can't see that from here.
- ⚠️ **The touch target is text-sized.** The Save `div` has no padding, so it's roughly one line tall and about 30px wide. That's well under the ~44px target. The bar's `padding: 6` doesn't count, since it isn't clickable.
- ⚠️ **There's no failure path.** A failed save leaves "Unsaved changes" on screen and announces nothing. The lens's check is that errors are announced and say how to fix them.
- ✅ **Color-only meaning:** the unsaved state is carried by text, not color alone.
- ✅ **Motion:** there is none. If a spinner replaces "...", honor `prefers-reduced-motion`.
- ✅ **Alt text, images and heading order:** not applicable to this snippet.

## visual-design
Aesthetic: no brand tokens or adjectives were given. I inferred **modern-minimal, dark slate** from the palette. That's an assumption, so override it if the target is different. Style-relative items are judged within that family.

**Hard rules**
- ❌ **Layout is broken.** The parent is a plain block `div`, the `<span>` is inline, and the Save `<div>` is block-level. "Save" therefore drops onto its own line under "Unsaved changes", inside a 6px-padded box. A save bar almost certainly wants status left and action right. Fix: make the bar `display: flex` with `justify-content: space-between` and `align-items: center`.
- ❌ **Nothing directs attention.** The primary action ("Save") is styled as the dimmest usable text on the bar, and the status is dimmer still. The only high-weight thing is the empty background. Save should be the strongest element and read as a button.
- ❌ **Text is illegible at its size.** 11px at about 1.5:1 fails readability and contrast in any aesthetic. This overlaps `accessibility`, and both apply.
- ⚠️ **There is no type scale.** The status is a hard-coded 11px and Save inherits an unspecified size. That gives an arbitrary jump with no hierarchy step. 11px is also below a normal caption floor of about 12px.
- ⚠️ **Spacing is arbitrary.** `padding: 6` is a one-off value and there's no gap between status and action. Use a spacing scale (4/8/12) and give the bar breathing room around the text.
- ⚠️ **Color has no intent.** Two unrelated greys (`#3a4150`, `#6b7280`) plus the background are inline hex literals, with no tokens. The status text sits closer to the background than to the other text, which looks accidental. "Unsaved changes" is a warning-type state but has no semantic color.

**Style-relative (modern-minimal dark)**
- ✅ **Palette mood and decoration:** the muted slate palette and lack of decoration fit the family. The restraint has gone too far, though: it has become low contrast rather than quiet.
- ⚠️ **Type personality is unset.** No `fontFamily` or weight is declared, so the bar takes whatever it inherits.
- ⚠️ **Density is cramped,** but that comes from the missing flex layout and padding, not from a density choice. Fix the layout before judging it.

## Top 3 fixes
1. **Replace the clickable `div` with `<button type="button">`, disabled while `saving`, with a visible focus ring.** This clears the biggest failure (keyboard and screen-reader access) and also fixes the missing focus, the semantics and the double-submit risk.
2. **Raise both text colors to at least 4.5:1 against `#1f2430`, and make Save the brightest element.** That fixes both contrast failures and the hierarchy problem at once. Also raise the status text from 11px to about 12px or more.
3. **Lay the bar out with flex, spacing-scale padding, and a target of about 44px tall.** Change "..." to "Saving…" and put `role="status"` on the status text. This fixes the stacked layout, the target size and the announcement gap.

**Outside these lenses:** `save` isn't defined or passed in this snippet, so I assumed it's module-scope and didn't check it. State closure and affordance (no success or error feedback, no hover or pressed states) belong to `ux-designer`, which wasn't run.

Run `/guildproof:sharpen` with these findings to get a corrected version, or re-run this with `--fix`.