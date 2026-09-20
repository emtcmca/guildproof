## 1. Structural invariants (GALLERY AGENT)

- ✅ **Output matches the agent's Output contract, section for section.** `agents/planner.md:64-69` requires Goal + DoD, Tasks, Critical path, Parallelizable, and Risks & decision points. All five are present, and the extra "Assumptions" section is what the honesty floor asks for. Every task carries a "Depends on:" line and an acceptance check.
  - Two looseness notes: the Goal/DoD is a paragraph plus five bullets, not the "one or two lines" the contract asks for. The tasks are multi-bullet blocks, not the one-line `#n — acceptance — depends on` shape. I don't count either as a structural failure because no section or field is missing.
- ✅ **A Voice is detectable.** Examples: "Everything downstream waits on #3, the first real worker," and "If the allowlist is large, the #8 branch dominates and should get the most people."

## 2. Quality dimensions

- ⚠️ **Contract honored.** All sections are present, but the Goal/DoD overruns its length and the task-line format is loosened (see above). There is also a critical-path defect.
  - The plan claims a co-critical branch "**#3 → #8 → #10 → #11**". Its own dependency lines contradict that: #11 depends on "#7, #8, #9", not #10, and #10 feeds #12.
  - The Parallelizable section agrees with the dependency lines, not with the critical-path claim: "#10 and #11 overlap once #8 lands."
  - The primary path, "#1 → #2 → #3 → #4 → #5 → #7 → #11 → #12", checks out against the dependency lines. The secondary claim is wrong.
  - The cut line also drops #10 "only if #1's measurement shows small data," but #12 lists "Depends on: #10, #11." The cut would break a stated dependency.
- ⚠️ **Guardrails honored (hard gate).** The core unknowns are flagged. "It has, or can add, a background job runner, private file storage and a transactional email sender," and #1 asks "what exists?" for runner, storage, mailer and flag mechanism. Several other dependencies are treated as available without being flagged:
  - Staging: "tested up and down on a staging copy," "on staging."
  - Alerting and metrics: "An alert on failure rate."
  - A scheduler for "A scheduled sweep."
  - A read replica: "batched reads or a replica."
  - An account-deletion path: "Deleting a user's account also removes their export files."
  - Percentage rollout support.
  - Auth is only in the assumptions list. It is not in #1's acceptance checklist, although the text says #1 exists to "confirm or kill these."
- ⚠️ **In voice.** It reads as a competent planner, but more like a formal design doc than a standup, and it is long for a CSV export.
- ⚠️ **Self-challenge done.** The "Sharpest objection: do you need async plus email at all?" and the cut line are real. The method's step-6 checks ("is the critical path real," "did I assume a dependency never confirmed") visibly missed the co-critical contradiction and the unflagged staging and alerting assumptions.

## 3. Case must list

- ✅ **Vertical, verifiable tasks with acceptance criteria and explicit dependencies.** Every task has both. #3 ("profile only") followed by #8 (per-entity widening) is a genuine vertical slice. The caveat is that #2–#6 are split by component (endpoint, worker, download, email, UI), and the first end-to-end increment only arrives at #7, which is labelled "walking skeleton" but is assembled last.
- ✅ **Critical path named, parallel work called out.** A named path and a Parallelizable section are present; the co-critical branch flaw is noted above.
- ✅ **Risks and decision points surfaced.** Async vs. sync, link model and TTL, re-authentication, DSAR/compliance scope, the failure-notice decision, memory and database load, and retention are all covered.
- ✅ **Codebase unknowns flagged as confirm-items.** Runner, storage, mailer and flag mechanism go through #1, and "Unconfirmed infrastructure" repeats it. Auth is covered only by reference to the assumptions list.

## 4. Case must-not list

- ✅ **No spec or implementation code.** There is no code. The task bodies lean toward spec territory (six named button states, a status state machine, specific HTTP codes, an a11y requirement), but these are framed as acceptance criteria.
- ✅ **Never leaves the system broken between steps.** The feature is dark behind a flag from #2, and each task is additive.
- ✅ **No core infrastructure asserted without a flag.** The core pieces are flagged. The secondary ones (staging, alerting, scheduler) are a ⚠️ under guardrails, not a violation of the core intent.
- ✅ **No ceremony padding.** #7 (milestone) and #10 (scale check) are verification-only and borderline. #7 is the first true end-to-end check and #10 backs a stated risk, so I don't call either a violation.

There are no ❌ marks, but there are four ⚠️ marks: a wrong co-critical chain that contradicts the plan's own dependencies, a cut line that breaks #12's dependency on #10, unflagged secondary infrastructure assumptions, and evidence that the self-challenge missed these.

VERDICT: WEAK