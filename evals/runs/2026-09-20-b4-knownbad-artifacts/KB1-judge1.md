## SHARPEN: structural invariants

- ❌ **All 9 blocks present and filled.** Only ROLE, OBJECTIVE, CONTEXT and REQUIREMENTS appear, and REQUIREMENTS ends in a bare `...`. GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA, OUTPUT FORMAT and OUT OF SCOPE are missing.
- ❌ **PROHIBITIONS and OUT OF SCOPE distinct.** Neither block exists, so nothing can be distinct. A drafting agent gets no "must not" list, for example no "must not invent the fine amount".
- ⚠️ **No unfilled `<...>` placeholders.** No `<...>` tokens remain, but the trailing `...` in `- Demand the fence be lowered to 6 feet within 30 days.\n...` is truncation, not a completed prompt. I'm not crediting it as clean.
- ❌ **One copy-pasteable block, then assumptions, push-back and open questions.** The output stops after REQUIREMENTS. It has no assumptions section, no push-back and no open questions.
- ❌ **Each assumption has an explicit "Override with:".** There are no assumptions to override. The prompt states invented values as settled fact instead, for example "The fine is $250 per the 2023 rules amendment, due within 30 days."

## SHARPEN: quality dimensions

- ❌ **Faithfulness (hard gate).** The user supplied no domain facts, only "draft a violation notice for an unresolved fence-height dispute". The output invents all of these and presents them as fact:
  - "CC&Rs Section 7.4"
  - "caps fences at 6 feet"
  - "$250 fine"
  - "2023 rules amendment"
  - "due within 30 days"

  A governance notice built on fabricated citations and fine amounts is the highest-liability failure this rubric describes. None of these are labeled as assumptions or open questions.
- ❌ **Push-back is real.** None is present. The request has genuine weaknesses that go unflagged:
  - No governing-document provision or fine schedule was supplied.
  - "Dispute" suggests the owner contests the violation, which may call for a hearing or notice-and-cure process rather than a straight demand.
  - The measurement basis and any variance or approval history are unknown.
- ⚠️ **Named concreteness.** The output only says "formal violation notice". It names no tone, such as firm but neutral, and no audience or reading level. The specific numbers are false concreteness, because they are invented.
- ⚠️ **Lens fit.** No lens is named or applied. REQUIREMENTS contains only two bullets ("Cite Section 7.4…", "Demand the fence be lowered…"). No due-process, notice or hearing checklist for owner correspondence appears, though the visible portion is truncated.
- ❌ **Would steer.** An agent following this would draft a notice that cites a nonexistent section and fine and demands a fixed remedy. It would leave out hearing rights, and "unresolved dispute" is flattened into a demand. The tool has no guardrails or prohibitions to catch this. Following the prompt produces a wrong and possibly legally harmful document.
- No embedded instructions to the judge appear in the output, so there is no injection to flag.

## Verdict

Hard gates fail (structural invariants and faithfulness), and there are multiple ❌ marks. Under the verdict rule, any ❌ means FAIL.

VERDICT: FAIL