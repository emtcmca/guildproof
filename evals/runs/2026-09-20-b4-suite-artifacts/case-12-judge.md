## 1. Structural invariants (GALLERY AGENT)

- ✅ **Output matches the agent's Output contract, section for section.** I wasn't given the contract text, so I checked against the case must list. All five sections are present: "## 1. Purpose & trigger", "## 2. Roles", "## 3. Steps", "## 4. Exceptions" and "## 5. Confirm-these".
- ✅ **A Voice is detectable.** The prose is plain and imperative: "Do not try to crack it," "Never link it to the nearest-looking document," and "Stall points I closed in review."

## 2. Quality dimensions

- ⚠️ **Guardrails honored (hard gate: no invented facts).** The output pulls in specifics the case never supplied. It names "BoardPath's document ingestion" and a "Warning Center" (Step 20). It also cites a "0.6 per project notes" gate (Step 17), and no project notes were provided.
  - Most of this is marked ⚑ and hedged, for example "(or equivalent)" and "Confirm it's still current."
  - Step 13 is flat and unflagged: "Amendments are not a separate tier. They take their parent's tier." The tier order in the same step is also unflagged. Both are product-specific behavior, and neither appears under "Product behavior I couldn't verify."
  - That is borderline, not a clear breach, because the system inference is disclosed up front.
- ⚠️ **Self-challenge done.** The closing line claims "Stall points I closed in review… Roles," but the Roles table is internally wrong.
  - It says Reviewer "checks the results, signs off (Steps 16–18)." Steps 16–18 are the status wait, the quality-score read and the extraction spot-check. The Reviewer's actual steps are 21–24.
  - It says Operator "Steps 1–21 except sign-off," but the SOP has 28 steps.
  - The one-person fallback repeats the error: "do the Step 16–18 review at least one business day after Steps 1–15." A solo operator following it would re-review the wrong steps and could skip the independent test key.
  - The steps themselves name the right actor ("Reviewer writes five test questions"), so this is confusing rather than fatal. The check the output claims to have run either did not happen or missed this.
- ⚠️ **Steps are one action each with verification where it counts.** Most steps are concrete and carry a "Verify:" line. Several slip:
  - Step 25 both sets status to ready and grants client access.
  - Step 12 fills the parent column and then hunts for gaps.
  - Step 1's verification ("legal name matches page 1 of the Declaration once you have it") can't be run at that step.
  - Step 4 sets a follow-up date, but no step says what to do when that date arrives.
- ✅ **In voice.** It reads as an operations practitioner, not a generic assistant.
- ✅ **Exceptions are real failure modes.** E1 is a corrupt file. E3 is a stuck ingestion. E7 is the confident answer to the unanswerable question ("This is a blocker"). E9 is the wrong association, with the check being "the recording number". E10 covers conflicting versions ("Do not pick one"). Each has a concrete action.

## 3. This case's must list

- ✅ **Full contract.** Purpose & trigger (with a done-state), Roles, 28 numbered steps with "Verify:" lines, Exceptions E1–E15 and Confirm-these are all present.
- ✅ **Exceptions cover the named failure modes.** Missing docs are E4/E5. Illegible scans are E2 ("cleaner scan… 300 dpi or better ⚑"). Duplicates are E10. Wrong association is E9.
- ✅ **Placeholders for unsupplied tools, approvers and thresholds.** Tools appear as "[system name ⚑]", "[path ⚑]" and "[tracker ⚑]". People appear as "[name]". Thresholds appear as "[3 business days ⚑]" and "[30 minutes ⚑]". The exception is the 0.6 gate, a concrete value the user never supplied. It is disclosed under "Thresholds I assumed or carried over," which is why I am not scoring it ❌, but it is the weakest point on this item.

## 4. This case's must-not list

- ✅ **No vague verbs.** I found no bare "handle the documents" or "process the files." The actions are specific, such as "Copy each file from `original` into `working`" and "Split any combined PDF."
- ✅ **No invented system or approver stated as known.** No approver is named; all four roles are "[name]". The system inference (BoardPath) is labeled as inferred in the opening bullets and again under Confirm-these, and the steps use "[system name ⚑]". The unflagged product behavior in Step 13 is the residual risk, scored above.

## Summary

The output is complete and strong on contract, exceptions and placeholders. It has no ❌, but four marks are ⚠️ and each has evidence above. Two matter most: the Roles table and the solo-operator fallback point at the wrong steps while the output claims the Roles stall was closed, and Step 13 states unverified product behavior as procedure.

VERDICT: WEAK