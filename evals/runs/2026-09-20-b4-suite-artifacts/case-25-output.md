# Evaluation: onboarding subject-line set (no rubric supplied)

## Rubric used (derived, not supplied)

You gave no rubric, so I derived one from the artifact's evident purpose: a three-line subject set for a B2B SaaS onboarding sequence. Correct it before trusting the grades.

- **Scale:** ✅ meets the criterion, ⚠️ partially meets it, ❌ fails it. Overall verdict is PASS, WEAK or FAIL.
- **Criteria:**
  1. Spam-pattern and trust risk
  2. Specificity (value signal)
  3. Actionability (one clear next step)
  4. Set coherence (each line has a distinct job in the sequence)
  5. Tone fit for a B2B audience
  6. Length and front-loading
- **Derived hard gate (must-not):** no ALL-CAPS urgency and no stacked exclamation marks in a subject line.

**What I assumed:** I don't know where each line sits in the sequence, the product, the audience seniority, the brand voice, or any send data. These grades are heuristic and about the copy only. Nothing here says how the lines will inbox or perform.

## Scores (worst-first)

- ❌ **Spam-pattern and trust risk.** Line 3 is the problem: "ACTION REQUIRED: Complete your setup now!!!" combines all-caps, a triple exclamation and a bare urgency claim. It also asserts a requirement with no stated consequence, and B2B recipients tend to read that pattern as phishing or a dunning notice. If setup isn't actually blocking anything, the line also overstates its case. Lines 1 and 2 don't share this defect.
- ❌ **Specificity.** None of the three names a product, a first-name token, or a concrete step or outcome. "Let's get you started" leaves open started with what. "Complete your setup" leaves open which setup step. "Your account is ready" gives no reason to open beyond status. Any SaaS could send these three.
- ⚠️ **Actionability.** Line 2 tells the reader the account is ready but gives no next step. Line 1 gestures at one ("get you started") without naming it. Line 3 demands action but doesn't say which. No line names a single specific next step.
- ⚠️ **Set coherence.** The lines can be read as a progression from welcome to status to nudge, but the set doesn't say so. Lines 1 and 2 overlap, since both are plausible day-0 messages. Line 3 also sits awkwardly against line 2: if "Your account is ready," it's unclear what "setup" is still outstanding. The register jumps from celebratory to neutral to alarmed with no middle step.
- ⚠️ **Tone fit for B2B.** Line 1's emoji and "Welcome aboard!" are stock consumer-SaaS phrasing. That's a risk flag, not a defect: it depends on your brand voice, which I don't have. What costs points is that the celebratory framing carries no information. Line 2's plain tone is the best fit of the three.
- ✅ **Length and front-loading.** All three are short (about 21, 39 and 43 characters by my count). Lines 1 and 2 put their meaning early. Caveat on line 3: the all-caps prefix uses the first ~16 characters, so the actual ask may fall past the cut-off on a narrow mobile preview. That's a rule of thumb, not something measured here.

**Per-line rollup:** Line 2 is the strongest but under-specified. Line 1 is acceptable but hollow. Line 3 is the weakest and trips the hard gate.

## Hard gates

**Failed: no all-caps urgency or stacked exclamation marks (line 3).** This gate is my derivation, not yours. If you remove it, the verdict would still be WEAK on specificity, though line 3's trust problem would then be a ⚠️ rather than a cap.

## Verdict

**WEAK** (1 ✅ · 3 ⚠️ · 2 ❌, capped by the hard-gate failure). The set is clear and short, but it is generic. One line reads as spam-pattern urgency, and nothing shows the three lines were designed as a sequence.

## Top 3 fixes (ranked by leverage)

1. **Rework line 3.**
   - Drop the caps and the exclamation marks.
   - Name the one specific unfinished step.
   - Use "required" only if the step really blocks use of the product, and state the consequence if it does.
   - This clears the hard gate and lifts spam-pattern risk from ❌ to ✅. It also raises actionability and tone.

2. **Give each line one concrete, true detail.** That could be the product name, a first-name token, the specific first action, or the time to value. Use only facts about the product you can stand behind. This lifts specificity from ❌ toward ✅ and helps actionability.

3. **Define each subject's job in the sequence: its trigger and timing.**
   - Differentiate lines 1 and 2, or merge them.
   - Fire line 3 only when setup is genuinely incomplete, so it never contradicts line 2.
   - This lifts set coherence from ⚠️ to ✅.

**Skip:**
- Whether to keep the emoji in line 1. That's brand-voice preference until you tell me your voice rules.
- Casing and length tweaks. Length already passes.
- A/B-test wording debates before fixes 1 and 2 are in.

For the corrected lines, feed these fixes to `/sharpen` or a copy-rewrite pass. I don't rewrite the lines myself.