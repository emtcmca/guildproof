**Scored against `agents/debugger.md`, which I read.** Its Output contract has four sections: Failure, Reproduction, Hypotheses, Most likely + why. The honesty floor forbids a fix before a cause and forbids "try this and see" lists.

## 1. Structural invariants (GALLERY AGENT)

- ✅ **Contract sections present.** All four appear, in order. The Hypotheses each have cause, why plausible, and probe, plus a confidence tag: "**H1. Replication lag: a read-your-writes violation. Confidence: medium, lead theory.**"
- ⚠️ **Section for section.** The output adds a fifth section, "Observations that would sharpen the ranking", which is not in the contract. It is close to the agent's "When unsure" behaviour but is a departure from the contract. This is not a hard fail.
- ✅ **Voice detectable.** Calm and systematic: "I don't have a stack trace, logs, the fetch library... Everything below is ranked from priors, not evidence." "I can't run anything, so this is what to build."
- ✅ **Self-challenge done.** It has an explicit block: "Does the lead explain all the evidence? ... This is the weak spot... What would prove me wrong: A stale read where the serving replica's replay LSN was already past the write LSN."
- ✅ **Honesty floor, attribution.** "roughly 1 of 5 saves (your estimate, unverified)". It invents no logs or versions, and it declares what it lacks.

## 2. Quality dimensions

- ⚠️ **Contract honored and guardrails honored (hard gate).** No invented facts and no fix is proposed: "I'm not proposing a fix yet." Two overclaims remain:
  - "A 20% rate rules out a deterministic logic error." This is false. A deterministic bug gated on a data or state condition, such as which field was edited, also produces partial rates.
  - "If they persist, H1 is dead." Pinning one GET to the primary only shows that replica lag is not the sole cause.
  Neither is a fabricated fact, so they are ⚠️ rather than ❌.
- ⚠️ **Ranking discipline (likelihood × ease-of-test).** H2 is labelled "cheapest to test" but ranked second. H1 needs LSN instrumentation on Postgres, and it leads "because the read replica is the stack detail most tied to..." That is a likelihood argument, not the stated combined metric.
- ✅ **In voice.** It reads as the persona and not as a generic assistant.
- ✅ **Probes distinguish.** Probe 0 splits server from client: "Stale in the body means the server side, H1 to H5. Fresh body but stale UI means the client, H2." The per-hypothesis probes are discriminating:
  - H1: replay LSN against write LSN.
  - H3: `Age` and cache flags.
  - H5: instance ID plus cache hit.

## 3. This case's must list

- ✅ **Full contract present.** All four sections are there. Failure includes expected, actual and trigger.
- ⚠️ → ✅ **Ranked by likelihood × ease, probes distinguish.** The probes clearly separate causes. The ease-weighting is muddled, as noted above, but the mechanism is met.
- ❌ **Surface the three strong candidates.** Two are covered. Client cache not invalidated appears in H2: "the mutation doesn't invalidate the right cache key". Replica lag is H1. **Optimistic UI not reconciled with server response is never named as a hypothesis.** The word "optimistic" does not appear. The observations list asks "whether it refetches after save or uses the PUT response" but never asks whether the UI applies optimistic updates. H2's "overwrite the fresh state" race gets near the mechanism, but the candidate is not surfaced or probed as its own cause.

## 4. This case's must-not list

- ✅ **No fix before cause.** It says "Changing the trigger... would hide the bug without fixing it" and gives no fix.
- ✅ **No generic "try this and see" list.** Probes are tied to hypotheses. "Turn off background refetch" is borderline, but it is paired with a discriminating observation.

## Verdict

There is one ❌, on a case-specific must item. Under the rubric, any ❌ means FAIL. The two overclaims and the extra section are ⚠️ and would not fail on their own. Without the optimistic-UI omission this would be WEAK.

VERDICT: FAIL