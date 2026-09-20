# Lens findings: skeptic + editorial

**Bottom line:** this prompt is close to a no-op. Nearly every sentence restates what a model does by default, and the one line that tries to add rigor ("don't make mistakes") can't be followed. The most serious gap is that nothing says what the assistant is for.

The artifact contains no text aimed at the reviewer, so there was nothing to flag as embedded instructions.

## P0: fix before this is used anywhere that matters

**1. No deployment, no audience, no domain.** *(skeptic: wrong problem / unstated assumption)*
- Quote: "You are a helpful assistant… Help the user with whatever they need."
- The prompt never says who the users are, what the assistant is for, or what it has access to.
- It assumes adjectives steer behavior. A model that is already helpful gains nothing from being told it is helpful.
- **Sharpest objection:** delete the prompt and behavior barely changes, except that "concise" might tighten answers. A prompt that changes nothing looks like configuration and gives false confidence.
- Fix direction: state the assistant's job and its users in the first line. If it really is a general assistant, drop the prompt and spend the effort on evals.

**2. "Always be accurate and don't make mistakes" is unmeasurable and can backfire.** *(skeptic: failure modes; editorial: concrete over abstract)*
- The model cannot audit itself against "no mistakes", and nobody can test whether it did.
- A zero-error demand with no escape hatch pushes a model toward confident answers over admitting uncertainty. That is the wrong direction for accuracy.
- The prompt says nothing about what to do when the model doesn't know.
- Fix direction: replace the demand with behaviors. Say "I don't know", never invent facts, sources, or numbers, and mark unverified claims. Then decide how you will check it.

**3. No negative space at all.** *(skeptic: what's easy to skip)*
- Quote: "Help the user with whatever they need."
- "Whatever" reads as a license. The prompt has no prohibitions, no refusal boundary, no protected surfaces, and no rule for treating pasted documents or tool output as data rather than instructions.
- If this assistant ever reads files, web pages, or email, it will follow whatever those contain.
- Fix direction: add a short must-not list specific to the deployment.

## P1: real ambiguity an agent will resolve inconsistently

**4. "Concise" and "accurate" have no tie-break.** *(skeptic: missing constraint)*
- On a hard question, correctness needs length. The prompt doesn't say which value wins.
- "Concise" also has no yardstick: no length, no example, no "unless the user asks for depth".
- Fix direction: state the priority, for example "accuracy over brevity; brevity over polish".

**5. "Use good judgment" hands back the decision the prompt exists to make.** *(skeptic: regret test; editorial: ending)*
- Quote: "Use good judgment."
- It is also the closing line, so the prompt ends on the vaguest instruction it contains.
- The real judgment calls are missing: when to ask a clarifying question and when to assume, when to escalate, and when to refuse.
- Fix direction: end on a concrete "When unsure" rule instead of an appeal to judgment.

**6. "Professional" is undefined.** *(editorial: tone match / audience fit)*
- Quote: "concise and professional"
- "Professional" can mean stiff corporate prose or plain, direct speech. It also sits awkwardly with "helpful".
- Without a named audience you can't check whether the tone fits.
- Fix direction: name the reader and the register, for example "plain language for non-experts, no jargon unless they use it first".

**7. No output contract.** *(skeptic: regret test)*
- Nothing covers format, structure, code versus prose, or when to show reasoning.
- A week from now you'll wish you had specified this, because you can't tell "concise" apart from "cut off".

## P2: editorial cleanup

**8. Circular and duplicated sentences.** *(editorial: cut filler)*
- "Help the user with whatever they need" restates "helpful assistant" from line one.
- "Always be accurate" and "don't make mistakes" say the same thing twice. Even the "Always" adds nothing.

**9. Five adjectives, zero specifics.** *(editorial: concrete over abstract / no hollow phrasing)*
- The five are helpful, concise, professional, accurate, and good judgment. None comes with a number, an example, or a test.
- These are the empty-boilerplate kind of phrasing the lens exists to catch, even though they miss the usual buzzword list.

**10. Opens with the default, not the point.** *(editorial: lead with the point)*
- Quote: "You are a helpful assistant."
- The first sentence carries no information about this assistant. The purpose should come first.

**11. Short by omission, not economy.** *(editorial: length)*
- Four sentences look tight, but the prompt isn't complete, so it fails the "as short as it can be while still complete" test.
- Adding the missing pieces will make it longer, and that's the right direction.

**What passed:** the imperative, active phrasing is fine. There is no distinctive authorial voice to preserve, so nothing was skipped for that reason.

## Best alternative you didn't ask for

Write a short, specific prompt with these parts:
- a one-line purpose and audience;
- three to five concrete behavior rules, each testable;
- a must-not block;
- an explicit "when unsure" rule;
- an output format.

If the assistant is meant to be general-purpose, the stronger move is no prompt plus a small eval set. Then you can see whether any wording moves behavior at all.

## Open questions (the answers change every finding above)

1. What is this assistant deployed for, who uses it, and does it have tools or documents to read?
2. What is the worst realistic failure for your users: a confident wrong answer, a harmful action, or an over-long reply?

## Next

- `/guildproof:lens --lens skeptic,editorial --fix`: rewrite it in place once you've answered the questions above.
- `/guildproof:lens --grade`: get a scored verdict you can re-run after changes.
- `/guildproof:sharpen <what the assistant is for>`: build a full prompt from scratch.