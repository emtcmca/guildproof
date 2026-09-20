---
id: "17"
route: orchestration
status: active
latest-run: PASS (live, 7-agent build + independent verifier) — runs/2026-06-25-2101-orchestration-case17-live-7agent.md
expected-agents: [feature-spec, data-modeler, security-review, backend-builder, frontend-builder, test-author, docs-writer]
tests: multi-agent decomposition, seam ownership, conflict resolution, single-voice synthesis, executed Step 6.5 verify
---

> **Runnable as of the Layer 2 coordinator v0** (`/guildproof:orchestrate`). Latest live run
> (2026-06-25): **7 specialist slices dispatched as real subagents + 1 independent verifier**;
> caught a three-way expiry conflict, assigned the unowned `expires_at`-enforcement seam, and the
> verifier caught a HIGH `widgets` over-serialization defect — synthesis **halted and escalated**
> per Step 6.5. **PASSED.** This case is the orchestration regression anchor.

## Input

```
Add public, read-only shareable links to user dashboards.
```

A genuinely multi-domain build request: it crosses spec, data, security, API, UI, tests, docs.

## Must (when a coordinator runs it)

- **Decompose** into slices that cover the domains with **no overlap** — the "public link =
  data-exposure" concern is stated **once**, not re-raised by three agents.
- **Assign every seam an owner.** Specifically: `expires_at` is *stored* by data-modeler but
  enforcement must be explicitly owned (the API/read slice), not left as "someone checks it."
- **Resolve cross-agent conflicts before output** — e.g. feature-spec's "no expiry in the MVP
  cut line" vs. security-review's "expiry is mandatory." The coordinator decides; it doesn't
  paste both and move on.
- **Synthesize to one coherent deliverable in one voice** — a plan a person can act on, not a
  concatenation of seven agent outputs in seven formats.
- **Completeness:** spec, schema, security posture, endpoint contract, UI, tests, and docs are
  each represented or explicitly deferred with a reason.
- **Coverage-gap honesty:** any slice that no existing agent covers is **logged as an unmet
  gap** (what was asked, why nothing fits) and surfaced — not silently dropped or fake-covered.
  Recurring gaps become the spec for a new forged agent.

## Must not

- Emit raw concatenated agent outputs (a pile is not a deliverable).
- Leave any seam unowned or any cross-agent conflict unresolved.
- Silently drop a domain that the request clearly implies.

## Reference

Manual stand-in-coordinator run of this exact query (the seams it exposed) is documented in
`ROADMAP.md` → Layer 2 → "Worked example: shareable dashboard links."
