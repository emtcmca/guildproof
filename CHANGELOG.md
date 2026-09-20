# Changelog

All notable changes to guildproof. This project follows [Semantic Versioning](https://semver.org/).

Entries below are taken from the annotated tags and the commit history on `main`, not from
memory. Counts are stated on the ref they were taken on, because counts in this project have
drifted in both directions more than once.

## [0.4.0] — unreleased

**Renamed from `promptsmith` to `guildproof`.** Both GitHub repositories were renamed on
2026-09-19; the old URLs redirect, so existing links keep working. Commands are now
`/guildproof:*`. Lenses and agents you created under the old paths are still found —
`~/.claude/promptsmith-lenses/` and `~/.claude/promptsmith-agents/` are read as a fallback, so
nothing you made is orphaned. Only the new paths are written.

The name changed because at least nine other projects called PromptSmith exist, including a
prompt rewriter for a coding agent on the same install channel.

### Added

- **Cross-model eval harness** (`evals/harness/`). Runs one artifact to pinned models across
  three vendors through three isolated transports — `claude -p`, `codex exec`, and the Gemini
  REST API. Every model id is pinned; no aliases and no CLI defaults, because an alias silently
  changes what a published number was measured on. `--check` reads your machine and prints how
  to fix each target it cannot run. `--dry-run` shows every call it would make and spends
  nothing. Targets your machine cannot run are reported as UNMEASURED, never as passing.
- **The cross-model verifier result** (`evals/runs/2026-09-20-crossmodel-verifier.md`). 12
  models, 3 vendors, 48 cells, 288 judged cells, two blinded judges per target, Cohen's
  κ 0.97. Unprompted, **0 of 48 scorings** said whether the work was blocked and **0 of 48**
  stated whether the review was independent; with the verifier prompt, 48 of 48 did. The gap
  shows no trend with model capability in any of the three families. The run doc publishes the
  four results that cut against guildproof with the same prominence as the wins.
- **B4 known-bad release gate** (`evals/harness/run-knownbad.py`,
  `evals/runs/2026-09-20-b4-knownbad.md`). A repeatable, exit-coded gate that grades the six
  known-bad fixtures blind and fails unless all six are graded FAIL. Each fixture is stripped
  of its own answer before a judge sees it, and the strip is asserted rather than assumed. Ships
  with a positive control, because six fixtures all failing is also what a judge stuck on FAIL
  would produce.
- **Benchmark coverage table** (`evals/benchmarks/README.md`) stating, per feature, which
  claims in this repo carry measurement and which do not. It is deliberately uncomfortable in
  places. Specs for the two unrun benchmarks (`/orchestrate`, `/forge-agent`) are there too.
- **Proof table in the README**, above the fold, with every figure verified programmatically
  against the committed scorecards before it was published.
- **`AGENTS.md`** — machine-facing orientation for coding agents arriving at the repo.
- **Eval case 41** — an agent-verifier case built on a planted cross-tenant field leak.
- **CI** (`.github/workflows/fresh-machine.yml`). Runs the harness's free commands on a genuinely
  fresh machine across Linux, macOS and Windows, after first asserting that no vendor CLI and no
  API key is present — otherwise a green result would only mean it worked somewhere already set
  up. Also asserts, from outside the runner, that no known-bad fixture leaks its answer.
- **B4 suite runner** (`evals/harness/run-suite.py`, `evals/runs/2026-09-20-b4-suite.md`). Runs the
  numbered cases unattended, with the producer and the judge as separate OS processes for every
  case. Its most useful output was not the verdicts: reaching a trustworthy result required fixing
  five transport bugs and four defects in `evals/rubric.md` where the ruler contradicted the
  shipped contract. One case went FAIL to PASS on a byte-identical output, re-judged only.
- **`scripts/validate.mjs`** — zero-dependency structure check: counts on disk against counts
  claimed in prose, required frontmatter, no phantom agent or lens references, no dead command
  namespace. Carries a selftest against deliberately broken fixtures, so the check itself can
  be shown to fail.

### Changed

- `plugin.json` and `marketplace.json` now lead with the verifier and the halt, which is the
  part of this toolkit that carries measurement, rather than with the size of the gallery.
- Eval suite 37 → 38 cases.
- `docs/USING-PROMPTSMITH.md` → `docs/USING-GUILDPROOF.md`.

### Fixed

- Four false claims in the README about the companion skills package: the skill count, how many
  gallery specialists are published, and two statements that some agents were left out. All
  twenty gallery specialists ship, plus the engine and a grading skill, 22 in total.
- The hero GIF's alt text called it a live terminal run. It is drawn frame by frame from the
  text of a real run, and now says so.
- The manual-install section said to copy four things above a five-row table.

### Known limits at this version

Stated here rather than left to be discovered:

- The cross-model result rests on **one artifact and one defect class** (a cross-tenant field
  leak). Nothing in it generalises to a race condition, a missing idempotency key, or a broken
  migration. This is the study's biggest weakness.
- **`/sharpen` has never been benchmarked**, and it is the oldest and most central claim here.
- **`/orchestrate` and `/forge-agent` carry no measurement.** Four eval cases and one live
  seven-agent run exist for orchestration; that is a demonstration, not a rate.
- B4's numbered half ran 2026-09-20: 34 of 38 judged, 2 PASS / 24 WEAK / 8 FAIL, with the 4
  `/orchestrate` cases unmeasured by transport. Those verdict counts are a regression gate and
  not a rate. Reaching a trustworthy result required fixing five transport bugs and four defects
  in the rubric itself.
- **k = 2 for the cross-model study and the known-bad gate, but k = 1 for the numbered suite**,
  which is thin for anything in it that reads as a recall miss. Every eval judge is a Claude
  model. Judge choice was measured rather than assumed, but a non-Claude judge would be a
  stronger design and is not yet calibrated.

## [0.3.0] — 2026-07-21

Pre-launch hardening plus grade mode.

- **Security:** 3 HIGH and 5 MEDIUM findings closed — untrusted slice outputs, the agent
  instruction/data boundary, lens shadowing, and the `--fix` intent gate.
- **Works as installed:** `CLAUDE_PLUGIN_ROOT` paths; all 20 gallery agents carry descriptions;
  phantom agents removed.
- **New grade mode:** `/lens --grade` scores a prompt against a rubric, and `--against` compares
  two versions and names regressions.
- **Evals:** 27 → 37 cases, 3 → 6 known-bad fixtures. Full blind run 36 PASS / 1 WEAK (fixed) /
  0 FAIL, with 6 of 6 known-bad fixtures correctly failed.
- Four commands: `/sharpen`, `/forge-agent`, `/lens` (plus `--fix`, `--grade`), `/orchestrate`.

## [0.2.0] — 2026-06-25

Honesty-floor hardening and a focused 20-agent gallery.

- `planner`, `evaluator` and `compliance-reviewer` added; marketing agents split out.
- Counts reconciled across the docs.
- Full-suite eval gate: 26 PASS / 1 WEAK / 0 FAIL.

[0.4.0]: https://github.com/emtcmca/guildproof/compare/v0.3.0...main
[0.3.0]: https://github.com/emtcmca/guildproof/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/emtcmca/guildproof/releases/tag/v0.2.0
