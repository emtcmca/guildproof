# Lens review: marketing copy

**Lenses run:** `ai-tells` (built-in, as requested via `--lens`). No project-local override was in play.
**Carve-outs applied:** none. The copy has no quotations, no statutory or contractual text and no domain terminology. `robust` is generic hype here, not the statistics sense. There is no evident authorial voice to protect, so nothing was skipped.

## ai-tells

**P0: tool fingerprints (unfilled placeholders)**
- ❌ `[Company]` (sentence 1). This is an unfilled placeholder in the opening line. **Fix:** insert the real name. I can't supply it.
- ❌ `[Insert CTA here]` (last line). The only conversion point on the page is a stub. **Fix:** name the actual next step, such as a button label or link text for the one thing the reader does next. Don't invent an offer.

**P1: Tier 1 vocabulary (16 hits in about 95 words)**
- ❌ `In today's rapidly evolving landscape, [Company] is proud to unveil` is a template opener with `landscape` (Tier 1) inside it. **Replace with:** `[Company] makes [what it does] for [who].`
- ❌ `a game-changing platform that empowers teams to seamlessly leverage cutting-edge AI` packs four Tier 1 words (`game-changing`, `seamlessly`, `leverage`, `cutting-edge`) into one clause, and it names no task. **Replace with:** `a platform that lets [team] [specific task] with [specific AI capability].`
- ❌ `Our robust, comprehensive solution delves into the intricate tapestry of your workflow` has `robust`, `delves` and `tapestry` (Tier 1), plus `comprehensive` and `intricate` (Tier 2). **Replace with:** `[Company] [what it actually does to] your workflow`, and name the tools or steps it touches. Don't swap `leverage` for `utilize` or `delves` for `explores`. Those are the same tell, or Tier 2.
- ❌ `fostering a holistic approach that underscores what truly matters` combines Tier 1 `foster` and `underscore`, Tier 2 `holistic`, and "-ing" padding. The phrase `what truly matters` is a vague claim with nothing behind it. **Replace with:** cut the clause. If it hides a real claim, state it: `[the outcome, with a number if you have one].`
- ❌ `a startup navigating the realm of scale` has two Tier 1 words (`navigating`, `realm`) and mixes the metaphor. **Replace with:** `a startup that's scaling up.`
- ❌ `an enterprise seeking to elevate operational efficiency` uses Tier 1 `elevate`. **Replace with:** `an enterprise cutting [specific cost or time].`
- ❌ `our platform unlocks meaningful, impactful outcomes` uses Tier 1 `unlocks` and two Tier 3 words that carry no information. **Replace with:** `our platform [does X], so you [get Y: hours saved, errors cut].`

**P1: template and significance-inflation phrases**
- ❌ `It's not just a tool — it's a testament to what's possible.` combines the "not just X, it's Y" construction with `testament` (Tier 1). It says nothing about the product. **Replace with:** cut it. If there is a real differentiator, state it directly: `Unlike [alternative], it [the one concrete difference].`
- ❌ `Let's dive in and embark on this journey together!` is a chatbot-style "let's dive in" plus Tier 1 `embark`. **Replace with:** cut it. The CTA follows directly.
- ⚠️ `Ready to transform your workflow?` is a rhetorical question, and `transform` is the same hype family as the words above, though it isn't on the tier lists. **Replace with:** the CTA itself as a plain imperative once it's filled in, for example `[Verb] [thing].`
- ⚠️ `platform` / `solution` / `tool` all name the same product. This is synonym cycling, and each swap makes the referent slightly less clear. **Replace with:** pick one noun and keep it.
- ⚠️ `Whether you're a startup … or an enterprise …` is a stock audience-sweep. It's acceptable only if the outcome that follows differs for each audience. Right now it doesn't.

**P2: structure and rhythm**
- ⚠️ Adjective stacking: `robust, comprehensive`, `meaningful, impactful` and `intricate` all appear in adjacent pairs. Cutting one from each pair fixes nothing, because the noun is still unspecific.
- ✅ Em-dash count is 1, under the roughly one-per-paragraph threshold. It is flagged above only as part of the "not just X, it's Y" construction, not as overuse.
- ✅ Sentence lengths vary (about 21, 21, 11, 24, 9 and 8 words), so uniform rhythm isn't the problem.
- ✅ Checked and clean: chatbot openers ("Certainly!"), sycophancy, AI self-reference, vague attribution ("experts say"), hedge-stacking, emoji or hashtag stuffing, leftover markup.

**Second pass:** I re-scanned every proposed replacement in context. None introduces a Tier 1 or Tier 2 word, and none uses `streamline`, `empower` or `utilize`. Every replacement that needs a fact keeps a bracketed slot for it.

## Top 3 fixes

1. **Supply the three missing facts, then fill both placeholders.** The facts are what it does, for whom, and one measurable outcome. Removing the tells alone leaves almost no sentences, because none of the copy states a fact. The prose is filler around them. This has the highest leverage, and I can't do it for you without inventing claims.
2. **Delete the opener and the two sentences that follow it, plus `It's not just a tool…` and the `dive in / embark` line.** The first two sentences hold 10 of the 16 Tier 1 hits, and the "not just a tool" sentence and the closing line add two more. Cutting them removes most of the density in one move.
3. **Rewrite paragraph 2 around concrete outcomes.** Replace `navigating the realm of scale`, `elevate operational efficiency` and `unlocks meaningful, impactful outcomes` with a named cost, time or error reduction per audience, and let the CTA carry the last line.

Run `/guildproof:sharpen` with these findings to get a corrected version. `--fix` would also work, but it would leave the fact slots as bracketed placeholders until you supply them.