# promptsmith — launch plan

> **Renamed.** This project was `promptsmith` until 2026-09-18 and is now `guildproof`.
> This document is a record written under the old name, so it keeps the old name and the
> old `/promptsmith:*` commands. The current commands are `/guildproof:*`.

Status: **Phase 0 complete 2026-07-22. Phases 1-4 not started as of 2026-09-02.** Sequenced.
Nothing in Phase 1+ ships until Phase 0 is done — promoting a repo that looks mid-build burns
the one first impression each channel gives you.

Baseline at time of writing (2026-07-21): public repo, 2 stars, 0 topics, no release notes,
`v0.2.0` tag with 6 unreleased features on `main`.

**Where it actually stands, 2026-09-02.** `v0.3.0` shipped 2026-07-22 with topics, description,
homepage, and a real GitHub Release. Then nothing: no awesome-list PR has ever been opened
(`gh search prs --author emtcmca` returns two PRs, both to `anthropics/claude-for-legal`), no
article, no Show HN. Still 2 stars. Six weeks of the plan being written and not run. The blocker
was never readiness.

**What changed under the plan.** `promptsmith-skills` did not exist when this was written — it
was built 2026-07-26 as a generated distribution mirror, because `npx skills add` only indexes
`skills/<name>/SKILL.md` and this repo's `agents/` and `commands/` are invisible to it. There
are now two products with two audiences and two channels, so Phase 1 splits (see below).

---

## The positioning problem (read first)

There are hundreds of "prompt improver" repos. Almost none of them can answer *"how do you know
it works?"* promptsmith can, and that is the only durable wedge:

- **37 eval cases, 15 logged runs, 6 known-bad calibration fixtures**, plus an independent judge
  on high-stakes routes. (Counted on `main` 2026-09-02, not recalled. The original entry here
  said 27 cases and 14 runs; both were true when written and went stale by standing still, which
  is the exact defect a reviewer catches first.)
- **A red-team pass** (13 findings) with a threat model in `docs/SECURITY.md`.
- **An honesty floor** enforced across 100% of gallery agents — no fabricated facts, citations,
  or MCP servers.
- **A live 7-agent orchestration run** where the verifier caught a HIGH over-serialization
  defect and *halted synthesis* instead of shipping it (`evals/runs/2026-06-25-2101-*`).

So the pitch is never "I made a prompt tool." It is **"I built an eval harness for prompt
scaffolding, and here is what it caught."** The tool is the artifact; the receipts are the story.

Corollary lesson from `transparent-confidence`: do not make adoption or traction claims. There
is no traction yet. Claim only what is measured.

### Wording rule (decided 2026-07-21)

promptsmith **is not** an eval harness; it is a prompt & context engineering toolkit that **has**
one. Getting this wrong is a self-inflicted wound: a developer who installs expecting to eval
*their* prompts and finds four slash commands has been misled, and a product whose entire pitch is
"we don't make unsubstantiated claims" cannot open with one.

- **Product surfaces** (README top-line, `plugin.json`, repo description, awesome-list entries)
  → **"eval-backed."** Never "is an eval harness."
- **Story surfaces** (article, HN first comment, LinkedIn, social) → lead with the eval harness at
  full strength. *"Most prompt tools can't answer 'how do you know it works?' So I built the eval
  harness first."* True as narrative, and it is the whole thesis.

**Updated 2026-07-21 — grade mode shipped (as `/lens --grade`), so the line moves.** A user can now
run their own prompt through a scored rubric and compare two versions with regressions named. On
product surfaces you may now say promptsmith **grades prompts against a rubric** and is
**eval-backed**, because both are literally true. *(Grading was briefly a standalone `/grade`
command; merged into `/lens --grade` the same day, pre-promotion, after two launch reviews flagged
the lens/grade overlap. Command surface is four.)*

Still do not say it *is* an eval harness, flatly. `evals/` (the 37-case regression suite with
known-bad calibration) tests promptsmith; `/lens --grade` scores the user's prompts. They are
related by method, not identical, and a reader who installs expecting the former gets the latter.
The honest strong claim:

> The same score → change → re-score → keep-only-what-didn't-regress loop promptsmith runs on
> itself, pointed at your prompts.

