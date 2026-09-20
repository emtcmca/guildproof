# Judge scoring: `lens --fix` on the case-05 component

I re-derived the numbers before scoring. `#3a4150` on `#1f2430` computes to about 1.5:1 (L≈0.0526 vs 0.0177), and `#c9cfdb` on `#1f2430` to about 9.9:1. The output's arithmetic is correct.

## 1. Structural invariants (LENS)

- ✅ **Per-lens block, ✅/⚠️/❌ prefixes.** There are separate `## accessibility` and `## visual-design` sections, and every finding carries a mark.
- ✅ **Worst-first ordering.** Accessibility runs A1–A3 ❌, then A4–A5 ⚠️, then the ✅ lines. Visual-design runs V1 ❌, then V2–V3 ⚠️, then ✅.
- ✅ **Names which lenses ran.** "Both lenses are built-in. No project-local lens shadows either one."
- ❌ **Ends with the top-3 list and the `/guildproof:sharpen` offer.**
  - The top-3 list sits mid-document.
  - The output ends on "Unfixed observations and open questions".
  - The `/guildproof:sharpen` offer appears nowhere.
  - The case's own must-list overrides the offer under `--fix`, but the end-of-output requirement is missed either way.

## 2. Quality dimensions (LENS)

- ✅ **Maps to checklist.** Findings trace to the lens items: contrast, keyboard/role, `aria-expanded`, target size, and type size.
- ✅ **Specific.**
  - It quotes `color:'#3a4150'`, `fontSize:11`, and `{open && <Panel />}`.
  - It catches the click-bubbling defect (A4) and the invalid-HTML button-wrapping-interactive-content problem, neither of which the case prompted.
  - It hedges the height figure as an estimate.
- ⚠️ **Impact-ordered.** The order is right, but V1 restates A1 as a separate ❌, which inflates the count. The top-3 is sound.
- ⚠️ **No padding.** Several ✅ lines are not-applicable filler rather than coverage: "Forms: not applicable", "Heading order: nothing to check here", "Line length: not applicable", "Type hierarchy: not assessable".
- ✅ **Faithfulness (hard gate, with one caveat).** Nothing invented about `Panel`. Assumptions are stated, and the contrast figures are labeled hand-computed. The caveat is that `#c9cfdb` is a chosen value rather than a derived one. It is disclosed and hedged in the open questions.

## 3. Case must list

- ✅ **Findings first, then a corrected component in a copy-pasteable block.** The output has a fenced `jsx` block after the findings.
- ✅ **Real defects fixed.** The corrected component uses `<button type="button">`, a lighter foreground, `fontSize:14`, and `aria-expanded={open}`.
- ✅ **Minimal and targeted.** Every change is mapped to a finding in the table. The neutralizing button resets (`background:'none'`, `border:0`, and so on) are justified as preserving the original look.
- ❌ **End with a one-line summary of what changed.**
  - The output has a multi-row change table, a "Second pass" section, and a "Two side effects" section.
  - It then ends on "Unfixed observations and open questions".
  - There is no one-line summary, and nothing that does that job sits last.

## 4. Case must-not list

- ✅ **No restyle beyond the findings.** The dark background, `padding:12`, and layout are preserved. The 44px minimum height traces to A5 and is disclosed as a side effect.
- ✅ **No invented values (borderline).**
  - `#c9cfdb` is a new hex, but it was needed to fix contrast.
  - The output discloses it as its own choice, not a brand token, and asks whether a real foreground token exists (V3).
  - The must-not asks for flagged placeholders for unknown values. This output offers a hedged concrete value plus the open question. I give it the benefit of the doubt, but it is the weakest ✅.
- ✅ **`<Panel />` kept, open/close logic unchanged.** `setOpen(!open)` is intact and `{open && ...}` is preserved. Moving `Panel` out of the click target is justified by A4 and by the invalid-HTML rule.
- ✅ **Not findings-only.** A corrected component is delivered.

## Verdict rule

The substance is strong: correct arithmetic, a genuine extra catch in A4, and disciplined restraint. The output still has a ❌ on a structural invariant (no closing top-3 plus sharpen offer) and a ❌ on a must-list item (no one-line "what changed" summary at the end). The ⚠️ marks on padding and duplication would only make it WEAK. Under the rule, any ❌ means FAIL.

VERDICT: FAIL