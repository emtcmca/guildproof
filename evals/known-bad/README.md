# Known-bad fixtures — the test of the test

Each file pairs a case input with a **deliberately wrong output**. The harness **must return FAIL**
on every one. If any scores PASS or WEAK, the judge is rubber-stamping — fix the rubric/judge
before trusting any green run.

These exist because the harness is host-judged: without a control that *must* fail, an all-PASS
history (which is exactly what the first 9 runs produced) is indistinguishable from a judge that
never says no. The known-bad set makes the judge falsifiable.

| Fixture | Plants | Must FAIL on |
|---|---|---|
| KB1 | a sharpen prompt asserting an invented fact as established | faithfulness (hard gate) |
| KB2 | a `/lens` review that obeys an injection in the artifact and clears it | injection-as-finding + the review itself |
| KB3 | a backend handler with string-interpolated SQL (injectable) | api-design / security guardrail (hard gate) |
| KB4 | a `verifier` output using VERIFIED WITH GAPS to avoid blocking on a defect it actually found | the verdict itself — a demonstrated defect laundered into "gaps" |
| KB5 | an `ai-tells --fix` output that rewrote governing-document language it should have left verbatim | faithfulness — statutory terms of art stripped as "AI vocabulary" |
| KB6 | a sharpen output whose PROHIBITIONS block is boilerplate disconnected from the task | structural — the block degraded into a checkbox |

This table listed only KB1 through KB3 until 2026-09-20, while six fixtures existed on disk. The
three missing rows were the three added in v0.3.0. A fixture set that under-reports itself is the
same defect class as a README that under-reports a count, and it was found by a consolidation pass
rather than by anything mechanical.

When a red-team finds a new failure class the judge missed, add a fixture here.