That sentence is defensible line by line, and it is stronger than the overclaim would have been.

---

## Phase 0 — ship-readiness (blocking)

No promotion until every box is checked. Order revised 2026-07-21 after three adversarial audits;
the audits are folded in as steps 2–3 because fixing files after an eval run invalidates the run.

```
1. clean-install smoke test   ← gates everything                     ✅ done 2026-07-21
2. delivery shell
   2a. functional  (paths, agent descriptions, phantom agents)       ✅ done 2026-07-21
   2b. docs + metadata (GIF, Option B, plugin.json, doc drift)       ✅ done 2026-07-21
3. security findings          (3 HIGH, 5 MED)                        ✅ done 2026-07-21
4. user-facing eval loop      (/lens --grade)                        ✅ done 2026-07-21
5. new eval cases             (27→37 cases, 3→6 fixtures)            ✅ done 2026-07-21
6. full suite re-run          → v0.3.0 → promote          ✅ SUITE GREEN 2026-07-21
7. clean-install re-verify    ✅ PASS 2026-07-21 — plugin.json bumped to 0.3.0
```

**Phase 0 complete.** All seven steps done. Clean-install re-verify confirmed every
`${CLAUDE_PLUGIN_ROOT}` path resolves from a non-repo cwd, all 20 agents load with descriptions,
no phantom agents, four commands advertised, twelve lenses present, manifest bumped to 0.3.0.
Next: merge to main, tag v0.3.0, cut the GitHub Release — *then* Phase 1 promotion (awesome-list
PRs), Phase 2 (article), Phase 3 (Show HN).

**Step 6 done — suite green.** All 37 cases run blind: **36 PASS · 1 WEAK (fixed) · 0 FAIL**,
calibration **6/6 known-bad correctly FAILED**. Full record: `evals/runs/2026-07-21-post-adversarial-pass.md`.
Only step 7 (clean-install re-verify) remains before the tag. Promotion (awesome-list PRs, article,
HN) stays gated behind the tag.

Worth keeping for the article: the harness's first real outing caught a defect in its own fixture
and a defect in its own methodology *before* it caught anything in the product, and two subagents
reported their own contamination unprompted. That is what a working eval loop looks like from the
inside, and it is a better story than a clean green run.

**What step 1 changed about the plan.** The smoke test found a defect neither audit caught: all 20
gallery agents lacked a `description`, the one frontmatter field a host uses to auto-select an
agent by task context. The gallery — the marquee feature in the README and `plugin.json` — could
not be invoked automatically. Worth noting for the launch story: this was invisible to code
review and visible in 30 seconds from a live agent roster. **Install it before you market it.**

Step 1 runs first because items in step 2 are unknowable without it: if `lenses/` and `templates/`
genuinely don't resolve at runtime, that is an architecture fix, not a doc edit. Step 7 repeats it
because every step in between touches files the installer copies.

- [x] **Commit the README restructure + demo GIF.** The GIF is the single highest-leverage asset
      — most visitors decide in 5 seconds, above the fold. It was referenced by the README while
      untracked, so the hero image was broken on GitHub the whole time.
- [x] **Ship the proof asset — done 2026-07-22.** The "why download this?" gap the GTM/cold-user
      audits flagged. Built as the **prompt delta** (`proof-prompt-delta.png/.gif`): one-line
      request → the fleshed prompt promptsmith hands back, each added line tagged in the margin
      with the decision the one-liner left unstated (retryable-only, jitter, the double-charge
      prohibition, the honesty-floor open question). Answer-vs-answer **code delta**
      (`proof-code-delta.png/.gif`) kept for a dev audience in a README `<details>`. README section
      retitled "What you actually get"; both generators committed (`make-prompt-delta.py`,
      `make-code-delta.py`) so the assets are reproducible. Original design was answer-first;
      switched to prompt-first after a target-reader review found the code-only cut didn't show
      the product.
- [x] **Re-run the full eval suite — done 2026-07-21.** 36 PASS · 1 WEAK (fixed) · 0 FAIL;
      6/6 known-bad fixtures correctly FAILED. Scorecard: `evals/runs/2026-07-21-post-adversarial-pass.md`.
