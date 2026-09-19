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
