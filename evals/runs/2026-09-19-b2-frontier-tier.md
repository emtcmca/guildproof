# B2 — Specialist behaviors, frontier tier

**Date:** 2026-09-19 · **Benchmark:** [B2](../benchmarks/README.md) · **Small-tier run:**
[2026-09-19-b2-specialist-behaviors.md](2026-09-19-b2-specialist-behaviors.md) ·
**Artifacts:** [`2026-09-19-b2-frontier-artifacts/`](2026-09-19-b2-frontier-artifacts/)

Same four specialists, same staged inputs, same wording, same k, same checklists. **The only
variable changed is the model.** The small-tier run used `claude-haiku-4-5-20251001`; this one used
the session's frontier model.

Two differences in the judging, both deliberate:

- **The two judges run on different models** (Opus and Sonnet). At the small tier both judges were
  the same model. Here the subjects are the frontier model, so a same-model judge could plausibly be
  generous toward outputs shaped like its own. Splitting the judges across models makes that bias
  measurable instead of arguable.
- **A different label permutation** from the small tier, so position cannot correlate with arm across
  the two runs.

## Result

| Specialist | Behavior | Bare | With guildproof |
|---|---|---|---|
| debugger | separates the user's claims from verified facts | 2/4 | 3/4 |
| debugger | declines to invent a reproduction | 4/4 | 4/4 |
| debugger | ranks hypotheses, each with a cheapest probe | 3/4 | 4/4 |
| debugger | separates trigger from root cause | 2/4 | 4/4 |
| debugger | no masking one-line patch handed over | 4/4 | 4/4 |
| security-review | ranks by exploitability × impact | 3/4 | 4/4 |
| security-review | names the attack, not just the weakness | 3/4 | 4/4 |
| security-review | separates observed from assumed | 4/4 | 4/4 |
| security-review | states what it did NOT check | 3/4 | 4/4 |
| api-reviewer | reviews the contract, not just the code | 4/4 | 4/4 |
| api-reviewer | flags breaking changes | 4/4 | 4/4 |
| api-reviewer | names the abuse path | 2/4 | 4/4 |
| verifier | tri-state verdict | **0/4** | 4/4 |
| verifier | explicit BLOCKING line | **0/4** | 4/4 |
| verifier | explicit Independence line | **0/4** | 4/4 |
| verifier | defects ranked by severity | 2/4 | 4/4 |
| verifier | does not rewrite the code | **0/4** | 4/4 |
| verifier | a receipt for each clean axis | 1/4 | 4/4 |
| **Total** | | **41/72 (57%)** | **71/72 (99%)** |

## The finding, and it is not the total

Put the two tiers side by side and the story is not "guildproof adds 42 points."

| Specialist | Small bare | Small guildproof | Frontier bare | Frontier guildproof |
|---|---|---|---|---|
| debugger | 2/20 (10%) | 11/20 (55%) | 15/20 (75%) | 19/20 (95%) |
| security-review | 7/16 (44%) | 16/16 (100%) | 13/16 (81%) | 16/16 (100%) |
| api-reviewer | 6/12 (50%) | 7/12 (58%) | 10/12 (83%) | 12/12 (100%) |
| **verifier** | **2/24 (8%)** | 22/24 (92%) | **3/24 (13%)** | 24/24 (100%) |

**A frontier model is already a capable debugger, security reviewer and API reviewer without any of
this.** It went from 10% to 75% on the debugger checklist and from 50% to 83% on api-reviewer purely
by being a better model. Three of the four specialists are largely closing the gap on their own, and
api-reviewer's small-tier loss disappears: at this tier it ties on two items and wins the third.

**The verifier does not close. It is 8% at the small tier and 13% at the frontier tier.** Model
strength bought it five points. A frontier model asked to verify an artifact against a contract, with
no prompt, produced no tri-state verdict, no BLOCKING line and no Independence line in any of eight
scorings across both tiers, and rewrote the code instead of reporting defects every single time.

That is the claim this benchmark actually supports: **not that guildproof makes a model smarter, but
that a capable model will not spontaneously produce a blocking, independent verdict, and that this
does not improve as models improve.** Getting better at finding defects is not the same as being
willing to stop the job, and only one of those scales with the model.

## Structure versus judgment

Several checklist items restate the output contract the prompt itself specifies. Asking "did it print
a BLOCKING line" of an arm instructed to print one measures instruction-following. Splitting the
items by what they actually demand:

| | Frontier bare | Frontier guildproof | Delta | (Small-tier delta) |
|---|---|---|---|---|
| **Structure** — emit a section the prompt names | 39% | 100% | +61 pts | +79 pts |
| **Judgment** — do or refrain from something substantive | 68% | 98% | **+30 pts** | +39 pts |

The classification is in this run's script and is debatable; `ranks hypotheses with a probe` and
`states what it did not check` could be argued either way. Both splits are published so a reader can
reclassify and recompute.

**The judgment delta is the honest headline: +30 points at the frontier tier, +39 at the small
tier.** It shrinks as the model improves, exactly as it should. Anyone quoting the raw 57% to 99%
without this split is quoting a number that is half instruction-following.

## Judge agreement, and the bias check

**Cross-model agreement: 64 of 72 cells (89%), Cohen's κ = 0.68.** Lower than the small tier's κ =
0.92, which was measured between two judges on the *same* model. Two judges on different models agree
less. That is the expected result and the more honest number, because same-model agreement partly
measures shared habits rather than a decidable checklist.

**The generosity check came back clean.** The Opus judge marked items present 79% of the time, the
Sonnet judge 76%: a 3-point gap. If a same-model judge were flattering outputs from its own model,
this is where it would show, and it did not. That was the reason for splitting the judges and it is
the one methodological question this run answers better than the small-tier run did.

## Method limits

Everything in the small-tier run's limits section still applies: one input per specialist, four of
B2's eight inputs unrun, blinding weaker than B3 because the scored behaviors *are* output structure,
redaction enforced by promise rather than construction, and behavior presence not being correctness.
Plus two specific to this run:

- **Judge 1 is the same model as the subjects.** Disclosed rather than hidden; the generosity check
  above is what makes it defensible, and judge 2 is a different model.
- **One judge renamed itself.** The Sonnet judge on the debugger bundle returned its `specialist`
  field as `debugging-diagnosis-judge (5-item rubric, judge 2 of 2)`, and another returned a
  filename. Specialist attribution was therefore recovered from each scorecard's rubric length, which
  is unambiguous because the four checklists have 3, 4, 5 and 6 items. The inference is recorded in
  each committed scorecard as `_specialist_inferred_from_rubric_length`. No scores were changed.
- **Zero rows were excluded** this time. The small-tier run excluded five; tightening the schema
  description to state the item count fixed it.

## Substance errors the judges caught, in both arms

Worth reading, because they are the reason "behaviors present" is not "answer correct". The judges
recorded confidently wrong statements in guildproof-arm outputs too: one asserted that a two-frame
stack trace establishes a client-component render when it does not, and three separate outputs across
both arms claimed that class instances and getters are silently dropped across the React server
boundary when React normally throws a loud serialization error instead. One output attached
probability estimates to six hypotheses that sum to exactly 100% while admitting it had not read the
relevant line. The prompt buys the shape of a good answer. It does not buy being right.
