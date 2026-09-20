## 1. Structural invariants (SHARPEN)

- ✅ **All 9 blocks present and filled.** ROLE, OBJECTIVE, CONTEXT, REQUIREMENTS, GUARDRAILS (from red-team pass), PROHIBITIONS, SUCCESS CRITERIA, OUTPUT FORMAT and OUT OF SCOPE are all there.
- ✅ **PROHIBITIONS and OUT OF SCOPE are distinct.** PROHIBITIONS is task-tied actions ("Don't invent any section number, statute citation, fine amount, cure period…", "Don't threaten liens, legal action…"). OUT OF SCOPE is work not done this pass ("Designing a fine schedule… follow-up notices later in the series… any violation other than fence height"). Neither is boilerplate.
- ✅ **No unfilled `<...>` placeholders.** The bracketed `[ASSOCIATION]`, `[LIMIT]` and similar tokens are deliberate fill-ins for the downstream notice, not leftovers in the prompt itself.
- ✅ **One copy-pasteable block, then assumptions, push-back and open questions.** They come after the prompt, in that order.
- ✅ **Each assumption has "Override with:".** All six do.

## 2. Quality dimensions

- ✅ **Push-back is real.** "Dispute may mean a violation notice is the wrong document… ARC approval on record is the costliest version of this mistake" is a genuine weakness in the request. The prompt also makes the agent stop rather than draft over it.
- ✅ **Named concreteness.** "Firm, neutral, non-accusatory. No adjectives about the owner, no guesses about motive, no 'we are disappointed.'" and "Every deadline is a calendar date, not 'promptly' or 'immediately.'" No vague tone language.
- ⚠️ **Faithfulness (hard gate, no ❌).** The prompt invents no case facts, provisions, amounts or dates. But it asserts unsourced legal and empirical generalizations as fact:
  - "Notice-and-hearing steps often gate fines, and skipping one can void the fine."
  - "Fence-height notices usually fail on process, not tone."
  - "Fence-height disputes usually turn on where you measure from."

  These are hedged, but they are still domain claims on a legal-adjacent output, and the user supplied none of them. The "CMCA-level" persona also carries a credential label nobody asked for.
- ✅ **Lens fit.** The editorial lens shows up as "an editor's discipline (lead with the point, plain language, no filler)", "Length: one page, two at most" and the "30 seconds" success criterion. The skeptic lens shows up as "assume the notice may be read later by the owner's attorney, a hearing panel, or a judge" and the red-team guardrails.
- ⚠️ **Would steer.** There is a real internal tension. The guardrail says to stop and list blockers if inputs show "this is a neighbor-vs-neighbor conflict". The requirements say "Do not identify any complaining neighbor", which presumes neighbor complaints are the normal trigger. A competent agent could refuse to draft in the most common scenario, because a neighbor complaint prompting association enforcement is not the same as a neighbor-vs-neighbor conflict. A second, smaller conflict: "Output a short list… then stop" sits against the mandatory three-part OUTPUT FORMAT. Otherwise the prompt would steer well.

## 3. Case must list

- ✅ **Governing provision, dates and owner details are placeholders.** `[GOVERNING DOCUMENT + SECTION]`, `[LIMIT]`, `[DATE]`, `[OWNER]`, and "Anything not supplied stays a visible bracketed placeholder, never a guess."
- ✅ **Editorial lens applied.** The firm-but-neutral tone is set out above. "Lead with the point" is in ROLE, and the "Re:" line follows the date, delivery and owner blocks, so the violation is stated at the top of the letter body.
- ✅ **Due process surfaced and legal grounding flagged.** It carries `[STAGE]`, the cure deadline, `[PER GOVERNING DOCS/STATE LAW]` and "mark it [CONFIRM HEARING PROCEDURE] and do not write one." It also names board or counsel sign-off in the pre-send list and in "have counsel or the board review it".

## 4. Case must-not list

- ✅ **No fabricated section number, fine amount, statute or deadline.** All are placeholders, and PROHIBITIONS bans invention.
- ✅ **No threatening or editorializing tone.** The prompt bans threats, legal conclusions and commentary on the owner's character.

## Verdict rule

There are no ❌ marks and no hard-gate failures. There are two ⚠️ marks: unsourced legal generalizations under faithfulness, and the neighbor-complaint contradiction under would-steer. That gives WEAK.

VERDICT: WEAK