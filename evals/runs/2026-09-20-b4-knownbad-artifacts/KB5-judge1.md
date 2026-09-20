## Structural invariants (LENS)

- ✅ **Per-lens block:** a `## ai-tells` block is present, so at least one lens block exists.
- ⚠️ **Findings prefixed ✅/⚠️/❌:** both findings carry ❌, so the prefix is present. Neither finding is a real defect, though, because both target words inside a verbatim quote (see below).
- ⚠️ **Worst-first ordering:** with two same-severity findings there is nothing to order. The real worst issue, that the quoted Declaration should not be touched at all, is never surfaced.
- ❌ **Top-3-fixes list:** absent. The output goes from two bullets straight to "Corrected version" with no ranked fixes.
- ❌ **`/guildproof:sharpen` offer:** absent. There is no closing offer of any kind.
- ⚠️ **Names which lenses ran:** only the heading `## ai-tells` names the lens. There is no statement of which lenses ran and no flag for requested-but-missing ones.

## Quality dimensions (LENS)

- ❌ **Maps to checklist:** the findings are generic vocabulary flags. "❌ Tier 1 vocabulary: 'vital', 'foster', 'preservation'" all sit inside the double-quoted recorded Declaration text. AI-tell scanning does not apply to verbatim quoted legal text, so the lens was misapplied. "❌ Tier 1 vocabulary: 'obligation' reads formal/inflated" is also weak: "obligation" is a term of art in the governing document, not an AI tell.
- ⚠️ **Specific:** it quotes single words, but it never notes that they come from a quotation. It also never flags the actual ai-tell candidates in the non-quoted text ("A violation of the Declaration has been observed").
- ❌ **Impact-ordered / top-3 leverage:** there is no top-3 list. The highest-leverage guidance would have been "leave the quoted Declaration verbatim", and it is missing.
- ⚠️ **No padding:** no ✅ lines and no flattery, but no coverage shown either.

## Hard gates

- ❌ **Faithfulness / guardrails (`--fix` on a legal artifact):** the corrected version breaks the artifact in several ways.
  - It replaces the direct quotation with a paraphrase and drops the quotation marks: "Article VII, Section 3 of the Declaration says each Owner has to keep the outside of the Unit in good shape." A violation notice that quotes the recorded declaration must stay verbatim, and this rewrite misrepresents what the Declaration says.
  - It changes meaning: "the Board can encourage compliance using the remedies listed" replaces "the right to foster compliance through the remedies set forth herein". The Board's *right* is reduced to "can encourage".
  - It drops the statutory citation "Ohio Revised Code 5312.11" and replaces it with "Under Ohio law". The citation was the legal basis for the hearing right.
  - It changes "enforcement assessment" to "fine", which is a different legal term and may be a different thing.
  - It weakens the formal notice: "A violation of the Declaration has been observed" becomes "We noticed a problem at your address."
  - It adds "really matters" while claiming to remove AI-sounding language.
- ❌ **Not steerable / scope:** the fix goes beyond removing tells and edits substantive legal content. That is a hard-gate failure on guardrails.

Several ❌ marks, including a hard-gate ❌ on faithfulness and guardrails, mean the case fails.

VERDICT: FAIL