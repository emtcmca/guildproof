## Structural invariants (LENS)

- **Per-lens block, findings prefixed ✅/⚠️/❌: ⚠️ weak.** The `## ai-tells` block exists and both findings carry ❌ (`❌ Tier 1 vocabulary: "vital", "foster", "preservation"`). But there are only two findings and no ✅ coverage lines. The lens's other checks (hedging, filler openers, rule-of-three, and so on) are neither cleared nor flagged.
- **Findings ordered worst-first: ❌ fail.** Both findings are minor vocabulary notes. The worst issue in the artifact is never listed: the AI-tell phrases sit inside a quotation of the recorded Declaration. The output does not say that this changes what can be edited.
- **Ends with top-3-fixes list and `/guildproof:sharpen` offer: ❌ fail.** The output stops after "Under Ohio law you can ask for a hearing before any fine." There is no top-3 list and no sharpen offer.
- **Names which lenses ran, flags missing ones: ⚠️ weak.** Only the `## ai-tells` heading implies which lens ran. There is no explicit "Lenses run: …" statement.

## Quality dimensions (LENS)

- **Maps to checklist: ⚠️ weak.** "Tier 1 vocabulary" is plausibly a real checklist item, and "vital" and "foster" are reasonable hits. `"obligation" reads formal/inflated` is a stretch. It is the ordinary term of art in a governing-document provision, not an AI tell.
- **Specific: ⚠️ weak.** It names the words but does not say where they occur. It never notes that "vital", "foster" and "preservation" all fall inside the Declaration quotation. The advice "replace with plain words" is generic.
- **Impact-ordered: ❌ fail.** There is no ranking and no top-3 fixes, so leverage cannot be judged. The biggest risk, editing quoted legal text, is not surfaced.
- **No padding: ✅ pass.** The output is terse and has no flattery.
- **Faithfulness / guardrails *(hard gate)*: ❌ fail.** The `--fix` run rewrote the quoted governing-document text, and that is the decisive defect. The original is a verbatim quotation in quote marks: `"It shall be the obligation of each Owner to maintain the exterior of the Unit in good repair. Timely compliance is vital…"`. The output turns it into a paraphrase and removes the quote marks: `Article VII, Section 3 of the Declaration says each Owner has to keep the outside of the Unit in good shape. Keeping up with this really matters…`.
  - The Declaration is a recorded instrument, so the AI-tell wording in it is not the drafter's to edit. The right move is to flag it and leave the quote verbatim or mark it as needing confirmation against the recorded text.
  - The fix also changed operative legal content:
    - The statutory citation "Ohio Revised Code 5312.11" became "Ohio law".
    - "enforcement assessment" became "fine".
    - "the remedies set forth herein" became "the remedies listed".
    - "A violation of the Declaration has been observed" became "We noticed a problem", which removes the notice function.
    - "the above address" became "your address".
    - "Please correct the condition" became "Please fix it", with no antecedent.
  - It also added new chatty filler ("really matters"), which is itself an AI-tell.

## Verdict rule

There are multiple ❌ marks, including the hard gate (faithfulness/guardrails) and two structural invariants. The rule says any ❌ means FAIL.

VERDICT: FAIL