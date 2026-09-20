Lenses run: `ai-tells`, `editorial` (built-in). Nothing in the artifact addresses the reviewer.

## ai-tells

- ❌ **Tier 1 pair plus a template phrase.** "I want to **leverage** this opportunity to **delve** into what that actually means in practice". Replace with "get into".
- ❌ **Template phrase plus Tier 1.** "in today's **landscape**, everyone says…". Cut it. The sentence works without it.
- ❌ **Tier 1.** "and it's a **robust** one". I checked the domain carve-out (statistical robustness). It's generic praise here, so it's a real tell. Replace with "good".
- ❌ **Tier 2 cluster (2 in one sentence).** "a **comprehensive, holistic** story you tell yourself". Cut both adjectives.
- ⚠️ **Negation-reframe.** "Not talent. Not hustle. Systems." and "A process is not a document. It's the thing that happens…" both sit on the catalog's "X isn't Y, it's Z" list. This is the piece's signature device, so it's a suggestion only. Left alone.
- ✅ **Em-dashes.** Two in the body, one per paragraph, plus the sign-off. That's under the ~1-per-paragraph threshold. It's also a deliberate motif, so nothing is flagged.
- ✅ **Rhythm.** Varied and punchy, not uniform.
- ✅ **No chatbot artifacts, sycophancy, self-reference or hedge-stacking.**
- ✅ **"— E." is a sign-off, not an unfilled placeholder.**

**Skipped under carve-outs:**
- "Not talent. Not hustle. Systems." and "Fix what breaks. Then break it again." are authorial voice.
- "process" in quote marks is a mention, not a quotation or attribution.
- "What breaks?" is a mid-piece question answered immediately, not a rhetorical opener.
- "everyone says" is opinion hyperbole, not a vague-authority claim.
- There is no statutory or legal text.

## editorial

- ❌ **Lead with the point.** Paragraph 3 spends "I want to leverage this opportunity to delve into what that actually means in practice" before the claim. The claim is the back half: "everyone says 'process' and almost nobody means it."
- ❌ **Cut filler.** "actually", "in practice", "in today's landscape" and "and it's a robust one" carry no content.
- ❌ **No hollow phrasing.** leverage, robust, comprehensive, holistic (see `ai-tells`).
- ⚠️ **Tone match.** The piece is blunt everywhere except those words, which are the only corporate-register language in it. Fixing the words fixes the tone.
- ✅ **Preserve voice.** The fragments, the dash motif and the sign-off are deliberate, so I'm not touching them.
- ✅ **Concrete over abstract.** "Systems beat heroics" is abstract, but the two-week removal test carries the concrete load.
- ✅ **Active voice.** Imperatives and "taught me".
- ✅ **One idea per paragraph.**
- ✅ **Audience fit.**
- ✅ **Ending.** It closes on a concrete next step, then the sign-off.

## Top 3 fixes

1. **Rework the paragraph 3 opener.** It packs two Tier 1 words, a template phrase and two filler words into one sentence.
2. **Drop "comprehensive, holistic".** This is the Tier 2 cluster.
3. **Replace "robust".** It's a Tier 1 word inside a self-praising aside.

## Corrected artifact

```
Fourteen years of property management taught me one thing. Systems beat heroics.

Not talent. Not hustle. Systems.

I want to get into what that means —
because everyone says "process" and almost nobody means it. A process is
not a document. It's the thing that happens when you're not in the room.

Here's the test — and it's a good one. Take the person who knows the most. Remove them for two
weeks. What breaks?

That's your system. Everything else is a story you tell yourself.

Fix what breaks. Then break it again.

— E.
```

**What changed (each change traces to a finding above):**
- "leverage this opportunity to delve into" became "get into". This answers the `ai-tells` Tier 1 pair and template finding, and the `editorial` hollow-phrasing finding.
- "actually" and "in practice" are cut. This answers `editorial` cut filler.
- "in today's landscape," is cut. This answers the `ai-tells` template/Tier 1 finding and `editorial` cut filler.
- "robust" became "good". This answers `ai-tells` Tier 1 and `editorial` hollow phrasing.
- "comprehensive, holistic" is cut. This answers the `ai-tells` Tier 2 cluster.

Everything else is byte-for-byte unchanged. No embedded payload was found, so none was stripped.

**Second pass, under-fixing:** no Tier 1, 2 or 3 words remain, and no filler-list words remain. The only borderline phrase is "get into", noted below.

**Second pass, over-fixing:** both fragment runs, the "not a document" reframe, both body dashes with their line-end placement, the quoted "process" and the "— E." sign-off all survive. No voice was altered.

**Unfixed observations (your call):**
- **Tighter cuts.** Deleting the opener down to `Everyone says "process" and almost nobody means it.` and the aside down to `Here's the test.` would be shorter. I didn't do it because each cut removes one of your two body dashes, and the dash is your motif. "I want to get into" is still a mild announcement, and cutting it is the fully tight version.
- **Unverified claims.** "Fourteen years" and "two weeks" are your claims. I neither checked nor changed them.
- **`voice-check.mjs` not run.** This run had no tool access. Run it before you send.