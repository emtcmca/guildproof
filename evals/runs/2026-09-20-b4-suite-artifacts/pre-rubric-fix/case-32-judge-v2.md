# Scoring: `lens --fix` on the case-05 component

## 1. Structural invariants (LENS, `--fix` path)

- ✅ **Per-lens block, findings prefixed ✅/⚠️/❌.** Two blocks, `## accessibility` and `## visual-design`, each with prefixed findings such as "❌ **A1. Contrast.**".
- ✅ **Worst-first ordering.** Accessibility runs ❌ A1–A3, then ⚠️ A4–A5, then ✅ lines. Visual-design runs ❌ V1, then ⚠️ V2–V3, then ✅ lines.
- ✅ **Top-3-fixes list.** "## Top 3 fixes, by impact" is present and each item cites its finding IDs.
- ✅ **No `/guildproof:sharpen` offer on the `--fix` path.** No offer appears, which is correct.
- ❌ **`--fix` path expects the corrected artifact plus a one-line summary of what changed.** The corrected artifact is there. The summary is a multi-row table ("What changed, and which finding each change answers"), not one line. The output then goes on to "Second pass", "Two side effects" and "Unfixed observations and open questions", so it doesn't end on any summary.
- ✅ **Names which lenses ran.** "Lens review: `accessibility`, `visual-design`. Both lenses are built-in."

**Structural hard-gate failure:** the one-line closing summary is missing.

## 2. Quality dimensions

I recomputed the contrast figures. `#3a4150` on `#1f2430` is about 1.51:1, and `#c9cfdb` on `#1f2430` is about 9.9:1. Both match the output.

- ✅ **Maps to checklist.** Findings cover contrast, keyboard and semantics, `aria-expanded`, target size and font size, and they trace to specific lens items.
- ✅ **Specific.** The output quotes the artifact ("`color:'#3a4150'` on `background:'#1f2430'` is about **1.5:1**") and gives the mechanism for A4 ("any click inside `Panel` bubbles up and calls `setOpen(!open)`").
- ⚠️ **Impact-ordered.** Fix 3 bundles A4, A5 and V2. A4 is a functional bug the output itself describes as "A settings panel would collapse while you use it", yet it is rated ⚠️ and ranked below the cosmetic font-size and target-size items. Fix 1 vs Fix 2 (contrast vs keyboard operability) is also arguable.
- ⚠️ **No padding.** V1 restates A1 ("This is the same defect as A1"). V3 is speculation ("which is my guess and not something I can confirm"), so it is an open question filed as a finding. Several ✅ lines mark not-applicable or not-assessable items ("Forms: not applicable", "Line length: not applicable"). The output also adds a second-pass section beyond what the route asks for.
- ✅ **Faithfulness (hard gate).** Estimates are hedged ("my estimate", "hand-computed, verify"), and the `Panel` color inheritance side effect is disclosed. The ~37px row height is a loose estimate: the parent's 16px strut would likely make the row nearer 42px. It is labeled as an estimate and the conclusion (under 44px) still holds.

## 3. This case's must list

- ✅ **Findings first, then a corrected component in a copy-pasteable block.** The `jsx` block follows the findings.
- ✅ **Fixes the real defects.** `<button type="button">`, `aria-expanded={open}`, `#3a4150` → `#c9cfdb`, and `fontSize:11` → `14` are all done.
- ✅ **Minimal and targeted, each change traceable.** The table maps every change to a finding, and the reset properties are justified as button-default cancellation.
- ❌ **End with a one-line summary of what changed.** The output ends with "Unfixed observations and open questions". The closest thing is the multi-row table, which is neither one line nor last.

## 4. This case's must-not list

- ✅ **No restyle.** The dark palette, background, 12px padding and toggle logic are unchanged. The panel wrapper `padding:'0 12px 12px'` preserves the original inset and is tied to A4/A5.
- ✅ **No invented values.**
  - `#c9cfdb` is a new hex, but a foreground replacement is unavoidable for the contrast fix.
  - It is flagged as hand-computed and as possibly the wrong token ("instead of my `#c9cfdb`").
  - It is not presented as a brand color.
  - The code itself carries no placeholder marker, which is the only reason I hesitated.
  - No invented copy or imports.
- ✅ **`<Panel />` and open/close behavior preserved.** `{open && <div ...><Panel /></div>}` is unchanged in behavior.
- ✅ **Not findings-only.** A corrected artifact is returned.

## Verdict

The substance is strong: the fixes are correct, minimal and traced, the contrast math checks out, and the disclosures are honest. But the explicit must item "End with a one-line summary of what changed" is not met, and the rubric's `--fix` structural expectation of a one-line summary is missed with it. The output also has a few ⚠️ points on impact ordering and padding. Under the verdict rule, any ❌ means FAIL.

VERDICT: FAIL