# guildproof eval runner — protocol

The host (Claude Code) follows this to run and score cases. No external infra, no API keys —
the host both runs and judges, matching guildproof's zero-call ethos.

## Inputs

- One or more case files from `cases/`.
- `rubric.md` (invariants + dimensions + scale + judge stance).

## Procedure (per case)

1. **Read the case.** Note its `route`, target command/agent, expected lenses, and its
   case-specific must / must-not.

2. **Run it as a user would.** Load `skills/prompt-engineering/SKILL.md` (and, for a gallery
   case, the agent file) and execute the case `Input` on the named route. Produce the real
   output. **Capture it verbatim** — that artifact is what gets scored, not a paraphrase.

3. **Structural pass.** Walk the route's invariants in `rubric.md`. Mark each ✅/❌ with a
   one-line reason. Any ❌ is a hard-gate fail.

4. **Quality pass (adversarial).** As a skeptic judge (and `prompt-engineer` eye for prompt
   outputs), score each quality dimension for the route ✅/⚠️/❌ + reason. Try to break it;
   make ✅ be earned. Quote the output you react to.

   **Independent judging for high-stakes routes.** The producer must not grade its own work on the
   cases that matter most. Apply the **rule** in `rubric.md` (not a fixed case list, which goes
   stale): a case needs an independent judge if it tests a security gate, a legal/regulatory/
   medical/financial output, a code or config artifact, an artifact-producing route including any
   `--fix` run, or orchestration. At time of writing: cases **13, 15, 16, 17, 20, 21, 22, 23, 27**
   and every `--fix` case. For these, spawn the judge as a **separate subagent** — the `verifier`
   agent is purpose-built for this — given *only* the case input + the captured output + the rubric,
   **not** the producing context, reasoning, or self-description. Its frame is "assume this is wrong;
   refute it." Record the judge's identity in the scorecard. (A self-graded run on a high-stakes case
   is not a valid result — it's the bias the harness exists to remove.)

5. **Case-specific checks.** Score the case's own must / must-not (e.g. "must not cite a
   governing provision it wasn't given"). A must-not violation is a hard-gate fail.

6. **Verdict.** Apply `rubric.md` → PASS / WEAK / FAIL, honoring hard gates (structural,
   faithfulness/guardrail, must-not).

7. **Record.** Append the case's scorecard to the run file (below).

## Output — scorecard

Write one file per run: `runs/YYYY-MM-DD-HHmm-<label>.md`. Header, then one section per case.

```markdown
# Eval run — YYYY-MM-DD HHmm

- commit: <git short SHA>
- changed since last run: <one line, or "baseline">
- cases: <ids run>

## <case id> — <route> — VERDICT: PASS|WEAK|FAIL

**Structural**
- ✅/❌ <invariant> — <reason>

**Quality**
- ✅/⚠️/❌ <dimension> — <reason, with a quote>

**Case-specific**
- ✅/❌ <must / must-not> — <reason>

**Notes / defects found** — <what to fix in the engine/lens/agent, if anything>

---

## Run summary
- PASS: n   WEAK: n   FAIL: n
- Top defects to fix, worst-first:
  1. ...
```

## Calibration — prove the judge can FAIL

A harness that has never produced a FAIL is not calibrated; it may be rubber-stamping. So
`evals/known-bad/` holds **negative fixtures**: a case input paired with a deliberately *bad*
output (an invented fact, a bypassed injection, an SQL-injectable handler). The harness **must
return FAIL** on each. Run them whenever the rubric or runner changes:

- If a known-bad fixture scores PASS or WEAK, the judge is broken — fix the rubric/judge before
  trusting any green run. The fixtures are the test *of the test*.
- Keep the known-bad set adversarial and current: when a red-team finds a new failure class the
  judge missed, add a fixture for it.

## Refinement loop

After changing a lens / engine / agent, re-run the **same** cases into a new run file. Diff
against the prior run: keep the change only if the targeted dimension improved and nothing
regressed. The `runs/` history is the regression trail — commit every run.

## Notes

- Judge the artifact the engine actually produced, not what it "should" have produced.
- If the same defect shows across cases, that's an engine/template fix, not a per-case nit.
- Keep runs honest: a WEAK that's really a FAIL helps no one. Default harsh.
