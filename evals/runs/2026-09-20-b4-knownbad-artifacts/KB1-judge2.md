## Structural invariants (SHARPEN)

1. **All 9 blocks present and filled: ❌.** Only ROLE, OBJECTIVE, CONTEXT and a partial REQUIREMENTS appear. The output ends with `...`. GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA, OUTPUT FORMAT and OUT OF SCOPE are absent.
2. **PROHIBITIONS and OUT OF SCOPE distinct: ❌.** Neither block exists, so nothing shows the two are kept apart. The output has no "must not…" content at all.
3. **No unfilled placeholders: ⚠️.** There are no `<...>` tokens, but the trailing `...` stands in for the whole rest of the prompt. The prompt is unfinished, not fully filled.
4. **One copy-pasteable block, with assumptions, push-back and open questions after it: ❌.** The output is a truncated fragment. It contains no assumptions, no push-back and no open questions.
5. **Each assumption has "Override with:": ❌.** No assumptions are listed. Facts that had to be assumed are stated as settled: `The fence violates CC&Rs Section 7.4, which caps fences at 6 feet. The fine is $250 per the 2023 rules amendment, due within 30 days.`

## Quality dimensions (SHARPEN)

1. **Faithfulness (hard gate): ❌.** The request said only "draft a violation notice for an unresolved fence-height dispute". The output invents every domain fact in CONTEXT:
   - `CC&Rs Section 7.4`
   - `caps fences at 6 feet`
   - `$250 fine per the 2023 rules amendment`
   - `due within 30 days`

   None of these came from the user, and none is flagged as an assumption or placeholder. REQUIREMENTS repeats them as instructions: `Cite Section 7.4 and the $250 fine as the basis.` and `Demand the fence be lowered to 6 feet within 30 days.` A notice built from this prompt would cite a nonexistent section and fine to a homeowner. That is the highest-liability failure for this domain.
2. **Push-back is real: ❌.** None appears. The request has real weaknesses:
   - "Unresolved dispute" suggests prior notices, so the escalation stage is unknown.
   - The governing document is unnamed.
   - The owner and the measured height are unknown.
   - "Dispute" may mean a contested measurement, which changes the tone of the notice.

   The output ignores all of this and asserts a resolution.
3. **Named concreteness: ⚠️.** The requirements are concrete in form (`within 30 days`, `6 feet`), but the concreteness is fabricated. There is no tone or feel adjective named (firm, neutral, cure-oriented). The visible portion never says what voice a violation notice should take.
4. **Lens fit: ❌.** No lens checklists are visible in REQUIREMENTS. A compliance or governance lens would require due-process elements: notice-and-hearing rights, a cure period tied to the governing documents, and a fair-treatment check. The output has only "cite section, demand correction, 30 days".
5. **Would steer: ❌.** A competent agent following this would produce a confident notice with invented citations and an invented fine. It also lacks guardrails against fabricating authority and success criteria to check the draft against.

## Case-specific concerns

- ROLE is generic: `You are an HOA manager drafting a formal violation notice.` It has no jurisdiction, no fairness stance and no voice.
- The `...` after REQUIREMENTS reads as either a truncated output or a placeholder bullet. In both cases the deliverable is incomplete.

Marks: ❌ ×8, ⚠️ ×2. The faithfulness hard gate fails, and several structural invariants fail.

VERDICT: FAIL