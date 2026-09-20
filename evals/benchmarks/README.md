# Benchmarks

The eval suite in `evals/cases/` asks "does each command and agent do its job?" These benchmarks ask
the question an installer asks: **"what changes if I add guildproof?"** Each one compares a run
*with* guildproof against the same model *without* it, on inputs where the answer can be checked.

Every contract and scoring rule below was written **before** any run. A benchmark whose rules are
written after seeing the outputs measures the author's hindsight, not the tool.

## House rules (all four benchmarks)

- **Two model tiers:** a frontier model and a small model. Record the exact model id per run.
- **k ≥ 2.** Every arm runs at least twice. One run is an anecdote.
- **Blind judging:**
  - A separate judge writes its own defect list from the contract *before* it reads any output.
  - It then scores outputs labelled only A and B.
  - Lines that reveal the arm are stripped first (see `../runs/2026-09-19-self-review-artifacts/blind-pairs.py`).
  - The label key never reaches the judge.
- **Everything committed:** prompts, outputs, judge lists, judgments, the label key and token counts,
  in a dated folder under `../runs/`.
- **Publish what comes back.** A result that cuts against guildproof ships with the same prominence
  as one that doesn't. The self-review run already did this.

## B1 — Build delta: does sharpening the request change the code that gets built?

The claim in the README's proof images, measured.

- **Arm A:** the model gets the raw one-line request and builds.
- **Arm B:** the request goes through the `prompt-engineering` skill's SHARPEN route first. The model
  builds from the sharpened prompt.
- **Scoring:** the judge checks the *code*, not the prompt, against a contract neither builder saw.
- **Reported:** per task, which contract clauses the code breaks, grouped by severity (HIGH / MEDIUM / LOW).
- **Headline:** "HIGH contract breaches per build, raw vs sharpened", by model tier.

Tasks are in [`b1-tasks.md`](b1-tasks.md). Each is a request a developer would actually type, with a
hidden contract that has at least one clause a hurried build commonly misses.

## B2 — Specialist behaviors: what the agent prompts change about an answer

- **Arm A:** the bare model gets the user's message.
- **Arm B:** the same message, with the specialist's prompt as the system prompt.
- **Specialists:** `debugger`, `security-review`, `api-reviewer`, `verifier`.
- **Scoring:** a fixed checklist of behaviors per specialist that a bare model tends to skip (below).
  Each item is scored present or absent from the output text, with a quote.

| Specialist | Behaviors scored |
|---|---|
| debugger | separates the user's claims from verified facts · declines to invent a reproduction · ranks hypotheses, each with a cheapest probe · separates trigger from root cause · does not hand over a masking one-line patch |
| security-review | ranks findings by exploitability × impact · names the attack, not just the weakness · separates observed from assumed · states what was not checked |
| api-reviewer | checks the contract (status codes, idempotency, pagination, error shape) not just the code · flags breaking changes · names the abuse path |
| verifier | tri-state verdict · BLOCKING line · Independence line · severity-ranked defects · no rewrite · a receipt for each clean axis |

Inputs are in [`b2-inputs.md`](b2-inputs.md).

## B3 — Self-review vs fresh verifier, at scale

The 2026-09-19 six-pair run was half a yes. B3 repeats it on the B1 tasks with k=2, so the result is
a rate, not an anecdote.

- **Self arm:** the builder, in its own conversation, is handed the verifier prompt and the contract.
- **Fresh arm:** a new agent gets the identical prompt, contract and code.
- **Reported:** false-clean rate (a real defect marked ✅) and defect recall, per arm and tier.

## B4 — Full suite at the release tag

Every case in `evals/cases/`, plus the six known-bad fixtures, run at the exact commit being tagged.

- The known-bad fixtures must all FAIL. That's the proof the judge can say no.
- **Reported:** PASS / WEAK / FAIL counts, and KB fixtures correctly failed out of 6.

**Known-bad half: RUN 2026-09-20 at `9a71114`. 6 of 6 correctly failed, k=2, blinded.** Plus a
positive control — a known-good output through the identical path — scoring WEAK/WEAK, which is
what rules out the result being a judge stuck on FAIL. Run doc:
[`evals/runs/2026-09-20-b4-knownbad.md`](../runs/2026-09-20-b4-knownbad.md); runner:
[`evals/harness/run-knownbad.py`](../harness/run-knownbad.py), exit-coded so it works as a gate.

**Suite half: RUN 2026-09-20 at `1c5d7c6`. 34 of 38 judged: 2 PASS, 24 WEAK, 8 FAIL**, plus the 4
`/orchestrate` cases reported UNMEASURED-BY-TRANSPORT because `claude -p` cannot dispatch
registered subagents. Run doc: [`evals/runs/2026-09-20-b4-suite.md`](../runs/2026-09-20-b4-suite.md);
runner: [`evals/harness/run-suite.py`](../harness/run-suite.py).

