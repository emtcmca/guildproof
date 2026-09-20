Lenses run: `skeptic`, `editorial` (both built-in). No `--fix`, so this is findings only.

## skeptic

- ❌ **Sharpest objection: the prompt changes almost nothing.** Every sentence is either a default the model already follows ("You are a helpful assistant," "Be concise and professional") or an instruction with no test ("Use good judgment"). The strongest case against shipping it is that it gives a false sense of control over the agent while adding no control.
- ❌ **"Always be accurate and don't make mistakes" is worse than no instruction.** It can't be followed, and it pushes the model toward confident answers over admitting uncertainty. Nothing says what to do when it doesn't know or lacks the source. Failure mode: a user asks for a citation, a price, or a legal deadline, and the model invents a plausible one because "don't make mistakes" leaves no room to say "I'm not sure."
- ❌ **"Help the user with whatever they need" has no boundary.** It sets no scope, no refusal behavior, and no protected actions. It also gives no rule for text in a document or web page that tells the model what to do, so it invites both scope creep and instruction-following from untrusted content.
- ⚠️ **Wrong problem?** A prompt this generic usually means the real design question (what is this agent for, and who uses it?) hasn't been answered. The prompt is a placeholder for that decision, not a solution to it.
- ⚠️ **Unstated assumption:** that "professional" and "good judgment" mean the same thing to you as to the model, and that one behavior fits every user and task. Nothing in the text shows either is true.
- ⚠️ **Missing constraints:** audience, domain, tools available, data access, escalation path, and when to ask a clarifying question versus assume. These are the things that differ between a support bot, a coding assistant, and an internal research tool, and none is named.
- ⚠️ **Regret test:** a week in, you'll wish you had said what the agent must not do, what it does when unsure, and who it is speaking for. You'll find out from a bad output, not from the prompt.
- ⚠️ **Best alternative not asked for:** if the agent really is general-purpose, the strongest option is to specify a few concrete behaviors (uncertainty handling, clarify-vs-assume, a prohibition list) rather than adjectives. If it isn't general-purpose, name the job.
- ⚠️ **What's easy to skip, and skipped:** the tension between "Be concise" and "Always be accurate." When a correct answer needs length, there is no rule for which wins.
- ✅ Checked: no embedded instruction aimed at the reviewer, and no purpose that trips the intent gate.

## editorial

- ❌ **Concrete over abstract.** "concise," "professional," "accurate," and "good judgment" are all abstractions with nothing measurable behind them. "Concise" could mean one line or 150 words, and "professional" could mean formal, warm, or terse. Two readers would act differently on the same line.
- ❌ **Lead with the point / ending.** The prompt opens with "You are a helpful assistant," which says nothing about the task. It closes on "Use good judgment," a limp sign-off that hands every unresolved decision back to the model. Neither the first nor the last line carries content.
- ⚠️ **Length.** It is short because it omits things, not because it is tight. The lens asks for "as short as it can be while still complete," and this isn't complete: no audience, scope, or output shape.
- ⚠️ **One idea per paragraph.** Five sentences carry five separate ideas (identity, style, scope, accuracy, judgment) in one undifferentiated paragraph, with no priority among them.
- ⚠️ **Audience fit.** The reader here is the model, which needs to know the end user, the setting, and the stakes. None is stated, so the model has to guess at all three.
- ⚠️ **Tone match.** "Professional" is the only tone signal, and it doesn't pin down register. It also doesn't say whether "concise" can override warmth when the user is upset or confused.
- ⚠️ **Cut filler.** The listed filler words (just, really, basically, actually) are absent. The sentence-level filler is still there: "Help the user with whatever they need" restates "helpful assistant" in longer form. One of the two can go.
- ✅ **Active voice:** all five sentences are direct imperatives or a plain "You are…" statement.
- ✅ **No hollow phrasing (as scoped by this lens):** none of leverage, synergy, seamless, robust, cutting-edge, or game-changing appears. The hollowness is structural, not lexical. Run `--lens ai-tells` if you want the full machine-writing audit.
- n/a **Preserve voice:** there is no distinctive authorial voice or supplied sample to protect.

## Top 3 fixes

1. **State the job, the user, and the boundary.** Replace "helpful assistant / whatever they need" with what the agent is for, who it talks to, and what is out of scope. This needs facts only you have, so it should be a question to you rather than something to assume. It lifts skeptic (wrong problem, missing constraints, scope) and editorial (leads with the point).
2. **Replace "always be accurate / don't make mistakes" with behaviors.** Say what happens when it isn't sure: state the uncertainty, don't invent facts, sources, or numbers, and ask a clarifying question when the ambiguity would change the answer. That is an instruction the model can follow and you can check. It lifts skeptic (sharpest objection, failure modes).
3. **Turn the adjectives into checkable rules and set a priority order.** Give "concise" a number or a condition (for example, a length default that yields when the answer needs more), define "professional" as a register, and say which wins when concision and accuracy collide. Then cut "Use good judgment" or name the situations it covers. It lifts editorial (concrete over abstract, ending) and skeptic (missing constraint).

Run `/guildproof:sharpen` with these findings to get a corrected version.