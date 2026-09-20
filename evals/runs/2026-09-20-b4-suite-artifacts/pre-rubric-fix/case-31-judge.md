# Scoring: `lens --lens ai-tells,editorial --fix`

## 1. Structural invariants (LENS)

- ✅ **Per-lens block, ✅/⚠️/❌ prefixes.** There are `## ai-tells` and `## editorial` blocks, and every finding carries a mark.
- ✅ **Worst-first ordering.** In `ai-tells`, four ❌ come first, then the ⚠️, then the ✅ lines. `editorial` follows the same pattern (❌❌❌ ⚠️ ✅…).
- ✅ **Top-3 fixes list.** The `## Top 3 fixes` section is present.
- ❌ **`/guildproof:sharpen` offer.** The rubric requires the route to end with the offer, and it appears nowhere in the output. The output ends on "`voice-check.mjs` not run. This run had no tool access. Run it before you send." The rubric does not exempt `--fix`, so this is a structural failure.
- ✅ **Names the lenses that ran.** The first line reads "Lenses run: `ai-tells`, `editorial` (built-in)." It reports no missing lenses, and none were requested-but-missing.

## 2. Quality dimensions (LENS)

- ✅ **Maps to checklist.** The findings name catalog items: "Tier 1 pair plus a template phrase", "Tier 2 cluster", "Negation-reframe", "Lead with the point", "Cut filler". They are not generic advice.
- ✅ **Specific.** Every ❌ quotes the artifact, for example "a **comprehensive, holistic** story you tell yourself".
- ⚠️ **Impact-ordered.** The top 3 leaves out "in today's landscape", which is a Tier 1 word plus a template phrase. Fix 1 says "two Tier 1 words, a template phrase and two filler words into one sentence", but those sit in the first sentence, not the "landscape" one. The editorial ❌ "Lead with the point" is also not resolved by the fix. The retained "I want to get into what that means" is still an announcement, and the output admits this only under "Unfixed observations".
- ⚠️ **No padding / marks earned.** Several ✅ lines carry no quote or reason: "✅ **Audience fit.**", "✅ **One idea per paragraph.**", and "✅ **Rhythm.** Varied and punchy". They flatter coverage without showing what was checked.
- ⚠️ **Internal inconsistency.** "Not talent. Not hustle. Systems." is a ⚠️ finding ("sit on the catalog's 'X isn't Y, it's Z' list"). The same string then appears under "Skipped under carve-outs" as "authorial voice". It cannot be both flagged and carved out.
- ⚠️ **Replacement quality.** "robust" became "good", so "and it's a good one" is still a contentless self-praising aside. The output does not acknowledge that the editorial filler finding survives in that clause.
- ✅ **Faithfulness (hard gate).** No facts were invented. "Fourteen years" and "two weeks" are explicitly left unverified and unchanged.

## 3. Must list

- ✅ **Cut the genuine tells.** In the corrected artifact, "leverage this opportunity to delve into" became "get into". "in today's landscape," is gone, "robust" became "good", and "comprehensive, holistic" is cut. I compared the artifact line by line and found nothing else changed.
- ✅ **Preserve signature.** "Not talent. Not hustle. Systems.", "Fix what breaks. Then break it again.", the "— E." sign-off, and both body dashes with their placement all survive. The line-end dash in "means —" is intact.
- ✅ **Flag voice-altering changes as suggestions and leave the text alone.** The output says "it's a suggestion only. Left alone." for the reframe, and gives the same treatment to the tighter-cuts option: "I didn't do it because each cut removes one of your two body dashes."
- ✅ **Two-directional second pass.** The output has separate "under-fixing" and "over-fixing" passes, and both are substantive.

## 4. Must-not list

- ✅ **Flatten fragments, regularize dashes, drop sign-off.** None of these happened.
- ✅ **Treat deliberate repetition as AI anaphora.** This is borderline. The output does list the fragment run as a catalog ⚠️, but it changed nothing and calls it "the piece's signature device". I count it as not violated, but the inconsistency noted above stands.
- ✅ **Rewrite wholesale.** The change is minimal and targeted, and the output's "byte-for-byte unchanged" claim holds up against the artifact.

## Verdict rationale

The substantive fix is good. It is minimal, voice-preserving, and honest about its limits. But the missing `/guildproof:sharpen` offer is a structural ❌, and the rubric makes any structural ❌ a hard-gate failure. Several ⚠️ marks (impact ordering, the flagged-and-skipped contradiction, unearned bare ✅ lines) would otherwise have made this WEAK.

VERDICT: FAIL