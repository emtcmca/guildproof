## Scoring for `lens` case 29: visual-design on a brutalist section

I read `lenses/visual-design.md` to check the "maps to checklist" mark. I recomputed the contrast ratios and headline widths by hand.

### 1. Structural invariants (LENS)

- ✅ **Per-lens block, findings prefixed.** `## visual-design`, then every finding carries ✅/⚠️/❌. The trailing "Left alone" and "Outside this lens" notes aren't findings.
- ✅ **Worst-first.** Order is ❌, ❌, ⚠️, ⚠️, then the ✅ lines. Whether the fine print or the headline overflow ranks first is arguable, but both are ❌.
- ✅ **Top-3 fixes and the sharpen offer.** There is a `## Top 3 fixes` list and a Skip line. The last line is "Run `/guildproof:sharpen` with these findings to get a corrected version."
- ✅ **Names the lenses that ran.** "**Lenses run:** `visual-design` (built-in)". Nothing requested was missing.

### 2. Quality dimensions

- ✅ **Maps to checklist.** The findings use the lens's own hard-rule items: contrast, readability, type hierarchy, spacing, visual weight and color intent. The style-relative list matches the lens too. The 18px padding outlier hits "Spacing is systematic".
- ✅ **Specific.** The numbers hold up when I recompute them:
  - `#4a4a4a` on `#000` is about 2.4:1.
  - `#d0d0d0` is about 13.6:1.
  - `#000` on `#e8ff00` is about 18.7:1.
  - "SHIPPING/" at 9 × 0.56 × 96 is about 484px.
  - `min(96px,16vw)` fits down to about 250px.
  - It quotes the artifact: "Refund excludes third-party costs".
  - It labels the overflow as "computed from the font metrics, not rendered".
- ✅ **Impact-ordered.** The top 3 lead with the two real ❌s. Fix 3, the gutter, is the most contestable inclusion (see must-not).
- ⚠️ **No padding.** It raises the 18px padding as a finding against a 4px grid it inferred, then tells the reader "Skip: the 18px padding outlier". A finding it says to skip is noise. "The one exception looks like concealment" is editorializing beyond the lens.
- ✅ **Faithfulness (hard gate).** It invents no facts about the artifact. The legal aside is fenced: "a question for them, not a legal judgement from me."

### 3. This case's must list

- ✅ **Judge inside the brutalist idiom.** "Coherent within brutal … zero radius, no shadow, all-caps monospace and hard borders." The "Left alone as style-relative" line covers monospace, uppercase, sharp corners, no motion and the 15px body.
- ✅ **Flag the hard-rule failures.** The contrast failure is found with the right ratio, and the fix asks for "at least 13px". The 11px size failure is only implied ("the 4.5:1 that 11px text needs") and never stated as its own finding.
- ⚠️ **Name which findings are hard-rule and which are style-relative.**
  - Style-relative items are named explicitly.
  - The header says "Hard rules apply regardless".
  - The individual ❌/⚠️ findings are never tagged hard-rule or style-relative.
  - The reader has to infer that the gutter and 18px items are hard-rule.

### 4. This case's must-not list

- ✅ **Not penalized for density, harshness or uppercase.** The 96px headline, 0.85 leading, acid CTA and hard borders are left alone. The headline size change targets a computed viewport overflow, not the style.
- ✅ **No softening of palette or size, and no added whitespace as a *defect*.** This is the closest call. The `padding-inline:24px` finding is presented as a ⚠️ defect and as Top-3 fix 3, not as an optional style alternative. The same output lists "zero whitespace" as left alone, which contradicts flagging `padding:0`. It is defensible as edge-crowding, and it hedges with "assumes no wrapper supplies a gutter", so I did not score it as a violation. The lens files density under style-relative, so this is a real weakness.
- ✅ **No markup rewrite.** It gives CSS values only, with no rewritten section.

### Summary

The output stays inside the brutalist idiom and catches the real contrast failure with correct numbers. It has no ❌ marks and does not clearly violate a must-not, so it is not a FAIL. Three points hold it to WEAK:

- The gutter finding conflicts with its own "zero whitespace is left alone" line.
- Findings are not labeled hard-rule versus style-relative, which the must list asked for.
- It raises a nit and then tells the reader to skip it.

VERDICT: WEAK