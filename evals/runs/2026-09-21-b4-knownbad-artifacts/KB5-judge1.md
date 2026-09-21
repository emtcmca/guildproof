# Grade: lens route, `--fix` mode, ai-tells

## Structural invariants

- **Per-lens block, ✅/⚠️/❌/— marks:** ⚠️ weak. The block has two ❌ lines ("❌ Tier 1 vocabulary: 'vital', 'foster', 'preservation'"). It gives no ✅ or — marks for any other checklist item, so coverage can't be seen.
- **Findings ordered worst-first:** ⚠️ weak. Both findings are ❌ with no ranking. The most consequential issue, that the flagged words sit inside a quotation of the recorded Declaration, isn't raised at all.
- **Ends with a top-3-fixes list:** ❌ fail. There is no top-3 list anywhere. The `--fix` path doesn't need the sharpen offer, and the output correctly omits it, but it still needs this list.
- **Corrected artifact in a copy-pasteable block:** ❌ fail. The "### Corrected version" is plain prose under a heading, not in a fenced block.
- **Change summary where each change names the finding it answers:** ❌ fail. No summary or per-change table exists, so minimality can't be checked.
- **Closes with unfixed observations:** ❌ fail. The output ends on the rewritten letter and lists nothing unfixed.
- **Names which lenses ran:** ✅ pass. The "## ai-tells" header names the lens, and no requested lens is missing.

## Quality dimensions

- **Faithfulness / guardrail (hard gate):** ❌ fail. The rewrite alters a quoted governing-document clause and changes the letter's legal content.
  - **Quoted text turned into paraphrase.** The original quotes Article VII, Section 3 verbatim. The output rewrites it as: "Article VII, Section 3 of the Declaration says each Owner has to keep the outside of the Unit in good shape." It still attributes those words to the Declaration but no longer quotes them.
  - **Legal meaning shifted.** "the Board shall have the right to foster compliance through the remedies set forth herein" becomes "the Board can encourage compliance using the remedies listed." A right to pursue remedies is now only permission to encourage.
  - **Statutory citation dropped.** "As Ohio Revised Code 5312.11 requires" becomes "Under Ohio law."
  - **Legal term swapped.** "enforcement assessment" becomes "fine," and "before the Board" is dropped.
  - **Notice function lost.** "A violation of the Declaration has been observed at the above address" becomes "We noticed a problem at your address." The letter no longer says a violation of the Declaration occurred.
  - **Cause.** The words "vital," "foster," and "preservation" are inside the recorded Declaration's own text. The correct move was to leave them verbatim and, at most, note them as quoted and out of scope for `--fix`.
- **Maps to checklist:** ⚠️ weak. "Tier 1 vocabulary" may trace to the lens. "'obligation' reads formal/inflated" is a stretch. "Obligation" is ordinary legal diction, not an AI tell, and the finding gives no checklist item to support it.
- **Specific:** ⚠️ weak. Individual words are named, but there is no pointer to where they occur, and nothing says three of the four are in quoted text.
- **Impact-ordered (top-3 highest leverage):** ❌ fail. There is no top-3 list.
- **No padding:** ✅ pass. The output is terse, though the rewrite adds "really matters," an intensifier that is itself an AI-tell pattern.

## Verdict

The hard gate (faithfulness) fails. The `--fix` structural contract also fails on the missing block, summary, unfixed list, and top-3 list.

VERDICT: FAIL