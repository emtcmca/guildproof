## 1. Structural invariants (SHARPEN)

- ✅ **All 9 blocks present and filled.** ROLE, OBJECTIVE, CONTEXT, REQUIREMENTS, GUARDRAILS, PROHIBITIONS, SUCCESS CRITERIA, OUTPUT FORMAT and OUT OF SCOPE each appear as a labeled block with real content.
- ✅ **PROHIBITIONS and OUT OF SCOPE are distinct.**
  - PROHIBITIONS names agent actions tied to this task: "Don't invent: no fence-height limit, section number, statute, fine amount…" and "Don't attribute intent, bad faith or motive to the owner."
  - OUT OF SCOPE names work not being done: "Ruling on the merits of the dispute; boundary or survey determinations; drafting a fine schedule, hearing notice or attorney referral…"
  - Minor blur: the last PROHIBITIONS bullet, "Don't exceed scope: no drive-by rewrite of prior notices…", restates scope. It isn't boilerplate, so the block is not collapsed.
- ✅ **No unfilled `<...>` placeholders.** The only bracketed items are `[sender?]`, `[CC&Rs §__]` and similar. These are deliberate letter placeholders, not template residue.
- ✅ **One copy-pasteable block, with assumptions, push-back and open questions after it.**
- ✅ **Each assumption has "Override with:".** All six carry it; the last is "Override with `--lens`."

## 2. Quality dimensions

- ✅ **Push-back is real.**
  - "**'Dispute' and 'violation' are different things.** If the owner contests it, or the fence was approved, grandfathered or affected by an amendment, this notice can cost the board more than it recovers."
  - "A fine or lien threat you can't source is the highest-risk sentence in the letter." This is a substantive weakness in the request, not flattery.
- ✅ **Named concreteness.** Tone is pinned down: "firm, courteous, plain language, one page, reading level a general homeowner can follow." Burned phrases are named: "we hope this letter finds you well," "kindly be advised," "pursuant to." A neutral formulation is given: "The fence at [address] measures [__] as of [date]."
- ⚠️ **Faithfulness (hard gate).** No fabricated provision, but the prompt leaks two unsupplied details.
  - PROHIBITIONS says `"you are in violation of Ohio law"`. The user never named a state, and Open Question 1 asks "Which state…?", so the prompt contradicts itself. It is only a negative example, so it is not a fabrication.
  - GUARDRAILS says: "Reference 'a report received' or the association's own inspection." Neither is a supplied fact, and neither is a placeholder. This conflicts with SUCCESS CRITERIA: "Every factual statement in the letter traces to a supplied input or is a visible placeholder." A model could assert that a report was received when none was.
- ✅ **Lens fit.**
  - Skeptic: the "from red-team pass" GUARDRAILS check the binding document, amendments and ARC approval, measurement method, selective enforcement, and escalation step.
  - Editorial: the "firm, fair and factual" tone.
  - ai-tells: the banned openers and "stacked hedges or inflated wording."
  - All three show up in REQUIREMENTS and GUARDRAILS, and the output names the lenses used.
- ✅ **Would steer.** A competent agent would produce a placeholder-driven one-page letter with a checklist. One inconsistency exists but does not change the outcome:
  - The push-back says "I've made the draft omit the consequence unless you supply the authority."
  - REQUIREMENTS still allows "the Board may pursue remedies available under [section]", which implies remedies exist.
  - PROHIBITIONS is stricter than REQUIREMENTS, so an agent would resolve this cautiously.

## 3. This case's MUST list

- ✅ **Governing provision, dates and owner details treated as facts to confirm.** "If any input is missing, leave a bracketed placeholder such as `[CC&Rs §__]` or `[measured height, date, by whom]`. Do not fill it in. List every unfilled placeholder at the end."
- ✅ **Editorial lens applied.** The tone is "firm, courteous, plain language." The structure "header (… RE line with notice type and step); the facts; the provision…" puts the matter first. The banned pleasantries remove any warm-up.
- ✅ **Due process surfaced, with legal grounding flagged.**
  - Inputs include the escalation step, the cure period "and its source", and "the hearing/appeal procedure".
  - GUARDRAILS says: "flag it at the top of the checklist as 'confirm hearing requirement before any fine.'"
  - Open Question 1 says the state and document "decides the hearing requirement, whether a fine is allowed…"

## 4. This case's MUST-NOT list

- ✅ **No unsupplied section number, fine amount, statute or deadline.** All are placeholders (`[CC&Rs §__]`, `[date]`). "Ohio law" appears only as a forbidden phrase, not as a citation.
- ✅ **No threatening or editorializing tone.** The prompt requires neutral factual language ("rather than 'you built an illegal fence'"). It also bars intent attribution, fine or lien threats without a cite, and attorney-style demand language.

## Verdict

There are no ❌ marks and no hard-gate failures. The one ⚠️ is faithfulness, for the unflagged "Ohio" reference and the unsourced "a report received" instruction. Under the rubric's rule (WEAK if ⚠️ but no ❌), this is a WEAK result.

VERDICT: WEAK