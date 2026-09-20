# Lens review: `accessibility`, `visual-design`

Both lenses are built-in. No project-local lens shadows either one.

## accessibility

- ❌ **A1. Contrast.** `color:'#3a4150'` on `background:'#1f2430'` is about **1.5:1**, against the 4.5:1 that text this size needs. It is unreadable for many users. I hand-computed this from sRGB relative luminance (about 0.053 vs 0.018), so confirm it with a contrast checker. Fix: lighten the foreground and keep the background.
- ❌ **A2. Keyboard and semantics.** `<div onClick={...}>` cannot be reached with Tab and has no Enter/Space handler. It has no role, so assistive tech sees plain text rather than a control. Fix: use a native `<button type="button">`.
- ❌ **A3. Screen-reader state.** Nothing announces expanded or collapsed, because there is no `aria-expanded`. The toggle changes the page silently for a screen-reader user. Fix: `aria-expanded={open}`.
- ⚠️ **A4. The whole container is the click target, including the panel.** `{open && <Panel />}` sits inside the `onClick` div, so any click inside `Panel` bubbles up and calls `setOpen(!open)`. A settings panel would collapse while you use it. This is a warning rather than a failure only because I can't see `Panel`'s contents. A `<button>` also can't legally wrap interactive content. Fix: make the button a sibling of the panel, not its parent.
- ⚠️ **A5. Target size.** The clickable row is roughly 37px tall (12 + about 13 for an 11px line + 12, my estimate), under the lens's ~44px. Fix: `minHeight:44` on the button, full width as before.
- ✅ Alt text: there are no images.
- ✅ Motion: there is none.
- ✅ Color alone: nothing is conveyed by color only.
- ✅ Forms: not applicable.
- ✅ Label: the visible text "Advanced settings" becomes the accessible name once the element is a button.
- ✅ Heading order: nothing to check here. I deliberately did not add a heading.

## visual-design

**Aesthetic inferred:** dark slate with a muted, restrained, minimal-functional look, taken from `#1f2430` and the recessive foreground. Nothing below penalizes that family. Palette mood, decoration, corner radius, motion and density are all coherent for it and are left alone.

**Hard rules**
- ❌ **V1. Contrast, legibility and visual weight.** This is the same defect as A1. The component's only interactive element is also its lowest-contrast element, so the eye can't find the control. One fix (A1) resolves both.
- ⚠️ **V2. Readability.** `fontSize:11` is small for a control label, and it compounds V1. Fix: 14.
- ⚠️ **V3. Color intent.** Both colors are raw inline hex. `#3a4150` reads like a border or surface tone used as text, which is my guess and not something I can confirm. I can't tell whether these are brand tokens, so I made no change and list it as an open question below.
- ✅ Spacing: `padding:12` is a multiple of 4. Only one value is visible, so nothing is inconsistent.
- ✅ Type hierarchy: not assessable. There is one label at one size, and `Panel`'s type is unseen. This is not a defect.
- ✅ Line length: not applicable.

## Top 3 fixes, by impact

1. **Lighten the foreground to pass contrast** (A1, V1). It is the difference between readable and effectively invisible.
2. **Replace the div with a native button and add `aria-expanded`** (A2, A3). This gives keyboard operation, a role and announced state.
3. **Split the panel out of the click target and set a 44px minimum height** (A4, A5, plus V2's font size). This stops clicks in the panel from collapsing it and fixes the target size.

## Corrected artifact

```jsx
<div style={{background:'#1f2430', color:'#c9cfdb'}}>
  <button
    type="button"
    onClick={() => setOpen(!open)}
    aria-expanded={open}
    style={{
      display:'block', width:'100%', minHeight:44, padding:12,
      textAlign:'left', background:'none', border:0,
      color:'inherit', fontFamily:'inherit', fontSize:14,
    }}
  >
    Advanced settings
  </button>
  {open && <div style={{padding:'0 12px 12px'}}><Panel /></div>}
</div>
```

## What changed, and which finding each change answers

| Change | Finding |
|---|---|
| `color:'#3a4150'` → `'#c9cfdb'`, about 9.9:1 on `#1f2430` (hand-computed, verify) | A1, V1 |
| `<span>` + `div onClick` → `<button type="button" onClick={...}>` | A2 |
| Added `aria-expanded={open}` | A3 |
| Button is now a sibling of the panel, not its parent | A4 |
| Wrapper `padding:12` moved onto the button, and the panel gets `padding:'0 12px 12px'` | A4, A5. This keeps the original 12px inset around both. |
| Added `minHeight:44` and `width:'100%'` | A5. The full-width row target is preserved. |
| `fontSize:11` → `14` | V2 |
| `display:'block'`, `textAlign:'left'`, `background:'none'`, `border:0`, `color:'inherit'`, `fontFamily:'inherit'` | A2. These only cancel the browser's default button look so the conversion doesn't restyle anything. |

**Second pass, checking both directions**
- **Under-fixing:** A1 to A5, V1 and V2 are each resolved. V3 is intentionally unresolved (see below). I did not remove the browser's default focus outline, so keyboard focus stays visible. Check it in your browser against the dark background.
- **Over-fixing:** The background color, the 12px padding value, the toggle logic and the dark-slate look are unchanged. I added no new colors beyond the one foreground swap.

**Two side effects to check**
- `Panel` inherits its text color from the wrapper, so its inherited text also changes from `#3a4150` to `#c9cfdb`. If `Panel` sets its own colors, nothing changes there. Look at it once open.
- The closed row grows from about 37px to 44px. That is a direct result of the A5 fix.

## Unfixed observations and open questions

- **Are `#1f2430` and `#3a4150` brand tokens?** If they are, `#3a4150` is probably the wrong token for text, and the fix should use your real foreground token instead of my `#c9cfdb` (V3).
- **`setOpen(!open)` reads stale state if clicks batch.** `setOpen(o => !o)` is safer. It isn't an accessibility or visual finding, so I left it.
- **There's no visible expand/collapse cue, such as a chevron, for sighted users.** That is a `ux-designer` lens matter. I didn't run that lens or add one.
- **`Panel` and the `open` state are unseen.** I assumed a standard `useState` boolean and made no changes on that basis.