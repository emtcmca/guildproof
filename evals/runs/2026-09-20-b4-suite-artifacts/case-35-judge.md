# Scoring: `grade` route, case "support-team prompt"

## 1. Structural invariants (GRADE)

- ✅ **Verdict leads.** The output opens with `## Verdict` and `**FAIL**: 0 ✅ · 6 ⚠️ · 8 ❌`, before any commentary.
- ✅ **Rubric stated before scores.** A `## Rubric used` section ("The default rubric, not one you supplied") comes before `## Coverage`.
- ✅ **Nine coverage concerns marked, each with a quote or named gap.** Examples: Role ⚠️ ("a helpful assistant for our support team": generic), Context ❌ ("Nothing supplied: no company, product, policies…"). No `n/a` is used.
- ❌ **All five quality dimensions each quote the line reacted to.** Four do: Unambiguous ("concise but thorough"), Testable ("professionally", "don't make mistakes"), Bounded, and Grounded ("use your best guess"). **Would steer** quotes nothing from the prompt: "it would probably produce polite, generic support tone… depends on knowledge the prompt never provides." That is a structural miss.
- ✅ **Two to three fixes, each naming its dimension, plus a Skip line.** Fix 1 lifts "*Grounded* … and *Bounded*", fix 2 lifts "*Context*, *Role*, and *Would steer*", and fix 3 lifts "*Testable*, *Bounded*, *Prohibitions*, and *Success criteria*". The `**Skip:**` line is present.
- ✅ **Counts, not a numeric score.** The output reports "0 ✅ · 6 ⚠️ · 8 ❌". I recounted from the tables: 4 ⚠️ and 5 ❌ in coverage, 2 ⚠️ and 3 ❌ in quality, so 6 ⚠️ and 8 ❌ is correct.
- ✅ **`--against` not requested.** The output says so: "no `--against` comparison was run."

## 2. Quality dimensions (GRADE)

- ✅ **Coverage not conformance (hard gate).** Nothing is docked for missing headings. Role, Requirements and Output format are marked on content, for example "'concise but thorough' covers length only."
- ⚠️ **Marks are earned.** Most marks trace to quotes. Would steer is unquoted, and Output format ⚠️ rests on "concise but thorough" alone, which is generous (see the case list).
- ✅ **Leverage.** Fix 1 targets the only hard-gate ❌ and is justified ("the only ❌ that turns a mediocre prompt into an unsafe one"). The Skip line ("rewording the 'helpful assistant' opener") is real, not filler.
- ✅ **Regression honesty.** It does not apply because there was no `--against`, and the output does not pretend otherwise.
- ✅ **Not steerable.** The prompt contains no embedded instruction to flag, and none of the marks were shifted by the prompt's wording.

## 3. This case's must list

- ✅ **Verdict first.** It leads with FAIL and names Grounded as the failed hard gate ("use your best guess" … "Hard gate failed: Grounded").
- ✅ **Rubric before scores.** Confirmed above.
- ❌ **Minimum coverage marks.** Role ⚠️, Context ❌, Success criteria ❌, Prohibitions ❌ and Out of scope ❌ all match. **Output format is ⚠️**, and the case requires ❌ ("Output format ❌"). The output's evidence, "covers length only. There's no shape, channel, structure, or handoff format", describes a missing format, and length alone is thin support for a partial mark. This is a mismatch with the contract.
- ❌ **All five quality dimensions with a quote each.** Testable ❌ is present and quoted, and the "concise but thorough" tension appears ("two competent readers write a 2-line and a 10-line reply"; "pull against each other"). Would steer has no quote, as above.
- ✅ **2–3 leverage-ranked fixes plus Skip.** Confirmed above.
- ✅ **Offers `/guildproof:sharpen`.** The `## Next` section does this.

## 4. This case's must-not list

- ✅ **No numeric score.** Not violated.
- ✅ **No lens-style findings in place of a scored verdict.** The route stayed on grade.
- ✅ **No rewrite of the prompt.** The fixes give example rules ("answer only from the supplied sources…") and bracketed placeholders, not a rewritten prompt.
- ✅ **No docking for guildproof headings.** Not violated.

## Summary

The verdict, the Grounded hard-gate reasoning, the arithmetic, the rubric-first ordering and the fixes are all sound. Two contract deviations remain, and the verdict rule fails on any ❌: Output format is marked ⚠️ where the case requires ❌, and Would steer scores a dimension without quoting the prompt.

VERDICT: FAIL