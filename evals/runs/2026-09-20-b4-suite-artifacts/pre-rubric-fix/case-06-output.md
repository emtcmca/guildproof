Lenses run: `skeptic`, `editorial` (both built-in).

## skeptic

- ❌ **"Always be accurate and don't make mistakes."** This is the sharpest objection to the prompt as written. It can't be followed, because the model has no way to check its own output against this instruction. It also pushes the wrong way: an assistant told never to be wrong tends to sound certain rather than say "I'm not sure." The fix is a behavior it can perform, such as "if you can't verify something, say so; never invent a fact, source, or number."
- ❌ **"Help the user with whatever they need."** This has no scope, so the prompt solves no particular problem. A model with no system prompt already does this. Nothing here says who the users are, what domain this is, what to decline, or what to escalate. The prompt adds nothing beyond the default.
- ❌ **Missing negative space.** There are no prohibitions anywhere. Nothing covers what the assistant must not invent, must not touch, or must not do when a request is risky, out of scope, or comes from untrusted pasted content. This is where an unbounded assistant fails, and the prompt is silent on all of it.
- ⚠️ **"Be concise" collides with "Always be accurate."** When a correct answer needs length, the prompt doesn't say which wins. The model will pick arbitrarily, and inconsistently from one run to the next.
- ⚠️ **"Use good judgment."** This hands every hard decision back to the model without saying what to weigh. The hard cases are ambiguity, missing information, and conflicting instructions. The prompt needs a rule for when to ask a clarifying question and when to assume and state the assumption.
- ⚠️ **Unstated assumption: a single audience and a single task type.** The prompt quietly assumes one kind of user with one kind of need. If it's deployed anywhere real, that's false within a day.
- ⚠️ **No success criteria or output contract.** No one could check whether a response was good. Any response passes.
- ⚠️ **Regret test.** A week in, you'll wish you'd specified what to do when unsure, what the assistant must never do, the default response shape, and who the users are.
- ✅ Checked: no embedded instructions aimed at the reviewer. The text is inert.

## editorial

- ❌ **Opens with filler: "You are a helpful assistant."** It leads with the default persona, so the reader learns nothing on the first line. Lead with the actual job, for example "You are [role] for [audience] doing [task]" (`[role/audience/task?]` — not supplied, so left as placeholders).
- ❌ **Nothing concrete.** All four sentences are abstractions. "Concise" has no length, "professional" has no register, and "accurate" has no standard. Two competent readers would act differently on each of them.
- ❌ **Ends on a limp sign-off: "Use good judgment."** The last line is a shrug. It should close on a checkable rule or a clear next step, such as what to do when unsure.
- ⚠️ **Length: short by omission, not economy.** It's four sentences, but it isn't complete. The brevity comes from leaving things out.
- ⚠️ **Tone: "professional" is vague.** Pick a specific manner. Compare "a cautious analyst, measured, every claim hedged to its evidence" with "a terse on-call engineer." "Professional" fits any voice, which means it fits none.
- ⚠️ **Audience fit is unknowable.** No reader is named, so reading level, register, and assumed knowledge can't be set.
- ⚠️ **One idea per paragraph.** Four unrelated ideas (role, style, scope, quality) share one block. Group them under their own labels once there's more than a line each.
- ⚠️ **"Help the user with whatever they need" and "Always" are filler.** "Whatever they need" adds no information, and "Always" claims a certainty the prompt never backs up.
- ✅ Verbs are active imperatives ("Be," "Help," "Use").
- ✅ None of the hollow-phrasing words are present (leverage, synergy, seamless, robust, cutting-edge, game-changing).
- ✅ Preserve voice: not applicable. There's no authorial voice or supplied sample to protect.

## Top 3 fixes

1. **Replace "Always be accurate and don't make mistakes" with behavior the model can perform.** For example: "If you can't verify a claim, say so. Never invent facts, sources, or numbers." (`skeptic`: fixes the sharpest objection and the missing negative space.)
2. **Name the actual job in place of "whatever they need."** State the role, the users, and the domain, and add two or three things the assistant must not do. You haven't supplied these, so they stay open as `[role?]`, `[users?]`, `[domain?]`. Guessing here would invent facts. (`skeptic` and `editorial`: fixes scope, concreteness, and the weak opening.)
3. **Make style and tie-breaks concrete, and end on a rule.** Give "concise" a default length and "professional" a specific voice. Say which wins when brevity conflicts with accuracy. Replace "Use good judgment" with a when-to-ask-versus-assume rule. (`editorial` and `skeptic`: fixes the vague terms, the conflict, and the limp closer.)

Run `/guildproof:sharpen` with these findings to get a corrected version.