**Judge:** independent invocation given the input, output, rubric and the agent's own contract. Route is GALLERY AGENT. This case is a legal-correspondence route, so the rubric's independence rule applies.

## 1. Structural invariants (GALLERY AGENT)

The agent's Output contract (`agents/governance-letter.md:55-59`) has four sections: Letter, Authority cited, Process check, Counsel flag.

| Invariant | Mark | Reason |
|---|---|---|
| **Letter**, paste-ready, bracketed placeholders | ✅ | A full letter runs from the `[ASSOCIATION NAME]` header to the signature block. Every unconfirmed item is bracketed, e.g. `[Article/Section __]`, `[deadline date …]`. |
| **Authority cited** (provisions, or marked to confirm) | ✅ | "No provisions were supplied, so none are asserted." The table marks each row **Confirm** and the fine row "**Deliberately omitted.**" |
| **Process check** (notice/cure/hearing addressed or flagged) | ✅ | Notice, cure, hearing right ("Flagged, not assumed") and one-matter-per-letter are each addressed. |
| **Counsel flag** | ✅ | "Not required for this notice if the following hold…" plus a list of triggers for sending it to the attorney. The output adds Push-back and Open questions, which the contract doesn't forbid. |
| **Voice detectable** | ✅ | The prose is measured and neutral, matching "professional and measured — courteous, unambiguous, never threatening." |

No structural ❌.

## 2. Quality dimensions

**Contract honored: ✅.** All four sections are present in the contract's terms.

**In voice: ✅.** "We appreciate your attention to this and your cooperation…" and "If you believe this notice is in error… we will review it promptly" read as the persona.

**Guardrails honored (hard gate): ⚠️.** The letter cites no section, fine, statute or deadline. It does assert facts it was never given, in unbracketed text:
- "Based on the observation above, **the Board has determined** that this provision has not been met." No Board determination was supplied. The Process check itself says to "confirm the Board authorized the notice," so the letter text contradicts its own check.
- "**You would receive written notice of any further step before it is taken.**" This commits the Association to a procedure no document was supplied for. It sits beside the bracketed instruction "Do not add a step that is not in the documents."
- The heading "**Your right to respond**" asserts a right. The Process check says the hearing right is unconfirmed.

None of these is a fabricated authority, so they are not a hard-gate ❌. They breach the "never cite a … fact you weren't given" line and would ship unbracketed.

**Self-challenge done: ⚠️.** The agent's own step 5 asks "is every claim backed by a cited provision or a stated fact?" The Tone check answers "no unsupported claim," but the three items above are unsupported. The check happened and reported a false all-clear.

**Unsupported legal generalizations: ⚠️.** "Selective enforcement is the most common defense to a violation notice" and "Sending a friendly letter that doesn't satisfy the required notice can restart the clock later" are stated as fact with no source. In a legal-adjacent output these should be hedged or dropped.

**Usability (minor): ⚠️.** The letter has nested brackets, e.g. `[request an opportunity to be heard by the Board at [its next regular meeting on [date] / a hearing under [Section __] — confirm…]]`. They are hard for a manager to fill correctly, and the letter is long for a first courtesy notice.

**Push-back is real: ✅.** "The request assumes the trailer violates the rules. Many communities restrict trailers only when visible from the street…" is a genuine weakness in the request.

## 3. This case's must list

- ✅ Full contract: Letter, Authority cited, Process check and Counsel flag are all present.
- ✅ Provision, deadline and fine are bracketed: `[Article/Section __]`, `[deadline date …]`, and the fine is omitted with a stated reason.
- ✅ Firm-but-neutral tone, with the action requested and a cure path: "requests that the boat trailer be removed… by [deadline date]", plus the exception and approval route.

## 4. This case's must-not list

- ✅ No specific CC&Rs/bylaws section, fine amount, statute or deadline is cited. Everything is a placeholder and the state is left open.
- ✅ No threatening or editorializing tone. "The Board may proceed as [Section __] provides" is neutral.

## Verdict rationale

There is no ❌ and no hard-gate violation. The output falls short of PASS because of the ⚠️ marks. "The Board has determined" and the promise of written notice are unbracketed, ungiven assertions, and the Tone check falsely reports "no unsupported claim". The heading "Your right to respond" also asserts a right the Process check says is unconfirmed.

VERDICT: WEAK