## visual-design

**Lenses run:** `visual-design` (built-in). **Target family:** brutal, as you stated. Style-relative items are judged inside that family. Hard rules apply regardless. Absent whitespace, muted palette and rounded corners are not counted against it.

- ❌ **Contrast: the fine print fails.** `color:#4a4a4a` on `#000` is about **2.4:1**, against the 4.5:1 that 11px text needs. This is the line "Refund excludes third-party costs", which qualifies the section's central promise ("or we return the money"). Every other text element is legible, so the one exception looks like concealment. That runs against the family's own standard, since brutalism is supposed to expose things raw.
  - Fix: use at least `#767676` (about 4.6:1, the floor). In this palette, `#999` to `#d0d0d0` fits better. Set it at 13px or larger.
  - It also sits below the CTA, separated from the promise it qualifies. Move it into the paragraph, or set it directly under the promise at equal weight.
  - Separately, whoever owns the terms should check whether a refund limit shown this dimly is what they intend. That is a question for them, not a legal judgement from me.

- ❌ **Readability: the headline has no responsive rule.** `font-size:96px` is fixed, and nothing in the artifact adapts it to the viewport.
  - Courier New advances 0.6em per character. With `-0.04em` tracking, "SHIPPING/" and "WHOLE/JOB" each come to about 9 × 0.56 × 96 ≈ **484px**. "SHIPPING" alone is about 430px.
  - At 375–430px viewports the headline overflows or breaks mid-word. The headline is the whole design.
  - This is computed from the font metrics, not rendered. Confirm at 375px.
  - Fix: `font-size:min(96px,16vw)` keeps the longest line inside the viewport with a 24px gutter, down to about 250px wide.

- ⚠️ **Spacing: no horizontal inset.** `padding:0` on the section, `margin:0` on the h1, and `margin:24px 0` on the paragraph mean every text block, the CTA and the fine print sit at x=0. On a phone the first glyph crowds the bezel or rounded corner.
  - The full-bleed 8px rule is right and should stay.
  - This assumes no wrapper supplies a gutter.
  - Fix: give the h1, p, a and span `padding-inline:24px`, matching the existing 24px vertical rhythm. Padding on the h1 keeps its `border-bottom` full width.

- ⚠️ **Spacing: one off-scale value.** The rest of the spacing sits on a 4px grid (4, 8, 12, 24, 28). The CTA's `18px` vertical padding is the outlier. Use 16 or 20. This is low priority.

- ✅ **Type hierarchy exists.** The sizes run 96, 18, 15, 11, and the eye ranks them without reading. The 6× jump from headline to body is idiomatic for this family, so I left it alone.

- ✅ **Readability of body copy.** `max-width:62ch` is inside the 45–75ch range, and `line-height:1.6` is comfortable.

- ✅ **Contrast elsewhere.** `#fff` on `#000` is 21:1. `#d0d0d0` on `#000` is about 13.6:1. `#000` on `#e8ff00` is about 18.7:1.

- ✅ **Visual weight.** The headline wins, and the chartreuse CTA is the only chroma on the page, so the eye lands there second. The palette is three neutrals plus one accent used once, which is intentional and consistent.

- ✅ **Coherent within brutal.** The section uses zero radius, no shadow, all-caps monospace and hard borders. The 8px rule and 4px CTA border form a systematic 2:1 pair. Nothing borrows from another family.

- ✅ **Headline leading.** `line-height:0.85` is workable on an all-caps line because there are no descenders. On paper the slash descent stays inside the inter-line gap. Confirm in a render.

**Left alone as style-relative and coherent:** monospace throughout, uppercase, sharp corners, zero whitespace, no motion, and the 15px body under an 18px CTA label.

**Outside this lens.** I ran only `visual-design`, as you specified. Two things surfaced that belong to other lenses:
- The slash-broken headline reads aloud as "shipping slash is slash the slash whole slash job".
- The CTA has no defined hover or focus state.

Run `--lens accessibility,ux-designer` to cover both.

## Top 3 fixes

1. **Fix the fine print.** Raise it to at least 4.5:1 and at least 13px, and put it next to the promise it qualifies. It is the only hard-rule contrast failure, and it hides a material term.
2. **Make the headline responsive.** Use `font-size:min(96px,16vw)`, then verify at 375px. Without it, the section's main element breaks on phones.
3. **Add a 24px inline gutter** to the text blocks, keeping the h1 rule full-bleed.

**Skip:** the 18px padding outlier and the body-copy size. Neither is worth the churn.

Run `/guildproof:sharpen` with these findings to get a corrected version.