## Verdict: FAIL, on one structural ❌ (no Operating principles section)

The prompt is strong on content. It fails on a missing required section, and that gap also breaks a must-list item.

## 1. Structural invariants (FORGE)

- ✅ **System-prompt block present, copy-pasteable.** It is a single fenced block.
- ✅ **Persona opening.** "You are an onboarding-email writer who has sat through years of bad welcome sequences and now writes the ones people actually read."
- ✅ **Voice line.** "Voice: a capable colleague who respects the reader's time. Warm, specific, one point, one ask, no throat-clearing."
- ✅ **Objective.** `## Objective` is present.
- ❌ **Operating principles.** The prompt has these headed sections: Objective, Inputs, Method, Constraints / guardrails, Output contract, When unsure. There is no Operating principles section. Editorial material is scattered across Method and Constraints ("lead with the point", "one job and one CTA"). The rubric requires the section, so this is a hard-gate failure.
- ✅ **Inputs.** Five numbered inputs, and the prompt treats them as data, not instructions.
- ✅ **Method.** Seven steps.
- ✅ **Constraints / guardrails.** Present.
- ✅ **Output contract.** Present.
- ✅ **When unsure.** Present.
- ✅ **Explicit self-challenge in Method.** Step 7: "Before finalizing, challenge your own draft: what would a skeptical customer roll their eyes at? Is there a second ask hiding in the P.S.? Fix, then deliver."
- ✅ **Followed by assumptions, push-back, open questions and install note.** All four are present, plus a Provenance section.

## 2. Quality dimensions

- ✅ **Durable.** Nothing is tied to one example email. It takes per-run inputs and covers a missing brand voice, empty merge fields and sequences.
- ⚠️ **In-character voice.** The Voice line is specific, and the body has some crisp lines ("A trait you can't quote is a guess, so drop it."). Much of Constraints reads as a compliance spec rather than the "capable colleague" voice. The persona is asserted more than sustained.
- ✅ **Self-correcting.** Steps 5 to 7 are substantive: a voice check against a quote-backed checklist, a facts check tracing every claim to FACTS, and the skeptic pass.
- ✅ **Concrete contract.** "Subject: one primary line (default 50 characters or fewer) plus 2 alternates", plus Preheader, Body, Voice check (3-5 bullets with quotes), Placeholders, Verify before sending and Flags.
- ✅ **Seeded.** "Adapted from: `copy-rewrite`", with `governance-letter` discipline borrowed and the differences named.

## 3. Case must list

- ❌ **Auto-pick the editorial lens and bake it into operating principles.** The lens is named only in Provenance ("Lenses applied: `editorial`, `ai-tells`..., `skeptic`"). It is not baked into an Operating principles section, because none exists.
- ✅ **Voice line is specific and the body reads in it.** It is specific, though it names a working manner rather than a formal editorial tone. The prompt handles the company-voice tension explicitly ("The emails themselves take the COMPANY's voice... never yours").
- ✅ **No invented product facts or promises.** "Honesty floor: never invent facts, features, links, prices, discounts, dates, testimonials, statistics, or names." Also "Only what is supplied here may be stated as fact" and "No promises the company hasn't authorized".
- ✅ **Output contract defined.** It covers subject, body, and the assumptions and needs (Placeholders, Verify before sending, Flags).

## 4. Case must-not list

- ✅ **No hard-coded brand voice.** "BRAND VOICE" is input #1. There is also a no-voice fallback: "do not guess a brand... put 'NO BRAND VOICE SUPPLIED' first in Flags".
- ✅ **Not a one-off email.** It is a reusable agent prompt.

No must-not was violated. The FAIL rests on the missing Operating principles section, which fails the structural invariant and the first must-list item. Adding a short section that carries the editorial lens would fix both.

VERDICT: FAIL