- [x] **Cut `v0.3.0` — done 2026-07-21.** `plugin.json` bumped, tag pushed, GitHub Release
      published with real notes (`--latest`, not a draft).
- [x] **GitHub repo metadata — done 2026-07-21.** Topics, description (now names `/orchestrate`),
      and homepage all set:
      - Topics: `claude-code`, `claude-code-plugin`, `prompt-engineering`, `ai-agents`,
        `agent-orchestration`, `llm`, `anthropic`, `context-engineering`, `subagents`
      - Description: add `/orchestrate` (current one predates Layer 2)
      - Homepage URL: point at the README anchor or erictetzlaff.com
- [x] **Reconcile counts** — done 2026-07-21 and verified against `ls`: 20 agents · 12 lenses ·
      27 cases · 4 commands. (Superseded note follows.) Original entry: lens count changed
      (12 now) and drifted counts are exactly what a reviewer catches first.

---

## Phase 1 — evergreen distribution (highest ROI, zero cost)

Awesome-list PRs keep delivering traffic for years. Do these before any post — a post drives one
spike; a list entry compounds. **Stagger them** (2–3 days apart); simultaneous identical PRs
across every list reads as spam to maintainers who watch each other.

**Two products, two tracks.** An awesome-claude-code entry sends Claude Code users to the
plugin; a skills-list entry sends everyone else to the mirror. Sending either audience to the
wrong repo wastes the click, which is what the repos did to each other until 2026-09-02 — the
plugin README had no mention of the mirror, so every Codex, Copilot, and Cursor visitor hit a
Claude-Code-only install section and bounced. Fixed; the cross-link is Option C.

Track A — **promptsmith** (the plugin):

1. `hesreallyhim/awesome-claude-code` — the canonical one. Highest traffic.
2. Claude Code plugin marketplace registries (community-maintained plugin indexes).
3. `e2b-dev/awesome-ai-agents` — orchestration/gallery angle.
4. `promptslab/Awesome-Prompt-Engineering` or equivalent.

Track B — **promptsmith-skills** (the mirror):

1. `ComposioHQ/awesome-claude-skills` — already cited as a source in `planned-features.md`.
2. General agent-skill lists that are not Claude-specific — the mirror's whole argument is that
   it is not Claude-specific, and the plugin cannot make that argument.

### skills.sh — a channel this plan predates

The mirror is already listed (**16 installs as of 2026-09-02**, which is roughly one full-pack
install plus a few singles — that is the verification install, not adoption; do not cite it as
traction). Two mechanics worth knowing:

- **Listing is automatic and telemetry-driven.** There is no submission form. The directory
  registers a skill when someone *installs* it, so a repo can be perfectly published and still be
  invisible. Publishing is not distribution.
- **Ranking is install count over a rolling 8-week window**, and `find-skills` — the
  highest-installed skill in the directory — is the discovery path. It matches on the
  `description` field. That is why `build-skills.mjs` overrides upstream descriptions rather
  than copying them: same prompt body, different shop window. A weak description is a
  distribution bug, not a documentation nit.

The 8-week window means installs decay. Time the awesome-list PRs and the article to land inside
one window rather than spread across three.

### Track A — SUBMITTED 2026-09-02

