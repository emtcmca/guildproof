## Structural invariants (LENS, `--fix` path)

- **Per-lens block with ✅/⚠️/❌ or `—` marks:** ⚠️. There is a `## ai-tells` block with two ❌ lines, but no ✅ or `—` lines show what was checked, and the lens's other checklist items are never addressed.
- **Findings worst-first:** ✅. Both findings are ❌ and the order is defensible. There is little to order.
- **Top-3-fixes list:** ❌. The output never contains one. It goes from two findings straight to "### Corrected version".
- **Corrected artifact in a copy-pasteable block:** ⚠️. The text after "### Corrected version" is bare prose, not a fenced block.
- **Per-change summary naming the finding each change answers:** ❌. Nothing follows the corrected version. The output ends with "Under Ohio law you can ask for a hearing before any fine." Every change is unattributed, so the minimality check is not visible.
- **Close with unfixed observations:** ❌. The output has no unfixed list, and it does not say that anything was deliberately left alone.
- **No `/guildproof:sharpen` offer on `--fix`:** ✅. None is present, which is correct.
- **Names which lenses ran:** ⚠️. Only the header "## ai-tells" implies it. There is no statement of lenses run or missing.

## Quality dimensions

- **Faithfulness / guardrail (hard gate):** ❌.
  - The artifact contains a verbatim quotation of a recorded Declaration provision, and a governing-document quote must not be edited. The output paraphrases it: "Article VII, Section 3 of the Declaration says each Owner has to keep the outside of the Unit in good shape." The quotation marks are gone.
  - It also changes the substance of the quoted text. "The Board shall have the right to foster compliance through the remedies set forth herein" becomes "the Board can encourage compliance using the remedies listed." That turns recorded text into the fixer's own words while still attributing it to the Declaration.
  - It alters other legal content. "As Ohio Revised Code 5312.11 requires" becomes "Under Ohio law", which drops the statutory citation. "Enforcement assessment" becomes "fine", which is a different legal term. "A violation of the Declaration has been observed" becomes "We noticed a problem at your address", which drops the notice's operative reference to the Declaration.
  - It adds new hedged phrasing that was not in the source: "really matters."
- **Maps to checklist:** ❌. The flagged words "vital", "foster", "preservation" and "obligation" all sit inside the quoted Declaration text. They are not the drafter's prose, so they are not AI tells here. Flagging "obligation" as Tier 1 vocabulary is also weak on its own terms. The real prose-level items, such as the stiff "Dear Owner" opener and "prior to imposition of any enforcement assessment", are not flagged at all.
- **Specific:** ⚠️. It names words, but the reasons are one-line ("reads formal/inflated"). It doesn't point to which sentence in the artifact each word sits in, and it doesn't recognize that they are quoted.
- **Impact-ordered:** ❌. There is no top-3 list, and the most consequential issue (do not touch the verbatim quote) is absent.
- **No padding:** ✅. The output is short with no flattery, but the brevity comes from omitting required sections.

## Verdict

The output has several ❌ marks, including the hard-gate faithfulness failure. It rewrote a recorded legal quotation and changed statutory and legal terms, and it omitted the required top-3 fixes, change summary and unfixed list.

VERDICT: FAIL