**Read that distribution as a gate, never as a rate.** It is a single-arm absolute score with no
bare arm to cancel judge harshness against, and PASS demands zero ⚠️ across ~15-20 marks from a
judge instructed to default to ⚠️. The same property makes the repo's 2026-07-21 result of
36 PASS / 1 WEAK implausible in the opposite direction. That run's own doc names the reason without
needing help: **"wave 1 is not blind"** — producers were told to read only the `## Input` section,
`Read` returned the whole file including the Must and Must-not lists, and two of nine producers
disclosed it unprompted. Its producers and judges were also subagents inside one host session
rather than separate OS processes. **Getting a trustworthy result here took fixing five transport
bugs and four defects in this rubric**, which is the run's most transferable finding and is written
up in full.

---

# Coverage: what carries evidence and what does not

Added 2026-09-20, after B2 ran at two tiers and across three vendors.

This table exists because a reader deserves to know which claims on the README are measured.
It is deliberately uncomfortable in places. Keeping it accurate is cheaper than being caught.

| Feature | Benchmark | Status |
|---|---|---|
| `verifier` | B2, B3 | **Measured.** The gap does not close as models improve: bare arms moved 8% to 13% across tiers while other specialists moved 10% to 75%. |
| `debugger`, `security-review`, `api-reviewer` | B2 | **Measured, and it cuts against them.** Bare frontier models scored 75%, 81% and 83% on their own checklists. These prompts are competing with model progress. |
| `/sharpen` | **B1** | **Not run.** The oldest and most central claim in this repo has never been tested. |
| `/orchestrate` | **B5, below** | **Not designed until now.** Four eval cases and one live seven-agent run exist. That is a demonstration, not a measurement. |
| `/forge-agent` | **B6, below** | **Not measured.** |
| `/lens --grade` | cases 35-37 | Structural cases only, no with-versus-without benchmark. |
| Lens library extensibility | none | No evidence. |
| `docs-writer`, `frontend-builder`, `prompt-engineer`, `refactor-planner` | none | No dedicated eval case. |

## The durability question, and what it is NOT

For each feature, ask: **does a better model do this for free?** A feature whose advantage shrinks
every model release is a convenience with a shelf life. One whose advantage holds is a durable
asset. The verifier is the only component measured as durable so far.

**This is a question about what to CLAIM, not about what to ship.** A command that a strong model
could partly do unprompted is still worth having: it is repeatable, it has a fixed output shape,
and its lens library is extensible. Those properties are why the author uses `/lens` daily. The
durability finding changes how prominently a feature is sold, never whether it exists. Nothing in
this table is a deletion candidate.

## B5 - Orchestration: what the coordinator changes about a multi-domain build

The one benchmark that cannot use the cross-model harness. `/orchestrate` needs a host that can
spawn subagents, so this runs on Claude Code only and its honesty floor must say so.

- **Arm A:** one agent receives the whole multi-domain request and builds it in one conversation.
- **Arm B:** the same request through `/orchestrate`, which splits it across specialists and runs
  an independent verifier that can halt the pipeline.
- **Inputs:** requests that genuinely span domains and must agree at the seams, for example a
  schema plus an endpoint plus an auth rule plus tests, where the tests must match the schema the
  other slice chose.
- **Scoring**, by a judge holding a contract neither arm saw:
  - **seam defects** - places where two parts of the deliverable contradict each other. This is
    the defect class a single conversation is supposed to avoid and an orchestrated run is
    supposed to catch. It is the headline number.
  - **coverage gaps** - requirements no slice addressed.
  - **did the verifier halt when it should have**, and did it halt when it should not have. A
    coordinator that never blocks is not a gate, and one that always blocks is useless.
- **Report:** seam defects per build, and the false-halt rate beside the true-halt rate. Never
  the halt rate alone: a rule that over-blocks passes every gate while making the tool useless.

## B6 - Forged agent prompts: does `/forge-agent` beat an ad-hoc prompt?

Two stages, and the second reuses B1's machinery.

- **Stage 1:** for each role, produce two system prompts. Arm A is a short ad-hoc prompt of the
  kind someone writes in thirty seconds. Arm B is the output of `/forge-agent` for the same role.
- **Stage 2:** the same model, on the same tasks, once under each prompt. The judge scores the
  work product against a contract written before either prompt existed.
- **Scoring:** contract breaches by severity, plus whether each prompt states its own limits and
  refusals. A forged prompt that only reads better but produces the same work has failed.
- **Honesty floor:** the ad-hoc prompt is written by the same person who wrote `/forge-agent`,
  which is a conflict. Either have the ad-hoc arm authored by a model given only the role name,
  or state the conflict in the run doc. Prefer the former.

## Priority order

1. **B1.** It tests the repo's original thesis, and it is the only benchmark that could give
   guildproof a second measured leg. Write the contracts first and publish whatever comes back.
   The verifier result is strong enough that B1 does not need to succeed. It needs to be known.
2. **B4** at the release tag, for the six known-bad fixtures.
3. **B5**, because `/orchestrate` is advertised prominently and carries no measurement.
4. Remaining B2 inputs across the pinned model matrix.
5. **B6.**
6. `/lens --grade` and lens extensibility, last, and only if there is something worth asking.
