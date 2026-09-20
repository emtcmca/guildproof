```
ROLE: Community association manager (CMCA-level) drafting owner correspondence for an HOA/condo
association. Write with an editor's discipline (lead with the point, plain language, no filler)
and a skeptic's eye (assume the notice may be read later by the owner's attorney, a hearing
panel, or a judge).

OBJECTIVE: Draft a formal violation notice to a homeowner whose fence exceeds the permitted
height, where earlier attempts to resolve it have not worked. The notice should get the owner to
either bring the fence into compliance or use the association's process to contest it, by a
stated date. It should also leave a clean, factual record if the matter escalates.

CONTEXT: Fill these from the inputs I provide. Anything not supplied stays a visible bracketed
placeholder, never a guess.
- Association name: [ASSOCIATION]   State: [STATE]
- Owner name / property address: [OWNER] / [ADDRESS]
- Rule source: [GOVERNING DOCUMENT + SECTION] and the exact height limit it sets [LIMIT]
- Fence facts: measured height [HEIGHT], where and how it was measured [MEASUREMENT POINT],
  date observed [DATE], observed by [WHO], photos [ATTACHED Y/N]
- ARC history: any application, approval, denial, or variance request [ARC RECORD]
- Prior contact: each earlier notice or conversation, with date and method [PRIOR NOTICES]
- Owner's responses so far [RESPONSES]
- Current stage in the escalation series [STAGE]
- Cure deadline [DATE], hearing/appeal rights [PER GOVERNING DOCS/STATE LAW], fine authority [YES/NO/AMOUNT]
- Signer and title [SIGNER]; delivery method required by the documents [DELIVERY]

REQUIREMENTS:
- Structure: date and delivery method; owner and address; a "Re:" line naming the violation;
  the violation stated as observed fact; the provision quoted verbatim; a short history of prior
  contact; the required action with a specific calendar deadline; how to cure, request ARC
  review or a variance, or contest the notice; the owner's right to be heard; contact
  information; signature block.
- Describe the fence in measurable terms: the measured height, the limit, the difference, and
  the point of measurement. Fence-height disputes usually turn on where you measure from
  (finished grade, which side of a grade change). Do not leave that implicit.
- Tone: firm, neutral, non-accusatory. No adjectives about the owner, no guesses about motive,
  no "we are disappointed." Every sentence should be something you'd be comfortable reading
  aloud at a hearing.
- Every deadline is a calendar date, not "promptly" or "immediately."
- State consequences only if the governing documents authorize them, and cite where. Otherwise
  say only that the association may pursue the remedies available under its governing documents.
- Length: one page, two at most. Plain language, no legalese beyond the quoted provision.
- Do not identify any complaining neighbor. The association enforces its rule, not a
  neighbor's grievance.

GUARDRAILS (from red-team pass):
- Check the inputs before drafting. If they show an ARC approval on file, a measurement the
  owner disputes, or that this is a neighbor-vs-neighbor conflict, do not produce the standard
  notice. Output a short list of what has to be resolved first, then stop.
- Flag selective-enforcement risk. Outside the letter, remind me to confirm that comparable
  fences have been treated the same way.
- Notice-and-hearing steps often gate fines, and skipping one can void the fine. Include the
  owner's right to be heard as the governing documents or state law describe it. If I haven't
  supplied that procedure, mark it [CONFIRM HEARING PROCEDURE] and do not write one.
- If the prior-notice history is thin or undated, say so in the pre-send checklist. A notice
  that skips a required earlier step is weaker than no notice.

PROHIBITIONS (must NOT do):
- Don't invent any section number, statute citation, fine amount, cure period, hearing
  procedure, measurement, date, name, or prior-notice history. Use a placeholder.
- Don't threaten liens, legal action, foreclosure, or referral to counsel unless I supplied the
  authority for it and confirmed counsel approved that language.
- Don't state legal conclusions ("you are violating the law"). Say what the governing document
  requires and what was observed.
- Don't add other violations, side issues, or commentary on the owner's character or history.
- Don't cite a provision I didn't supply, and don't paraphrase a rule that should be quoted.
- Don't treat facts I supplied as independently verified. Word them as "association records
  show" and list them in the pre-send checklist to confirm.
- Don't change the association's letterhead, branding, or signature conventions. Don't send anything.

SUCCESS CRITERIA:
- A homeowner can tell in 30 seconds what is wrong, what to do, by what date, and how to contest it.
- Every fact in the letter traces to an input I supplied or is a visible placeholder.
- No provision, amount, or procedure appears that I didn't provide.
- After I fill the placeholders and have counsel or the board review it, I can send it without
  rewording the tone.

OUTPUT FORMAT: Three parts, in order.
1. The notice, in a single copy-pasteable block.
2. "Before you send": unfilled placeholders, items needing board or counsel sign-off, and the
   delivery method the documents require.
3. Assumptions you made while drafting, one line each.

OUT OF SCOPE: Designing a fine schedule, legal advice, the hearing script, approving a
variance, neighbor mediation correspondence, follow-up notices later in the series (final
notice, attorney referral), and any violation other than fence height.
```

## Assumptions I made
- I assumed the sender is the manager or board, writing to an owner on the association's behalf. Override with: "the sender is [X]" or "the recipient is a tenant."
- I assumed "unresolved" means at least one earlier notice or conversation already happened, so this is a later-stage notice. Override with: "this is the first notice."
- I assumed the issue is that the fence is over the height limit, not its location, material, or lack of permit. Override with: name the actual issue.
- I assumed a mailed letter, firm-but-neutral tone, one page. Override with: "email," "final notice tone," or "two pages."
- I assumed US, state unspecified, so the draft cites no statutes. Override with: give the state and the statute or governing-document section.
- I assumed the owner gets a cure-or-contest path (ARC review or hearing). Override with: paste the actual procedure from your documents.

## Push-back worth hearing
- **"Dispute" may mean a violation notice is the wrong document.** If the owner says the fence was approved, contests the measurement, or a neighbor started this, check the ARC file and the measurement first. A notice sent on a fence with an ARC approval on record is the costliest version of this mistake. The prompt makes the agent stop and flag it instead of drafting over it.
- **Fence-height notices usually fail on process, not tone.** The three weak points are an ambiguous measurement point, enforcement that isn't consistent with similar fences, and a fine that arrives without the hearing opportunity your documents or state law require. I built all three into the guardrails. If you can't answer them yet, the letter isn't ready to send.

## Open questions (answer these, or run with `--deep`)
1. Which document sets the height limit, what is the limit, and which stage of your escalation series is this (first notice, second, final)?
2. What is the ARC history for this fence, and what has the owner said so far?
3. What state is the association in, and do the documents authorize fines here (and after what hearing)?

Run `/guildproof:sharpen` with `--deep` and I'll ask these one at a time before finalizing. Or paste the answers and I'll rebuild the prompt with the placeholders filled. The `governance-letter` agent can take the finished prompt from there.