[`hesreallyhim/awesome-claude-code` issue #2715](https://github.com/hesreallyhim/awesome-claude-code/issues/2715).
Bot validation **passed** the same minute; labels went `validation-pending` → `validation-passed`,
all fields parsed, license auto-detected as Apache-2.0. Awaiting maintainer review, which has no
SLA. Nothing further to do; do not follow up more than once.

**That list does not take PRs, and this is the finding to carry forward.** Their CONTRIBUTING:
"Do not open a PR. Just fill out the form," and, in a warning block, "It is **not** possible to
submit a resource recommendation using the `gh` CLI." Opening a PR risks "being restricted from
interacting with this repository." Recommendations must also be created by human beings. So the
agent-side work is the packet; Eric submits it in the web UI.

Submission form:
`https://github.com/hesreallyhim/awesome-claude-code/issues/new?template=recommend-resource.yml`

**The exact values submitted** (reusable if the issue is ever closed and refiled):

| Field | Value |
|---|---|
| Title | `[Resource]: promptsmith` (the form PREFILLS `[Resource]: <name of your resource>` — replace the whole line, do not append) |
| Display Name | `promptsmith` |
| Category | `Agent Orchestration` |
| Link | `https://github.com/emtcmca/promptsmith` |
| Author Name | `Eric Tetzlaff` |
| Author Link | `https://github.com/emtcmca` |

Description, 478 chars, 3 sentences, every number ground-truthed on `main` that day
(4 commands, 12 lenses, 20 agents, 37 cases, 6 known-bad fixtures):

> A Claude Code plugin for prompt and context engineering. /sharpen turns a rough request into a
> complete prompt, /forge-agent authors reusable agent system prompts, /lens reviews an artifact
> through twelve expert lenses or grades a prompt against a rubric, and /orchestrate dispatches a
> twenty-agent gallery across a multi-domain request. It makes no model calls, has no
> dependencies, and ships a 37-case eval suite including six deliberately-broken fixtures the
> suite must fail.

Checklist: check the first five. **The sixth is a trap** — it reads "By checking this box, I admit
that I am not reading any of these statements." Leave it unchecked.

**Category was the judgment call.** `Agent Orchestration` holds autonomous loops and
plan-work-review harnesses (Ralph variants, gstack, RIPER), which promptsmith is not. It fits
because `/orchestrate` dispatches the gallery and `/forge-agent` authors agent system prompts —
the same machinery as their accepted "Harness" entry. There is no prompt-engineering category, and
`Skills` is worse: that category is skill bundles and promptsmith ships two. A maintainer can
recategorize; miscategorization is far less fatal than ineligibility.

**Pre-flight, all verified 2026-09-02:** not already listed (checked all 162 rows of
`THE_RESOURCES_TABLE_NEW.csv`); no prompt or context-engineering toolkit anywhere on the list;
first commit 2026-06-24, 70 days against their 14-day minimum; Apache-2.0 detected via the API;
repo and author links both 200; description inside 10–500 chars and ≤3 sentences, no emoji, no
second person.

**Two honest caveats recorded at submission time.** The 90 commits on `main` fall on only six
distinct days — bursts in June and July, then nothing until the day of submission. The rule is
satisfied and that day's commits were substantive, but the graph does not read as steady
development and that is a plausible silent close. And their CONTRIBUTING says outright: "If
'getting on the list' is any part of a promotional strategy for your project, you should be
prepared to have a backup plan," with "no guarantee is made as to whether you will receive a
response." 53k stars, 162 curated entries, against 2 stars here. Silence is the expected outcome.

**`promptsmith-skills` is ineligible for this list**, and that is settled rather than untried: a
required checkbox asserts "This resource is specific to Claude Code," and the mirror is
deliberately host-agnostic. Track B is its only path.

**Do not edit issue #2715.** The bot re-runs validation on every edit. There is no upside — it
parsed correctly — and a re-run is noise in a maintainer's feed.

### For the lists that DO take PRs (Track B and beyond)

Read `CONTRIBUTING.md` first and confirm the submission mechanism before writing anything; Track A
proves the mechanism is not guessable. Where it is a PR: match the existing entry format exactly,
one entry per PR, alphabetical placement, one-line description under whatever char limit they
enforce, no marketing adjectives. A malformed entry is a silent close.

Draft entry line (tune per list):

> **[promptsmith](https://github.com/emtcmca/promptsmith)** — Prompt & context engineering
> commands for Claude Code: sharpen rough requests, forge reusable agent system prompts, review
> through expert lenses, and orchestrate a 20-agent gallery. Zero deps, no API keys, eval-backed.

---

## Phase 2 — the article (the real asset)

One well-built technical post that the HN submission and every social post points back to.
Write it once; reuse it everywhere.

**Do not write "I built a prompt tool."** Write the teardown. Candidate angles, best first:

1. **"I ran 7 AI agents on one feature. They contradicted each other — here's the log."**
   The case-17 run is genuinely interesting *independent of promptsmith*. All seven agents agreed
   the public payload should be an "allow-list DTO." The allow-list was written at the **column**
   level, and one of those columns was a `widgets` JSONB blob that shipped whole to anonymous
   callers — widget config routinely carries data-source connection strings, internal IDs, and
   owner-scoped filter values. The producer missed it. The security slice missed it. The contract
   missed it. An independent `verifier`, handed only the artifact and the claimed contract and
   told to assume it was wrong, caught it, returned FAIL/BLOCKING, and **halted synthesis** rather
   than emitting a plan that read as finished.

   The general finding, and it is not specific to this tool: **agreement at one granularity hides
   a gap at another.** Everyone said "allow-list DTO"; nobody owned filtering *inside* `widgets`.
   The seam was not missing from the conversation, it was hiding inside a term the whole room had
   already agreed on. That is a real multi-agent failure mode and it is the reason to read the
   log. The tool is the answer at the end, not the premise.
   Source: `evals/runs/2026-06-25-2101-orchestration-case17-live-7agent.md`.

   > **Do not tell the `expires_at` version of this story.** Until 2026-09-02 this entry said
   > three agents each assumed another owned `expires_at` enforcement, so nobody enforced it. The
   > run log does not support that. `expires_at` was a three-way disagreement about whether expiry
   > should exist at all — `feature-spec`: none in v1; `data-modeler`: optional, `NULL = never`;
   > `security-review`: non-negotiable — the coordinator resolved it to a mandatory server-set 30d
   > default, and the seam table assigns enforcement to the backend public-read query with the
   > owner column marked `Y`. It was caught and assigned, which is the opposite of unowned.
   > Corrected against the run file. An article premise that misdescribes the log it links is the
   > one paragraph a hostile reader will actually check.
2. **"How do you eval a prompt tool that makes zero model calls?"** — the known-bad fixtures and
   independent-judge design. Narrow, credible, low bullshit surface.
3. **"An honesty floor for agent system prompts"** — the no-fabrication invariant and the
   audit that found 8 of 20 agents violating it. Admitting the bug is the credibility.

Angle 1 has the widest reach; angle 2 earns the most respect from the people who matter.
Recommendation: **write angle 1, and make angle 2 the second half.**

Publish to dev.to (canonical), cross-post to the personal blog with `rel=canonical`.

**Rules:** show real logged output, not paraphrase. Link the actual run files. Include the
failure. No screenshots of prose — code blocks. No "revolutionary/game-changing/leverage."

---

## Phase 3 — Show HN

Submit **after** the article and release are live, so the repo survives the click-through.

- Title: `Show HN: Promptsmith – prompt engineering commands for Claude Code, with an eval harness`
- Tue–Thu, ~8–10am ET.
- First comment (post it yourself, immediately): what it is, what it explicitly does *not* do
  (no model calls, no API keys, static-copy install by design), the honest limitation
  (`/orchestrate` is Claude-Code-only), and a direct link to the evals directory.
- Expect hostility toward "another AI prompt tool." The defense is not argument — it is the
  eval harness and the logged failure. Lead the first comment with it.
- Answer every comment for the first 3 hours. Never argue; concede real points publicly.

---

## Phase 4 — owned channels

- **LinkedIn** — the warmest audience. Same story as the article, compressed. Link the repo.
- **X / Bluesky** — thread of the case-17 conflict, one screenshot per beat.
- **Reddit** — `r/ClaudeAI`, `r/ClaudeCode`. Read each sub's self-promo rule first; several ban
  it outright or require a flair. Contribute before posting.
- **Anthropic Discord / community channels** — plugin-sharing threads if they exist.

---

## What success looks like (set expectations honestly)

A good outcome for a niche dev tool with no existing audience is **tens of stars and a handful
of real users**, not hundreds. The metric that actually matters: **one external issue or PR
filed by someone Eric does not know.** That is the signal `transparent-confidence` never got
(2 stars, 6 self-seeded issues, downloads trending down). Track that, not stars.

Do not cite promptsmith adoption numbers in a resume, profile, or pitch until that signal exists.

---

## Sequence summary

```
Phase 0 (blocking)  →  Phase 1 (staggered, evergreen)  →  Phase 2 (article)  →  Phase 3 (HN)  →  Phase 4
ship-ready             awesome lists                      dev.to                Show HN         LinkedIn/X/Reddit
```
