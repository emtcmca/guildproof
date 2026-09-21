# Grade: `sharpen` route

Case input: `/guildproof:sharpen draft a violation notice for an unresolved fence-height dispute`

The output ends in a literal `...` after the first REQUIREMENTS bullet. I graded only what is on the page and did not assume the missing blocks exist.

## Structural invariants

- ❌ **All 9 blocks present and filled.** Only ROLE, OBJECTIVE, CONTEXT and REQUIREMENTS appear. GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA, OUTPUT FORMAT and OUT OF SCOPE are absent. The output stops at `...` after `- Demand the fence be lowered to 6 feet within 30 days.`
- ❌ **PROHIBITIONS and OUT OF SCOPE distinct.** Neither block exists, so the separation the rubric calls the most likely silent regression cannot be shown.
- ⚠️ **No unfilled `<...>` template slots.** None remain. The output also has no bracketed gap flags such as `[CC&Rs §__]`, which is the problem covered under faithfulness. The mark is only weak because the output is too incomplete to say the template was fully filled.
- ❌ **Prompt in one copy-pasteable block, followed by assumptions, push-back and open questions.** None of the three follow-on sections is present. The output ends mid-list.
- ❌ **Each assumption has an explicit "Override with:".** There are no assumptions listed, and none are flagged anywhere.

## Quality dimensions

- ❌ **Faithfulness (hard gate).** The input supplies no facts about the dispute. The output states these as fact:
  - `The fence violates CC&Rs Section 7.4, which caps fences at 6 feet.`
  - `The fine is $250 per the 2023 rules amendment, due within 30 days.`
  - `Cite Section 7.4 and the $250 fine as the basis.`

  Section number, height cap, fine amount, amendment year and cure period are all invented domain facts, and none is flagged as a gap. `skills/prompt-engineering/SKILL.md:106` requires a `[square-bracket]` flag for any missing fact, and the rubric calls inventing one "the single failure that makes the draft unusable and untrustworthy." Nothing was flagged. If someone pastes this into an agent, it will draft a notice citing a nonexistent clause and an unauthorized fine, which is the highest-liability outcome for a violation notice.
- ❌ **Push-back is real.** There is no push-back section. It should have raised that the dispute's facts, governing documents, prior notice history and owner identity are missing. It should also have raised that "unresolved" implies earlier notices, and that a fine may need a hearing or notice-and-cure step.
- ❌ **Named concreteness.** No tone or feel is named. A violation notice needs a stated register such as firm but fair, or formal and non-threatening. `You are an HOA manager drafting a formal violation notice` names only "formal".
- ⚠️ **Lens fit.** The topic points to a governance/compliance lens: cure period, due process, statutory notice. The visible REQUIREMENTS carry no lens checklist items, only "Cite…" and "Demand…". The rest of the list is cut off, so this is weak rather than fail.
- ❌ **Would steer.** An agent given this would draft a confident notice built on fabricated authority. That steers it wrong, not merely incompletely.

## Verdict rule

Multiple ❌ marks, including the faithfulness hard gate and the structural invariants.

VERDICT: FAIL